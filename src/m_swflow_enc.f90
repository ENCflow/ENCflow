module m_swflow_enc
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_ffactor, only : m_ffactor_init, m_ffactor_calc, m_ffactor_dispose
  use list_enc, only : t_list_enc, list_enc_read
  implicit none
  private

  !--------------------------------------------------------------------
  ! パブリックルーチンとパブリック変数の宣言
  !--------------------------------------------------------------------
  public :: m_swflow_enc_init
  public :: m_swflow_enc_calc
  public :: m_swflow_enc_dispose


  !--------------------------------------------------------------------
  ! モジュール内で共有される構造体と変数の宣言
  !--------------------------------------------------------------------
  ! 制御フラグとパラメータの宣言
  ! ---- システムのパラメータからセットする ---
  integer :: f_advection_term               ! 移流項の計算の有無
  integer :: f_pressure_term                ! 圧力項の計算の有無
  ! ---- ENCのパラメータファイルからセットする ---
  integer :: f_gravity_correction != 1       ! 重力の補正
  integer :: f_exflux_reduction != 1         ! reduction of excessive flux
  integer :: f_hcap_upwind != 1              ! 上流側水深によるセル境界水深の制限
  integer :: f_adaptive_runge != 1           ! 適応的ルンゲクッタ
  integer :: f_friction_fastmath != 0        ! 摩擦項計算の高速化
  integer :: f_advection_tvd != 9            ! 移流項にTVDスキームを使用　
  integer :: f_rivermouth_drop              ! 河口から海へ段落ち強制
  real :: p_diagratio != 2 / (2 + sqrt(2.))  ! ratio of diagonal component
  real :: p_adv_upwind_index != 0.0          ! upwind index of advection term
  real :: p_adprunge_thresh != 2.0           ! threshold of adaptive Runge-Kutta

  ! 状態変数の構造体の宣言と定義
  type t_enc_status
    real, allocatable :: uv(:,:,:)   ! セル境界での流速(符合は中心セルから近傍セルに向かい正)
    real, allocatable :: mn(:,:,:)   ! セル境界での流量
    real, allocatable :: h1(:,:)     ! セル中心での計算済み水深
    real, allocatable :: taxy(:,:,:) ! セル中心での移流項(第1添字は1~4，それぞれ風上差分と中心差分のx,y成分)
  end type
  type(t_enc_status) :: sx_actual


  !--------------------------------------------------------------------
  ! モジュール内で共有される重み係数の定義
  !--------------------------------------------------------------------
  ! 中心セルから見たk近傍セルのインデックス
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

  ! 中心セルから見たk近傍の境界フラックスのインデックス
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]

  ! 重み係数
  integer :: din2(1:8)           ! din(:)**2
  integer :: djn2(1:8)           ! djn(:)**2
  real :: w8x(1:8)               ! 勾配モデルの重み係数
  real :: w8y(1:8)               ! 勾配モデルの重み係数
  real :: w8dr(1:8)              ! 近傍セル中心までの距離
  real :: w8dr2(1:8)             ! 近傍セル中心までの距離の二乗
  real :: l8x(1:8)               ! k軸方向のフラックス通過幅の重み
  real :: l8y(1:8)               ! k軸方向のフラックス通過幅の重み
  real :: l8(1:8)                ! k軸方向のフラックス通過幅の重み 
  real :: r8x(1:8)               ! din(:)/dx
  real :: r8y(1:8)               ! djn(:)/dy
  real :: n8x(1:8)               ! k軸の単位ベクトルのx方向成分
  real :: n8y(1:8)               ! k軸の単位ベクトルのy方向成分
  real :: w8mx(1:8)              ! k軸のフラックスからセル中心でのx方向平均量への寄与率
  real :: w8my(1:8)              ! k軸のフラックスからセル中心でのy方向平均量への寄与率
  real :: mn2dh(1:8)             ! k軸の単位幅流量から中心セルの水深減少量への変換係数


contains
 
!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! ENCの初期化
!----------------------------------------------------------------------
subroutine m_swflow_enc_init(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_list_enc) :: list



  ! ENCパラメータファイルを読み込む
  call list_enc_read(p, list)

  f_gravity_correction = list%f_gravity_correction 
  f_exflux_reduction = list%f_exflux_reduction 
  f_hcap_upwind = list%f_hcap_upwind 
  f_adaptive_runge = list%f_adaptive_runge 
  f_friction_fastmath = list%f_friction_fastmath 
  f_advection_tvd = list%f_advection_tvd 
  f_rivermouth_drop = list%f_rivermouth_drop 
  p_diagratio = list%p_diagratio 
  p_adv_upwind_index = list%p_adv_upwind_index 
  p_adprunge_thresh = list%p_adprunge_thresh 

  ! システムパラメータから継承するENCパラメータをセットする
  select case (p%f_govequation)
    case (0)      ! DynWE
      f_advection_term = 1
      f_pressure_term = 1
    case (1)      ! DifWE
      f_advection_term = 0
      f_pressure_term = 1
    case default  ! KinWE
      f_advection_term = 0
      f_pressure_term = 0
  end select

  ! 重み係数をセットする
  call init_weights(p)

  ! 初期条件を設定する
  call init_enc_status(p, g, s, sx_actual)

  ! 高速摩擦計算ルーチンを初期化する
  call m_ffactor_init(f_friction_fastmath, p%dd, 30.0, 'UV')

end subroutine


!----------------------------------------------------------------------
! ENCの計算
!----------------------------------------------------------------------
subroutine m_swflow_enc_calc(p, g, s, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(inout) :: ierror
  call prepare(p, g, s, sx_actual)
  call advection(p, g, s, sx_actual)
  call momentum(p, g, s, sx_actual, ierror)
  call continuous(p, g, s, sx_actual)
  call complete(p, g, s, sx_actual)
end subroutine


!----------------------------------------------------------------------
! ENCの終了
!----------------------------------------------------------------------
subroutine m_swflow_enc_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%f_state_save > 0) call save_state(p, sx_actual)
  call del_enc_status(sx_actual)
  call m_ffactor_dispose
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 重み係数の初期化
!----------------------------------------------------------------------
subroutine init_weights(p)
  type(t_sysparam), intent(in) :: p

  integer :: k
  real :: lpx, lpy, ldx, ldy

  forall(k=1:8) din2(k) = din(k)**2
  forall(k=1:8) djn2(k) = djn(k)**2
  forall(k=1:8) r8x(k) = real(din(k)) / p%dx
  forall(k=1:8) r8y(k) = real(djn(k)) / p%dy

  w8dr(1:8) = [ p%dr, p%dy, p%dr, p%dx, p%dx, p%dr, p%dy, p%dr ]
  forall(k=1:8) w8dr2(k) = w8dr(k)**2

  ! k軸の単位ベクトルのx, y方向成分
  n8x(1:8) = [ -p%dx/p%dr,  0.0,  p%dx/p%dr, -1.0, 1.0, -p%dx/p%dr, 0.0, p%dx/p%dr ]
  n8y(1:8) = [ -p%dy/p%dr, -1.0, -p%dy/p%dr,  0.0, 0.0,  p%dy/p%dr, 1.0, p%dy/p%dr ]

  ! フラックスの通過幅の割合
  !   lpy, ldyはy軸に投影したLの長さのΔyに対する割合(x方向フラックスが通過)
  !   lpx, ldxはx軸に投影したLの長さのΔxに対する割合(y方向フラックスが通過)
  !   lpy, lpxは斜め方向、ldy, ldxは軸方向
  !   ここで lpx + (ldx * 2) = 1, lpy + (ldy * 2) = 1 である
  if (p%dy > p%dx) then
    lpy = 1 - (p%dx / p%dy)**2 * p_diagratio
    ldy = p_diagratio / 2 * (p%dx / p%dy)**2
    lpx = 1 - p_diagratio
    ldx = p_diagratio / 2
  else
    lpy = 1 - p_diagratio
    ldy = p_diagratio / 2
    lpx = 1 - (p%dy / p%dx)**2 * p_diagratio
    ldx = p_diagratio / 2 * (p%dy / p%dx)**2
  end if

  ! k軸方向フラックスの通過幅の割合
  !   l8yはy軸に投影したLの長さのΔyに対する割合(x方向フラックスが通過)
  !   l8xはx軸に投影したLの長さのΔxに対する割合(y方向フラックスが通過)
  l8y(1:8) = [ ldy, 0.0, ldy, lpy, lpy, ldy, 0.0, ldy ]
  l8x(1:8) = [ ldx, lpx, ldx, 0.0, 0.0, ldx, lpx, ldx ]

  ! 勾配モデルの重み係数
  w8x(1:8) = [ ldy, 0.0, ldy, lpy, lpy, ldy, 0.0, ldy ]
  w8y(1:8) = [ ldx, lpx, ldx, 0.0, 0.0, ldx, lpx, ldx ]


  ! k軸方向フラックスの通過幅
  forall(k=1:8) l8(k) = sqrt((l8y(k) * p%dy)**2 + (l8x(k) * p%dx)**2)

  ! セル境界の流速・流量からセル中心の平均流速・平均流量の増分を計算するための係数
  !   セル中心から近傍に向かうフラックスuvをn8x, n8yで除して投影前のxとyの正の方向成分に戻す
  !   近傍の方向に応じた開口幅(辺長)をl8x, l8yで調整し、
  !   セルの左右(上下)の平均をとるために2で割る
  w8mx(1:8) = [ 1/n8x(1), 0.0, 1/n8x(3), 1/n8x(4), 1/n8x(5), 1/n8x(6), 0.0, 1/n8x(8) ]
  w8my(1:8) = [ 1/n8y(1), 1/n8y(2), 1/n8y(3), 0.0, 0.0, 1/n8y(6), 1/n8y(7), 1/n8y(8) ]
  forall(k=1:8) w8mx(k) = w8mx(k) * l8y(k) / 2
  forall(k=1:8) w8my(k) = w8my(k) * l8x(k) / 2

  ! セル境界での単位幅流量から中心セルの1時間ステップでの水位減少量を計算するための係数
  forall(k=1:8) mn2dh(k) = (l8(k) / (p%dx * p%dy)) * p%dt
  
end subroutine


!----------------------------------------------------------------------
! 状態変数の初期化と初期条件の設定
!----------------------------------------------------------------------
subroutine init_enc_status(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(out) :: sx

  real :: ue, ve
  integer :: i, j, k, in, jn, ie, je

  ! メモリを確保する
  allocate(sx%uv(1:4,0:p%nx,0:p%ny), source = 0.0)
  allocate(sx%h1(1:p%nx,1:p%ny), source = 0.0)
  allocate(sx%mn(1:4,0:p%nx,0:p%ny), source = 0.0)
  if (f_advection_tvd > 0) then
    allocate(sx%taxy(1:4,1:p%nx,1:p%ny), source = 0.0)
  else
    allocate(sx%taxy(1:2,1:p%nx,1:p%ny), source = 0.0)
  end if

  ! 流速の初期条件を設定する
  !$omp parallel do private(i, j, k, in, jn, ie, je, ue, ve)
  !do j = 1, p%ny
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        ! k近傍セルのインデックスを計算する
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        ! k近傍セルとの境界フラックスのインデックスを計算する
        ie = i + die(k)
        je = j + dje(k)
        ! セル境界での流速を計算する(座標軸方向が正)
        ue = (s%u(i,j) + s%u(in,jn)) / 2
        ve = (s%v(i,j) + s%v(in,jn)) / 2
        ! セル境界流速の境界法線方向成分を計算する(中心から近傍方向が正)
        sx%uv(k,ie,je) = ue * n8x(k) + ve * n8y(k)
      end do
    end do
  end do
  !$omp end parallel do

  if (p%f_state_restore > 0) call restore_state(p, sx)

end subroutine


!----------------------------------------------------------------------
! 状態変数の削除
!----------------------------------------------------------------------
subroutine del_enc_status(sx)
  type(t_enc_status), intent(inout) :: sx
  if (allocated(sx%uv)) deallocate(sx%uv)
  if (allocated(sx%mn)) deallocate(sx%mn)
  if (allocated(sx%h1)) deallocate(sx%h1)
  if (allocated(sx%taxy)) deallocate(sx%taxy)
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine prepare(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j
  if (p%initialized) continue

  !$omp parallel do private(i, j)
  !do j = 1, p%ny  ! <--- OpenMPでこの行を生かすとifxのみ原因不明の浮動小数点エラー
  do j = g%wy(1), g%wy(2)
    !do i = 1, p%nx   ! <--- この行は大丈夫
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      ! 新時間ステップでの水深を初期化して降雨を加える
      ! 降雨は現時間ステップでの計算には反映されない
      ! したがって運動方程式の計算後に加算しても問題ない
      sx%h1(i,j) = s%h(i,j) + s%pre(i,j) * p%dt / g%gv(i,j)
    end do
  end do
  !!$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine momentum(p, g, s, sx, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer, intent(inout) :: ierror

  integer :: i, j, k
  logical :: have_exflux
  logical :: have_runge
  logical :: have_error
  integer :: n_exfluxes
  integer :: n_runge
  integer :: n_error

  ! 全ての有効セルにおいて対象セルと近傍セルとの間の流量流速を計算する
  ! 同時に水を移動させて対象セルと近傍セルの水深を更新する
  ! (ただし連続式をここで解くとスレッドセーフでない)
  n_exfluxes = 0
  n_runge = 0
  n_error = 0
  !$omp parallel do private(i, j, k, have_exflux, have_runge, have_error) &
  !$omp reduction(+:n_exfluxes), reduction(+:n_runge), reduction(+:n_error)
  ! This loop should be an independ "omp parallel do"
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        ! 対象セルi,jとそのk近傍との境界における流量流速と水深の計算を実行
        call calc_kth_momentum(p, g, s, sx, i, j, k, have_exflux, have_runge, have_error)
        if (have_exflux) n_exfluxes = n_exfluxes + 1
        if (have_runge) n_runge = n_runge + 1
        if (have_error) n_error = n_error + 1
      end do
    end do
    ! OpenMPのからexitで抜けることはできない?
  end do
  !$omp end parallel do
  s%n_exfluxes = n_exfluxes
  s%n_runge = n_runge

  if (n_error > 0) then
    print *, "**********************************************************************"
    print *, "********* Unrealistic calculation (Velocity exceeds 250 m/s) *********"
    print *, "**********************************************************************"
    ierror = ierror + n_error
  end if

end subroutine


!----------------------------------------------------------------------
!
!----------------------------------------------------------------------
subroutine calc_kth_momentum(p, g, s, sx, i, j, k, have_exflux, have_runge, have_error)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer, intent(in) :: i, j
  integer, intent(in) :: k
  logical, intent(out) :: have_exflux
  logical, intent(out) :: have_runge
  logical, intent(out) :: have_error

  integer :: in, jn
  integer :: ie, je
  real :: uve, mne
  real :: uve1, mne1
  real :: tae
  real :: dh
  real :: dhc, dhn
  real :: cor
  real :: maglim

  ! この文はこの場所になければならない
  have_exflux = .false.
  have_runge = .false.
  have_error = .false.

  ! k近傍セルのインデックスを計算する
  in = i + din(k)
  jn = j + djn(k)
  if (g%x(in,jn) <= 0) return
  if (in <= 1 .or. in >= p%nx .or. jn <= 1 .or. jn >= p%ny) return

  ! k近傍セルとの境界フラックスのインデックスを計算する
  ie = i + die(k)
  je = j + dje(k)

  ! 移動限界水深未満の場合は流量ゼロ(ddを大きくすると過大流出が増える)
  if (s%h(i,j) < p%dd .and. s%h(in,jn) < p%dd) then
    sx%uv(k,ie,je) = 0
    sx%mn(k,ie,je) = 0
    return
  end if

  ! セル境界の流速をセットする
  uve = sx%uv(k,ie,je)
  mne = sx%mn(k,ie,je)

  ! セル境界の移流項をセットする
  if (f_advection_term > 0) then
    !call calc_kth_advection(tae)
    tae = calc_kth_advection()
  else
    tae = 0
  end if

  ! 中心セルi,jからk近傍セルin,jnへの流速uv1と単位幅流量mn1を計算する
  call calc_kth_flux(p, g, s, sx, uve, tae, i, j, k, in, jn, 0, uve1, mne1)

  ! 適応的ルンゲクッタ
  !   流速または流量がmaglim倍以上、1/maglim以下、逆方向に変化した場合はルンゲクッタで再計算
  maglim = p_adprunge_thresh
  if (f_adaptive_runge > 0) then
    if ((mne >= 0 .and. (mne1 > mne * maglim .or. mne1 < mne / maglim)) .or. &
        (mne < 0  .and. (mne1 < mne * maglim .or. mne1 > mne / maglim))) then
      have_runge = .true.
      call calc_kth_flux(p, g, s, sx, uve, tae, i, j, k, in, jn, 1, uve1, mne1)
    end if
  end if

  ! 発散チェック
  if (abs(uve1) > 250.) then
    have_error = .true.
  end if

  ! 河口から海への段落ち強制
  if (f_rivermouth_drop > 0) call rivermouth_drop

  ! セル境界での単位幅流量から境界の両側のセルでの水深の減少量を計算する
  dh = mne1 * mn2dh(k)    ! 家屋占有率がゼロの場合の中心セルの水深減少量
  dhc = dh / g%gv(i,j)
  dhn = -dh / g%gv(in,jn)

  ! 過大な流出の抑制
  !if ((dh > 0 .and. dhc + p%dd > s%h(i,j)) .or. (dh < 0 .and. dhn + p%dd > s%h(in,jn))) then
  if ((dh > 0 .and. s%h(i,j) - dhc <= 0) .or. (dh < 0 .and. s%h(in,jn) - dhn <= 0)) then
    have_exflux = .true.
    if (f_exflux_reduction > 0) then
      if (dh > 0) then
        cor = max(s%h(i,j) - p%dd, 0.0) / dhc
      else
        cor = max(s%h(in,jn) - p%dd, 0.0) / dhn
      end if
      uve1 = uve1 * cor
      mne1 = mne1 * cor
    end if
  end if

  ! セル境界の流速を更新する
  sx%uv(k,ie,je) = uve1

  ! セル境界の流量を更新する
  sx%mn(k,ie,je) = mne1

contains
  !--------------------------------------------------------------------
  ! 移流項を計算する
  function calc_kth_advection() result(ta)
    real :: ta
    real :: taxe, taye
    real :: taxe2, taye2, tae2
    integer :: inn, jnn, ino, jno
    real :: duvc, duvr, duvl, duv0
    real :: rr, rl, phir, phil, phi
    ! 風上差分による移流項
    taxe = (sx%taxy(1,i,j) + sx%taxy(1,in,jn)) / 2  ! 移流項(x方向, 符合は座標軸方向が正)
    taye = (sx%taxy(2,i,j) + sx%taxy(2,in,jn)) / 2  ! 移流項(y方向, 符合は座標軸方向が正)
    ta = taxe * n8x(k) + taye * n8y(k)             ! 移流項(符合は中心セルから近傍セルに向かい正)
    ta = ta * 1.5
    ! TVD(風上差分と中心差分の混合)
    if (f_advection_tvd > 0) then
      ! 中心差分による移流項
      taxe2 = (sx%taxy(3,i,j) + sx%taxy(3,in,jn)) / 2
      taye2 = (sx%taxy(4,i,j) + sx%taxy(4,in,jn)) / 2
      tae2 = taxe2 * n8x(k) + taye2 * n8y(k)
      tae2 = tae2 * 1.5
      inn = in + din(k)  ! k近傍のさらに外側のセル
      jnn = jn + djn(k)  ! k近傍のさらに外側のセル
      ino = i + din(9-k) ! k近傍の反対側のセル
      jno = j + djn(9-k) ! k近傍の反対側のセル
      duvr = (s%u(inn,jnn) - s%u(in ,jn )) * n8x(k) + (s%v(inn,jnn) - s%v(in ,jn )) * n8y(k)
      duvc = (s%u(in ,jn ) - s%u(i  ,j  )) * n8x(k) + (s%v(in ,jn ) - s%v(i  ,j  )) * n8y(k)
      duvl = (s%u(i  ,j  ) - s%u(ino,jno)) * n8x(k) + (s%v(i  ,j  ) - s%v(ino,jno)) * n8y(k)
      duv0 = duvc + sign(1.E-5, duvc)
      rr = duvr / duv0
      rl = duvl / duv0

      phil = max(0.0, min(1.0, rl))
      phir = max(0.0, min(1.0, rr))

      !phir = max(0.0, min(1.0, 2 * rr))
      !phil = max(0.0, min(1.0, 2 * rl))

      if (phil >= 0 .and. phir >= 0) then
        phi = min(1.0, min(phir, phil))
      else
        phi = 0.0
      end if

      !if (uve > 0) then
      !  phi = phil
      !else if (uve < 0) then
      !  phi = phir
      !else
      !  phi = min(phir, phil)
      !end if

      ! 風上差分と中心差分の混合
      ta = ta + phi * (tae2 - ta)
      !ta = (ta + tae2) / 2
    end if
  end function
  !--------------------------------------------------------------------
  ! 河口から海への段落ち強制
  subroutine rivermouth_drop
    real :: h
    if (g%rw(i,j) > 0 .and. g%sw(in,jn) > 0) then
      ! 中心から近傍に段落ち
      h = max(s%h(i,j), 0.0)      ! 中心セルの水深
      uve1 = ((2. / 3.)**(3. / 2)) * sqrt(p%gg * h)
      mne1 = uve1 * h
    else if (g%rw(in,jn) > 0 .and. g%sw(i,j) > 0) then
      ! 近傍から中心に段落ち
      h = max(s%h(in,jn), 0.0)    ! 近傍セルの水深
      uve1 = -((2. / 3.)**(3. / 2)) * sqrt(p%gg * h)
      mne1 = uve1 * h
    end if
  end subroutine

end subroutine


!----------------------------------------------------------------------
! 中心セルi,jからk近傍セルへin,jnの流速uve1と単位幅流量mne1を計算する
!----------------------------------------------------------------------
subroutine calc_kth_flux(p, g, s, sx, uve0, tae, i, j, k, in, jn, f_runge, uve1, mne1)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  real, intent(in) :: uve0        ! セル境界での流速
  real, intent(in) :: tae         ! セル境界での移流項
  integer, intent(in) :: i, j     ! 中心セルのインデックス
  integer, intent(in) :: k        ! 近傍セルの方位
  integer, intent(in) :: in, jn   ! 近傍セルのインデックス
  integer, intent(in) :: f_runge  ! ルンゲクッタのフラグ
  real, intent(out) :: uve1       ! 中心セルから近傍セルに向かう流速
  real, intent(out) :: mne1       ! 中心セルから近傍セルに向かう単位幅流量

  real :: he                      ! セル境界の水深
  real :: ge                      ! セル境界での重力加速度
  real :: tg0e, tge, tfe          ! セル境界での重力項、摩擦項
  real :: rne, hhe, vve           ! セル境界での粗度係数、摩擦項用水深、摩擦項用絶対流速
  real :: gve, bbe                ! セル境界での家屋の空隙率、家屋の平均サイズ
  real :: lme                     ! セル境界での付加質量力補正係数
  real :: vue2                    ! セル境界でのuveと直交する方向の流速の二乗
  real, parameter :: a(1:4) = [ 4., 3., 2., 1. ]
  real :: hc0, hn0
  real :: hc, hn
  real :: dtl
  integer :: l

  ! セル境界での物理量を求める
  vve = (s%vv(i,j) + s%vv(in,jn)) / 2       ! 速度の絶対値
  rne = (g%rn(i,j) + g%rn(in,jn)) / 2       ! 粗度係数
  gve = (g%gv(i,j) + g%gv(in,jn)) / 2       ! 家屋の空隙率
  bbe = (g%bb(i,j) + g%bb(in,jn)) / 2       ! 家屋の平均サイズ
  if (gve == 1) bbe = 1.e10                 ! 家屋なしの場合は家屋サイズは大きな値
  lme = gve + (1 - gve) * p%cm              ! 付加質量力補正係数

  ! 摩擦項で使用する流速
  !   静止からの流動開始直後に流速が小さいために摩擦が過小となることを防ぐために
  !   (この現象は正攻法では時間刻みを極めて小さくしないと解消しない)
  vve = max(vve, p%vv)

  ! セル境界での有効重力加速度を計算
  ge = p%gg                                 ! 重力加速度
  if (f_gravity_correction > 0) ge = correct_ge()

  ! セル境界での底面勾配項(符合は中心セルから近傍セルに向かい正)
  tg0e = -ge * (g%z(in,jn) - g%z(i,j)) / w8dr(k) * gve

  ! セル境界でのuveと直交する流速成分の二乗を計算
  !   ルンゲクッタで流速の絶対値を更新する際に使用する
  vue2 = max(vve**2 - uve0**2, 0.0)

  ! 中心セルと近傍セルの水深をセット
  hc0 = s%h(i,j)
  hn0 = s%h(in,jn)
  hc = hc0
  hn = hn0

  ! ルンゲクッタの段数を初期化
  if (f_runge > 0) then
    l = 1                ! ルンゲクッタの場合は1段目から
  else
    l = 4                ! 陽的オイラーの場合は4段目のみを実行
  end if

  ! ルンゲクッタのループ
  do while (l <= 4)
    ! セル境界での水深を求める
    he = (hc + hn) / 2

    ! セル境界での水深が上流側水深よりも深くならない様に調整
    if (f_hcap_upwind > 0) he = correct_he()

    ! 摩擦項で使用する水深
    !   水深が浅い場合に摩擦が過大となることを防ぐために水深の最小値を制限
    hhe = max(he, p%dv)

    ! セル境界での重力項(符合は中心セルから近傍セルに向かい正)
    if (f_pressure_term > 0) then
      tge = tg0e - ge * (hn - hc) / w8dr(k) * gve
    else
      tge = tg0e
    end if

    ! セル境界での摩擦項
    !   摩擦項は半陰解法で計算するため、次元が他の項と異なる(値は常に正)
    tfe = -ge * rne**2 * vve * m_ffactor_calc(hhe) * gve

    ! セル境界での抗力項
    !   摩擦項と一緒に半陰解法で計算するため、次元が他の項と異なる(値は常に正)
    tfe = tfe - p%kk * p%cd / bbe * (1 - gve) * vve / 2

    ! l段目の時間刻み
    dtl = p%dt / a(l) / lme

    ! セル境界での流速(符合は中心セルから近傍セルに向かい正)を更新
    !   摩擦項を半陰解法で計算する
    !   どちらも中心セルから近傍セルに向かい正
    uve1 = (uve0 + (tae + tge) * dtl) / (1 - tfe * dtl) 
    mne1 = uve1 * he

    ! これ以降はルンゲクッタ最終段(陽的オイラー)では不要
    if (l >= 4) exit

    ! ルンゲクッタの次段のために流速の絶対値と水深を更新
    !   移流項はルンゲクッタのループに含まれないため精度は陽的オイラーのまま
    block
      integer :: kk
      real :: mnec, mnen
      integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
      real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]
      ! セル境界での流速の絶対値を更新
      vve = sqrt(uve1**2 + vue2)

      ! 仮の水深を更新
      !   式の詳細は連続式を解くルーチン内のコメントを参照のこと
      hc = hc0       ! 中心セルの水深
      hn = hn0       ! 近傍セルの水深
      do kk = 1, 8
        ! 中心セルと近傍セルの方位kkにおける流量
        !   sx%mnは計算しながら次々と上書されていくため
        !   すでに更新済みの流量も混在しており、このルンゲクッタはあくまで概算となるが
        !   経験的・結果的に更新前の流量"のみ"を使うよりも安定する
        mnec = sign_e(kk) * sx%mn(ke(kk),i+die(kk),j+dje(kk))   ! 中心セルからそのkk近傍への流量
        mnen = sign_e(kk) * sx%mn(ke(kk),in+die(kk),jn+dje(kk)) ! 近傍セルからそのkk近傍への流量
        ! 方位k(近傍セルでは方位9-k)は今回更新された流量
        if (kk == k) mnec = mne1
        if (kk == 9 - k) mnen = -mne1     ! 近傍セルの流出量は中心セルの流出量の逆符号
        ! 仮の水深を更新
        hc = hc - mnec * mn2dh(kk) / g%gv(i,j) / a(l)
        hn = hn - mnen * mn2dh(kk) / g%gv(in,jn) / a(l)
      end do
    end block

    ! 段数を更新して次の段へ
    l = l + 1
  end do

contains
  !--------------------------------------------------------------------
  ! セル境界水深が上流側水深よりも深くならないよう調整
  function correct_he() result(he_corr)
    real :: he_corr
    if (uve0 > 0) then      ! 中心セルが上流側
      he_corr = min(he, hc)      !   中心セルの水深より深くならないように
    else if (uve0 < 0) then ! 近傍セルが上流側
      he_corr = min(he, hn)      !   近傍セルの水深より深くならないように
    else
      he_corr = he
    end if
  end function
  !--------------------------------------------------------------------
  ! 重力加速度を急勾配地形に合わせて調整
  !   Ni, Y., Cao, Z., & Liu, Q. (2019). 
  !     Mathematical modeling of shallow-water flows on steep slopes.
  !     Journal of Hydrology and Hydromechanics, 67(3), 252–259. DOI:10.2478/johh-2019-0012
  function correct_ge() result(ge_corr)
    real :: ge_corr
    if (vve > 0) then
      ge_corr = ge * w8dr2(k) / (w8dr2(k) + (g%z(in,jn) - g%z(i,j))**2)
    else
      ge_corr = ge
    end if
  end function

end subroutine


!----------------------------------------------------------------------
! 連続式による水深の更新と平均流速・流量の計算
!----------------------------------------------------------------------
subroutine continuous(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j, k
  integer :: in, jn, ie, je
  real :: uv1, mn1
  real :: dh
  real :: mnmax
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  !$omp parallel do private(i, j, k, in, jn, ie, je, uv1, mn1, dh, mnmax)
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle
      if (g%x(i,j) <= 0) cycle
      s%u(i,j) = 0
      s%v(i,j) = 0
      s%m(i,j) = 0
      s%n(i,j) = 0
      mnmax = 0
      ! sx%h1(i,j) = s%h(i,j) + s%pre(i,j) * p%dt / g%gv(i,j) ! <--- この行を生かしてprepareを殺すとエラー
      ! 対象セルi,jの8近傍全ての水の流出入を計算し平均流量・流速と水位を更新する
      s%ddir1(i,j) = 0
      s%ddir8(i,j) = 0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (in <= 1 .or. in >= p%nx .or. jn <= 1 .or. jn >= p%ny) cycle
        ! ここでddと比較するのは前時間ステップでの値hでなければならない
        ! そのためこのループ内でhを直接更新してはいけない
        if (s%h(i,j) < p%dd .and. s%h(in,jn) < p%dd) cycle
        ! 中心セルi,jから見たk近傍の境界フラックスのインデックス
        ie = i + die(k)
        je = j + dje(k)
        ! 境界での流速と流量を求める(中心から近傍に向かい正)
        !   近傍5~8は隣接するセルから見た(9-k)近傍に相当する(向きは逆)
        uv1 = sign_e(k) * sx%uv(ke(k),ie,je)
        mn1 = sign_e(k) * sx%mn(ke(k),ie,je)
        ! 水深の減少量(m)に換算
        !   家屋占有率が0.0で無い場合はここで補正係数を乗じる
        dh = mn1 * mn2dh(k) / g%gv(i,j)
        ! 水深を更新
        sx%h1(i,j) = sx%h1(i,j) - dh
        ! セル中心の平均流速・流量への寄与分を加算
        s%u(i,j) = s%u(i,j) + uv1 * w8mx(k)
        s%v(i,j) = s%v(i,j) + uv1 * w8my(k)
        s%m(i,j) = s%m(i,j) + mn1 * w8mx(k)
        s%n(i,j) = s%n(i,j) + mn1 * w8my(k)
        ! 流下方向を判定
        !if (mn1 > mnmax) s%ddir1(i,j) = 2**k             ! 最大流出方向
        if (mn1 > mnmax) then
          s%ddir1(i,j) = 2**k             ! 最大流出方向
          mnmax = mn1
        end if
        if (dh > 0) s%ddir8(i,j) = s%ddir8(i,j) + 2**k   ! 全ての流出方向
      end do
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 変数の更新
!----------------------------------------------------------------------
subroutine complete(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(in) :: sx
  !real a, b

  integer :: i, j 
  if (p%initialized) continue

  !$omp parallel do private(i, j)
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      s%h(i,j) = sx%h1(i,j)
      s%e(i,j) = s%h(i,j) + g%z(i,j)
      s%vv(i,j) = sqrt(s%u(i,j)**2 + s%v(i,j)**2)
      s%qq(i,j) = sqrt(s%m(i,j)**2 + s%n(i,j)**2)
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 移流項の計算
!----------------------------------------------------------------------
subroutine advection(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx

  integer :: i, j, k
  real :: dux, duy, dvx, dvy
  real :: ww(1:8), wwx(1:8), wwy(1:8)
  real :: ulm(1:p%nx,1:p%ny), vlm(1:p%nx,1:p%ny)
  real :: lm

  if (f_advection_term == 0) return

  !$omp parallel do private(i, j, lm)
  do j = g%wy(1), g%wy(2)
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      lm = g%gv(i,j) + (1 - g%gv(i,j)) * p%cm
      ulm(i,j) = s%u(i,j) * lm
      vlm(i,j) = s%v(i,j) * lm
    end do
  end do
  !$omp end parallel do

  !$omp parallel do private(i, j, k, ww, wwx, wwy, dux, duy, dvx, dvy)
  do j = g%wy(1)+1, g%wy(2)-1
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      ! 風上差分による移流項の計算
      ww(:) = get_ww(s%u(i,j), s%v(i,j), s%vv(i,j))
      forall(k=1:8) wwx(k) = w8x(k) * ww(k)
      forall(k=1:8) wwy(k) = w8y(k) * ww(k)
      call get_diff(ulm, vlm, s%h, p%dd, wwx, wwy, g%x, i, j, p%nx, p%ny, dux, duy, dvx, dvy)
      sx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
      sx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      if (f_advection_tvd > 0) then
        ! 中心差分による移流項の計算
        call get_diff(ulm, vlm, s%h, p%dd, w8x, w8y, g%x, i, j, p%nx, p%ny, dux, duy, dvx, dvy)
        sx%taxy(3,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
        sx%taxy(4,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      end if
    end do
  end do
  !$omp end parallel do

!end subroutine
contains
  ! 風上差分用のウェイトを計算
  function get_ww(u, v, vv) result(ww_upw)
    real, intent(in) :: u, v
    real, intent(in) :: vv
    real :: ww_upw(1:8)
    real :: wk
    if (p_adv_upwind_index > 0 .and. vv > 0) then
      do k = 1, 8
        wk = -(u * n8x(k) + v * n8y(k)) / vv                    ! -1~1
        wk = max(1 - (1 - wk) * p_adv_upwind_index / 2, 0.0)    ! 0～1
        ww_upw(k) = wk
      end do
    else
      ww_upw(:) = 1
    end if
  end function
end subroutine


!----------------------------------------------------------------------
! 変数u, vの微分
!----------------------------------------------------------------------
subroutine get_diff(u, v, h, dd, wx, wy, x, i, j, nx, ny, dux, duy, dvx, dvy)
  real, intent(in) :: u(1:nx,1:ny)
  real, intent(in) :: v(1:nx,1:ny)
  real, intent(in) :: h(1:nx,1:ny)
  real, intent(in) :: dd
  real, intent(in) :: wx(1:8), wy(1:8)
  integer, intent(in) :: x(0:nx+1,0:ny+1)
  integer, intent(in) :: i, j, nx, ny
  real, intent(out) :: dux, duy
  real, intent(out) :: dvx, dvy

  real :: du, dv
  real :: swx, swy, wwx, wwy
  integer :: in, jn, k

  dux = 0
  duy = 0
  dvx = 0
  dvy = 0
  swx = 0
  swy = 0

  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (h(in,jn) < dd) cycle
    wwx = x(in,jn) * wx(k)
    wwy = x(in,jn) * wy(k)
    du = (u(in,jn) - u(i,j))
    dv = (v(in,jn) - v(i,j))
    dux = dux + du * r8x(k) * wwx
    dvx = dvx + dv * r8x(k) * wwx
    duy = duy + du * r8y(k) * wwy
    dvy = dvy + dv * r8y(k) * wwy
    swx = swx + wwx !* din2(k)
    swy = swy + wwy !* djn2(k)
  end do

  if (swx > 0) then
    dux = dux / swx
    dvx = dvx / swx
  end if
  if (swy > 0) then
    duy = duy / swy
    dvy = dvy / swy
  end if

end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine save_state(p, sx)
  type(t_sysparam), intent(in) :: p
  type(t_enc_status), intent(in) :: sx
  integer :: un
  if (p%initialized) continue
  open(newunit=un, file=trim(p%dir_result)//'/save_enc.dat', form='unformatted')
  write(un) sx%uv
  close(un)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine restore_state(p, sx)
  type(t_sysparam), intent(in) :: p
  type(t_enc_status), intent(inout) :: sx
  integer :: un
  if (p%initialized) continue
  open(newunit=un, file=trim(p%dir_result)//'/save_enc.dat', form='unformatted')
  read(un) sx%uv
  close(un)
end subroutine



!===== 8方位コロケート格子計算終了 ====================================
!======================================================================
end module
