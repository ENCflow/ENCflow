module m_swi
  ! ============ 土壌雨量指数モジュール(気象庁 3段直列タンク。§49)============
  ! 土砂災害警戒の実務指標「土壌雨量指数」(SWI)をセル別に計算する
  ! 純診断モジュール。どの物理場にも書き込まず、地上雨量 s%pre だけを読む。
  ! 有効化は fn_swi(&list_swi)。無効時は確保・呼び出しゼロ(§0)。
  !
  ! 【モデル】石原・小葉竹(1979)の直列3段タンク(気象庁が全国一律の
  ! 定数で運用する形。岡田ほか 2001, 測候時報 68 / 気象庁解説)。
  ! 各タンクの側方流出 q_k = Σ α・max(S−L, 0) は系外へ、底面浸透
  ! β・S は次段へ(第3タンクは系外)。SWI = S1 + S2 + S3 (mm)。
  ! 定数は全国一律の原式固定(namelist にしない — §19.8)。
  ! 時間積分は陽解法(線形 ODE。安定条件 dt < 2/(α1+α2+β1) ≈ 5.4 h に
  ! 対し dt <= 600 s を init で強制 = 精度・安定とも十分)。
  !
  ! 【純度の契約(§49)】指数を公式定義どおりに保つため:
  !   - 併用可は定率遮断(f_icmodel=1)のみ。s%pre を書き換える貯留型
  !     遮断・積雪や、他の全プロセスモジュールは init で par_stop
  !   - dt > 600 s(気象庁の計算間隔 10 分)は par_stop
  !   - dx,dy /= 1000 m は par_warn(指数はセル面積に依存しないが、
  !     公式の 1km プロダクトと同条件でないことを通知)
  !
  ! 【出力】s%swi(現在値)・s%swimax/swimaxt(期間最大と発生時刻)を
  ! 確保・更新し、m_output が Swi フレームと Swi9999/Swit9999 を自動出力
  ! (f_out スイッチなし = モジュール有効時は常時。Sd/Sw と同じ様式)。
  ! 最大値統計は save 対象外(hmax 系と同じ意図的仕様。§7)。
  !
  ! 【リスタート】タンク貯留 S1,S2,S3 はモデル私有ファイル swi.dat
  ! (RLE 3面。m_gwflow_bucket 契約5)。restore 時に無ければ par_stop。
  ! ==========================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_swi, only : t_list_swi, list_swi_read
  use list_intercept, only : t_list_intercept, list_intercept_read
  use m_parallel, only : is_root, par_info, par_warn, par_stop, dcp, &
                         par_gather_to, par_scatter_cell
  use m_fileio, only : fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  implicit none
  private

  public :: t_swi
  public :: m_swi_init
  public :: m_swi_calc
  public :: m_swi_dispose

  ! タンク定数(石原・小葉竹1979 / 気象庁の全国一律値。原式固定。
  ! 単位: L は mm、α・β は 1/hr)【要文献照合: 岡田ほか2001 測候時報68】
  real, parameter :: swi_l1 = 15.0       ! 第1タンク 第1流出孔高
  real, parameter :: swi_l2 = 60.0       ! 第1タンク 第2流出孔高
  real, parameter :: swi_l3 = 15.0       ! 第2タンク 流出孔高
  real, parameter :: swi_l4 = 15.0       ! 第3タンク 流出孔高
  real, parameter :: swi_a1 = 0.1        ! 第1タンク 第1流出係数
  real, parameter :: swi_a2 = 0.15       ! 第1タンク 第2流出係数
  real, parameter :: swi_a3 = 0.05       ! 第2タンク 流出係数
  real, parameter :: swi_a4 = 0.01       ! 第3タンク 流出係数
  real, parameter :: swi_b1 = 0.12       ! 第1タンク 浸透係数
  real, parameter :: swi_b2 = 0.05       ! 第2タンク 浸透係数
  real, parameter :: swi_b3 = 0.01       ! 第3タンク 浸透係数

  type t_swi
    ! init に早期 return 経路がある型は全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    real :: dth = 0.0                    ! 時間刻み (hr)(前計算)
    real :: pre2mm = 0.0                 ! s%pre (m/s) → 1ステップの雨量 (mm)
    real, allocatable :: s1(:,:)         ! 第1タンク貯留 (mm)(帯確保)
    real, allocatable :: s2(:,:)         ! 第2タンク貯留 (mm)
    real, allocatable :: s3(:,:)         ! 第3タンク貯留 (mm)
  end type

contains


!----------------------------------------------------------------------
! 土壌雨量指数の初期化(排他・時間刻み・解像度の検証と状態の確保)
!----------------------------------------------------------------------
subroutine m_swi_init(si, p, g, s)
  type(t_swi), intent(out) :: si
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s      ! swi/swimax/swimaxt の確保
  type(t_list_swi) :: list
  type(t_list_intercept) :: iclist
  integer :: i, j

  if (len_trim(p%fn_swi) == 0) return

  call list_swi_read(p, list)
  if (list%f_swi == 0) return     ! fn を書いたまま一時無効化する経路

  ! --- 純度の契約(§49): 併用可は定率遮断のみ ---
  ! 指数は「地上雨量そのもの」から定義される。s%pre を書き換える
  ! 貯留型遮断・積雪はもちろん、混同を避けるため他の全プロセス
  ! モジュールとの重ね合わせを禁止する(定率遮断は定常スケーリングで
  ! 意図的な使用を許容)
  if (len_trim(p%fn_precip) == 0) then
    call par_stop("list_swi: 土壌雨量指数には降水(fn_precip)が必要です")
  end if
  if (len_trim(p%fn_gwflow) > 0 .or. len_trim(p%fn_evap) > 0 &
      .or. len_trim(p%fn_snow) > 0 .or. len_trim(p%fn_glacier) > 0 &
      .or. len_trim(p%fn_geomorph) > 0 .or. len_trim(p%fn_wq) > 0 &
      .or. len_trim(p%fn_salt) > 0 .or. len_trim(p%fn_meteo) > 0) then
    call par_stop("list_swi: 土壌雨量指数は他のプロセスモジュールと併用できません" &
                  // "(公式定義の入力は地上雨量そのもの。併用可は定率遮断のみ — §49)")
  end if
  if (len_trim(p%fn_intercept) > 0) then
    call list_intercept_read(p, iclist)
    if (iclist%f_icmodel == 2) then
      call par_stop("list_swi: 貯留型遮断(f_icmodel=2)とは併用できません" &
                    // "(雨量が非定常に減衰し指数の定義から乖離。定率遮断のみ可 — §49)")
    end if
  end if

  ! --- 時間刻み・解像度(§49) ---
  if (p%dt > 600.0) then
    call par_stop("list_swi: 土壌雨量指数は dt <= 600 s(気象庁の計算間隔 10 分)" &
                  // "で計算してください")
  end if
  if (abs(g%dx - 1000.0) > 0.5 .or. abs(g%dy - 1000.0) > 0.5) then
    call par_warn("swi: dx,dy が 1km ではありません(指数はセル面積に依存しない" &
                  // "ため計算は有効ですが、気象庁の 1km プロダクトと同条件では" &
                  // "ありません — §49)")
  end if

  if (any(list%swi0 < 0.0)) call par_stop("list_swi: swi0 must be >= 0")

  ! --- 状態の確保と初期値(海セル・無効セルには置かない) ---
  allocate(si%s1(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(si%s2(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(si%s3(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%swi(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%swimax(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%swimaxt(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (any(list%swi0 > 0.0)) then
    ! ゾーン2 = x/sw は全域が使える(帯行 jsh:jeh は全域の有効行)
    do j = dcp%jsh, dcp%jeh
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        si%s1(i,j) = list%swi0(1)
        si%s2(i,j) = list%swi0(2)
        si%s3(i,j) = list%swi0(3)
        s%swi(i,j) = list%swi0(1) + list%swi0(2) + list%swi0(3)
      end do
    end do
  end if

  si%dth = p%dt / 3600.0                 ! s → hr
  si%pre2mm = 1000.0 * p%dt              ! m/s → mm/step

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(p, g, si, s)

  si%enabled = .true.
  si%initialized = .true.
  call par_info("soil water index (JMA 3-tank) enabled")
end subroutine


!----------------------------------------------------------------------
! 1ステップの更新(毎ステップ。run_main が遮断適用後に呼ぶ)
!   入力は地上雨量 s%pre のみ。書き込みは自セル・私有タンクと
!   s%swi/swimax/swimaxt のみ(純診断。collective なし)
!----------------------------------------------------------------------
subroutine m_swi_calc(si, p, g, s)
  type(t_swi), intent(inout) :: si
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: s1, s2, s3, q1, q2, q3, b1, b2, b3

  if (.not. si%enabled) return

  !$omp parallel do schedule(static) private(i, j, s1, s2, s3, q1, q2, q3, b1, b2, b3)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      s1 = si%s1(i,j) + s%pre(i,j) * si%pre2mm       ! 降雨は第1タンクへ (mm)
      s2 = si%s2(i,j)
      s3 = si%s3(i,j)
      ! 側方流出(系外)と底面浸透(次段へ)。陽解法(現在貯留から評価)
      q1 = swi_a1 * max(s1 - swi_l1, 0.0) + swi_a2 * max(s1 - swi_l2, 0.0)
      b1 = swi_b1 * s1
      q2 = swi_a3 * max(s2 - swi_l3, 0.0)
      b2 = swi_b2 * s2
      q3 = swi_a4 * max(s3 - swi_l4, 0.0)
      b3 = swi_b3 * s3
      s1 = s1 - (q1 + b1) * si%dth
      s2 = s2 + (b1 - q2 - b2) * si%dth
      s3 = s3 + (b2 - q3 - b3) * si%dth
      si%s1(i,j) = s1
      si%s2(i,j) = s2
      si%s3(i,j) = s3
      s%swi(i,j) = s1 + s2 + s3
      if (s%swi(i,j) > s%swimax(i,j)) then
        s%swimax(i,j) = s%swi(i,j)                   ! 期間最大の指数
        s%swimaxt(i,j) = s%t / 60.0                  ! 発生時刻 (min)
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル swi.dat。契約5。§7)
!   タンク貯留 S1,S2,S3 の 3 面。swimax 系の統計は save 対象外(§7)
!----------------------------------------------------------------------
subroutine save_state(p, g, si)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_swi), intent(in) :: si
  real, allocatable :: wk(:,:)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/swi.dat', form='unformatted', &
         status='replace')
  end if
  call par_gather_to(wk, si%s1)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, si%s2)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, si%s3)
  if (is_root) call fileio_write_rle(un, wk)
  if (is_root) close(un)
end subroutine


subroutine restore_state(p, g, si, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_swi), intent(inout) :: si
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un, i, j

  fname = trim(p%dir_save)//'/swi.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("swi: state file not found (was fn_swi enabled when saving): " &
                  //fname)
  end if
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, si%s1)
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, si%s2)
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, si%s3)
    close(un)
  else
    call par_scatter_cell(dum, si%s1)
    call par_scatter_cell(dum, si%s2)
    call par_scatter_cell(dum, si%s3)
  end if
  ! 復元直後の表示・出力のために SWI を再構成(タンクの純関数)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      s%swi(i,j) = si%s1(i,j) + si%s2(i,j) + si%s3(i,j)
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 土壌雨量指数モジュールを破棄する(save は dispose で行う。契約5)
!----------------------------------------------------------------------
subroutine m_swi_dispose(si, p, g)
  type(t_swi), intent(inout) :: si
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  if (.not. si%enabled) return
  if (p%f_state_save > 0) call save_state(p, g, si)
  if (allocated(si%s1)) deallocate(si%s1)
  if (allocated(si%s2)) deallocate(si%s2)
  if (allocated(si%s3)) deallocate(si%s3)
  si%enabled = .false.
  si%initialized = .false.
end subroutine

end module
