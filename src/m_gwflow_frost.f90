module m_gwflow_frost
  ! ========= 凍土による浸透抑制(気温連動の浸透能低減) =========
  ! 融雪期の出水(凍った地面の上を融雪水が流れる)を表すため、度日
  ! ベースの凍結指数 FI(°C·day)をセル状態として持ち、鉛直浸透能に
  ! 乗じる低減係数 s%frofac ∈ [fro_fmin, 1] を毎ステップ供給する
  ! (2026-08-18。developer.md §16.4)。
  !   - 有効化は &list_gwflow の f_gwfrost=1(加算的プロセス。無効時は
  !     資源を一切確保しない)。設定は同じ fn_gwflow 内の
  !     &list_gwflow_frost(自分で読む。m_gwflow_bucket 契約)
  !   - 凍結指数の時間発展(気温 Ta は m_meteo から。減率込み):
  !       dFI = (T_f − Ta)·dts/86400          (Ta < T_f: 凍結の進行)
  !       dFI = fro_ct·(T_f − Ta)·dts/86400   (Ta ≥ T_f: 融解 = 負)
  !     積雪断熱(fro_swe0 > 0 かつ積雪モジュール有効時):
  !       dFI ← dFI·exp(−swe/fro_swe0)(雪の下では地面と大気の熱結合が
  !       弱まる = 凍結も融解も遅い)
  !     FI は 0 でクランプ、fro_fimax > 0 なら上限クリップ(凍結深の
  !     飽和の簡便表現。長い厳冬で春の解凍が非現実的に遅れるのを防ぐ)
  !   - 低減係数(線形ランプ): fac = max(fro_fmin, 1 − FI/fro_fifull)
  !     消費者は鉛直浸透モデル(greenampt/bucket)が浸透能に乗じる
  !     (allocated(s%frofac) ガード = 無効時ビット一致)
  !   - 度日法の積雪(m_snow)と同じ気温入力を使う最簡モデル。
  !     地温・凍結深・不凍水は解かない(fro_fifull が実質の校正点)
  !   - meteo の初期化順序の制約(m_gwflow_init は m_meteo_init より先)
  !     のため、気温入力の存在検査は m_main が m_meteo_init の後に
  !     m_gwflow_check_meteo で行う
  !   - FI は持続する内部状態 → 契約5: gwflow_frost.dat で save/restore
  !     (初期値は fro_fi0 一様。restore が勝つ)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_meteo, only : t_meteo, meteo_temp_set, meteo_temp_cell
  use m_fileio, only : fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, dcp, is_root, &
                         par_gather_to, par_scatter_cell
  implicit none
  private
  public :: gwflow_frost_init
  public :: gwflow_frost_calc
  public :: gwflow_frost_dispose

  real, parameter :: secday = 86400.0

  ! モデル私有の設定・状態(単一インスタンス前提。developer.md §12)
  type t_frost
    real, allocatable :: fi(:,:)     ! 凍結指数 FI (°C·day ≥ 0。帯+ハロ)
    real :: fifull = 0.0             ! fac が fro_fmin に達する FI (°C·day)
    real :: fmin = 0.0               ! 低減係数の下限 [0,1)(0 = 完全凍結で不浸透)
    real :: tf = 0.0                 ! 凍結・融解のしきい気温 (°C)
    real :: ct = 1.0                 ! 融解効率(融解度日の倍率)
    real :: swe0 = 0.0               ! 積雪断熱の e-folding 水当量 (m。0 = 断熱なし)
    real :: fimax = 0.0              ! FI の上限 (°C·day。0 = 上限なし)
    logical :: initialized = .false.
  end type
  type(t_frost) :: fro

contains


!----------------------------------------------------------------------
! 凍土モデルの初期化(固有グループ &list_gwflow_frost を自分で読む)。
! 気温入力の存在検査は m_main の m_gwflow_check_meteo(ヘッダ参照)
!----------------------------------------------------------------------
subroutine gwflow_frost_init(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: un, ios
  real :: fro_fifull, fro_fmin, fro_tf, fro_ct, fro_swe0, fro_fimax, fro_fi0
  namelist /list_gwflow_frost/ fro_fifull, fro_fmin, fro_tf, fro_ct, &
                               fro_swe0, fro_fimax, fro_fi0

  fro_fifull = 0.0
  fro_fmin = 0.0
  fro_tf = 0.0
  fro_ct = 1.0
  fro_swe0 = 0.0
  fro_fimax = 0.0
  fro_fi0 = 0.0

  call par_info("reading list_gwflow_frost in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_frost: cannot open " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_frost, iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_frost: cannot read namelist " &
                              // "(f_gwfrost=1 requires &list_gwflow_frost)")
  close(un)

  if (fro_fifull <= 0.0) call par_stop("list_gwflow_frost: fro_fifull must be > 0")
  if (fro_fmin < 0.0 .or. fro_fmin >= 1.0) then
    call par_stop("list_gwflow_frost: fro_fmin must be in [0,1)")
  end if
  if (fro_ct <= 0.0) call par_stop("list_gwflow_frost: fro_ct must be > 0")
  if (fro_swe0 < 0.0) call par_stop("list_gwflow_frost: fro_swe0 must be >= 0")
  if (fro_fimax < 0.0) call par_stop("list_gwflow_frost: fro_fimax must be >= 0")
  if (fro_fimax > 0.0 .and. fro_fimax < fro_fifull) then
    call par_stop("list_gwflow_frost: fro_fimax must be >= fro_fifull (or 0 = no cap)")
  end if
  if (fro_fi0 < 0.0) call par_stop("list_gwflow_frost: fro_fi0 must be >= 0")

  fro%fifull = fro_fifull
  fro%fmin = fro_fmin
  fro%tf = fro_tf
  fro%ct = fro_ct
  fro%swe0 = fro_swe0
  fro%fimax = fro_fimax

  ! 凍結指数(私有状態)と低減係数(共有状態。消費者は鉛直浸透モデル)
  allocate(fro%fi(1:g%nx, dcp%jsh:dcp%jeh), source = fro_fi0)
  allocate(s%frofac(1:g%nx, dcp%jsh:dcp%jeh), &
           source = max(fro%fmin, 1.0 - fro_fi0 / fro%fifull))
  if (p%f_state_restore > 0) call restore_state(p, g)

  fro%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 凍結指数の更新と低減係数の供給(鉛直浸透モデルより前に呼ぶこと =
! m_gwflow_calc の実行順序が結合仕様)。meteo_temp_set は collective
!----------------------------------------------------------------------
subroutine gwflow_frost_calc(p, g, s, mt, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(inout) :: mt
  real, intent(in) :: dts
  integer :: i, j
  real :: tc, df, fi

  ! 評価時刻の気温をセット(collective。全ランク同一判定で呼ぶ)
  call meteo_temp_set(mt, p, g, s%t)

  !$omp parallel do schedule(static) private(i, j, tc, df, fi)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      ! 地表面標高の気温(積雪面・氷面補正はしない — 断熱は swe0 で表す)
      tc = meteo_temp_cell(mt, i, j, s%z(i,j))
      df = (fro%tf - tc) * dts / secday          ! 凍結度日 (> 0) / 融解度日 (< 0)
      if (df < 0.0) df = df * fro%ct
      if (fro%swe0 > 0.0 .and. allocated(s%swe)) then
        df = df * exp(-s%swe(i,j) / fro%swe0)    ! 積雪断熱(凍結・融解とも減速)
      end if
      fi = max(fro%fi(i,j) + df, 0.0)
      if (fro%fimax > 0.0) fi = min(fi, fro%fimax)
      fro%fi(i,j) = fi
      s%frofac(i,j) = max(fro%fmin, 1.0 - fi / fro%fifull)
    end do
  end do
  !$omp end parallel do

  ! セル局所の更新のみ — ハロ交換は不要(契約3)

end subroutine


!----------------------------------------------------------------------
! リスタート保存(rank0 が全域を gather して RLE 保存。契約5)
!----------------------------------------------------------------------
subroutine save_state(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, allocatable :: wk(:,:)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  call par_gather_to(wk, fro%fi)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/gwflow_frost.dat', form='unformatted', &
         status='replace')
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


!----------------------------------------------------------------------
! リスタート復元(版・格子・精度の検証は m_state が済ませている。
! 自ファイルの有無のみ確認 — 無ければ設定齟齬として停止。契約5)
!----------------------------------------------------------------------
subroutine restore_state(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  fname = trim(p%dir_save)//'/gwflow_frost.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("gwflow_frost: state file not found " &
                  // "(was f_gwfrost enabled when saving): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, fro%fi)
  else
    call par_scatter_cell(dum, fro%fi)
  end if
end subroutine


!----------------------------------------------------------------------
! 凍土モデルの破棄(save は dispose で行う。契約5。
! s%frofac の解放は m_state_dispose が行う)
!----------------------------------------------------------------------
subroutine gwflow_frost_dispose(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  if (.not. fro%initialized) return
  if (p%f_state_save > 0) call save_state(p, g)
  if (allocated(fro%fi)) deallocate(fro%fi)
  fro%initialized = .false.
end subroutine

end module
