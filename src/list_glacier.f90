module list_glacier
  ! ================ 氷河設定ファイルの読み込み(&list_glacier) ================
  ! list_* は namelist を読むだけ。解釈・検証・導出(単位換算、係数の合成、
  ! 相互依存の検査)は m_glacier の init が行う(developer.md §12, §45)
  ! ==========================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_glacier
  public :: list_glacier_read

  integer, parameter :: maxpathlen = 256

  type t_list_glacier
    integer :: f_glacier = 1                 ! 0 でファイルを残したまま一時無効化
    character(len=80) :: dt_glacier_c = "1 day"  ! 氷河更新間隔(氷化・流動・侵食の間欠実行)
    real :: gl_morfac = 1.0                  ! 氷河時間の加速係数(geomorph の morfac と
                                             !   共通の「地形時間」。併用時は同値必須)
    real :: gl_dens = 900.0                  ! 氷の密度 (kg/m3)
    real :: gl_tfirn_yr = 10.0               ! 雪→氷変換(フィルン化)の e-folding 時間 (年)
    real :: gl_ddfi = -9999.0                ! 氷面の度日係数 (mm/℃/day。必須)
    real :: gl_tmelt = 0.0                   ! 氷面融解の気温閾値 (℃)
    integer :: f_glflow = 1                  ! SIA 氷体流動 (0:流動なし, 1:有効)
    real :: gl_afl = 1.0e-16                 ! Glen 流動則の係数 A (Pa^-3 yr^-1)
    real :: gl_cfl = 0.4                     ! 陽解法サブサイクルの安全係数 (0-1)
    integer :: gl_nsubmax = 10000            ! 1回の更新のサブサイクル数上限(暴走ガード)
    integer :: f_glslide = 0                 ! Weertman 底面滑動 (0:なし, 1:有効)
    real :: gl_as = -9999.0                  ! 滑動係数 As (m yr^-1 Pa^-3。f_glslide=1 で必須)
    integer :: f_glero = 0                   ! 氷河侵食 (0:なし, 1:有効。f_glslide 必須)
    real :: gl_kg = -9999.0                  ! 侵食係数 Kg(滑動速度べき乗則。f_glero=1 で必須。
                                             !   gl_lexp=1 なら無次元(us は m/yr で評価))
    real :: gl_lexp = 1.0                    ! 侵食則の滑動速度べき指数 l
    integer :: f_glava = 0                   ! 雪の重力再配分=雪崩 (0:なし, 1:有効)
    real :: gl_ava_tanc = 0.6                ! 雪崩の限界勾配 tan(θc)
    character(len=maxpathlen) :: fn_glacier_hi0 = ""  ! 初期氷厚分布 (m 氷厚。省略時=氷なし)
  end type

contains

!----------------------------------------------------------------------
! 氷河設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_glacier_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_glacier), intent(inout) :: list

  integer :: f_glacier, f_glflow, f_glslide, f_glero, f_glava, gl_nsubmax
  real :: gl_morfac, gl_dens, gl_tfirn_yr, gl_ddfi, gl_tmelt, gl_afl, gl_cfl
  real :: gl_as, gl_kg, gl_lexp, gl_ava_tanc
  character(len=80) :: dt_glacier_c
  character(len=maxpathlen) :: fn_glacier_hi0
  integer :: un, ios
  character(len=1024) :: iom

  namelist /list_glacier/ f_glacier, dt_glacier_c, gl_morfac, gl_dens, &
                          gl_tfirn_yr, gl_ddfi, gl_tmelt, &
                          f_glflow, gl_afl, gl_cfl, gl_nsubmax, &
                          f_glslide, gl_as, f_glero, gl_kg, gl_lexp, &
                          f_glava, gl_ava_tanc, fn_glacier_hi0

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_glacier = list%f_glacier
  dt_glacier_c = list%dt_glacier_c
  gl_morfac = list%gl_morfac
  gl_dens = list%gl_dens
  gl_tfirn_yr = list%gl_tfirn_yr
  gl_ddfi = list%gl_ddfi
  gl_tmelt = list%gl_tmelt
  f_glflow = list%f_glflow
  gl_afl = list%gl_afl
  gl_cfl = list%gl_cfl
  gl_nsubmax = list%gl_nsubmax
  f_glslide = list%f_glslide
  gl_as = list%gl_as
  f_glero = list%f_glero
  gl_kg = list%gl_kg
  gl_lexp = list%gl_lexp
  f_glava = list%f_glava
  gl_ava_tanc = list%gl_ava_tanc
  fn_glacier_hi0 = list%fn_glacier_hi0

  call par_info("reading list_glacier in "//trim(p%fn_glacier))
  open(newunit=un, file=trim(p%fn_glacier), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_glacier: cannot open "//trim(p%fn_glacier)//": "//trim(iom))
  read(un, nml=list_glacier, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_glacier: cannot read namelist: "//trim(iom))
  close(un)

  list%f_glacier = f_glacier
  list%dt_glacier_c = dt_glacier_c
  list%gl_morfac = gl_morfac
  list%gl_dens = gl_dens
  list%gl_tfirn_yr = gl_tfirn_yr
  list%gl_ddfi = gl_ddfi
  list%gl_tmelt = gl_tmelt
  list%f_glflow = f_glflow
  list%gl_afl = gl_afl
  list%gl_cfl = gl_cfl
  list%gl_nsubmax = gl_nsubmax
  list%f_glslide = f_glslide
  list%gl_as = gl_as
  list%f_glero = f_glero
  list%gl_kg = gl_kg
  list%gl_lexp = gl_lexp
  list%f_glava = f_glava
  list%gl_ava_tanc = gl_ava_tanc
  list%fn_glacier_hi0 = fn_glacier_hi0

end subroutine

end module
