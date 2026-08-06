module m_intercept_initloss
  ! ========== 貯留型遮断モデルの見本: 初期損失モデル ==========
  ! 累積遮断量 st がセルごとの最大貯留量 smax に達するまで降雨を遮断し
  ! (I = min(P, 残容量))、以後は素通しにする(Initial Loss)。
  ! 蒸発による貯留の回復(乾き戻り)は表現しない。
  ! 最大貯留量は一様値(ic_smax_mm)または分布ファイル(fn_icsmax)で
  ! 与える(いずれも mm。fn_icsmax 指定時は ic_smax_mm を使わない)。
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
  use m_fileio, only : fileio_read_matrix, fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, par_abort, dcp, is_root, &
                       par_scatter_cell, par_gather_to
  implicit none
  private
  public :: intercept_initloss_init
  public :: intercept_initloss_calc
  public :: intercept_initloss_step
  public :: intercept_initloss_dispose

  ! モデル私有の設定と内部状態(単一インスタンス前提。developer.md §12)
  type t_icinit
    real :: smax = 0.0                     ! 最大貯留量 (m)(一様指定時)
    real, allocatable :: smaxmap(:,:)      ! 最大貯留量の分布 (m)(分布指定時のみ確保。帯)
    real, allocatable :: st(:,:)           ! 累積遮断量 (m)(内部状態。帯)
    real, allocatable :: pr0(:,:)          ! 原雨量 (m/s)(私有保管。帯)
    real, allocatable :: prh0(:,:)         ! 原雨量 (mm/h)(私有保管。帯)
    logical :: initialized = .false.
  end type
  type(t_icinit) :: ici

contains


!----------------------------------------------------------------------
! 初期損失モデルの初期化(固有グループ &list_intercept_initloss を自分で読む)
!----------------------------------------------------------------------
subroutine intercept_initloss_init(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer :: un, ios
  real :: ic_smax_mm
  character(len=256) :: fn_icsmax
  namelist /list_intercept_initloss/ ic_smax_mm, fn_icsmax

  ic_smax_mm = -1.0
  fn_icsmax = ""

  call par_info("reading list_intercept_initloss in " // trim(p%fn_intercept))
  open(newunit=un, file=trim(p%fn_intercept), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_intercept))
  read(un, nml=list_intercept_initloss, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_intercept_initloss")
  close(un)

  if (len_trim(fn_icsmax) > 0) then
    ! 分布指定: 最大貯留量マップ (mm) を読み、m に換算して帯で保持
    call read_smax_map(p, g, trim(fn_icsmax))
  else
    ! 一様指定
    if (ic_smax_mm <= 0.0) then
      call par_stop("list_intercept_initloss: ic_smax_mm must be > 0 (or specify fn_icsmax)")
    end if
    ici%smax = ic_smax_mm / 1000.0         ! mm -> m
  end if

  allocate(ici%st(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(ici%pr0(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(ici%prh0(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)

  ! 内部状態の復元(契約C)。m_state の門番(check_save_info)は
  ! m_state_init で通過済み
  if (p%f_state_restore > 0) call restore_state(p)

  ici%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 最大貯留量の分布ファイルを読む(mm 単位。m_intercept_fixed の契約5と同型)
!----------------------------------------------------------------------
subroutine read_smax_map(p, g, fn)
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
    call par_stop("list_intercept_initloss: fn_icsmax が見つかりません: " // fname)
  end if

  allocate(ici%smaxmap(1:g%nx, dcp%jsh:dcp%jeh))
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
                "list_intercept_initloss: fn_icsmax の値が負", i, j, smap(i,j)
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
! 降雨更新直後: 原雨量を私有配列に写し取る(契約A。s%pre は変更しない)
!----------------------------------------------------------------------
subroutine intercept_initloss_calc(p, g, s, it)
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
subroutine intercept_initloss_step(p, g, s, it)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j
  logical :: use_map
  real :: pr, cap, d, f

  if (it < 0) continue         ! 引数未使用の警告を抑制

  use_map = allocated(ici%smaxmap)

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
! 内部状態 st の復元(契約C)。rank0 が全域一時に読み、帯へ scatter する
!----------------------------------------------------------------------
subroutine restore_state(p)
  type(t_sysparam), intent(in) :: p
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  fname = trim(p%dir_save) // '/intercept_initloss.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("intercept_initloss の保存ファイルがありません(保存時も初期損失モデルでしたか): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:dcp%nx_g, 1:dcp%ny_g), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, ici%st)
  else
    call par_scatter_cell(dum, ici%st)
  end if
  call par_info("restore: intercept_initloss の貯留状態を復元しました")
end subroutine


!----------------------------------------------------------------------
! 内部状態 st の保存(契約C)。帯を rank0 へ gather して RLE で書く
!----------------------------------------------------------------------
subroutine save_state(p)
  type(t_sysparam), intent(in) :: p
  real, allocatable :: wk(:,:)
  integer :: un

  call sysdep_mkdir(trim(p%dir_save))
  if (is_root) then
    allocate(wk(1:dcp%nx_g, 1:dcp%ny_g), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)   ! 参照されないダミー
  end if
  call par_gather_to(wk, ici%st)
  if (is_root) then
    open(newunit=un, file=trim(p%dir_save)//'/intercept_initloss.dat', &
         form='unformatted', status='replace')
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


!----------------------------------------------------------------------
! 初期損失モデルの破棄(f_state_save 指定時は内部状態を保存してから)
!----------------------------------------------------------------------
subroutine intercept_initloss_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%f_state_save > 0) call save_state(p)
  if (allocated(ici%smaxmap)) deallocate(ici%smaxmap)
  if (allocated(ici%st)) deallocate(ici%st)
  if (allocated(ici%pr0)) deallocate(ici%pr0)
  if (allocated(ici%prh0)) deallocate(ici%prh0)
  ici%initialized = .false.
end subroutine

end module
