module m_boundary
  ! 境界条件のデータ供給層(スキーム非依存。docs/boundary_plan.md)。
  !   - 辺境界(edge): 計算領域外縁4辺の境界条件型(不透過/自由流出/長波放射)。
  !     適用(離散化)は m_swflow_XX 側(ENC は boundary_uvmn)。
  !     方角と添字の正本: 西= i=1、東= i=nx、北= j=1(ラスタ上端)、
  !     南= j=ny(m_georef の北西隅原点・行順に一致)
  !   - 内部ソース(source): 湧き出し・吸い込み(複数。セル集合+
  !     流量時系列 Q(t)、負値=吸い込み)。makebdc が現時刻の
  !     セルあたり水深増分 q を毎ステップ用意し、適用は
  !     m_swflow_enc の boundary_h。
  !   - 水位規定セル群(stage): セル集合の水位を η(t) に強制する
  !     (流域出口の流出境界、背水・感潮域等。複数)。makebdc が
  !     現時刻の η を用意し、適用は boundary_h の最後
  !     (h = max(η − z, 0) のクランプ。最優先)。周囲との面フラックス
  !     は momentum が通常計算するため u,v,m,n・record に自然に乗る。
  !   - 区間流入(inflow): 外縁に接するセル区間に流量時系列 Q(t) を
  !     規定する(河川流入等。複数)。適用は boundary_uvmn(区間の
  !     外縁法線面の mn1 規定=指向性の流入。辺の型を面単位で上書き)。
  !     流入は非負(流出は stage / source を使う)。
  !   - 内部水理構造物(structure): ポンプ・カルバート等の共通骨格
  !     (2つのセル集合+水理則 Q+質量保存転送。§22)。設定は独立
  !     ファイル fn_structure、実装は submodule m_boundary_structure。
  !     makebdc が水理則で目標流量を決め、適用は boundary_h の転送節。
  ! 族が肥大したら族別モジュールに分割する(boundary_plan.md §4.1。
  ! 内部水理構造物族は 2026-08-07 に submodule へ分割済み)
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : par_stop, par_warn, is_root, dcp, &
                       par_allreduce_sumr, par_allreduce_maxi
  use m_util, only : itoa
  use list_boundary, only : t_list_boundary, list_boundary_read, &
                            nbsrcmax, nsrccmax, nsrcvmax
  implicit none
  private

  public :: t_boundary
  public :: m_boundary_init
  public :: m_boundary_set_etaref
  public :: m_boundary_dispose
  public :: m_boundary_makebdc
  public :: e_bc_wall, e_bc_outflow, e_bc_radiation, e_bc_inflow
  public :: e_side_w, e_side_e, e_side_n, e_side_s
  ! 共有補助手続き(submodule m_boundary_structure も使う)。private のままだと
  ! gfortran が全呼び出しをインライン化してシンボルを局所化・消去し、
  ! submodule からのホスト結合参照がリンク不能になる(実際に踏んだ)
  public :: interp_series, read_cell_file2

  ! 辺境界の型コード
  integer, parameter :: e_bc_wall = 0      ! 不透過(既定)
  integer, parameter :: e_bc_outflow = 1   ! 自由流出(洪水向け: 通過流+段落ち)
  integer, parameter :: e_bc_radiation = 2 ! 長波放射(津波向け: 水位偏差を透過)
  integer, parameter :: e_bc_inflow = 3    ! 流量規定面(区間流入。面単位の内部型。
                                           !   f_bc_* の値としては指定不可)

  ! 辺番号(btype の添字)
  integer, parameter :: e_side_w = 1       ! 西 (i=1)
  integer, parameter :: e_side_e = 2       ! 東 (i=nx)
  integer, parameter :: e_side_n = 3       ! 北 (j=1: ラスタ上端)
  integer, parameter :: e_side_s = 4       ! 南 (j=ny)

  ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
  type t_bound_edge
    integer :: btype(1:4) = e_bc_wall      ! 4辺の境界条件型 (W, E, N, S)
    real :: eta_man(1:4) = -9999.0         ! 基準水位の明示指定値 (-9999=未指定)
    real, allocatable :: eta_cell(:,:)     ! 確定した基準水位(セル別。
                                           !   (j,W/E)・(i,N/S)。set_etaref が構築)
  end type

  type t_bound_src                         ! 湧き出し・吸い込み1個
    integer :: ncell = 0                   ! セル数
    integer, allocatable :: cell(:,:)      ! セル座標 (1:2, 1:ncell)
    integer :: nval = 0                    ! 時系列データ数
    real, allocatable :: val(:,:)          ! 時系列 (1:2, 1:nval) (s, m3/s)
    real :: q = 0.0                        ! 現時刻のセルあたり水深増分 (m)。
                                           !   等体積分配の dx·dy 換算値で、
                                           !   空隙率 gv は適用側で除す
  end type

  type t_bound_stage                       ! 水位規定セル群1個
    integer :: ncell = 0                   ! セル数
    integer, allocatable :: cell(:,:)      ! セル座標 (1:2, 1:ncell)
    integer :: nval = 0                    ! 時系列データ数
    real, allocatable :: val(:,:)          ! 時系列 (1:2, 1:nval) (s, m)。
                                           !   固定値指定は1点時系列に退化
    real :: eta = 0.0                      ! 現時刻の規定水位 (m)
  end type

  type t_bound_inflow                      ! 区間流入1個
    integer :: ncell = 0                   ! 面エントリ数(角セルは辺ごとに複製)
    integer, allocatable :: cell(:,:)      ! セル座標 (1:2, 1:ncell)
    integer, allocatable :: side(:)        ! 各エントリの辺 (e_side_*)
    integer :: nval = 0                    ! 時系列データ数
    real, allocatable :: val(:,:)          ! 時系列 (1:2, 1:nval) (s, m3/s)
    real :: q = 0.0                        ! 現時刻の流量 (m3/s)
    integer :: dist = 0                    ! 区間内の配分モード(0:開口幅で均等、
                                           !   1:水深按分=流入流速一様、
                                           !   2:通水能按分=重み h^{5/3})
    integer :: nsval = 0                   ! 流入土砂濃度の時系列データ数(0=指定なし)
    real, allocatable :: sval(:,:)         ! 濃度時系列 (1:2, 1:nsval) (s, m3/m3)
    integer :: nqsval = 0                  ! 流入流砂量の時系列データ数(0=指定なし。
                                           !   濃度時系列と区間ごとに排他)
    real, allocatable :: qsval(:,:)        ! 流砂量時系列 (1:2, 1:nqsval) (s, m3/s 固体体積)
    real :: cs = 0.0                       ! 現時刻の流入体積濃度 (m3/m3)。
                                           !   流砂量指定では cs = Qs(t)/Q(t) の等価濃度
                                           !   (注入総量 = Qs・dt が厳密。Q=0 の間は
                                           !   注入されない=水が運ぶ)
    integer :: ncsclip = 0                 ! 等価濃度の上限クリップ発動回数
  end type

  ! 内部水理構造物族の水理則の共通インターフェース(§22)。
  ! 目標流量 Q を上下流の基準値の純関数として返す(履歴状態なし)。
  ! 引数に t_structure 自身を渡さないのは前方参照の循環を避けるため
  ! (手続きポインタ成分の interface は型定義より前に必要)
  abstract interface
    function i_struct_law(rule, nrule, geom, refu, refd) result(q)
      real, intent(in) :: rule(:,:)        ! 運転ルール折れ線(種別ごとの意味)
      integer, intent(in) :: nrule         ! 折れ線の点数
      real, intent(in) :: geom(:)          ! 形状等の定数(種別ごとの意味)
      real, intent(in) :: refu             ! 取水(上流)側の基準値 (m)
      real, intent(in) :: refd             ! 吐口(下流)側の基準値 (m)
      real :: q                            ! 目標流量 (m3/s。符号付き >0 = cin→cout)
    end function
  end interface

  ! 内部水理構造物の種別コード
  integer, parameter :: e_struct_pump = 1     ! 排水ポンプ
  integer, parameter :: e_struct_culvert = 2  ! カルバート(矩形断面・双方向)
  integer, parameter :: e_struct_diversion = 3 ! 分水(rating による受動的な一方向取水)

  type t_structure                         ! 内部水理構造物1基(§22)。
                                           !   共通骨格: 取水セル群 cin → 吐口セル群
                                           !   cout(または域外)+ 水理則 law による
                                           !   目標流量 Q + 質量保存転送(適用は
                                           !   boundary_h)。水理則は手続きポインタ
                                           !   成分で切り替える(排他切替の様式)
    integer :: kind = 0                    ! 種別 (e_struct_*)
    integer :: ncin = 0                    ! 取水セル数
    integer, allocatable :: cin(:,:)       ! 取水セル座標 (1:2, 1:ncin)
    integer :: ncout = 0                   ! 吐口セル数(0 = 域外排水。ポンプのみ)
    integer, allocatable :: cout(:,:)      ! 吐口セル座標 (1:2, 1:ncout)
    integer :: f_ref = 0                   ! 基準の選択(種別ごとの意味。ポンプ:
                                           !   0=水位η, 1=水深h。代表セル=各セル群の
                                           !   先頭)
    integer :: nrule = 0                   ! 運転ルール折れ線の点数
    real, allocatable :: rule(:,:)         ! 折れ線 (1:2, 1:nrule) (基準値 m, m3/s)。
                                           !   ポンプの一定流量 pump_q0 は1点折れ線に
                                           !   退化。線形補間・範囲外端値(=現在状態の
                                           !   純関数。履歴状態なし)
    real :: geom(1:10) = 0.0               ! 形状等の定数(種別ごとの意味。ポンプは未使用)
    procedure(i_struct_law), pointer, nopass :: law => null()  ! 水理則
    real :: q = 0.0                        ! 現時刻の目標流量 (m3/s。makebdc が更新。
                                           !   符号付き >0 = cin→cout)
  end type

  type t_boundary
    type(t_bound_edge) :: edge             ! 辺境界
    integer :: nsrc = 0                    ! ソース数
    type(t_bound_src), allocatable :: src(:)  ! 湧き出し・吸い込み
    integer :: nstage = 0                  ! 水位規定セル群の数
    type(t_bound_stage), allocatable :: stage(:)  ! 水位規定セル群
    integer :: ninflow = 0                 ! 区間流入の数
    type(t_bound_inflow), allocatable :: inflow(:)  ! 区間流入
    real, allocatable :: csin(:,:)         ! 境界流入濃度のセル別テーブル (m3/m3)。
                                           !   濃度指定のある区間が1つでもあれば確保し、
                                           !   makebdc が毎ステップ現時刻値を書く。
                                           !   swflow_enc の advect_scalar が境界面からの
                                           !   流入の風上濃度として読む(未確保=全て清水)
    integer :: nstruct = 0                 ! 内部水理構造物の数
    type(t_structure), allocatable :: struct(:)  ! 内部水理構造物(§22)
    logical :: initialized = .false.
  end type

  ! 内部水理構造物族の実装は submodule m_boundary_structure(§22)
  interface
    module subroutine init_structure(b, p, g)
      type(t_boundary), intent(inout) :: b
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
    end subroutine
    module subroutine structure_makebdc(b, p, g, s)
      type(t_boundary), intent(inout) :: b
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
    end subroutine
  end interface

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 境界条件の読み込み・検証・位置解決(初期化ゾーン2: 全域マスク前提)
!----------------------------------------------------------------------
subroutine m_boundary_init(b, p, g)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_boundary) :: list

  b%initialized = .true.

  !--- 境界条件パラメータファイル(fn_boundary)の族 ---
  if (len_trim(p%fn_boundary) > 0) then
    call list_boundary_read(p, list)

    !--- 辺境界 ---
    call init_edge(b, list)

    !--- 内部ソース(湧き出し・吸い込み) ---
    call init_source(b, p, g, list)

    !--- 水位規定セル群 ---
    call init_stage(b, p, g, list)

    !--- 区間流入 ---
    call init_inflow(b, p, g, list)
  end if

  !--- 内部水理構造物族(独立ファイル fn_structure。fn_boundary の
  !    有無に依らず初期化する。§22)---
  call init_structure(b, p, g)

end subroutine


!----------------------------------------------------------------------
! 現時刻の境界条件値を用意する(毎ステップ、swflow より前に呼ぶ)
!----------------------------------------------------------------------
subroutine m_boundary_makebdc(b, p, g, s)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: isrc, istage, ifl
  real :: q

  !--- 各ソースの現時刻の流量をセル1個・1ステップあたりの水深増分に換算 ---
  do isrc = 1, b%nsrc
    q = interp_series(b%src(isrc)%val, b%src(isrc)%nval, s%t)
    b%src(isrc)%q = q / (b%src(isrc)%ncell * g%dx * g%dy) * p%dt
  end do

  !--- 各水位規定セル群の現時刻の規定水位を補間 ---
  do istage = 1, b%nstage
    b%stage(istage)%eta = interp_series(b%stage(istage)%val, b%stage(istage)%nval, s%t)
  end do

  !--- 各区間流入の現時刻の流量を補間 ---
  do ifl = 1, b%ninflow
    b%inflow(ifl)%q = interp_series(b%inflow(ifl)%val, b%inflow(ifl)%nval, s%t)
    ! 流入土砂濃度(指定のある区間のみ)。セル別テーブルは自帯の行だけ書く
    ! (advect_scalar が読むのは自帯セルのみ=ハロ不要)
    if (b%inflow(ifl)%nsval > 0) then
      b%inflow(ifl)%cs = interp_series(b%inflow(ifl)%sval, b%inflow(ifl)%nsval, s%t)
    else if (b%inflow(ifl)%nqsval > 0) then
      ! 流砂量指定: cs = Qs/Q の等価濃度に還元(按分が水と自動連動し、
      ! 注入総量 = cs×流入水量 = Qs・dt が厳密)。Q=0 の間は注入なし。
      ! Qs/Q が体積濃度として非物理(>=1)になる設定はクリップして
      ! dispose で警告する(黙らない)
      block
        real :: qs2
        qs2 = interp_series(b%inflow(ifl)%qsval, b%inflow(ifl)%nqsval, s%t)
        if (b%inflow(ifl)%q > 0.0) then
          b%inflow(ifl)%cs = qs2 / b%inflow(ifl)%q
          if (b%inflow(ifl)%cs >= 1.0) then
            b%inflow(ifl)%cs = 1.0
            b%inflow(ifl)%ncsclip = b%inflow(ifl)%ncsclip + 1
          end if
        else
          b%inflow(ifl)%cs = 0.0
        end if
      end block
    end if
    if (b%inflow(ifl)%nsval > 0 .or. b%inflow(ifl)%nqsval > 0) then
      block
        integer :: m2, i2, j2
        do m2 = 1, b%inflow(ifl)%ncell
          i2 = b%inflow(ifl)%cell(1,m2)
          j2 = b%inflow(ifl)%cell(2,m2)
          if (j2 >= dcp%js .and. j2 <= dcp%je) b%csin(i2,j2) = b%inflow(ifl)%cs
        end do
      end block
    end if
  end do

  !--- 各内部水理構造物の現時刻の目標流量を水理則から決める(§22。
  !    実装は submodule m_boundary_structure)---
  if (b%nstruct > 0) call structure_makebdc(b, p, g, s)

end subroutine


!----------------------------------------------------------------------
! 放射境界の基準水位を確定する(m_state_init の直後に呼ぶ)
!   優先順位:
!     (1) bc_eta_* の明示指定(一様値)
!     (2) 初期条件が水位固定(f_htype=2)なら一様 e0(乾いた境界セルも
!         海面基準で排水される)
!     (3) それ以外は境界セルの初期水位 s%e(セルごと)
!   (3) は初期条件と厳密に整合し、t=0 の放射フラックスが全境界セルで
!   厳密にゼロになる。restore 時は復元状態から再導出する(「保存状態を
!   初期条件に使う」restore の意味論と整合。復元時に波が境界を通過中だと
!   基準がずれる点は既知の制約)。
!   MPI: 各ランクは自分が参照しうる行(帯+ハロ)だけを埋める。共有行は
!   隣接ランクが同じ s%e(帯切り出しで同値)から冗長に導出する(通信不要)
!----------------------------------------------------------------------
subroutine m_boundary_set_etaref(b, p, g, s)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: sd, i, j
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (.not. any(b%edge%btype == e_bc_radiation)) return
  allocate(b%edge%eta_cell(1:max(g%nx, g%ny), 1:4), source = 0.0)

  do sd = 1, 4
    if (b%edge%btype(sd) /= e_bc_radiation) cycle
    if (b%edge%eta_man(sd) > -9998.0) then
      b%edge%eta_cell(:,sd) = b%edge%eta_man(sd)       ! 明示指定(一様)
    else if (s%ini%f_htype == 2) then
      b%edge%eta_cell(:,sd) = s%ini%e0                 ! 水位固定の初期条件と同値
    else
      ! 境界セルの初期水位から導出
      select case (sd)
        case (e_side_w)
          do j = dcp%jsh, dcp%jeh
            b%edge%eta_cell(j,sd) = s%e(1,j)
          end do
        case (e_side_e)
          do j = dcp%jsh, dcp%jeh
            b%edge%eta_cell(j,sd) = s%e(g%nx,j)
          end do
        case (e_side_n)
          if (dcp%jsh <= 1 .and. 1 <= dcp%jeh) then
            do i = 1, g%nx
              b%edge%eta_cell(i,sd) = s%e(i,1)
            end do
          end if
        case (e_side_s)
          if (dcp%jsh <= g%ny .and. g%ny <= dcp%jeh) then
            do i = 1, g%nx
              b%edge%eta_cell(i,sd) = s%e(i,g%ny)
            end do
          end if
      end select
    end if
  end do

end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_boundary_dispose(b)
  type(t_boundary), intent(inout) :: b
  if (allocated(b%src)) deallocate(b%src)
  if (allocated(b%stage)) deallocate(b%stage)
  if (allocated(b%inflow)) then
    ! 流砂量指定の等価濃度クリップの報告(全ランク同値のため root のみ表示)
    block
      integer :: ifl2
      do ifl2 = 1, b%ninflow
        if (b%inflow(ifl2)%ncsclip > 0 .and. is_root) then
          call par_warn("bound_inflow: 区間 "//itoa(ifl2)//" で Qs/Q が体積濃度 1 を" &
                        //"超え "//itoa(b%inflow(ifl2)%ncsclip)//" 回クリップしました" &
                        //"(流量と流砂量の整合を確認してください)")
        end if
      end do
    end block
    deallocate(b%inflow)
  end if
  if (allocated(b%csin)) deallocate(b%csin)
  if (allocated(b%struct)) deallocate(b%struct)
  if (allocated(b%edge%eta_cell)) deallocate(b%edge%eta_cell)
  b%nsrc = 0
  b%nstage = 0
  b%ninflow = 0
  b%nstruct = 0
  b%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 辺境界の解釈と検証
!----------------------------------------------------------------------
subroutine init_edge(b, list)
  type(t_boundary), intent(inout) :: b
  type(t_list_boundary), intent(in) :: list
  character(len=1), parameter :: side_name(1:4) = ['w', 'e', 'n', 's']
  integer :: bt(1:4)
  integer :: sd

  if (.not. list%present_edge) return

  bt(e_side_w) = list%f_bc_w
  bt(e_side_e) = list%f_bc_e
  bt(e_side_n) = list%f_bc_n
  bt(e_side_s) = list%f_bc_s
  do sd = 1, 4
    if (bt(sd) < e_bc_wall .or. bt(sd) > e_bc_radiation) then
      call par_stop("list_bound_edge: f_bc_"//side_name(sd) &
                    //" は 0(不透過)・1(自由流出)・2(放射) を指定してください: "//itoa(bt(sd)))
    end if
  end do
  b%edge%btype = bt
  b%edge%eta_man(e_side_w) = list%bc_eta_w
  b%edge%eta_man(e_side_e) = list%bc_eta_e
  b%edge%eta_man(e_side_n) = list%bc_eta_n
  b%edge%eta_man(e_side_s) = list%bc_eta_s

end subroutine


!----------------------------------------------------------------------
! 内部ソースの解釈・検証・格納
!   セル集合と時系列は namelist 配列(番兵 -9999 で終端)または
!   ファイル指定。位置の検証は全域マスク(ゾーン2)で全ランク冗長に行う
!----------------------------------------------------------------------
subroutine init_source(b, p, g, list)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_boundary), intent(in) :: list
  logical :: active(1:nbsrcmax)
  integer :: isrc, n, k, i, j

  if (.not. list%present_source) return

  !--- 有効なソース(セルか時系列かファイル指定がある)を数える ---
  do isrc = 1, nbsrcmax
    active(isrc) = (list%src_cell(1,1,isrc) > -9999) &
                   .or. (list%src_val(1,1,isrc) > -9999) &
                   .or. (len_trim(list%fn_src_cell(isrc)) > 0) &
                   .or. (len_trim(list%fn_src_val(isrc)) > 0)
  end do
  b%nsrc = count(active)
  if (b%nsrc <= 0) return
  if (.not. all(active(1:b%nsrc))) then
    call par_stop("list_bound_source: ソース番号は 1 から連続で指定してください")
  end if

  allocate(b%src(1:b%nsrc))

  do isrc = 1, b%nsrc

    !--- セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_src_cell(isrc)) > 0) then
      call read_cell_file(trim(p%dir_data)//"/"//trim(list%fn_src_cell(isrc)), b%src(isrc))
    else
      n = 0
      do k = 1, nsrccmax
        if (list%src_cell(1,k,isrc) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(b%src(isrc)%cell(1:2,1:max(n,1)))
      b%src(isrc)%cell(1:2,1:n) = list%src_cell(1:2,1:n,isrc)
      b%src(isrc)%ncell = n
    end if

    !--- 流量時系列(ファイル指定が優先。namelist の時刻は分→秒に換算) ---
    if (len_trim(list%fn_src_val(isrc)) > 0) then
      call read_val_file(trim(p%dir_data)//"/"//trim(list%fn_src_val(isrc)), b%src(isrc))
    else
      n = 0
      do k = 1, nsrcvmax
        if (list%src_val(1,k,isrc) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(b%src(isrc)%val(1:2,1:max(n,1)))
      b%src(isrc)%val(1,1:n) = list%src_val(1,1:n,isrc) * 60   ! 分を秒に換算
      b%src(isrc)%val(2,1:n) = list%src_val(2,1:n,isrc)
      b%src(isrc)%nval = n
    end if

    !--- 検証 ---
    if (b%src(isrc)%ncell <= 0) then
      call par_stop("list_bound_source: ソース "//itoa(isrc)//" にセルがありません")
    end if
    if (b%src(isrc)%nval <= 0) then
      call par_stop("list_bound_source: ソース "//itoa(isrc)//" に時系列がありません")
    end if
    do k = 1, b%src(isrc)%ncell
      i = b%src(isrc)%cell(1,k)
      j = b%src(isrc)%cell(2,k)
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_bound_source: ソース "//itoa(isrc)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_bound_source: ソース "//itoa(isrc)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
    end do

  end do

end subroutine


!----------------------------------------------------------------------
! 水位規定セル群の解釈・検証・格納
!   セル集合は namelist 配列(番兵 -9999 終端)またはファイル。
!   規定水位は固定値(stage_eta)か時系列(stage_val / fn_stage_val)。
!   固定値は1点時系列に退化させ、実行時は単一経路にする
!----------------------------------------------------------------------
subroutine init_stage(b, p, g, list)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_boundary), intent(in) :: list
  logical :: active(1:nbsrcmax)
  integer :: istage, n, k, i, j

  if (.not. list%present_stage) return

  !--- 有効な群(セルか水位かファイル指定がある)を数える ---
  do istage = 1, nbsrcmax
    active(istage) = (list%stage_cell(1,1,istage) > -9999) &
                     .or. (list%stage_eta(istage) > -9998.0) &
                     .or. (list%stage_val(1,1,istage) > -9999) &
                     .or. (len_trim(list%fn_stage_cell(istage)) > 0) &
                     .or. (len_trim(list%fn_stage_val(istage)) > 0)
  end do
  b%nstage = count(active)
  if (b%nstage <= 0) return
  if (.not. all(active(1:b%nstage))) then
    call par_stop("list_bound_stage: 群番号は 1 から連続で指定してください")
  end if

  allocate(b%stage(1:b%nstage))

  do istage = 1, b%nstage

    !--- セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_stage_cell(istage)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_stage_cell(istage)), &
                           b%stage(istage)%ncell, b%stage(istage)%cell)
    else
      n = 0
      do k = 1, nsrccmax
        if (list%stage_cell(1,k,istage) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(b%stage(istage)%cell(1:2,1:max(n,1)))
      b%stage(istage)%cell(1:2,1:n) = list%stage_cell(1:2,1:n,istage)
      b%stage(istage)%ncell = n
    end if

    !--- 規定水位(時系列ファイル > namelist 時系列 > 固定値の優先順) ---
    if (len_trim(list%fn_stage_val(istage)) > 0) then
      call read_val_file2(trim(p%dir_data)//"/"//trim(list%fn_stage_val(istage)), &
                          b%stage(istage)%nval, b%stage(istage)%val)
    else if (list%stage_val(1,1,istage) > -9999) then
      n = 0
      do k = 1, nsrcvmax
        if (list%stage_val(1,k,istage) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(b%stage(istage)%val(1:2,1:max(n,1)))
      b%stage(istage)%val(1,1:n) = list%stage_val(1,1:n,istage) * 60   ! 分を秒に換算
      b%stage(istage)%val(2,1:n) = list%stage_val(2,1:n,istage)
      b%stage(istage)%nval = n
    else if (list%stage_eta(istage) > -9998.0) then
      ! 固定値は1点時系列に退化(補間は常に固定値を返す)
      allocate(b%stage(istage)%val(1:2,1:1))
      b%stage(istage)%val(1,1) = 0.0
      b%stage(istage)%val(2,1) = list%stage_eta(istage)
      b%stage(istage)%nval = 1
    end if

    !--- 検証 ---
    if (b%stage(istage)%ncell <= 0) then
      call par_stop("list_bound_stage: 群 "//itoa(istage)//" にセルがありません")
    end if
    if (b%stage(istage)%nval <= 0) then
      call par_stop("list_bound_stage: 群 "//itoa(istage) &
                    //" に規定水位(stage_eta か時系列)がありません")
    end if
    do k = 1, b%stage(istage)%ncell
      i = b%stage(istage)%cell(1,k)
      j = b%stage(istage)%cell(2,k)
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_bound_stage: 群 "//itoa(istage)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_bound_stage: 群 "//itoa(istage)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
    end do

    !--- 計算開始時刻の規定水位を初期化する ---
    !   swflow の init は boundary_h(クランプ適用)を呼ぶが、その時点で
    !   makebdc は未実行。ここで初期化しないと型既定値 0 で初期クランプ
    !   され、規定セルが t=0 に不正に排水される(実際に踏んだバグ)
    b%stage(istage)%eta = interp_series(b%stage(istage)%val, b%stage(istage)%nval, p%t0)

  end do

end subroutine


!----------------------------------------------------------------------
! セル一覧ファイルを読む(各行 "i j")
!----------------------------------------------------------------------
subroutine read_cell_file(fname, src)
  character(len=*), intent(in) :: fname
  type(t_bound_src), intent(inout) :: src
  integer :: un, n, k, ios

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//fname)
  n = 0
  do
    read(un, *, iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)
  allocate(src%cell(1:2,1:max(n,1)))
  do k = 1, n
    read(un, *) src%cell(1,k), src%cell(2,k)
  end do
  close(un)
  src%ncell = n

end subroutine


!----------------------------------------------------------------------
! 流量時系列ファイルを読む(各行 "時刻(min) 流量(m3/s)"。時刻は秒に換算)
!----------------------------------------------------------------------
subroutine read_val_file(fname, src)
  character(len=*), intent(in) :: fname
  type(t_bound_src), intent(inout) :: src
  integer :: un, n, k, ios
  real :: t, val

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//fname)
  n = 0
  do
    read(un, *, iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)
  allocate(src%val(1:2,1:max(n,1)))
  do k = 1, n
    read(un, *) t, val
    src%val(1,k) = t * 60
    src%val(2,k) = val
  end do
  close(un)
  src%nval = n

end subroutine


!----------------------------------------------------------------------
! 区間流入の解釈・検証・格納
!   セル集合(外縁に接するセル列)は namelist 配列またはファイル。
!   流量は時系列(namelist かファイル)で、非負のみ(流出は stage /
!   source を使う)。角セル(2辺に接する)は辺ごとにエントリを複製し、
!   両方の法線面から按分流入する
!----------------------------------------------------------------------
subroutine init_inflow(b, p, g, list)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_boundary), intent(in) :: list
  logical :: active(1:nbsrcmax)
  integer :: ncell
  integer, allocatable :: cell(:,:)
  integer :: sides(1:4), nsides
  integer :: ifl, n, k, m, i, j

  if (.not. list%present_inflow) return

  !--- 有効な区間(セルか時系列かファイル指定がある)を数える ---
  do ifl = 1, nbsrcmax
    active(ifl) = (list%inflow_cell(1,1,ifl) > -9999) &
                  .or. (list%inflow_val(1,1,ifl) > -9999) &
                  .or. (len_trim(list%fn_inflow_cell(ifl)) > 0) &
                  .or. (len_trim(list%fn_inflow_val(ifl)) > 0)
  end do
  b%ninflow = count(active)
  if (b%ninflow <= 0) return
  if (.not. all(active(1:b%ninflow))) then
    call par_stop("list_bound_inflow: 区間番号は 1 から連続で指定してください")
  end if

  allocate(b%inflow(1:b%ninflow))

  do ifl = 1, b%ninflow

    !--- セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_inflow_cell(ifl)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_inflow_cell(ifl)), &
                           ncell, cell)
    else
      n = 0
      do k = 1, nsrccmax
        if (list%inflow_cell(1,k,ifl) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(cell(1:2,1:max(n,1)))
      cell(1:2,1:n) = list%inflow_cell(1:2,1:n,ifl)
      ncell = n
    end if
    if (ncell <= 0) then
      call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" にセルがありません")
    end if

    !--- 流量時系列(ファイル指定が優先) ---
    if (len_trim(list%fn_inflow_val(ifl)) > 0) then
      call read_val_file2(trim(p%dir_data)//"/"//trim(list%fn_inflow_val(ifl)), &
                          b%inflow(ifl)%nval, b%inflow(ifl)%val)
    else
      n = 0
      do k = 1, nsrcvmax
        if (list%inflow_val(1,k,ifl) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(b%inflow(ifl)%val(1:2,1:max(n,1)))
      b%inflow(ifl)%val(1,1:n) = list%inflow_val(1,1:n,ifl) * 60   ! 分を秒に換算
      b%inflow(ifl)%val(2,1:n) = list%inflow_val(2,1:n,ifl)
      b%inflow(ifl)%nval = n
    end if
    if (b%inflow(ifl)%nval <= 0) then
      call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" に流量時系列がありません")
    end if
    do k = 1, b%inflow(ifl)%nval
      if (b%inflow(ifl)%val(2,k) < 0) then
        call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" の流量は非負のみです" &
                      //"(流出は stage / source を使用)")
      end if
    end do

    !--- 流入土砂の濃度時系列(任意。未指定 = 清水流入)---
    if (len_trim(list%fn_inflow_cs(ifl)) > 0) then
      call read_val_file2(trim(p%dir_data)//"/"//trim(list%fn_inflow_cs(ifl)), &
                          b%inflow(ifl)%nsval, b%inflow(ifl)%sval)
    else
      n = 0
      do k = 1, ubound(list%inflow_cs, 2)
        if (list%inflow_cs(1,k,ifl) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      if (n > 0) then
        allocate(b%inflow(ifl)%sval(1:2,1:n))
        b%inflow(ifl)%sval(1,1:n) = list%inflow_cs(1,1:n,ifl) * 60   ! 分を秒に換算
        b%inflow(ifl)%sval(2,1:n) = list%inflow_cs(2,1:n,ifl)
        b%inflow(ifl)%nsval = n
      end if
    end if
    do k = 1, b%inflow(ifl)%nsval
      if (b%inflow(ifl)%sval(2,k) < 0.0 .or. b%inflow(ifl)%sval(2,k) >= 1.0) then
        call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" の濃度は" &
                      //" [0,1) の体積濃度で指定してください")
      end if
    end do

    !--- 流入土砂の流砂量時系列(任意。濃度時系列と区間ごとに排他)---
    if (len_trim(list%fn_inflow_qs(ifl)) > 0) then
      call read_val_file2(trim(p%dir_data)//"/"//trim(list%fn_inflow_qs(ifl)), &
                          b%inflow(ifl)%nqsval, b%inflow(ifl)%qsval)
    else
      n = 0
      do k = 1, ubound(list%inflow_qs, 2)
        if (list%inflow_qs(1,k,ifl) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      if (n > 0) then
        allocate(b%inflow(ifl)%qsval(1:2,1:n))
        b%inflow(ifl)%qsval(1,1:n) = list%inflow_qs(1,1:n,ifl) * 60   ! 分を秒に換算
        b%inflow(ifl)%qsval(2,1:n) = list%inflow_qs(2,1:n,ifl)
        b%inflow(ifl)%nqsval = n
      end if
    end if
    do k = 1, b%inflow(ifl)%nqsval
      if (b%inflow(ifl)%qsval(2,k) < 0.0) then
        call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" の流砂量は非負のみです")
      end if
    end do
    if (b%inflow(ifl)%nsval > 0 .and. b%inflow(ifl)%nqsval > 0) then
      call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" で濃度(inflow_cs)と" &
                    //"流砂量(inflow_qs)は同時に指定できません(排他)")
    end if

    !--- 検証と (セル, 辺) エントリの構築(角セルは辺ごとに複製) ---
    allocate(b%inflow(ifl)%cell(1:2,1:2*ncell))   ! 複製ぶんの余裕
    allocate(b%inflow(ifl)%side(1:2*ncell))
    m = 0
    do k = 1, ncell
      i = cell(1,k)
      j = cell(2,k)
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
      nsides = 0
      if (i == 1)    then; nsides = nsides + 1; sides(nsides) = e_side_w; end if
      if (i == g%nx) then; nsides = nsides + 1; sides(nsides) = e_side_e; end if
      if (j == 1)    then; nsides = nsides + 1; sides(nsides) = e_side_n; end if
      if (j == g%ny) then; nsides = nsides + 1; sides(nsides) = e_side_s; end if
      if (nsides == 0) then
        call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が計算領域外縁に接していません")
      end if
      do n = 1, nsides
        m = m + 1
        b%inflow(ifl)%cell(1,m) = i
        b%inflow(ifl)%cell(2,m) = j
        b%inflow(ifl)%side(m) = sides(n)
      end do
    end do
    b%inflow(ifl)%ncell = m
    deallocate(cell)

    !--- 配分モード ---
    b%inflow(ifl)%dist = list%inflow_dist(ifl)
    if (b%inflow(ifl)%dist < 0 .or. b%inflow(ifl)%dist > 2) then
      call par_stop("list_bound_inflow: 区間 "//itoa(ifl)//" の inflow_dist は" &
                    //" 0(均等)/1(水深按分)/2(通水能按分)で指定してください")
    end if

    !--- 計算開始時刻の流量を初期化する(stage と同じ理由。swflow init の
    !    boundary_uvmn が makebdc より先に走る) ---
    b%inflow(ifl)%q = interp_series(b%inflow(ifl)%val, b%inflow(ifl)%nval, p%t0)
    if (b%inflow(ifl)%nsval > 0) then
      b%inflow(ifl)%cs = interp_series(b%inflow(ifl)%sval, b%inflow(ifl)%nsval, p%t0)
    else if (b%inflow(ifl)%nqsval > 0) then
      if (b%inflow(ifl)%q > 0.0) then
        b%inflow(ifl)%cs = min(interp_series(b%inflow(ifl)%qsval, &
                               b%inflow(ifl)%nqsval, p%t0) / b%inflow(ifl)%q, 1.0)
      end if
    end if

  end do

  !--- 境界流入濃度のセル別テーブル(濃度指定のある区間が1つでもあれば
  !    確保。値は makebdc が毎ステップ書く。未確保 = 全区間清水) ---
  do ifl = 1, b%ninflow
    if (b%inflow(ifl)%nsval > 0 .or. b%inflow(ifl)%nqsval > 0) then
      allocate(b%csin(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
      exit
    end if
  end do

end subroutine


!----------------------------------------------------------------------
! セル一覧ファイルを読む(各行 "i j"。汎用版)
!----------------------------------------------------------------------
subroutine read_cell_file2(fname, ncell, cell)
  character(len=*), intent(in) :: fname
  integer, intent(out) :: ncell
  integer, allocatable, intent(out) :: cell(:,:)
  integer :: un, n, k, ios

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//fname)
  n = 0
  do
    read(un, *, iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)
  allocate(cell(1:2,1:max(n,1)))
  do k = 1, n
    read(un, *) cell(1,k), cell(2,k)
  end do
  close(un)
  ncell = n

end subroutine


!----------------------------------------------------------------------
! 時系列ファイルを読む(各行 "時刻(min) 値"。時刻は秒に換算。汎用版)
!----------------------------------------------------------------------
subroutine read_val_file2(fname, nval, val)
  character(len=*), intent(in) :: fname
  integer, intent(out) :: nval
  real, allocatable, intent(out) :: val(:,:)
  integer :: un, n, k, ios
  real :: t, v

  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: "//fname)
  n = 0
  do
    read(un, *, iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)
  allocate(val(1:2,1:max(n,1)))
  do k = 1, n
    read(un, *) t, v
    val(1,k) = t * 60
    val(2,k) = v
  end do
  close(un)
  nval = n

end subroutine


!----------------------------------------------------------------------
! 時系列 val(1,:)=時刻(s), val(2,:)=値 を時刻 t で線形補間する
! (範囲外は端の値を保持)
!----------------------------------------------------------------------
function interp_series(val, n, t) result(q)
  real, intent(in) :: val(:,:)
  integer, intent(in) :: n
  real, intent(in) :: t
  real :: q
  real :: t0, t1, q0, q1
  integer :: k

  if (t <= val(1,1)) then             ! 最初の時刻よりも前の場合
    q = val(2,1)
  else if (t > val(1,n)) then         ! 最後の時刻より後の場合
    q = val(2,n)
  else
    q = val(2,n)
    do k = 2, n
      t1 = val(1,k)
      if (t < t1) then
        t0 = val(1,k-1)
        q0 = val(2,k-1)
        q1 = val(2,k)
        q = q0 + (t - t0) / (t1 - t0) * (q1 - q0)
        exit
      end if
    end do
  end if

end function

end module
