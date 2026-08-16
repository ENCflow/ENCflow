module list_geomorph
  ! 地形変化条件設定ファイル(namelist)の読み込み。
  ! この層は生の値(未指定 = 型宣言のデフォルトが番兵)を運ぶだけで、
  ! 解釈・補完・検証は m_geomorph が行う(list_* 層の共通契約)
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_geomorph
  public :: list_geomorph_read

  type t_list_geomorph
    ! --- 実行制御 ---
    real :: dt_geomorph = 0.0        ! 地形変化の更新時間間隔 (s)。0なら毎ステップ
    real :: morfac = 1.0             ! 加速係数(地形時間の加速。全プロセス共通)

    ! --- プロセス別フラグ(排他選択ではなく重ね合わせ。0:無効) ---
    ! 各プロセスは独立に有効化でき、calc は有効なものを順に適用する
    integer :: f_creep = 0           ! 斜面クリープ(線形拡散)(0:無効, 1:有効)
    real :: creep_d = 0.0            ! クリープ拡散係数 (m2/s)

    integer :: f_fluvial = 0         ! 掃流砂 Exner(河床の浸食・堆積)(0:無効, 1:有効)
    integer :: f_qbform = 1          ! 流砂量式(1:芦田・道上, 2:MPM)
    real :: fluv_d50 = 0.0           ! 代表粒径 (m)。f_fluvial=1 で必須
    real :: fluv_tausc = 0.05        ! 限界無次元掃流力 τ*c
    real :: fluv_porosity = 0.4      ! 河床の空隙率 λ
    real :: fluv_sgrav = 1.65        ! 土粒子の水中比重 s = (ρs - ρ)/ρ
    real :: fluv_dzmax = 0.05        ! 1エッジ・1更新の河床変動上限 (m)
    real :: fluv_diagratio = 0.5857864376  ! 斜め方向の通過幅配分(= 2/(2+√2)。
                                     ! m_swflow_enc の p_diagratio と同値の既定)
    integer :: fluv_bcfeed = 0       ! 開境界の掃流砂給砂(0:流入は無給砂,
                                     ! 1:平衡給砂。流出は常に容量輸送)

    integer :: f_suspend = 0         ! 浮遊砂(移流+浸食・沈降)(0:無効, 1:有効)
    integer :: f_esform = 1          ! 平衡濃度式(1:超過掃流力線形(簡易))
    real :: susp_d50 = 0.0           ! 浮遊砂の代表粒径 (m)。f_suspend=1 で必須
    real :: susp_wf = 0.0            ! 沈降速度 (m/s)。0 なら Rubey 式で d50 から導出
    real :: susp_tausc = 0.05        ! 浮遊の限界無次元掃流力 τ*c
    real :: susp_beta = 1.0          ! 沈降の底面濃度係数(c_b = β・C)
    real :: susp_esa = 0.0           ! 平衡濃度係数(C_eq = esa・(τ*/τ*c - 1))。
                                     ! f_suspend=1 で必須(体積濃度スケール)

    integer :: f_wash = 0            ! 斜面浸食(雨滴+面状。f_suspend が必須)(0:無効, 1:有効)
    real :: wash_kr = 0.0            ! 雨滴侵食係数(無次元。E_r = kr・降雨強度)
    real :: wash_kf = 0.0            ! 面状侵食係数 (m/s)(E_f = kf・(τ*/τ*c - 1))
    real :: wash_tausc = 0.05        ! 面状侵食の限界無次元掃流力 τ*c

    integer :: f_debris = 0          ! 土石流 E-D(高橋型平衡濃度)(0:無効, 1:有効)。
                                     ! f_suspend と排他(同一 hs 上の E-D 二重計上防止)。
                                     ! morfac=1 必須(イベント計算)。debris_plan.md §2.2
    real :: db_phi = 0.0             ! 土砂の内部摩擦角 (deg)。f_debris=1 で必須
    real :: db_delte = 0.0007        ! 侵食速度係数 δe(既定は Takahashi 2007 の一般値
                                     ! 【要文献照合】debris_plan.md §1)
    real :: db_deltd = 0.05          ! 堆積速度係数 δd(Kanako 系の慣用値【要文献照合】)
    integer :: f_dbstop = 0          ! 停止条件の切替 (0:なし(E-D の ∝|V| のみ),
                                     ! 1:低速凝集 — vv<db_vstop で超過濃度を河床へ)
    real :: db_vstop = 0.05          ! 停止判定の速度閾値 (m/s)。f_dbstop=1 の凝集と
                                     ! f_dbres=1 の降伏判定(静止維持)が共有する
    real :: db_wstop = 0.0           ! 低速凝集の河床転換レート (m/s)。f_dbstop=1 で必須
    integer :: f_dbres = 1           ! 抵抗則 (0:マニングのみ, 1:クーロン+マニング合成,
                                     ! 2:江頭構成則(降伏応力+粒子衝突・間隙流体の
                                     ! 層流抵抗。江頭ら1989 式(25)/Morpho2DH 式(17)(19)),
                                     ! 3:高橋・中川1991 石礫型(降伏 tanα'=0.45 +
                                     ! ダイラタント項 A'=4。濃度・相対水深で
                                     ! 石礫型/掃流状/泥流(マニング)を自動切替))
    integer :: f_dbed = 1            ! E-D 式 (1:高橋型平衡濃度への緩和(δe/δd。簡易形),
                                     ! 2:江頭・芦田1992 — E = |V|・C*・tan(θ−θe)。
                                     ! 流向勾配・パラメータ追加なし。Morpho2DH 式(5)-(7),
                                     ! 3:高橋・中川1991 式(12)(27) — 飽和床侵食+
                                     ! 慣性係数付き堆積。レートは δe/δd・q_T/d_L)
    real :: db_d50 = 0.0             ! 代表粒径 (m)。f_dbres=2,3 / f_dbed=3 で必須
    real :: db_erest = 0.0           ! 粒子の反発係数 e(0〜1)。f_dbres=2 で必須
                                     ! (材料固有値。文献に既定値なし)
    real :: db_cmin = 0.02           ! 江頭層流則を適用する濃度下限(これ未満は
                                     ! マニング則 = 希薄側の閉じ。層流則は C→0 で
                                     ! 発散するため必要な数値的切替。既定 2% は
                                     ! geomorph_plan.md §3 の希薄限界と整合)
    character(len=256) :: fn_dbinit = ""  ! 瞬時流動化の崩壊深分布ファイル (m)。
                                     ! 指定で f_release 有効(fn_* の有無の慣例)。
                                     ! f_debris=1 が必須。debris_plan.md §2.5
    real :: db_reltime = 0.0         ! 流動化の発生時刻 (s)。t0 以前なら最初の
                                     ! geomorph 更新で発火(1回だけ。リスタート安全)
    real :: db_relsat = 1.0          ! 崩壊土塊の飽和度 0〜1(gwflow 無効時の
                                     ! 間隙水付与 h += λ・relsat・D に使用。
                                     ! gwflow 有効時は容量超過引き渡しが担い不使用)
    integer :: f_slide = 0           ! 無限長斜面安定判定による自動流動化
                                     ! (0:無効, 1:有効)。f_debris=1 必須。
                                     ! Fs < 1 のセルの土層 sd を全層流動化する。
                                     ! 間隙水圧は gwflow の飽和厚 hg/sy0 から
                                     ! (gwflow 無効なら 0)。debris_plan.md §2.5
    real :: slide_c = 0.0            ! 有効粘着力 c' (Pa)。f_slide=1 で必須(0 可)
    real :: slide_phi = 0.0          ! 土のせん断抵抗角 φs (deg)。f_slide=1 で必須
    real :: slide_gamma = 0.0        ! 飽和単位体積重量 γt (N/m3)。f_slide=1 で必須
                                     ! (例: 18000〜20000。湿潤・飽和の区別は
                                     ! 一律 γt の近似)

    ! 将来のプロセス追加はここにフラグとパラメータを足す
    ! (例: f_badland 崩壊性浸食)
  end type

contains


!----------------------------------------------------------------------
! 地形変化条件設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_geomorph_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_geomorph), intent(out) :: list
  integer :: un, ios

  real :: dt_geomorph
  real :: morfac
  integer :: f_creep
  real :: creep_d
  integer :: f_fluvial
  integer :: f_qbform
  real :: fluv_d50
  real :: fluv_tausc
  real :: fluv_porosity
  real :: fluv_sgrav
  real :: fluv_dzmax
  real :: fluv_diagratio
  integer :: fluv_bcfeed
  integer :: f_suspend
  integer :: f_esform
  real :: susp_d50
  real :: susp_wf
  real :: susp_tausc
  real :: susp_beta
  real :: susp_esa
  integer :: f_wash
  real :: wash_kr
  real :: wash_kf
  real :: wash_tausc
  integer :: f_debris
  real :: db_phi
  real :: db_delte
  real :: db_deltd
  integer :: f_dbstop
  real :: db_vstop
  real :: db_wstop
  integer :: f_dbres
  integer :: f_dbed
  real :: db_d50
  real :: db_erest
  real :: db_cmin
  character(len=256) :: fn_dbinit
  real :: db_reltime
  real :: db_relsat
  integer :: f_slide
  real :: slide_c
  real :: slide_phi
  real :: slide_gamma

  namelist /list_geomorph/ dt_geomorph, morfac, f_creep, creep_d, &
                           f_fluvial, f_qbform, fluv_d50, fluv_tausc, &
                           fluv_porosity, fluv_sgrav, fluv_dzmax, fluv_diagratio, &
                           fluv_bcfeed, f_suspend, f_esform, susp_d50, susp_wf, susp_tausc, &
                           susp_beta, susp_esa, f_wash, wash_kr, wash_kf, wash_tausc, &
                           f_debris, db_phi, db_delte, db_deltd, f_dbstop, db_vstop, db_wstop, f_dbres, &
                           f_dbed, db_d50, db_erest, db_cmin, &
                           fn_dbinit, db_reltime, db_relsat, &
                           f_slide, slide_c, slide_phi, slide_gamma

  ! 型宣言のデフォルトを namelist 変数の初期値にする
  dt_geomorph = list%dt_geomorph
  morfac = list%morfac
  f_creep = list%f_creep
  creep_d = list%creep_d
  f_fluvial = list%f_fluvial
  f_qbform = list%f_qbform
  fluv_d50 = list%fluv_d50
  fluv_tausc = list%fluv_tausc
  fluv_porosity = list%fluv_porosity
  fluv_sgrav = list%fluv_sgrav
  fluv_dzmax = list%fluv_dzmax
  fluv_diagratio = list%fluv_diagratio
  fluv_bcfeed = list%fluv_bcfeed
  f_suspend = list%f_suspend
  f_esform = list%f_esform
  susp_d50 = list%susp_d50
  susp_wf = list%susp_wf
  susp_tausc = list%susp_tausc
  susp_beta = list%susp_beta
  susp_esa = list%susp_esa
  f_wash = list%f_wash
  wash_kr = list%wash_kr
  wash_kf = list%wash_kf
  wash_tausc = list%wash_tausc
  f_debris = list%f_debris
  db_phi = list%db_phi
  db_delte = list%db_delte
  db_deltd = list%db_deltd
  f_dbstop = list%f_dbstop
  db_vstop = list%db_vstop
  db_wstop = list%db_wstop
  f_dbres = list%f_dbres
  f_dbed = list%f_dbed
  db_d50 = list%db_d50
  db_erest = list%db_erest
  db_cmin = list%db_cmin
  fn_dbinit = list%fn_dbinit
  db_reltime = list%db_reltime
  db_relsat = list%db_relsat
  f_slide = list%f_slide
  slide_c = list%slide_c
  slide_phi = list%slide_phi
  slide_gamma = list%slide_gamma

  call par_info("reading list_geomorph in " // trim(p%fn_geomorph))
  open(newunit=un, file=trim(p%fn_geomorph), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_geomorph))
  read(un, nml=list_geomorph, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_geomorph")
  close(un)

  list%dt_geomorph = dt_geomorph
  list%morfac = morfac
  list%f_creep = f_creep
  list%creep_d = creep_d
  list%f_fluvial = f_fluvial
  list%f_qbform = f_qbform
  list%fluv_d50 = fluv_d50
  list%fluv_tausc = fluv_tausc
  list%fluv_porosity = fluv_porosity
  list%fluv_sgrav = fluv_sgrav
  list%fluv_dzmax = fluv_dzmax
  list%fluv_diagratio = fluv_diagratio
  list%fluv_bcfeed = fluv_bcfeed
  list%f_suspend = f_suspend
  list%f_esform = f_esform
  list%susp_d50 = susp_d50
  list%susp_wf = susp_wf
  list%susp_tausc = susp_tausc
  list%susp_beta = susp_beta
  list%susp_esa = susp_esa
  list%f_wash = f_wash
  list%wash_kr = wash_kr
  list%wash_kf = wash_kf
  list%wash_tausc = wash_tausc
  list%f_debris = f_debris
  list%db_phi = db_phi
  list%db_delte = db_delte
  list%db_deltd = db_deltd
  list%f_dbstop = f_dbstop
  list%db_vstop = db_vstop
  list%db_wstop = db_wstop
  list%f_dbres = f_dbres
  list%f_dbed = f_dbed
  list%db_d50 = db_d50
  list%db_erest = db_erest
  list%db_cmin = db_cmin
  list%fn_dbinit = fn_dbinit
  list%db_reltime = db_reltime
  list%db_relsat = db_relsat
  list%f_slide = f_slide
  list%slide_c = slide_c
  list%slide_phi = slide_phi
  list%slide_gamma = slide_gamma

end subroutine

end module
