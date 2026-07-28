!======================================================================
module m_geoinfo
  use m_sysparam, only : t_sysparam
  use list_geoinfo, only : t_list_geoinfo, list_geoinfo_read
  use m_fileio
  use m_util, only : itoa
  use m_parallel, only : par_info, par_stop, dcp, is_root
  implicit none
  private

  public :: t_geoinfo
  public :: m_geoinfo_init
  public :: m_geoinfo_shrink_coeffs
  public :: m_geoinfo_band_shrink
  public :: m_geoinfo_dispose


  type t_geoinfo
    integer :: nx                                     ! x方向セル数
    integer :: ny                                     ! y方向セル数
    real :: dx
    real :: dy
    real :: dr
    real :: lx
    real :: ly
    real :: min_gv                                    ! 家屋の空隙率の最小値
    real :: min_bb                                    ! 家屋の平均サイズの最小値
    real, allocatable :: z(:,:)                       ! 標高(m)
    real, allocatable :: rn(:,:)                      ! 粗度係数
    real, allocatable :: gv(:,:)                      ! 家屋の空隙率
    real, allocatable :: bb(:,:)                      ! 家屋の平均寸法
    real, allocatable :: lm(:,:)                      ! 有効慣性係数
    real, allocatable :: rscap(:,:)                   ! ため池の限界貯留高(m)
    integer, allocatable :: x(:,:)                    ! 対象領域判別マスク
    integer, allocatable :: sw(:,:)                   ! 海域マスク
    integer, allocatable :: rw(:,:)                   ! 河道マスク
    integer, allocatable :: lu(:,:)                   ! 土地利用
    integer, allocatable :: wx(:,:)                   ! 行ごとの計算対象範囲
    integer :: n_valcells = 0                         ! 計算対象セル数(海域除く)
    integer :: wy(1:2)                                ! 行の計算対象範囲
    logical :: initialized = .false.
  end type


  interface
    module subroutine init_geoinfo_user_1(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_2(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_3(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_4(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_5(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
  end interface

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 地理情報構造体を初期化する
!----------------------------------------------------------------------
subroutine m_geoinfo_init(g, p)
  type(t_sysparam), intent(inout) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(out) :: g             ! 地理情報構造体
  type(t_list_geoinfo) :: list                     ! パラメータファイル中の変数

  call list_geoinfo_read(p, list)
  call set_params(p, g, list)

  call allocate_arrays(g)
  call read_sw(p, g, list)     ! read_maskよりも先に実行する
  call read_mask(p, g, list)
  call read_z(p, g, list)
  call read_lu(p, g, list)
  call read_rw(p, g, list)
  call read_rn(p, g, list)
  call read_gvbb(p, g, list)
  call read_rscap(p, g, list)
  call adjust_rw(p, g, list)

  select case (list%f_user_routine_id)
    case (0)
      continue
    case (1)
      call init_geoinfo_user_1(p, g)
    case (2)
      call init_geoinfo_user_2(p, g)
    case (3)
      call init_geoinfo_user_3(p, g)
    case (4)
      call init_geoinfo_user_4(p, g)
    case (5)
      call init_geoinfo_user_5(p, g)
    case default
      call par_stop("undefined f_user_routine_id in list_geoinfo"//itoa(list%f_user_routine_id))
  end select


  call calc_wxy(p, g)
  call count_valcells(p, g)



  g%initialized = .true.

end subroutine

!----------------------------------------------------------------------
! 計算対象セル数を数える(海域は除く)
!   sw を全域添字で読むため、係数類の縮小(shrink_coeffs)より前=
!   m_geoinfo_init 内で実行すること。結果は t_geoinfo が保持し、
!   m_state など後段はコピーして使う(大域値は全ランク同一)
!----------------------------------------------------------------------
subroutine count_valcells(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j
  if (p%initialized) continue
  g%n_valcells = 0
  do j = 1, g%ny
    do i = 1, g%nx
      if (g%x(i,j) > 0 .and. g%sw(i,j) == 0) g%n_valcells = g%n_valcells + 1
    end do
  end do
  if (g%n_valcells <= 0) then
    call par_stop("no valid cell in the entire domain")
  end if
end subroutine


!----------------------------------------------------------------------
! 静的配列の帯縮小(第2次元を jlo:jhi に切り詰める)
!   逐次では確保範囲が変わらないため自然に何もしない。
!   x 方向(第1次元)は lbound/ubound を保つので、通常境界 (1:nx) にも
!   番兵付き境界 (0:nx+1) にもそのまま使える
!----------------------------------------------------------------------
subroutine shrink_band_r(a, jlo, jhi)
  real, allocatable, intent(inout) :: a(:,:)
  integer, intent(in) :: jlo, jhi
  real, allocatable :: t(:,:)
  if (lbound(a,2) == jlo .and. ubound(a,2) == jhi) return
  allocate(t(lbound(a,1):ubound(a,1), jlo:jhi))
  t(:,:) = a(:, jlo:jhi)
  call move_alloc(t, a)
end subroutine


subroutine shrink_band_i(a, jlo, jhi)
  integer, allocatable, intent(inout) :: a(:,:)
  integer, intent(in) :: jlo, jhi
  integer, allocatable :: t(:,:)
  if (lbound(a,2) == jlo .and. ubound(a,2) == jhi) return
  allocate(t(lbound(a,1):ubound(a,1), jlo:jhi))
  t(:,:) = a(:, jlo:jhi)
  call move_alloc(t, a)
end subroutine


!----------------------------------------------------------------------
! 物性係数の静的配列を担当帯+ハロに縮小する
!   m_main で par_decomp_init の直後に呼ぶ。これ以降、係数類への
!   全域添字アクセスは不可(帯内の大域添字はそのまま有効)。
!   係数を使う全域前処理は m_geoinfo_init 内(=この呼び出しより前)に
!   書くこと。
!   注意: マスク類(x, sw, rw)と z はここで縮小しない。fill_depression
!   (海域 sw・河道 rw を全域窓で参照)など、ゾーン2の全域処理が
!   使うため band_shrink まで全域を保つ(n_valcells の教訓)。
!   行メタデータ wx, wy は微小なので恒久的に全域のまま保持する。
!----------------------------------------------------------------------
subroutine m_geoinfo_shrink_coeffs(g)
  type(t_geoinfo), intent(inout) :: g
  call shrink_band_r(g%rn,  dcp%jsh, dcp%jeh)
  call shrink_band_r(g%gv,  dcp%jsh, dcp%jeh)
  call shrink_band_r(g%bb,  dcp%jsh, dcp%jeh)
  call shrink_band_r(g%lm,  dcp%jsh, dcp%jeh)
  call shrink_band_r(g%rscap, dcp%jsh, dcp%jeh)
  call shrink_band_i(g%lu,  dcp%jsh, dcp%jeh)
end subroutine


!----------------------------------------------------------------------
! 地形とマスク類を縮小する(全モジュールの初期化完了後、run_main の
! 直前に呼ぶ)。x は番兵境界ごと帯へ、sw / rw は通常の帯へ。
! z は Z ファイル出力(output_matrix_full)のため rank0 のみ全域を
! 保持し続ける(将来の浸食計算では「初期地形の正本」にもなる)。
! 時間ループでの sw/rw/gv の近傍参照(momentum, rivermouth の ±1)は
! ハロ幅2の帯確保で全て範囲内に収まることを監査済み
!----------------------------------------------------------------------
subroutine m_geoinfo_band_shrink(g)
  type(t_geoinfo), intent(inout) :: g
  call shrink_band_i(g%x,  dcp%jsh - 1, dcp%jeh + 1)
  call shrink_band_i(g%sw, dcp%jsh, dcp%jeh)
  call shrink_band_i(g%rw, dcp%jsh, dcp%jeh)
  if (.not. is_root) call shrink_band_r(g%z, dcp%jsh, dcp%jeh)
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_geoinfo_dispose(g)
  type(t_geoinfo), intent(inout) :: g
  if (allocated(g%z)) deallocate(g%z)
  if (allocated(g%rn)) deallocate(g%rn)
  if (allocated(g%lu)) deallocate(g%lu)
  if (allocated(g%gv)) deallocate(g%gv)
  if (allocated(g%bb)) deallocate(g%bb)
  if (allocated(g%lm)) deallocate(g%lm)
  if (allocated(g%rscap)) deallocate(g%rscap)
  if (allocated(g%x)) deallocate(g%x)
  if (allocated(g%sw)) deallocate(g%sw)
  if (allocated(g%rw)) deallocate(g%rw)
  if (allocated(g%wx)) deallocate(g%wx)
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! パラメータファイル中の変数を地理情報構造体にセット
!----------------------------------------------------------------------
subroutine set_params(p, g, list)
  type(t_sysparam), intent(inout) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  if (p%initialized) continue

  g%nx = list%nx
  g%ny = list%ny
  g%dx = list%dx
  g%dy = list%dy
  g%lx = list%lx
  g%ly = list%ly

  ! 領域指定の判別・補完・検証(dr の計算より前に行うこと)
  call resolve_geometry(g)

  g%dr = sqrt(g%dx**2 + g%dy**2)
  g%min_gv = list%min_gv
  g%min_bb = list%min_bb

end subroutine


!----------------------------------------------------------------------
! 領域指定の判別・補完・検証(幾何の正本はここで確定する)
!   指定方法A: lx, ly と nx, ny を与える → dx, dy を導出
!   指定方法B: dx, dy と nx, ny を与える → lx, ly を導出
!   過剰指定(lx と dx の両方あり): 整合を検査し、矛盾なら par_stop
!   未指定は 0 が番兵(list_geoinfo は生の値を運ぶだけ)
!   注意: 導出式(lx/nx, nx*dx)の式形を変えないこと。既存 reference との
!         ビット同値の条件になっている(developer.md §12)
!----------------------------------------------------------------------
subroutine resolve_geometry(g)
  type(t_geoinfo), intent(inout) :: g
  real, parameter :: rtol = 1.0e-6   ! 過剰指定の整合判定の相対許容差

  ! セル数はどちらの指定方法でも必須
  if (g%nx <= 0) call par_stop("list_geoinfo: nx が未指定か不正です")
  if (g%ny <= 0) call par_stop("list_geoinfo: ny が未指定か不正です")

  ! x 方向
  if (g%dx <= 0.0) then
    if (g%lx <= 0.0) then
      call par_stop("list_geoinfo: dx か lx のどちらかを指定してください")
    end if
    g%dx = g%lx / g%nx                     ! 指定方法A
  else if (g%lx <= 0.0) then
    g%lx = g%nx * g%dx                     ! 指定方法B
  else
    ! 過剰指定: 無言でどちらかを優先せず、整合を検査する
    if (abs(g%nx * g%dx - g%lx) > rtol * g%lx) then
      call par_stop("list_geoinfo: lx と nx*dx が矛盾しています。どちらか一方の指定にしてください")
    end if
  end if

  ! y 方向(x 方向と対称)
  if (g%dy <= 0.0) then
    if (g%ly <= 0.0) then
      call par_stop("list_geoinfo: dy か ly のどちらかを指定してください")
    end if
    g%dy = g%ly / g%ny                     ! 指定方法A
  else if (g%ly <= 0.0) then
    g%ly = g%ny * g%dy                     ! 指定方法B
  else
    if (abs(g%ny * g%dy - g%ly) > rtol * g%ly) then
      call par_stop("list_geoinfo: ly と ny*dy が矛盾しています。どちらか一方の指定にしてください")
    end if
  end if

end subroutine

!----------------------------------------------------------------------
! 地理情報構造体中の配列を確保
!----------------------------------------------------------------------
subroutine allocate_arrays(g)
  type(t_geoinfo), intent(inout) :: g
  allocate(g%z(1:g%nx,1:g%ny), source = 0.0)
  allocate(g%rn(1:g%nx,1:g%ny), source = 0.0)
  allocate(g%gv(1:g%nx,1:g%ny), source = 1.0)    ! 空隙率は1.0で初期化
  allocate(g%bb(1:g%nx,1:g%ny), source = 1.e10)  ! 家屋サイズは大きな値で初期化
  allocate(g%lm(1:g%nx,1:g%ny), source = 1.0)    ! 有効慣性係数は1.0で初期化
  allocate(g%rscap(1:g%nx,1:g%ny), source = 0.0) ! ため池の深さは0.0で初期化
  allocate(g%x(0:g%nx+1,0:g%ny+1), source = 0)   ! 領域マスクは全て領域外で初期化
  allocate(g%sw(1:g%nx,1:g%ny), source = 0)
  allocate(g%rw(1:g%nx,1:g%ny), source = 0)
  allocate(g%lu(1:g%nx,1:g%ny), source = 0)
  allocate(g%wx(1:2,1:g%ny))
end subroutine


!----------------------------------------------------------------------
! 海域マスクを読み込む
!----------------------------------------------------------------------
subroutine read_sw(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname

  if (len_trim(list%fn_sw) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_sw)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%sw, p%f_input_mode)
  end if

end subroutine

!----------------------------------------------------------------------
! 領域マスクデータを読み込む
!----------------------------------------------------------------------
subroutine read_mask(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname
  integer :: a(1:g%nx,1:g%ny)
  character(len=1024) :: msg

  if (list%f_masktype == 0) then
    ! マスク無しを指定の場合
    ! 領域マスク全域を1にセット
    g%x(1:g%nx,1:g%ny) = 1
  else if (list%f_masktype == 1) then
    ! 流域マスクを指定の場合
    ! ファイルから読み込む
    fname = trim(p%dir_data) // "/" // trim(list%fn_mask)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, a, p%f_input_mode)
        block
        integer :: i, j
        do j = 1, g%ny
          do i = 1, g%nx
            if (a(i,j) /= 0 .and. a(i,j) /= 1) then
              write(msg,'(a,3i7)') "list_geoinfo: invalid data in mask data", i, j, a(i,j)
              call par_stop(trim(msg))
            end if
          end do
        end do
        end block
    ! g%xは(0:nx+1,0:ny+1)なので範囲を指定してコピー
    g%x(1:g%nx,1:g%ny) = a(1:g%nx,1:g%ny)
  else if (list%f_masktype == 2) then
    ! 海域マスクから生成を指定の場合
    if (len_trim(list%fn_sw) == 0) then
      call par_stop('list_geoinfo: f_mastype=2 but fn_sw=""')
    end if
    call do_sw2x
  else
    ! 不正なマスクタイプ
    call par_stop("list_geoinfo: unknown mask type"//itoa(list%f_masktype))
  end if


  ! 領域の外側が海の場合、領域を1セル分拡張
  !if (.false.) then
  if (.true.) then
        block
        integer :: i, j, k, ii, jj
        integer :: x1(0:g%nx+1,0:g%ny+1)
        integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
        integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
        x1(:,:) = g%x(:,:)
        do j = 2, g%ny-1
          do i = 2, g%nx-1
            if (g%x(i,j) <= 0) cycle
            do k = 1, 8
              ii = i + din(k)
              jj = j + djn(k)
              if (g%x(ii,jj) <= 0 .and. g%sw(ii,jj) > 0) then
                ! 近傍セルが領域外かつ海の場合
                ! 近傍セルを領域内に
                x1(ii,jj) = 1
              end if
            end do
          end do
        end do
        g%x(:,:) = x1(:,:)
        end block
  end if


  ! 四辺を強制的に海域に
  if (list%f_edge_sw > 0) then
      block
      integer :: i, j
      do j = 1, g%ny
        g%sw(1,j) = 1
        g%sw(g%ny,j) = 1
      end do
      do i = 1, g%nx
        g%sw(i,1) = 1
        g%sw(i,g%ny) = 1
      end do
      end block
  end if

contains
  ! 海域マスクから領域マスクを作る
  !   このとき陸域と隣接する海域セルを計算領域に入れる
  subroutine do_sw2x
    integer :: i, j, k, ii, jj
    integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
    integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%sw(i,j) <= 0) then
          ! 海でないセルは有効セル
          g%x(i,j) = 1
          cycle
        end if
        ! 海域セルのうち陸域に隣接するセルは有効セルにする
        do k = 1, 8
          ii = i + din(k)
          jj = j + djn(k)
          if (ii < 1 .or. ii > g%nx) cycle
          if (jj < 1 .or. jj > g%ny) cycle
          if (g%sw(ii,jj) <= 0) then
            ! 近傍に海でないセルがある場合は有効セル
            g%x(i,j) = 1
            exit
          end if
        end do
      end do
    end do
  end subroutine

end subroutine


!----------------------------------------------------------------------
! 標高データを読み込む
!----------------------------------------------------------------------
subroutine read_z(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname
  integer :: i, j

  if (list%f_ztype == 0) then
    g%z = list%z0 * list%mag_z
  else
    fname = trim(p%dir_data) // "/" // trim(list%fn_z)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%z, p%f_input_mode)
    g%z(:,:) = g%z(:,:) * list%mag_z
  end if

  ! 海域の標高を0に強制
  do j = 1, g%ny
    do i = 1, g%nx
      if (g%sw(i,j) > 0) g%z(i,j) = 0
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 土地利用データを読み込む
!----------------------------------------------------------------------
subroutine read_lu(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname

  if (list%f_lusetype == 0) then
    g%lu = 0
  else
    fname = trim(p%dir_data) // "/" // trim(list%fn_luse)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%lu, p%f_input_mode)
  end if

end subroutine

!----------------------------------------------------------------------
! 河道マスクを読み込む
!----------------------------------------------------------------------
subroutine read_rw(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname

  if (len_trim(list%fn_rw) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_rw)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%rw, p%f_input_mode)
  end if

end subroutine

!----------------------------------------------------------------------
! 家屋の空隙率と平均寸法を読み込む
!----------------------------------------------------------------------
subroutine read_gvbb(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname
  integer :: i, j

  if (len_trim(list%fn_gv) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_gv)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%gv, p%f_input_mode)
  end if

  if (len_trim(list%fn_bb) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_bb)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%bb, p%f_input_mode)
  end if

  do j = 1, g%ny
    do i = 1, g%nx
      g%gv(i,j) = max(g%gv(i,j), g%min_gv)
      g%bb(i,j) = max(g%bb(i,j), g%min_bb)
      g%lm(i,j) = g%gv(i,j) + (1 - g%gv(i,j)) * p%cm
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! ため池の限界貯留高を読み込む
!----------------------------------------------------------------------
subroutine read_rscap(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname

  if (len_trim(list%fn_rscap) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_rscap)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%rscap, p%f_input_mode)
  end if

end subroutine


!----------------------------------------------------------------------
! 粗度係数データを読み込む
!----------------------------------------------------------------------
subroutine read_rn(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  integer :: nluse
  integer :: i, j
  character(:), allocatable :: fname
  character(len=1024) :: msg

  if (list%f_rntype == 0) then
    g%lu = 0
    g%rn = list%rn0
  else if (list%f_rntype == 1) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_rn)
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, g%rn, p%f_input_mode)
  else
    ! 土地利用と粗度係数の関係の数をカウントする
    nluse = 0
    do i = 1, ubound(list%lu2rn, 2)
      if (list%lu2rn(1,i) < 0) exit
      nluse = nluse + 1
    end do
    if (nluse < 1) then
      call par_stop("error in geoimfo: need lu2rn(:,:) for f_rntype=2")
    end if
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) == 0) cycle
        g%rn(i,j) = get_rn(list%lu2rn, nluse, g%lu(i,j))
        if (g%rn(i,j) < 0) then
          write(msg,'(a,i3,a,i0,a,i0,a)') &
                "error in geoinfo: landuse categoly", g%lu(i,j), " at", i, ",", j, " not found in lu2rn"
          call par_stop(trim(msg))
        end if
      end do
    end do
  end if

  if (list%f_masktype > 0) then
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) == 0) then
          g%rn(i,j) = 0
        end if
      end do
    end do
  end if



contains
  function get_rn(lu2rn, nlu, lu) result(rn)
    real :: rn
    !real, intent(in) :: lu2rn(1:2,1:maxnluse)
    real, intent(in) :: lu2rn(:,:)
    integer, intent(in) :: nlu
    integer, intent(in) :: lu
    integer :: ilu
    rn = -1
    do ilu = 1, nlu
      if (nint(lu2rn(1,ilu)) == lu) then
        rn = lu2rn(2,ilu)
        exit
      end if
    end do
  end function
         

end subroutine


!----------------------------------------------------------------------
! 河道マスク部を掘り込む
!----------------------------------------------------------------------
subroutine adjust_rw(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  integer :: i, j
  if (p%initialized) continue
  if (len(list%fn_rw) <= 0) return
  if (list%depth_rw == 0.0) return
  do j = 1, g%ny
    do i = 1, g%nx
      if (g%x(i,j) > 0 .and. g%rw(i,j) > 0) then
        g%z(i,j) = g%z(i,j) - list%depth_rw
        if (list%rn0_rw > 0.0) g%rn(i,j) = list%rn0_rw
      end if
    end do
  end do
end subroutine

!----------------------------------------------------------------------
! 行ごとの計算対象範囲を求める
!----------------------------------------------------------------------
subroutine calc_wxy(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j, s
  if (p%initialized) continue

  g%wy(1) = 1
  g%wy(2) = g%ny

  g%wx(1,:) = g%nx + 1
  g%wx(2,:) = 0

  do j = 1, g%ny
    do i = 1, g%nx
      s = g%x(i,j) + g%x(i+1,j-1) + g%x(i+1,j) + g%x(i+1,j+1)
      if (s > 0) then
        g%wx(1,j) = i
        exit
      end if
    end do
  end do

  do j = 1, g%ny
    do i = g%nx, 1, -1
      s = g%x(i,j) + g%x(i-1,j-1) + g%x(i-1,j) + g%x(i-1,j+1)
      if (s > 0) then
        g%wx(2,j) = i
        exit
      end if
    end do
  end do

end subroutine



end module
