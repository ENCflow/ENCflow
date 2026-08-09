!======================================================================
! 地形のユーザールーチン集(m_geoinfo の submodule)
!
!   親モジュールへの公開面は入口の手続きのみ:
!     user_geoinfo_defined : 識別名が登録済みかを返す(検証用。副作用なし)
!     user_geoinfo_names   : 登録済み識別名の一覧文字列(エラー表示用)
!     user_geoinfo_run     : 識別名で該当ルーチンを実行(rank0 のみで呼ばれる)
!   分岐(resolve)と識別名簿(routine_names)はこの submodule に閉じる。
!
!   ルーチンの追加手順(このファイルだけで完結する):
!     1. geoinfo_template を複製して実装する(全域添字 1:nx, 1:ny で書く契約)
!     2. routine_names に識別名を登録する(snake_case)
!     3. resolve の select case に分岐を1行追加する
!
!   注意: ここのルーチンは rank0 のみで実行されるため、par_stop
!   (collective)を呼んではならない。エラーは par_abort を使うこと
!======================================================================
submodule(m_geoinfo) user_geoinfo
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_abort
  implicit none

  ! ユーザールーチンの呼び出し規約
  abstract interface
    subroutine user_geoinfo_if(p, g)
      import :: t_sysparam, t_geoinfo
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
  end interface

  ! 識別名簿(エラー表示用の一覧)。名簿と resolve の分岐は同時に
  ! 更新すること(乖離は defined/run が「未定義名」として検出する)
  character(len=*), parameter :: routine_names(1:7) = [ character(len=32) :: &
      "wave_solid_wall",  &   ! 波例題: 斜めの不透過壁(2セル厚)
      "wave_leaky_wall",  &   ! 波例題: 斜めの半透過壁(1セル厚)
      "abukuma_terrain",  &   ! 阿武隈川例題: 深海の埋め立てと地盤高 1/10
      "tohoku_flood",     &   ! 東北大氾濫計算(スタブ)
      "gaussian_hill",    &   ! クリープ例題: 中央のガウス丘(解析解ベンチマーク)
      "slope_break",      &   ! 土石流例題: 遷緩点付き斜面(test/debris, test/slide)
      "template"          ]   ! 新規ルーチンの雛形(空)

contains

!======================================================================
!===================== 入口(親モジュールへ公開)=====================
!======================================================================

!----------------------------------------------------------------------
! 識別名が登録済みかを返す(検証用。全ランクで呼んでよい)
!----------------------------------------------------------------------
module function user_geoinfo_defined(name) result(res)
  character(len=*), intent(in) :: name
  logical :: res
  procedure(user_geoinfo_if), pointer :: fp
  fp => resolve(name)
  res = associated(fp)
end function

!----------------------------------------------------------------------
! 登録済み識別名の一覧文字列(エラー表示用)
!----------------------------------------------------------------------
module function user_geoinfo_names() result(names)
  character(len=:), allocatable :: names
  integer :: i
  names = ""
  do i = 1, size(routine_names)
    if (i > 1) names = names//", "
    names = names//trim(routine_names(i))
  end do
end function

!----------------------------------------------------------------------
! 識別名で該当ルーチンを実行する(rank0 のみで呼ばれる)
!   名前の検証は呼び出し側が全ランクで済ませている前提。ここでの
!   不一致は名簿と resolve の乖離(プログラミングエラー)なので abort
!----------------------------------------------------------------------
module subroutine user_geoinfo_run(p, g, name)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  character(len=*), intent(in) :: name
  procedure(user_geoinfo_if), pointer :: fp
  fp => resolve(name)
  if (.not. associated(fp)) call par_abort("user_geoinfo_run: 未定義の識別名 "//trim(name))
  call fp(p, g)
end subroutine

!======================================================================
!======================= 分岐(submodule 私有)=======================
!======================================================================

!----------------------------------------------------------------------
! 識別名 → 手続きポインタ(未定義名は null)
!----------------------------------------------------------------------
function resolve(name) result(fp)
  character(len=*), intent(in) :: name
  procedure(user_geoinfo_if), pointer :: fp
  select case (trim(name))
    case ("wave_solid_wall")
      fp => geoinfo_wave_solid_wall
    case ("wave_leaky_wall")
      fp => geoinfo_wave_leaky_wall
    case ("abukuma_terrain")
      fp => geoinfo_abukuma_terrain
    case ("tohoku_flood")
      fp => geoinfo_tohoku_flood
    case ("gaussian_hill")
      fp => geoinfo_gaussian_hill
    case ("slope_break")
      fp => geoinfo_slope_break
    case ("template")
      fp => geoinfo_template
    case default
      fp => null()
  end select
end function

!======================================================================
!========================== ユーザールーチン ==========================
!======================================================================

!----------------------------------------------------------------------
! 波例題: 斜めの不透過壁(2セル厚)
!----------------------------------------------------------------------
subroutine geoinfo_wave_solid_wall(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: k, ix, iy
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  do k = 1, int(g%nx / 4. * 3.)
    ix = k;
    iy = k + g%ny / 4
    iy = min(iy, g%ny)
    g%z(ix,iy) = 1.5
    g%x(ix,iy) = 0
    g%z(ix+1,iy) = 1.5
    g%x(ix+1,iy) = 0
  end do

end subroutine

!----------------------------------------------------------------------
! 波例題: 斜めの半透過壁(1セル厚)
!----------------------------------------------------------------------
subroutine geoinfo_wave_leaky_wall(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: k, ix, iy
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  do k = 1, int(g%nx / 4. * 3.)
    ix = k;
    iy = k + g%ny / 4
    iy = min(iy, g%ny)
    g%z(ix,iy) = 1.5
    g%x(ix,iy) = 0
  end do

end subroutine

!----------------------------------------------------------------------
! 阿武隈川例題: 深海の埋め立て(対象外化)と地盤高 1/10
!----------------------------------------------------------------------
subroutine geoinfo_abukuma_terrain(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  do j = 1, g%ny
    do i = 1, g%nx

      if (g%z(i,j) <= -2000) then
        g%z(i,j) = 1000
        g%x(i,j) = 0
      else if (g%z(i,j) <= -100) then
        g%z(i,j) = 1000
        g%x(i,j) = 0
      else
        g%z(i,j) = g%z(i,j) / 10
        g%x(i,j) = 1
      endif

    enddo
  enddo

end subroutine

!----------------------------------------------------------------------
! 東北大氾濫計算(スタブ)
!----------------------------------------------------------------------
subroutine geoinfo_tohoku_flood(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (g%initialized) continue  ! 引数未使用の警告を抑制
end subroutine


!----------------------------------------------------------------------
! クリープ例題: 領域中央のガウス丘
!   z(r) = A exp(-r^2 / (2 sigma^2))、A = 1 m、sigma = 10 dx。
!   線形拡散 dz/dt = D∇²z の解析解
!     z(r,t) = A sigma^2/(sigma^2+2Dt) exp(-r^2/(2(sigma^2+2Dt)))
!   との比較ベンチマーク(test/creep)専用。中心はセル ((nx+1)/2, (ny+1)/2)
!   で、距離はセル番号差 × 格子幅(プローブの pbxytype=0 と同じ計量)
!----------------------------------------------------------------------
subroutine geoinfo_gaussian_hill(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j, ic, jc
  real :: sigma2, r2
  real, parameter :: amp = 1.0
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ic = (g%nx + 1) / 2
  jc = (g%ny + 1) / 2
  sigma2 = (10.0 * g%dx)**2
  do j = 1, g%ny
    do i = 1, g%nx
      r2 = ((i - ic) * g%dx)**2 + ((j - jc) * g%dy)**2
      g%z(i,j) = amp * exp(-r2 / (2.0 * sigma2))
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 土石流・地滑り例題: 遷緩点付き斜面(test/debris, test/slide 専用)
!   x < xb では tanθ = 0.4(約 21.8°)の下り斜面、以降は平坦。
!     z(x) = st・(xb − x)  (x < xb),  0  (x >= xb),  x = (i − 0.5)dx
!   パラメータ(st = 0.4, xb = 30 m)は test/*/param.txt・Check_*.py の
!   z0 計算式と対で保守すること(gaussian_hill と同じ運用)
!----------------------------------------------------------------------
subroutine geoinfo_slope_break(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j
  real :: x
  real, parameter :: st = 0.4      ! 斜面勾配 tanθ
  real, parameter :: xb = 30.0     ! 遷緩点の x 座標 (m)
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  do j = 1, g%ny
    do i = 1, g%nx
      x = (i - 0.5) * g%dx
      if (x < xb) then
        g%z(i,j) = st * (xb - x)
      else
        g%z(i,j) = 0.0
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 新規ルーチンの雛形(空。複製して使う)
!----------------------------------------------------------------------
subroutine geoinfo_template(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (g%initialized) continue  ! 引数未使用の警告を抑制
end subroutine



end submodule
