module m_intercept_initloss
  ! ========== 貯留型遮断モデルの見本: 初期損失モデル ==========
  ! 累積遮断量 st がセルごとの最大貯留量 smax に達するまで降雨を遮断し
  ! (I = min(P, 残容量))、以後は素通しにする(Initial Loss)。
  ! 蒸発による貯留の回復(乾き戻り)は draw 口経由でのみ起きる
  ! (fn_evap 有効時に m_evap が引き落とす。§27。蒸発散無効なら従来
  ! どおり回復なし)。
  ! 最大貯留量は一様値(ic_smax_mm)または分布ファイル(fn_icsmax)で
  ! 与える(いずれも mm。fn_icsmax 指定時は ic_smax_mm を使わない)。
  !
  ! 【2 段の遮断率】(任意。2026-11-11。developer.md §106.8)満杯までの遮断率 a1
  ! (ic_alpha_fill。既定 1)と満杯後の遮断率 a2(ic_alpha_full。既定 0)を与えると、
  ! 満杯まで雨の a1 を遮断して樹冠に蓄え(容量を満たすのに要る雨は残容量/a1)、満杯の
  ! 後は雨の a2 を損失として取り除く(固定遮断率モデルと同じく蓄えない)。既定の
  ! a1 = 1・a2 = 0 は従来の初期損失そのもので、どちらも与えなければ従来と同じ式で計算する。
  !   初期損失 → 固定遮断率(初期損失・比例損失型): a1 = 1、a2 = α
  !   木村の一次流出率 f1・飽和雨量 R_sa: a1 = 1 − f1、smax = (1 − f1)·R_sa、a2 = 0
  ! 一様値または分布ファイル(fn_icalpha_fill・fn_icalpha_full)で与える。
  !
  ! 【貯留型モデルの契約(m_intercept_fixed の契約に追加)】
  !  (A) 原雨量の私有保管: calc(降雨更新直後)は s%pre / s%prh を
  !      変更せず、私有配列 pr0 / prh0 に写し取るだけにする。
  !      s%pre への適用は破壊的なので、毎ステップ再計算するモデルは
  !      必ず原雨量から計算し直すこと(適用済みの値に再適用しない)
  !  (B) step(毎ステップ、swflow が s%pre を読む前)で貯留状態を
  !      発展させ、s%pre / s%prh を原雨量から計算し直す。
  !      窓内の使用セルには毎ステップ必ず書くこと(前ステップの
  !      適用値が残ると誤る)。s%pre と s%prh は同率で減じる(契約1)
  !  (C) 内部状態(st)の save/restore はモデル私有ファイル
  !      intercept_initloss.dat で行う(dispose で保存、init で復元。
  !      復元は自ファイルの有無のみ確認し、無ければ par_stop。
  !      版・格子・精度の門番は m_state が済ませている。§7)。
  !      原雨量 pr0/prh0 は保存しない(再開時の makepre + calc で再構築
  !      される導出量)
  !  (D) 遮断量の分解 d = P*dt - Pe*dt は浮動小数点では機械精度の
  !      端数を持つ(乗除の往復)。質量台帳との突き合わせは相対
  !      1e-14 程度を同値とみなすこと
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_fileio, only : fileio_read_matrix
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : param_default
  use m_parallel, only : par_info, par_stop, par_abort, dcp, is_root, &
                       par_scatter_cell, par_gather_to
  implicit none
  private
  public :: t_icinit
  public :: intercept_initloss_init
  public :: intercept_initloss_calc
  public :: intercept_initloss_step
  public :: intercept_initloss_draw
  public :: intercept_initloss_dispose

  ! モデル私有の設定と内部状態。実体は切替器 m_intercept の t_intercept が持ち、
  ! 各手続きが第 1 引数で受ける(成分は本モジュール私有。nesting_plan.md §3.2 A 群)
  type t_icinit
    private
    real :: smax = 0.0                     ! 最大貯留量 (m)(一様指定時)
    real, allocatable :: smaxmap(:,:)      ! 最大貯留量の分布 (m)(分布指定時のみ確保。帯)
    logical :: two = .false.               ! 2 段の遮断率を使うか(ic_alpha_fill・ic_alpha_full の指定)
    real :: afill = 1.0, afull = 0.0       ! 満杯まで・満杯後の遮断率(一様指定時)
    real, allocatable :: afillmap(:,:)     ! 満杯までの遮断率の分布(分布指定時のみ確保。帯)
    real, allocatable :: afullmap(:,:)     ! 満杯後の遮断率の分布(分布指定時のみ確保。帯)
    real, allocatable :: st(:,:)           ! 累積遮断量 (m)(内部状態。帯)
    real, allocatable :: pr0(:,:)          ! 原雨量 (m/s)(私有保管。帯)
    real, allocatable :: prh0(:,:)         ! 原雨量 (mm/h)(私有保管。帯)
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 初期損失モデルの初期化(固有グループ &list_intercept_initloss を自分で読む)
!----------------------------------------------------------------------
subroutine intercept_initloss_init(ici, p, g)
  type(t_icinit), intent(inout) :: ici
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer :: un, ios
  real :: ic_smax_mm, ic_alpha_fill, ic_alpha_full
  character(len=256) :: fn_icsmax, fn_icalpha_fill, fn_icalpha_full
  namelist /list_intercept_initloss/ ic_smax_mm, fn_icsmax, ic_alpha_fill, ic_alpha_full, &
                                     fn_icalpha_fill, fn_icalpha_full

  ic_smax_mm = -1.0
  fn_icsmax = ""
  ic_alpha_fill = -9999.0
  ic_alpha_full = -9999.0
  fn_icalpha_fill = ""
  fn_icalpha_full = ""

  call par_info("reading list_intercept_initloss in " // trim(p%fn_intercept))
  open(newunit=un, file=trim(p%fn_intercept), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_intercept_initloss: cannot open " // trim(p%fn_intercept))
  read(un, nml=list_intercept_initloss, iostat=ios)
  if (ios /= 0) call par_stop("list_intercept_initloss: cannot read namelist")
  close(un)

  if (len_trim(fn_icsmax) > 0) then
    ! 分布指定: 最大貯留量マップ (mm) を読み、m に換算して帯で保持
    call read_smax_map(ici, p, g, trim(fn_icsmax))
  else
    ! 一様指定(未指定 = 番兵 −1 なら既定を採用し表示。developer.md §66)
    ic_smax_mm = param_default("intercept", "ic_smax_mm", ic_smax_mm, 1.5, " mm", unset=-1.0)
    if (ic_smax_mm <= 0.0) then
      call par_stop("list_intercept_initloss: ic_smax_mm must be > 0 (or specify fn_icsmax)")
    end if
    ici%smax = ic_smax_mm / 1000.0         ! mm -> m
  end if

  ! 2 段の遮断率(任意。どれも与えなければ従来の初期損失。既定の表示もしない = 従来の
  ! 最小入力の画面と同じ。与えたときは 2 つの採用値を表示する)
  ici%two = (ic_alpha_fill > -9998.0 .or. ic_alpha_full > -9998.0 .or. &
             len_trim(fn_icalpha_fill) > 0 .or. len_trim(fn_icalpha_full) > 0)
  if (ici%two) then
    if (len_trim(fn_icalpha_fill) > 0) then
      call read_ratio_map(p, g, trim(fn_icalpha_fill), "fn_icalpha_fill", .false., ici%afillmap)
    else
      ici%afill = param_default("intercept", "ic_alpha_fill", ic_alpha_fill, 1.0, "", unset=-9999.0)
      if (.not. (ici%afill > 0.0 .and. ici%afill <= 1.0)) then
        call par_stop("list_intercept_initloss: ic_alpha_fill must satisfy 0 < a <= 1")
      end if
    end if
    if (len_trim(fn_icalpha_full) > 0) then
      call read_ratio_map(p, g, trim(fn_icalpha_full), "fn_icalpha_full", .true., ici%afullmap)
    else
      ici%afull = param_default("intercept", "ic_alpha_full", ic_alpha_full, 0.0, "", unset=-9999.0)
      if (.not. (ici%afull >= 0.0 .and. ici%afull <= 1.0)) then
        call par_stop("list_intercept_initloss: ic_alpha_full must satisfy 0 <= a <= 1")
      end if
    end if
    call par_info("intercept: two-phase initial loss (ic_alpha_fill until the storage is full," &
                  //" ic_alpha_full after it is full)")
  end if

  allocate(ici%st(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(ici%pr0(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(ici%prh0(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)

  ! 内部状態の復元(契約C)。m_state の門番(check_save_info)は
  ! m_state_init で通過済み
  if (p%f_state_restore > 0) call restore_state(ici, p)

  ici%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 最大貯留量の分布ファイルを読む(mm 単位。m_intercept_fixed の契約5と同型)
!----------------------------------------------------------------------
subroutine read_smax_map(ici, p, g, fn)
  type(t_icinit), intent(inout) :: ici
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, allocatable :: smap(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  fname = trim(p%dir_data) // "/" // trim(fn)

  ! 存在確認は全ランクで(par_stop は collective)
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("list_intercept_initloss: fn_icsmax not found: " // fname)
  end if

  allocate(ici%smaxmap(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh))
  if (is_root) then
    allocate(smap(1:g%nx, 1:g%ny))
    call par_info(" reading " // fname)
    call fileio_read_matrix(fname, g%nx, g%ny, smap, p%f_input_mode)
    ! 検証は使用セルのみ。0 は「遮断なし」として許す
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        if (smap(i,j) < 0.0) then
          write(msg,'(a,2i7,es12.4)') &
                "list_intercept_initloss: fn_icsmax has a negative value at cell", i, j, smap(i,j)
          call par_abort(trim(msg))
        end if
      end do
    end do
    smap(:,:) = smap(:,:) / 1000.0         ! mm -> m に換算してから配布
    call par_scatter_cell(smap, ici%smaxmap)
  else
    call par_scatter_cell(dum, ici%smaxmap)
  end if
end subroutine


!----------------------------------------------------------------------
! 遮断率の分布ファイルを読む(無次元。read_smax_map と同型)。zero_ok なら 0 <= a <= 1、
! そうでなければ 0 < a <= 1 を使用セルで検査する
!----------------------------------------------------------------------
subroutine read_ratio_map(p, g, fn, name, zero_ok, amap)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn, name
  logical, intent(in) :: zero_ok
  real, allocatable, intent(out) :: amap(:,:)
  real, allocatable :: smap(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found, bad
  integer :: i, j

  fname = trim(p%dir_data) // "/" // trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_intercept_initloss: "//name//" not found: " // fname)
  allocate(amap(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh))
  if (is_root) then
    allocate(smap(1:g%nx, 1:g%ny))
    call par_info(" reading " // fname)
    call fileio_read_matrix(fname, g%nx, g%ny, smap, p%f_input_mode)
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        if (zero_ok) then
          bad = .not. (smap(i,j) >= 0.0 .and. smap(i,j) <= 1.0)
        else
          bad = .not. (smap(i,j) > 0.0 .and. smap(i,j) <= 1.0)
        end if
        if (bad) then
          write(msg,'(a,a,2i7,es12.4)') "list_intercept_initloss: ", name//" is out of range at cell", &
                i, j, smap(i,j)
          call par_abort(trim(msg))
        end if
      end do
    end do
    call par_scatter_cell(smap, amap)
  else
    call par_scatter_cell(dum, amap)
  end if
end subroutine


!----------------------------------------------------------------------
! 降雨更新直後: 原雨量を私有配列に写し取る(契約A。s%pre は変更しない)
!----------------------------------------------------------------------
subroutine intercept_initloss_calc(ici, p, g, s, it)
  type(t_icinit), intent(inout) :: ici
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it

  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (it < 0) continue         ! 引数未使用の警告を抑制

  ici%pr0(:,:) = s%pre(:,:)
  ici%prh0(:,:) = s%prh(:,:)
end subroutine


!----------------------------------------------------------------------
! 毎ステップ: 貯留を発展させ、s%pre / s%prh を原雨量から計算し直す(契約B)
!   d = min(原雨量×dt, 残容量) を貯留に加え、通過率 f = (P*dt-d)/(P*dt)
!   で pre / prh を同率で減じる(満杯なら素通し)
!----------------------------------------------------------------------
subroutine intercept_initloss_step(ici, p, g, s, it)
  type(t_icinit), intent(inout) :: ici
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j
  logical :: use_map
  real :: pr, cap, d, f

  if (it < 0) continue         ! 引数未使用の警告を抑制

  use_map = allocated(ici%smaxmap)
  if (ici%two) then
    call step_two_phase(ici, p, g, s, use_map)
    return
  end if

  !$omp parallel do schedule(static) private(i, j, pr, cap, d, f)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
      pr = ici%pr0(i,j)
      if (use_map) then
        cap = ici%smaxmap(i,j) - ici%st(i,j)
      else
        cap = ici%smax - ici%st(i,j)
      end if
      d = min(pr * p%dt, cap)
      if (d > 0.0) then                          ! d > 0 なら pr > 0
        ici%st(i,j) = ici%st(i,j) + d
        f = (pr * p%dt - d) / (pr * p%dt)        ! 通過率(0 <= f < 1)
        s%pre(i,j) = pr * f
        s%prh(i,j) = ici%prh0(i,j) * f
      else                                       ! 満杯または無降雨: 素通し
        s%pre(i,j) = pr
        s%prh(i,j) = ici%prh0(i,j)
      end if
    end do
  end do
  !$omp end parallel do

  ! 近傍参照なしのためハロ交換は不要(契約2)

end subroutine


!----------------------------------------------------------------------
! 蒸発散による貯留の引き落とし(t_intercept%draw の実装。§27)
!   需要 dem (m) のうち累積遮断量 st から引けた量を返し、st を減じる
!   (=遮断容量の乾き戻り)。呼び出し側(m_evap)は自帯の使用セルのみを
!   渡す契約(範囲検査はしない)。st は h と同じ柱状量基底 (m)
!----------------------------------------------------------------------
! 2 段の遮断率の 1 ステップ(§106.8)。雨 R = P·dt、残容量 cap、満杯までの遮断率 a1、
! 満杯後の遮断率 a2 として、満杯に要る雨 R_f = cap/a1 まで a1·R を蓄え、残り R − R_f の
! a2 を取り除く(蓄えない)。通過分 R − d − 損失の比で s%pre・s%prh を減じる(契約1)
!----------------------------------------------------------------------
subroutine step_two_phase(ici, p, g, s, use_map)
  type(t_icinit), intent(inout) :: ici
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  logical, intent(in) :: use_map
  integer :: i, j
  real :: pr, rr, cap, a1, a2, rf, d, ls, f

  !$omp parallel do schedule(static) private(i, j, pr, rr, cap, a1, a2, rf, d, ls, f)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
      pr = ici%pr0(i,j)
      if (.not. (pr > 0.0)) then                 ! 無降雨: 素通し
        s%pre(i,j) = pr
        s%prh(i,j) = ici%prh0(i,j)
        cycle
      end if
      if (use_map) then
        cap = max(ici%smaxmap(i,j) - ici%st(i,j), 0.0)
      else
        cap = max(ici%smax - ici%st(i,j), 0.0)
      end if
      a1 = ici%afill
      if (allocated(ici%afillmap)) a1 = ici%afillmap(i,j)
      a2 = ici%afull
      if (allocated(ici%afullmap)) a2 = ici%afullmap(i,j)
      rr = pr * p%dt
      d = 0.0
      ls = 0.0
      if (cap > 0.0) then
        rf = cap / a1                            ! 満杯に要る雨
        if (rr <= rf) then
          d = a1 * rr                            ! 満たしている途中
        else
          d = cap                                ! このステップで満杯になる
          ls = a2 * (rr - rf)
        end if
      else
        ls = a2 * rr                             ! 満杯
      end if
      ici%st(i,j) = ici%st(i,j) + d
      f = max(rr - d - ls, 0.0) / rr             ! 通過率
      s%pre(i,j) = pr * f
      s%prh(i,j) = ici%prh0(i,j) * f
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
function intercept_initloss_draw(ici, i, j, dem) result(w)
  type(t_icinit), intent(inout) :: ici
  integer, intent(in) :: i, j
  real, intent(in) :: dem
  real :: w
  w = min(ici%st(i,j), max(dem, 0.0))
  ici%st(i,j) = ici%st(i,j) - w
end function


!----------------------------------------------------------------------
! 内部状態 st の復元(契約C)。rank0 が全域一時に読み、帯へ scatter する
!----------------------------------------------------------------------
subroutine restore_state(ici, p)
  type(t_icinit), intent(inout) :: ici
  type(t_sysparam), intent(in) :: p
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  fname = trim(p%dir_save) // '/intercept_initloss.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("intercept: state file not found (was the initial loss model " &
                  //"enabled when saving): "//fname)
  end if

  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, ici%st)
  if (is_root) close(un)
  call par_info("restoring interception storage (initial loss model) from "//fname)
end subroutine


!----------------------------------------------------------------------
! 内部状態 st の保存(契約C)。帯を窓形に集約しながら RLE で書く(§83)
!----------------------------------------------------------------------
subroutine save_state(ici, p)
  type(t_icinit), intent(in) :: ici
  type(t_sysparam), intent(in) :: p
  integer :: un

  call sysdep_mkdir(trim(p%dir_save))
  if (is_root) open(newunit=un, file=trim(p%dir_save)//'/intercept_initloss.dat', &
                    form='unformatted', status='replace')
  call restart_write_cell(un, ici%st)
  if (is_root) close(un)
end subroutine


!----------------------------------------------------------------------
! 初期損失モデルの破棄(f_state_save 指定時は内部状態を保存してから)
!----------------------------------------------------------------------
subroutine intercept_initloss_dispose(ici, p)
  type(t_icinit), intent(inout) :: ici
  type(t_sysparam), intent(in) :: p
  if (p%f_state_save > 0) call save_state(ici, p)
  if (allocated(ici%smaxmap)) deallocate(ici%smaxmap)
  if (allocated(ici%st)) deallocate(ici%st)
  if (allocated(ici%pr0)) deallocate(ici%pr0)
  if (allocated(ici%prh0)) deallocate(ici%prh0)
  ici%initialized = .false.
end subroutine

end module
