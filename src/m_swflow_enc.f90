module m_swflow_enc
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_boundary, only : t_boundary
  use m_state, only : t_state
  use m_ffactor, only : m_ffactor_init, m_ffactor_calc, m_ffactor_dispose
  use list_enc, only : t_list_enc, list_enc_read
  use list_channel, only : t_list_channel, list_channel_read
  use m_parallel, only : par_info, par_stop, dcp, is_root, &
                       par_halo_cell, par_halo_edge, par_edge_merge, &
                       par_gather_edge_to, par_scatter_edge
  use m_sysdep_util, only : sysdep_mkdir
  use m_fileio, only : fileio_write_rle, fileio_read_rle
  implicit none
  private

  !--------------------------------------------------------------------
  ! パブリックルーチンとパブリック変数の宣言
  !--------------------------------------------------------------------
  public :: m_swflow_enc_init
  public :: m_swflow_enc_calc
  public :: m_swflow_enc_dispose

  ! nvfortran の submodule バグ回避(TPR #27323 系)。修正され次第 private に戻す
  public :: f_advection_tvd
  public :: p_adv_upwind_index
  public :: n8x, n8y

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
  integer :: f_bank_mode                    ! 堤防の水理モード(下の e_bank_*)
  real :: p_diagratio != 2 / (2 + sqrt(2.))  ! ratio of diagonal component
  real :: p_adv_upwind_index != 0.0          ! upwind index of advection term
  real :: p_adprunge_thresh != 2.0           ! threshold of adaptive Runge-Kutta
  ! ---- 境界条件(t_boundary)からセットする ---
  ! 境界条件の私有状態(辺型・面型・基準水位等)は submodule
  ! m_swflow_enc_bc が保持する(bc_init が構築)。親には continuous /
  ! restore_uvmn のホットパスが読む判定フラグだけを置く
  logical :: have_open_bc = .false.         ! 開いた面(不透過でない)があるか
                                            !   (bc_init が設定)

  ! 堤防(仮想壁面)モデル(developer.md §17)
  !   有効化は fn_channel の fn_bank / bank0 の有無(g%bank_active)。
  !   天端の絶対標高は geoinfo が河道セルごとに構築済み(g%zbank)。
  !   水理モード f_bank_mode は fn_channel の &list_channel から読む
  logical :: have_bank = .false.            ! 堤防天端が有効か
  integer, parameter :: e_bank_weir = 0     ! 越流のみ(単純堤防): 双方向とも天端まで不透過
  integer, parameter :: e_bank_oneway = 1   ! 樋門(逆止弁): 堤内→河道のみ透過、逆は天端まで不透過
  integer, parameter :: e_bank_pump = 2     ! 強制排水: 堤内→河道は河道水位によらず常時段落ち

  ! 堤防時の開口補正(developer.md §18)
  !   壁で恒久的に塞がれた斜め開口の通過幅シェアを、同じ横断方向の
  !   河道—河道「法線」エッジ(成分2, 4)へ振り替える。直線の幅1セル
  !   河道で通過幅が法線開口(lp ≈ 0.414)に縮退する過小通水を治し、
  !   横断方向の開口合計は面全長で厳密に保存される。斜めエッジと
  !   壁エッジ(越流の敷幅)は不変。塞がりゼロのエッジは係数1で
  !   現行と厳密一致(退化性)。frw は init で構築する静的テーブルで、
  !   時間ループでは読み取り専用(w8mx 等の重み定数と同格の扱い)
  integer :: f_bank_opening                 ! 開口補正 (0:なし, 1:振り替え)
  logical :: have_bopen = .false.           ! 開口補正が有効か(have_bank との合成)

  ! サブグリッド河道幅(developer.md §18)
  !   河道幅 W(g%wrw。セル属性)から2つの静的補正を導く:
  !   (1) 通水: 河道—河道エッジの通過幅係数を min(W_e/面長, 1) 倍する
  !       (W_e = 両セルの正の幅の最小値。frw に開口補正と重畳)。
  !   (2) 貯留: セルの平面積率 wfrac = min(W·L_ch/(dx·dy), 1) で
  !       水深換算を除算補正する(gv と同じ意味論の水深依存なし版。
  !       L_ch = 河道隣接8近傍への半距離の総和)。
  !   W ≥ 面長・平面積率 1 のセルでは係数がちょうど 1 となり、
  !   解像河道(掘り込み+壁)の表現と厳密に一致する(退化性)。
  !   セル内の非河道部の貯留は表現しない(河道セルの水位=河道内水位)
  integer :: f_channel_advection            ! 河道セルを含むエッジの移流項 (1:通常, 0:落とす)
  logical :: have_width = .false.           ! サブグリッド河道幅が有効か(g%width_active)
  logical :: have_frw = .false.             ! エッジ通過幅係数 frw が有効か
                                            !   (have_bopen または have_width)
  logical :: adv_drop_rw = .false.          ! 河道セルを含むエッジで移流項を落とすか
  real, allocatable :: frw(:,:,:)           ! エッジ別通過幅係数 (1:4, 0:nx, jsh-1:jeh)。
                                            !   開口補正は法線成分 2, 4 のみ、幅キャップは
                                            !   河道—河道の全成分に乗る
  real, allocatable :: wfrac(:,:)           ! セルの河道平面積率 (1:nx, jsh:jeh)。
                                            !   非河道・幅情報なしセルは 1
  ! 破堤(developer.md §18)
  !   サイト(河道セル・堤内地セルの対=エッジ)ごとに実効天端を
  !   時系列 f(t)(1=天端高, 0=堤内地盤高)で変える。サイトリストと
  !   行バケットは submodule m_swflow_enc_channel の私有状態
  !   (bank_wall が同 submodule 内で参照するため親には出さない)
  logical :: have_breach = .false.          ! 破堤サイトがあるか(breach_init が設定)

  real, allocatable :: cwx(:,:), cwy(:,:)   ! セルの方向別通水率 (1:nx, js:je)。
                                            !   幅キャップによるセル開口の減衰率
                                            !   (キャップ後/キャップ前の開口和の比)。
                                            !   continuous / restore_uvmn が u,v を
                                            !   これで除算し、vv・摩擦・抗力・移流が
                                            !   河道内流速を見る。m,n は正規化しない
                                            !   (§18。フラックス測線の実流量の条件)

  ! 状態変数の構造体の宣言と定義
  type t_enc_status
    real, allocatable :: uv(:,:,:)   ! セル境界での流速(符合は中心セルから近傍セルに向かい正)
    real, allocatable :: mn(:,:,:)   ! セル境界での流量(時刻n。ステップ中は読み取り専用)
    real, allocatable :: mn1(:,:,:)  ! セル境界での流量の書き込み先(時刻n+1。completeでmnへコミット)
    real, allocatable :: h1(:,:)     ! セル中心での計算済み水深
    logical :: initialized = .false.
  end type
  type(t_enc_status) :: sx_mod


  !--------------------------------------------------------------------
  ! モジュール内で共有される重み係数の定義
  !--------------------------------------------------------------------
  ! 中心セルから見たk近傍セルのインデックス
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

  ! 中心セルから見たk近傍の境界フラックスのインデックス
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]

  ! 界面エッジ行の成分補完マスク(dje(1:4) = [-1,-1,-1,0] に対応)
  !   行 js-1: 南隣セル(j=js-1, dje=0)が書く成分 → k=4 を南から取る
  !   行 je  : 北隣セル(j=je+1, dje=-1)が書く成分 → k=1,2,3 を北から取る
  !   dje を変更する場合はここも必ず更新すること
  logical, parameter :: esync_s(1:4) = [.false., .false., .false., .true. ]
  logical, parameter :: esync_n(1:4) = [.true.,  .true.,  .true.,  .false.]

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
  real :: lpx, lpy, ldx, ldy     ! 通過幅シェア(法線 lp・斜め ld。開口補正が使う)
  real :: r8x(1:8)               ! din(:)/dx
  real :: r8y(1:8)               ! djn(:)/dy
  real :: n8x(1:8)               ! k軸の単位ベクトルのx方向成分
  real :: n8y(1:8)               ! k軸の単位ベクトルのy方向成分
  real :: w8mx(1:8)              ! k軸のフラックスからセル中心でのx方向平均量への寄与率
  real :: w8my(1:8)              ! k軸のフラックスからセル中心でのy方向平均量への寄与率
  real :: mn2dh(1:8)             ! k軸の単位幅流量から中心セルの水深減少量への変換係数


  interface
    module subroutine adv_init(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine adv_prepare(p, g, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      type(t_enc_status), intent(in) :: sx
    end subroutine
    module function adv_edge(s, sx, i, j, k, in, jn, ie, je) result(ta)
      type(t_state), intent(in) :: s
      type(t_enc_status), intent(in) :: sx
      integer, intent(in) :: i, j, k, in, jn, ie, je
      real :: ta
    end function
    module subroutine adv_dispose()
    end subroutine
  end interface

  ! 境界条件の適用層(submodule m_swflow_enc_bc)
  interface
    module subroutine bc_init(p, g, b)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
    end subroutine
    module subroutine boundary_h(p, g, b, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
      type(t_state), intent(inout) :: s
      type(t_enc_status), intent(inout) :: sx
    end subroutine
    module subroutine boundary_uvmn(p, g, b, s, sx)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
      type(t_state), intent(in) :: s
      type(t_enc_status), intent(inout) :: sx
    end subroutine
    module function bc_open_face(in, jn) result(op)
      integer, intent(in) :: in, jn
      logical :: op
    end function
    module subroutine bc_dispose()
    end subroutine
  end interface

  ! 河道水理モデルの構築・壁面適用層(submodule m_swflow_enc_channel)。
  ! 状態(frw/wfrac/cwx/cwy と有効フラグ)は親カーネルのホットパスが
  ! 読むため親に置き、submodule は構築と壁面上書きを担う(§18)
  interface
    module subroutine build_channel_frw(g)
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine build_wfrac(g)
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine bank_wall(p, g, s, i, j, in, jn, uve1, mne1)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      integer, intent(in) :: i, j, in, jn
      real, intent(inout) :: uve1, mne1
    end subroutine
    module subroutine breach_init(p, g, s, ch)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
      type(t_list_channel), intent(in) :: ch
    end subroutine
    module subroutine breach_update(t)
      real, intent(in) :: t
    end subroutine
    module subroutine breach_dispose()
    end subroutine
  end interface

contains
 
!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! ENCの初期化
!----------------------------------------------------------------------
subroutine m_swflow_enc_init(p, g, b, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  type(t_list_enc) :: list
  type(t_list_channel) :: chlist



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

  ! 河道条件ファイルから堤防の水理モードを読む(未指定ならデフォルト値)
  if (len_trim(p%fn_channel) > 0) call list_channel_read(p, chlist)
  f_bank_mode = chlist%f_bank_mode
  f_bank_opening = chlist%f_bank_opening
  f_channel_advection = chlist%f_channel_advection

  ! 堤防(仮想壁面)・河道幅の有効判定は geoinfo の構築結果に従う
  have_bank = g%bank_active
  have_width = g%width_active
  if (f_bank_mode < e_bank_weir .or. f_bank_mode > e_bank_pump) then
    call par_stop("list_channel: f_bank_mode は 0(越流のみ), 1(樋門), 2(強制排水) のいずれか")
  end if
  if (f_bank_opening < 0 .or. f_bank_opening > 1) then
    call par_stop("list_channel: f_bank_opening は 0(なし), 1(振り替え) のいずれか")
  end if
  if (f_channel_advection < 0 .or. f_channel_advection > 1) then
    call par_stop("list_channel: f_channel_advection は 0(落とす), 1(通常) のいずれか")
  end if
  ! 有効判定は namelist 由来+geoinfo の構築結果で全ランク同一
  have_bopen = have_bank .and. f_bank_opening > 0
  have_frw = have_bopen .or. have_width
  adv_drop_rw = have_bank .and. f_channel_advection == 0

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
  call init_weights(p, g)

  ! エッジ通過幅係数(開口補正+幅キャップ)とセル平面積率を構築する
  ! (通過幅シェア lp/ld を使うため init_weights より後。zbank / wrw は
  ! 帯+ハロ(scatter_coeffs 済み)、rw/sw/x はゾーン2で全域=
  ! 全ランクが自分の帯+ハロ行を冗長構築する)
  if (have_frw) call build_channel_frw(g)
  if (have_width) call build_wfrac(g)

  ! 破堤サイトの解釈・検証・行バケット構築(zbank の帯と s%z を読むため
  ! この位置。have_breach を設定する)
  call breach_init(p, g, s, chlist)

  ! 境界条件の適用層を初期化する(辺型・面型・基準水位・流入区間の
  ! 開口幅の構築。開口幅が l8 を使うため init_weights より後に)
  call bc_init(p, g, b)

  ! 初期条件を設定する
  call init_enc_status(p, g, s, sx_mod)

  ! 移流項計算サブモジュールを初期化する
  call adv_init(p, g)

  ! 高速摩擦計算ルーチンを初期化する
  call m_ffactor_init(f_friction_fastmath, p%dd, 30.0, 'UV')

  ! 水深の境界条件をセットする
  !   init 時点で実効なのはため池の初期吸収だけ: 降雨は s%pre=0
  !   (makepre は run_main が初期化後に呼ぶ)、ソースは q=0
  !   (makebdc 未実行)で、どちらも構造的に +0 となる。
  !   restore 時も安全: 保存状態は最終ステップの boundary_h 適用後
  !   なので、ため池転送は冪等(保存 h>0 はため池満杯時のみ)。
  !   この前提を崩す変更(makepre の前倒し、pre の初期条件化等)を
  !   する場合はここを要再検討(developer.md §15)
  call boundary_h(p, g, b, s, sx_mod)

  ! エッジの強制条件(境界面流量)を初期水深から初期化する(complete が
  ! mn1→mn にコミットするので、初回ステップの RK が読む「前ステップの
  ! 境界流量」が内部エッジ(init_enc_status で初期化)と同格になる)。
  ! リスタート時は呼ばない: 保存された uv/mn に境界面の値が含まれており、
  ! 復元後の h(保存時の連続式適用後)から再計算すると保存時の値
  ! (適用前の h 起源)と食い違い、厳密復元が破れる
  if (p%f_state_restore <= 0) then
    call boundary_uvmn(p, g, b, s, sx_mod)
  end if

  ! 変数を更新して次のタイムステップの準備をする
  call complete(p, g, s, sx_mod)

end subroutine


!----------------------------------------------------------------------
! ENCの計算
!----------------------------------------------------------------------
subroutine m_swflow_enc_calc(p, g, b, s, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  integer, intent(inout) :: ierror

  ! ステップ頭: 前ステップ確定状態のハロ交換
  !   h/u/v/vv は幅2(移流項のハロ再計算=案Aの依存)、mn は幅1。
  !   交換対象と幅の根拠は developer.md §11 のステンシル解析を参照
  call par_halo_cell(s%h)
  call par_halo_cell(s%u)
  call par_halo_cell(s%v)
  call par_halo_cell(s%z)
  call par_halo_cell(s%vv)
  call par_halo_edge(sx_mod%mn)

  ! 破堤サイトの現時刻の実効天端を更新する(サイト数ぶんの時系列補間。
  ! t の純関数なので全ランクが同値を冗長計算する=通信不要)
  if (have_breach) call breach_update(s%t)

  ! 移流項を計算する
  call adv_prepare(p, g, s, sx_mod)

  ! 運動方程式を解いて流速を計算する
  call momentum(p, g, s, sx_mod, ierror)

  ! 界面エッジ行(js-1, je)の所有成分を南北で補完し合う
  ! (同一エッジのフラックスを共有 → 質量保存がビット厳密になる)
  call par_edge_merge(sx_mod%uv,  esync_s, esync_n)
  call par_edge_merge(sx_mod%mn1, esync_s, esync_n)

  ! エッジの流速・流量への強制条件をセットする(辺境界の流出、
  ! 区間流入など。各条件の有効判定は boundary_uvmn 内の節ごとに行う)
  call boundary_uvmn(p, g, b, s, sx_mod)

  ! 連続式を解いて水深を更新する
  call continuous(p, g, s, sx_mod)

  ! 水深の境界条件をセットする
  call boundary_h(p, g, b, s, sx_mod)

  ! 変数を更新して次のタイムステップの準備をする
  call complete(p, g, s, sx_mod)
end subroutine


!----------------------------------------------------------------------
! ENCの終了
!----------------------------------------------------------------------
subroutine m_swflow_enc_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%f_state_save > 0) call save_state(p, sx_mod)
  call bc_dispose
  call del_enc_status(sx_mod)
  if (allocated(frw)) deallocate(frw)
  if (allocated(wfrac)) deallocate(wfrac)
  if (allocated(cwx)) deallocate(cwx)
  if (allocated(cwy)) deallocate(cwy)
  call breach_dispose
  have_bopen = .false.
  have_width = .false.
  have_frw = .false.
  call m_ffactor_dispose
  call adv_dispose
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 重み係数の初期化
!----------------------------------------------------------------------
subroutine init_weights(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g

  integer :: k
  real :: dr

  dr = sqrt(g%dx**2 + g%dy**2)

  forall(k=1:8) din2(k) = din(k)**2
  forall(k=1:8) djn2(k) = djn(k)**2
  forall(k=1:8) r8x(k) = real(din(k)) / g%dx
  forall(k=1:8) r8y(k) = real(djn(k)) / g%dy

  w8dr(1:8) = [ dr, g%dy, dr, g%dx, g%dx, dr, g%dy, dr ]
  forall(k=1:8) w8dr2(k) = w8dr(k)**2

  ! k軸の単位ベクトルのx, y方向成分
  n8x(1:8) = [ -g%dx/dr,  0.0,  g%dx/dr, -1.0, 1.0, -g%dx/dr, 0.0, g%dx/dr ]
  n8y(1:8) = [ -g%dy/dr, -1.0, -g%dy/dr,  0.0, 0.0,  g%dy/dr, 1.0, g%dy/dr ]

  ! フラックスの通過幅の割合
  !   lpy, ldyはy軸に投影したLの長さのΔyに対する割合(x方向フラックスが通過)
  !   lpx, ldxはx軸に投影したLの長さのΔxに対する割合(y方向フラックスが通過)
  !   lpy, lpxは斜め方向、ldy, ldxは軸方向
  !   ここで lpx + (ldx * 2) = 1, lpy + (ldy * 2) = 1 である
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * p_diagratio
    ldy = p_diagratio / 2 * (g%dx / g%dy)**2
    lpx = 1 - p_diagratio
    ldx = p_diagratio / 2
  else
    lpy = 1 - p_diagratio
    ldy = p_diagratio / 2
    lpx = 1 - (g%dy / g%dx)**2 * p_diagratio
    ldx = p_diagratio / 2 * (g%dy / g%dx)**2
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
  forall(k=1:8) l8(k) = sqrt((l8y(k) * g%dy)**2 + (l8x(k) * g%dx)**2)

  ! セル境界の流速・流量からセル中心の平均流速・平均流量の増分を計算するための係数
  !   セル中心から近傍に向かうフラックスuvをn8x, n8yで除して投影前のxとyの正の方向成分に戻す
  !   近傍の方向に応じた開口幅(辺長)をl8x, l8yで調整し、
  !   セルの左右(上下)の平均をとるために2で割る
  w8mx(1:8) = [ 1/n8x(1), 0.0, 1/n8x(3), 1/n8x(4), 1/n8x(5), 1/n8x(6), 0.0, 1/n8x(8) ]
  w8my(1:8) = [ 1/n8y(1), 1/n8y(2), 1/n8y(3), 0.0, 0.0, 1/n8y(6), 1/n8y(7), 1/n8y(8) ]
  forall(k=1:8) w8mx(k) = w8mx(k) * l8y(k) / 2
  forall(k=1:8) w8my(k) = w8my(k) * l8x(k) / 2

  ! セル境界での単位幅流量から中心セルの1時間ステップでの水位減少量を計算するための係数
  forall(k=1:8) mn2dh(k) = (l8(k) / (g%dx * g%dy)) * p%dt

end subroutine




!----------------------------------------------------------------------
! 状態変数の初期化と初期条件の設定
!----------------------------------------------------------------------
subroutine init_enc_status(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(out) :: sx

  real :: ue, ve
  integer :: i, j, k, in, jn, ie, je

  ! メモリを確保する
  ! エッジ配列の j 範囲: セル j を挟むエッジは j-1 と j なので下限は jsh-1
  allocate(sx%uv(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)
  allocate(sx%h1(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(sx%mn1(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)
  allocate(sx%mn(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)

  ! 流速の初期条件を設定する
  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ie, je, ue, ve)
  do j = dcp%js, dcp%je
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

  ! 水深の初期条件を設定する
  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      sx%h1(i,j) = s%h(i,j)
    end do
  end do
  !$omp end parallel do

  if (p%f_state_restore > 0) then
    call restore_state(p, sx)
    call restore_uvmn(p, g, s, sx)
  end if

  sx%initialized = .true.

end subroutine


!----------------------------------------------------------------------
! 状態変数の削除
!----------------------------------------------------------------------
subroutine del_enc_status(sx)
  type(t_enc_status), intent(inout) :: sx
  if (allocated(sx%uv)) deallocate(sx%uv)
  if (allocated(sx%mn)) deallocate(sx%mn)
  if (allocated(sx%mn1)) deallocate(sx%mn1)
  if (allocated(sx%h1)) deallocate(sx%h1)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
! (旧 prepare: mn0=mn の繰り越しコピーは mn1 方式への移行で不要になった。
!  時刻n+1の値のコミットは complete で行う)


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
  !$omp parallel do schedule(dynamic) private(i, j, k, have_exflux, have_runge, have_error) &
  !$omp reduction(+:n_exfluxes), reduction(+:n_runge), reduction(+:n_error)
  ! This loop should be an independ "omp parallel do"
  do j = dcp%js, dcp%je
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
    call par_info("**********************************************************************")
    call par_info("********* Unrealistic calculation (Velocity exceeds 250 m/s) *********")
    call par_info("**********************************************************************")
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
  real :: maglim, maglim_inv

  ! この文はこの場所になければならない
  have_exflux = .false.
  have_runge = .false.
  have_error = .false.

  ! k近傍セルのインデックスを計算する
  !   領域外との遮断は x 番兵(x=0。確保 0:nx+1)が一手に担う。
  !   エッジ配列は (0:nx) 確保のため枠上セルのエッジ添字も範囲内で、
  !   枠の添字ガードは不要(境界面の定義は docs/boundary_plan.md §4.3)
  in = i + din(k)
  jn = j + djn(k)
  if (g%x(in,jn) <= 0) return

  ! k近傍セルとの境界フラックスのインデックスを計算する
  ie = i + die(k)
  je = j + dje(k)

  ! 移動限界水深未満の場合は流量ゼロ(ddを大きくすると過大流出が増える)
  if (s%h(i,j) < p%dd .and. s%h(in,jn) < p%dd) then
    sx%uv(k,ie,je) = 0
    sx%mn1(k,ie,je) = 0
    return
  end if

  ! セル境界の流速をセットする(前ステップ値=無印から読む)
  uve = sx%uv(k,ie,je)
  mne = sx%mn(k,ie,je)

  ! セル境界の移流項をセットする
  !   f_channel_advection=0 のときは河道セルを含むエッジで移流を落とす
  !   (サブグリッド幅の強い不均質下での安定化オプション。§18)
  if (f_advection_term > 0) then
    tae = adv_edge(s, sx, i, j, k, in, jn, ie, je)
    if (adv_drop_rw) then
      if (g%rw(i,j) > 0 .or. g%rw(in,jn) > 0) tae = 0
    end if
  else
    tae = 0
  end if

  ! 中心セルi,jからk近傍セルin,jnへの流速uv1と単位幅流量mn1を計算する
  call calc_kth_flux(p, g, s, sx, uve, tae, i, j, k, in, jn, 0, uve1, mne1)

  ! 適応的ルンゲクッタ
  !   流速または流量がmaglim倍以上、1/maglim以下、逆方向に変化した場合はルンゲクッタで再計算
  maglim = p_adprunge_thresh
  maglim_inv = 1.0 / maglim
  if (f_adaptive_runge > 0) then
    if ((mne >= 0 .and. (mne1 > mne * maglim .or. mne1 < mne * maglim_inv)) .or. &
        (mne < 0  .and. (mne1 < mne * maglim .or. mne1 > mne * maglim_inv))) then
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

  ! 堤防(仮想壁面)エッジの流速・流量の上書き(submodule m_swflow_enc_channel)
  if (have_bank) call bank_wall(p, g, s, i, j, in, jn, uve1, mne1)

  ! セル境界での単位幅流量から境界の両側のセルでの水深の減少量を計算する
  !   通過幅係数有効時はエッジ別係数 frw を乗じる(k<=4 は成分=k)。
  !   河道幅有効時はセルの平面積率 wfrac で水深換算を除算補正する
  dh = mne1 * mn2dh(k)    ! 家屋占有率がゼロの場合の中心セルの水深減少量
  if (have_frw) dh = dh * frw(k,ie,je)
  dhc = dh / g%gv(i,j)
  dhn = -dh / g%gv(in,jn)
  if (have_width) then
    dhc = dhc / wfrac(i,j)
    dhn = dhn / wfrac(in,jn)
  end if

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
  !   uvは単一バッファ(自エッジread-then-writeのみ。developer.md §7の例外)
  sx%uv(k,ie,je) = uve1

  ! セル境界の流量を更新する(書き込みは時刻n+1バッファへ)
  sx%mn1(k,ie,je) = mne1

contains
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
  lme = (g%lm(i,j) + g%lm(in,jn)) / 2       ! 有効慣性係数
  if (gve == 1) bbe = 1.e10                 ! 家屋なしの場合は家屋サイズは大きな値

  ! 摩擦項で使用する流速
  !   静止からの流動開始直後に流速が小さいために摩擦が過小となることを防ぐために
  !   (この現象は正攻法では時間刻みを極めて小さくしないと解消しない)
  vve = max(vve, p%vv)

  ! セル境界での有効重力加速度を計算
  ge = p%gg                                 ! 重力加速度
  if (f_gravity_correction > 0) ge = correct_ge()

  ! セル境界での底面勾配項(符合は中心セルから近傍セルに向かい正)
  tg0e = -ge * (s%z(in,jn) - s%z(i,j)) / w8dr(k) * gve

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
    tfe = tfe - p%kk * p%cd * hhe / bbe * (1 - gve) * vve / 2

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
      real :: fwc, fwn
      real :: winvc, winvn
      integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
      real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]
      ! セル境界での流速の絶対値を更新
      vve = sqrt(uve1**2 + vue2)

      ! 河道幅有効時のセル平面積率の逆数(無効時は 1.0 の乗算で厳密に不変)
      winvc = 1.0
      winvn = 1.0
      if (have_width) then
        winvc = 1.0 / wfrac(i,j)
        winvn = 1.0 / wfrac(in,jn)
      end if

      ! 仮の水深を更新
      !   式の詳細は連続式を解くルーチン内のコメントを参照のこと
      hc = hc0       ! 中心セルの水深
      hn = hn0       ! 近傍セルの水深
      do kk = 1, 8
        ! 中心セルと近傍セルの方位kkにおける流量
        !   前ステップ確定値(無印mn)を参照する。更新中のmn1を読むと
        !   スレッドタイミング依存のデータ競合になる(developer.md §8)
        mnec = sign_e(kk) * sx%mn(ke(kk),i+die(kk),j+dje(kk))   ! 中心セルからそのkk近傍への流量
        mnen = sign_e(kk) * sx%mn(ke(kk),in+die(kk),jn+dje(kk)) ! 近傍セルからそのkk近傍への流量
        ! 方位k(近傍セルでは方位9-k)は今回更新された流量
        if (kk == k) mnec = mne1
        if (kk == 9 - k) mnen = -mne1     ! 近傍セルの流出量は中心セルの流出量の逆符号
        ! 通過幅係数有効時はエッジ別係数を乗じる(無効時は 1.0 の
        ! 乗算で厳密に不変)
        fwc = 1.0
        fwn = 1.0
        if (have_frw) then
          fwc = frw(ke(kk),i+die(kk),j+dje(kk))
          fwn = frw(ke(kk),in+die(kk),jn+dje(kk))
        end if
        ! 仮の水深を更新
        hc = hc - mnec * mn2dh(kk) * fwc * winvc / g%gv(i,j) / a(l)
        hn = hn - mnen * mn2dh(kk) * fwn * winvn / g%gv(in,jn) / a(l)
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
      ge_corr = ge * w8dr2(k) / (w8dr2(k) + (s%z(in,jn) - s%z(i,j))**2)
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
  real :: uve, mne
  real :: dh
  real :: fw, winv
  real :: mnmax
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ie, je, uve, mne, dh, fw, winv, mnmax)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle
      if (g%x(i,j) <= 0) cycle
      s%u(i,j) = 0
      s%v(i,j) = 0
      s%m(i,j) = 0
      s%n(i,j) = 0
      sx%h1(i,j) = s%h(i,j)
      ! 河道幅有効時のセル平面積率の逆数(無効時は 1.0 の乗算で厳密に不変)
      winv = 1.0
      if (have_width) winv = 1.0 / wfrac(i,j)
      mnmax = 0
      ! 対象セルi,jの8近傍全ての水の流出入を計算し平均流量・流速と水位を更新する
      s%ddir1(i,j) = 0
      s%ddir8(i,j) = 0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) > 0) then
          ! ここでddと比較するのは前時間ステップでの値hでなければならない
          ! そのためこのループ内でhを直接更新してはいけない
          if (s%h(i,j) < p%dd .and. s%h(in,jn) < p%dd) cycle
        else
          ! 開いた辺の境界面は取り込む(流出が h1 と u,v,m,n に乗る)。
          ! 枠外近傍の s%h は確保範囲外のため dd 判定はしない
          ! (乾燥時は boundary_uvmn が 0 を書いており寄与も 0)
          if (.not. have_open_bc) cycle
          if (.not. bc_open_face(in, jn)) cycle
        end if
        ! 中心セルi,jから見たk近傍の境界フラックスのインデックス
        ie = i + die(k)
        je = j + dje(k)
        ! 境界での流速と流量を求める(中心から近傍に向かい正)
        !   近傍5~8は隣接するセルから見た(9-k)近傍に相当する(向きは逆)
        uve = sign_e(k) * sx%uv(ke(k),ie,je)
        mne = sign_e(k) * sx%mn1(ke(k),ie,je)
        ! 通過幅係数有効時はエッジ別係数を乗じる(無効時は 1.0 の
        ! 乗算で厳密に不変。質量換算と平均量の重みを同時に補正する)
        fw = 1.0
        if (have_frw) fw = frw(ke(k),ie,je)
        ! 水深の減少量(m)に換算
        !   家屋占有率が0.0で無い場合はここで補正係数を乗じる。
        !   河道幅有効時は平面積率 wfrac の逆数 winv も乗じる
        dh = mne * mn2dh(k) * fw * winv / g%gv(i,j)
        ! 水深を更新
        sx%h1(i,j) = sx%h1(i,j) - dh
        ! セル中心の平均流速・流量への寄与分を加算
        s%u(i,j) = s%u(i,j) + uve * (w8mx(k) * fw)
        s%v(i,j) = s%v(i,j) + uve * (w8my(k) * fw)
        s%m(i,j) = s%m(i,j) + mne * (w8mx(k) * fw)
        s%n(i,j) = s%n(i,j) + mne * (w8my(k) * fw)
        ! 流下方向を判定
        !if (mne > mnmax) s%ddir1(i,j) = 2**k             ! 最大流出方向
        if (mne > mnmax) then
          s%ddir1(i,j) = 2**k             ! 最大流出方向
          mnmax = mne
        end if
        if (dh > 0) s%ddir8(i,j) = s%ddir8(i,j) + 2**k   ! 全ての流出方向
      end do
      ! 河道幅有効セルは u,v をセル方向別通水率で正規化する(vv・摩擦・
      ! 抗力・移流が河道内流速を見る。m,n は流量積分の意味論を保つため
      ! 正規化しない=フラックス測線の実流量が保たれる条件。§18)
      if (have_width) then
        s%u(i,j) = s%u(i,j) / cwx(i,j)
        s%v(i,j) = s%v(i,j) / cwy(i,j)
      end if
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
  type(t_enc_status), intent(inout) :: sx
  integer :: i, j 
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  ! 流量のコミット: 時刻n+1の値を正準状態へ(セルの h1→h と対をなす)
  !   エッジの書き込み集合はセル窓より i,j とも1つ外側(die/dje=-1)に
  !   張り出すため、セルループに畳み込まず、行範囲 js-1..je で行う。
  !   ここでは行丸ごとメモリ転送するのでschedule(static)でよい
  !$omp parallel do schedule(static)
  do j = dcp%js - 1, dcp%je
    sx%mn(:,:,j) = sx%mn1(:,:,j)
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      s%h(i,j) = sx%h1(i,j)
      s%e(i,j) = s%h(i,j) + s%z(i,j)
      s%vv(i,j) = sqrt(s%u(i,j)**2 + s%v(i,j)**2)
      s%qq(i,j) = sqrt(s%m(i,j)**2 + s%n(i,j)**2)
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! restoreしたsx%uv,sx%mnからs%u,s%v,s%m,s%n,s%vv,s%qq,s%eを復元する
!   (vv は摩擦項が complete より前に読む、qq は t=0 の出力・計測が読む)
!   セルループの範囲・スキップ・重み・総和順は continuous と完全に
!   一致させること(復元値が保存時の値とビット一致する条件)。
!   continuous にある乾燥エッジ条件(h<dd 両セル)の複製は不要:
!   momentum が同条件のエッジの uv/mn1 を 0 に零化しているため、
!   無条件に総和しても寄与が 0 でスキップと同値になる
!----------------------------------------------------------------------
subroutine restore_uvmn(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_enc_status), intent(inout) :: sx
  integer :: i, j, k
  integer :: in, jn, ie, je
  real :: uve, mne
  real :: fw
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  !$omp parallel do schedule(dynamic) private(i, j, k, in, jn, ie, je, uve, mne, fw)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%sw(i,j) > 0) cycle   ! 海セルは continuous 同様に除外(u,v,m,n,vv,qq は 0 のまま)
      if (g%x(i,j) <= 0) cycle
      s%u(i,j) = 0.0
      s%v(i,j) = 0.0
      s%m(i,j) = 0.0
      s%n(i,j) = 0.0
      do k = 1, 8
        ! 中心セルi,jから見たk近傍セルのインデックス
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) then
          ! 開いた辺の境界面は continuous と同様に取り込む
          ! (取り込み条件は continuous と常に同時に更新すること)
          if (.not. have_open_bc) cycle
          if (.not. bc_open_face(in, jn)) cycle
        end if
        ! 中心セルi,jから見たk近傍の境界フラックスのインデックス
        ie = i + die(k)
        je = j + dje(k)
        ! 境界での流速と流量を求める(中心から近傍に向かい正)
        !   近傍5~8は隣接するセルから見た(9-k)近傍に相当する(向きは逆)
        uve = sign_e(k) * sx%uv(ke(k),ie,je)
        mne = sign_e(k) * sx%mn1(ke(k),ie,je)
        ! 通過幅係数は continuous と完全に一致させる(復元ビット一致の条件)
        fw = 1.0
        if (have_frw) fw = frw(ke(k),ie,je)
        ! セル中心の平均流速・流量への寄与分を加算
        s%u(i,j) = s%u(i,j) + uve * (w8mx(k) * fw)
        s%v(i,j) = s%v(i,j) + uve * (w8my(k) * fw)
        s%m(i,j) = s%m(i,j) + mne * (w8mx(k) * fw)
        s%n(i,j) = s%n(i,j) + mne * (w8my(k) * fw)
      end do
      ! u,v の正規化は continuous と完全に一致させる(復元ビット一致の条件)
      if (have_width) then
        s%u(i,j) = s%u(i,j) / cwx(i,j)
        s%v(i,j) = s%v(i,j) / cwy(i,j)
      end if
      s%e(i,j) = s%h(i,j) + s%z(i,j)
      s%vv(i,j) = sqrt(s%u(i,j)**2 + s%v(i,j)**2)
      s%qq(i,j) = sqrt(s%m(i,j)**2 + s%n(i,j)**2)
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine save_state(p, sx)
  type(t_sysparam), intent(in) :: p
  type(t_enc_status), intent(in) :: sx
  integer :: un
  real, allocatable :: wuv(:,:,:), wmn(:,:,:)
  ! 全域バッファに集約してから rank0 のみが書く。
  ! バッファ形状・帯外ゼロとも旧形式(全域確保時)とバイト互換
  if (is_root) then
    allocate(wuv(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
    allocate(wmn(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
  else
    allocate(wuv(1, 1, 1), source = 0.0)   ! 参照されないダミー
    allocate(wmn(1, 1, 1), source = 0.0)
  end if
  call par_gather_edge_to(wuv, sx%uv)
  call par_gather_edge_to(wmn, sx%mn)
  if (.not. is_root) return
  ! swflow の dispose は m_state より先に走るため、save ディレクトリは
  ! ここでも作る(sysdep_mkdir は冪等・rank0 限定)
  call sysdep_mkdir(p%dir_save)
  open(newunit=un, file=trim(p%dir_save)//'/swflow_enc.dat', form='unformatted', status='replace')
  ! ゼロ抑制 RLE で書く(乾燥エッジ・海域エッジのゼロを圧縮。§7)
  call fileio_write_rle(un, wuv)
  call fileio_write_rle(un, wmn)
  close(un)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine restore_state(p, sx)
  type(t_sysparam), intent(in) :: p
  type(t_enc_status), intent(inout) :: sx
  integer :: un
  real, allocatable :: wuv(:,:,:), wmn(:,:,:)
  character(:), allocatable :: fname
  logical :: found

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている。
  ! ここでは自ファイルの有無のみ確認する(developer.md §7)。
  ! 無い場合は黙ってスキップせず停止(保存時の格子系が ENC でない疑い)
  fname = trim(p%dir_save)//'/swflow_enc.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("swflow_enc の保存ファイルがありません(保存時の格子系は ENC でしたか): "//fname)
  end if

  ! rank0 だけが全域一時配列に読み、par_scatter_edge で各ランクの
  ! エッジ確保範囲(jsh-1:jeh)へ直接配布する(旧 Bcast 方式の置き換え。
  ! 非 root は全域一時を確保しない。全域一時が rank0 に残るのは
  ! RLE ストリームが先頭からの逐次展開のため。developer.md §7)
  if (is_root) then
    allocate(wuv(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
    allocate(wmn(1:4, 0:dcp%nx_g, 0:dcp%ny_g), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wuv)
    call fileio_read_rle(un, wmn)
    close(un)
  else
    allocate(wuv(1, 1, 1), source = 0.0)   ! 参照されないダミー
    allocate(wmn(1, 1, 1), source = 0.0)
  end if
  call par_scatter_edge(wuv, sx%uv)
  call par_scatter_edge(wmn, sx%mn)
  sx%mn1(:,:,:) = sx%mn(:,:,:)   ! 書き込みバッファも正準状態で初期化する
end subroutine



!===== 8方位コロケート格子計算終了 ====================================
!======================================================================
end module
