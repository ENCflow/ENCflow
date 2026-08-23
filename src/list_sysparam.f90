module list_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_sysparam
  public :: list_sysparam_read

  integer, parameter :: maxpathlen = 256

  type t_list_sysparam

    real :: t0 = 0                                ! 計算開始時刻 (s)
    real :: tt = 0                                ! 計算終了時刻 (s)
    real :: dt = 0                                ! 時間ステップ (s)
    real :: dt_disp = 60                          ! 画面表示時間刻み (s)
    real :: dt_file = 3600                        ! ファイル出力時間刻み (s)
    real :: dt_recrd = 60                         ! プローブ出力時間刻み (s)
    real :: st_file = 0                           ! ファイル出力開始時間 (s)
    real :: st_recrd = 0                          ! プローブ出力開始時間 (s)
    real :: et_file = -1                          ! ファイル出力終了時間 (s)
    real :: et_recrd = -1                         ! プローブ出力終了時間 (s)
    character(len=80) :: t0_c = ""                ! 計算開始時刻 (d, h, m, s)
    character(len=80) :: date0_c = ""             ! シミュレーション時刻 t=0 の暦
                                                  !   "YYYY-MM-DD" または "YYYY-MM-DD hh:mm"
                                                  !   (蒸発散・水質など暦を使う機能で必須。§27)
    character(len=80) :: tt_c = ""                ! 計算終了時刻 (d, h, m, s)
    character(len=80) :: dt_c = ""                ! 時間ステップ (d, h, m, s)
    character(len=80) :: t_cycle_c = ""           ! 強制の反復周期 (d, h, m, s。§32.4)
    character(len=80) :: dt_disp_c = ""           ! 画面表示時間刻み (s)
    character(len=80) :: dt_file_c = ""           ! ファイル出力時間刻み (s)
    character(len=80) :: dt_recrd_c = ""          ! プローブ出力時間刻み (s)
    character(len=80) :: st_file_c = ""           ! ファイル出力開始時間 (s)
    character(len=80) :: st_recrd_c = ""          ! プローブ出力開始時間 (s)
    character(len=80) :: et_file_c = ""           ! ファイル出力終了時間 (s)
    character(len=80) :: et_recrd_c = ""          ! プローブ出力終了時間 (s)

    real :: dd = 0.001                            ! この水深以上なら水の移動を計算する(限界水深)
    real :: dv = 0.001                            ! これ以下なら強制的にこの水深にする(仮想水深)
    real :: vv = 0.01                             ! これ以下なら摩擦項計算時の流速をこの流速に
    real :: gg = 9.8                              ! 重力加速度 (m/s^2)
    real :: cm = 2.0                              ! 家屋の付加質量力係数
    real :: cd = 1.0                              ! 家屋の抗力係数
    real :: kk = 0.5                              ! 抗力係数補正係数

    integer :: f_gridsystem = 0                   ! 格子システム
    integer :: f_govequation = 0                  ! 基礎方程式
    integer :: f_check_cfl = 1                    ! CFL条件による実行停止 (0:監視のみ,
                                                  !   1:Cn>1で停止(既定), 2:波速を無視した
                                                  !   移流クーラン数で判定・停止)
    integer :: f_state_save = 0                   ! 状態保存ファイルの出力
    integer :: f_state_restore = 0                ! 状態保存ファイルの利用 (0:なし, 1:再開=時刻継続, 2:初期条件として利用=新しい t0 から)
    integer :: f_input_mode = 1                   ! matrix入力形式(1:text, 2:bil, 4:geotiff。出力のビット値と共通)
    integer :: f_output_mode = 1                  ! matrix出力形式のビット和(1:text, 2:bil, 4:geotiff)

    integer :: f_out_z = 0                        ! ファイル出力(地盤高Z0001, offでもt=0は常に出力)
    integer :: f_out_h = 1                        ! ファイル出力(水深H0001)
    integer :: f_out_e = 0                        ! ファイル出力(水位E0001)
    integer :: f_out_u = 0                        ! ファイル出力(x方向流速u0001)
    integer :: f_out_v = 0                        ! ファイル出力(y方向流速v0001)
    integer :: f_out_m = 0                        ! ファイル出力(x方向線流量m0001)
    integer :: f_out_n = 0                        ! ファイル出力(y方向線流量n0001)
    integer :: f_out_vv = 0                       ! ファイル出力(流速絶対値V0001)
    integer :: f_out_qq = 0                       ! ファイル出力(流量絶対値Q0001)
    integer :: f_out_qc = 0                       ! ファイル出力(積算流量Qc0001)
    integer :: f_out_qd = 0                       ! ファイル出力(流向Qd0001) rerecordで必要
    integer :: f_out_ddd = 0                      ! ファイル出力(卓越流下方向Ddd0001)
    integer :: f_out_dda = 0                      ! ファイル出力(全流下方向Dda0001) rmdepress_riverで必要
    integer :: f_out_pre = 0                      ! ファイル出力(降雨強度Pr0001)
    integer :: f_out_hrs = 0                      ! ファイル出力(ため池水深Hrs0001)
    integer :: f_out_fr = 0                       ! ファイル出力(フルード数Fr0001)
    integer :: f_out_cn = 0                       ! ファイル出力(クーラン数Cn0001)
    integer :: f_out_hg = 0                       ! ファイル出力(地下貯留水深Hg0001)
    integer :: f_out_hmax = 1                     ! ファイル出力(最大水深H9999)
    integer :: f_out_hmaxt = 0                    ! ファイル出力(最大水深発生時刻Ht9999)
    integer :: f_out_vvmax = 0                    ! ファイル出力(最大流速V9999)
    integer :: f_out_qqmax = 0                    ! ファイル出力(最大流量Q9999)
    integer :: f_out_qqmaxt = 0                   ! ファイル出力(最大流量発生時刻Qt9999)
    integer :: f_out_qqmaxd = 0                   ! ファイル出力(最大流量の流向Qd9999)
    integer :: f_out_hs = 0                       ! ファイル出力(土砂柱状量Hs0001。土砂系有効時)
    integer :: f_out_fs = 0                       ! ファイル出力(斜面安全率Fs0001+期間最小Fs9999。
                                                  !   f_slide>0 が必須。-1 = 評価対象外)
    integer :: f_out_dmax = 0                     ! ファイル出力(最大流動深 h+hs のD9999。土砂系有効時)
    integer :: f_out_dmaxt = 0                    ! ファイル出力(最大流動深発生時刻Dt9999)
    integer :: f_out_fmax = 0                     ! ファイル出力(最大流体力 (h+hs)・V² のF9999)
    integer :: f_out_hd = 0                       ! ファイル出力(流動流木Hd0001。fn_driftwood 必須。§50)
    integer :: f_out_wd = 0                       ! ファイル出力(堆積流木Wd0001+期間最大到達量Wd9999)

    ! 画面・Log の表示列の選択(時刻・保存量 S 系列・Runge・ex_flux は常設)
    integer :: f_disp_debug = 0                   ! 画面表示(S 系列を全有効桁で表示。デバッグ・回帰テスト用)
    integer :: f_disp_h = 1                       ! 画面表示(最大水深 h_max)
    integer :: f_disp_vv = 1                      ! 画面表示(最大流速 V_max)
    integer :: f_disp_qq = 0                      ! 画面表示(最大流量 Q_max)
    integer :: f_disp_cn = 1                      ! 画面表示(最大クーラン数 Cn_max)

    ! ファイル名として"-"を指定するとシステムパラメータファイルと同一ファイル
    ! ファイル名として空白""を指定すると読み込まれない
    ! 設定ファイルを追加したら m_main の init_resultdir(結果ディレクトリへの
    ! 保存)にも追加すること
    character(len=maxpathlen) :: fn_geoinfo = "-"        ! 地形条件設定ファイル(必須)
    character(len=maxpathlen) :: fn_initial = ""         ! 初期条件設定ファイル
    character(len=maxpathlen) :: fn_precip = ""          ! 降水条件設定ファイル
    character(len=maxpathlen) :: fn_reservoir = ""       ! ため池条件設定ファイル
    character(len=maxpathlen) :: fn_tide = ""            ! 潮位条件設定ファイル
    character(len=maxpathlen) :: fn_boundary = ""        ! 境界条件設定ファイル
    character(len=maxpathlen) :: fn_structure = ""       ! 内部水理構造物設定ファイル
    character(len=maxpathlen) :: fn_record = ""          ! 記録設定ファイル
    character(len=maxpathlen) :: fn_geomorph = ""        ! 地形変化条件設定ファイル
    character(len=maxpathlen) :: fn_gwflow = ""          ! 地下水条件設定ファイル
    character(len=maxpathlen) :: fn_intercept = ""       ! 降雨遮断条件設定ファイル
    character(len=maxpathlen) :: fn_evap = ""            ! 蒸発散条件設定ファイル
    character(len=maxpathlen) :: fn_meteo = ""           ! 気象強制場設定ファイル
    character(len=maxpathlen) :: fn_wq = ""              ! 水質(負荷流出)設定ファイル
    character(len=maxpathlen) :: fn_snow = ""            ! 積雪・融雪設定ファイル
    character(len=maxpathlen) :: fn_glacier = ""         ! 氷河設定ファイル
    character(len=maxpathlen) :: fn_lavaflow = ""        ! 溶岩流設定ファイル
    character(len=maxpathlen) :: fn_salt = ""            ! 淡塩2層設定ファイル
    character(len=maxpathlen) :: fn_swi = ""             ! 土壌雨量指数設定ファイル(§49)
    character(len=maxpathlen) :: fn_driftwood = ""       ! 流木設定ファイル(§50)
    character(len=maxpathlen) :: fn_channel = ""         ! 河道条件設定ファイル
    character(len=maxpathlen) :: fn_enc = ""             ! ENC設定ファイル

    character(len=maxpathlen) :: fn_log = "Log.txt"      ! 状態ログファイル
    character(len=maxpathlen) :: dir_data = "."          ! 入力データディレクトリ
    character(len=maxpathlen) :: dir_result = "result"   ! 結果出力ディレクトリ
    character(len=maxpathlen) :: dir_save = "save"       ! 状態保存(save/restore)ディレクトリ
    character(len=maxpathlen) :: outfn_suffix = ""       ! 出力ファイル名のサフィックス
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================
subroutine list_sysparam_read(list, fn_sysparam)
  character(len=*), intent(in) :: fn_sysparam
  type(t_list_sysparam), intent(inout) :: list
  real :: t0                                 ! 計算開始時刻 (s)
  real :: tt                                 ! 計算終了時刻 (s)
  real :: dt                                 ! 時間ステップ (s)
  real :: dt_disp                            ! 画面表示時間刻み (s)
  real :: dt_file                            ! ファイル出力時間刻み (s)
  real :: dt_recrd                           ! プローブ出力時間刻み (s)
  real :: st_file                            ! ファイル出力開始時間 (s)
  real :: st_recrd                           ! プローブ出力開始時間 (s)
  real :: et_file                            ! ファイル出力終了時間 (s)
  real :: et_recrd                           ! プローブ出力終了時間 (s)
  character(:), allocatable :: t0_c          ! 計算開始時刻 (d, h, m, s)
  character(:), allocatable :: date0_c       ! t=0 の暦
  character(:), allocatable :: tt_c          ! 計算終了時刻 (d, h, m, s)
  character(:), allocatable :: dt_c          ! 時間ステップ (d, h, m, s)
  character(:), allocatable :: t_cycle_c     ! 強制の反復周期 (d, h, m, s)
  character(:), allocatable :: dt_disp_c     ! 画面表示時間刻み (d, h, m, s)
  character(:), allocatable :: dt_file_c     ! ファイル出力時間刻み (d, h, m, s)
  character(:), allocatable :: dt_recrd_c    ! プローブ出力時間刻み (d, h, m, s)
  character(:), allocatable :: st_file_c     ! ファイル出力開始時間 (d, h, m, s)
  character(:), allocatable :: st_recrd_c    ! プローブ出力開始時間 (d, h, m, s)
  character(:), allocatable :: et_file_c     ! ファイル出力終了時間 (d, h, m, s)
  character(:), allocatable :: et_recrd_c    ! プローブ出力終了時間 (d, h, m, s)
  real :: dd                                 ! この水深以上なら水の移動を計算する(限界水深)
  real :: dv                                 ! これ以下なら強制的にこの水深にする(仮想水深)
  real :: vv                                 ! これ以下なら摩擦項計算時の流速をこの流速に
  real :: gg                                 ! 重力加速度 (m/s^2)
  real :: cm                                 ! 家屋の付加質量力係数
  real :: cd                                 ! 家屋の抗力係数
  real :: kk                                 ! 抗力係数補正係数
  integer :: f_gridsystem                    ! 格子システム
  integer :: f_govequation                   ! 基礎方程式
  integer :: f_check_cfl                     ! CFL条件による実行停止 (0:監視のみ, 1:既定, 2:移流Cn)
  integer :: f_state_save                    ! 状態保存ファイルの出力
  integer :: f_state_restore                 ! 状態保存ファイルの利用 (0:なし, 1:再開, 2:初期条件として利用)
  integer :: f_input_mode                    ! matrix入力形式(1:text, 2:bil, 4:geotiff。出力のビット値と共通)
  integer :: f_output_mode                   ! matrix出力形式のビット和(1:text, 2:bil, 4:geotiff)
  integer :: f_out_z                         ! ファイル出力(地盤高Z0001)
  integer :: f_out_h                         ! ファイル出力(水深H0001)
  integer :: f_out_e                         ! ファイル出力(水位E0001)
  integer :: f_out_u                         ! ファイル出力(x方向流速u0001)
  integer :: f_out_v                         ! ファイル出力(y方向流速v0001)
  integer :: f_out_m                         ! ファイル出力(x方向線流量m0001)
  integer :: f_out_n                         ! ファイル出力(y方向線流量n0001)
  integer :: f_out_vv                        ! ファイル出力(流速絶対値Q0001)
  integer :: f_out_qq                        ! ファイル出力(流量絶対値V0001)
  integer :: f_out_qc                        ! ファイル出力(積算線流量Qc0001)
  integer :: f_out_qd                        ! ファイル出力(流向Qd0001)  rerecordで必要
  integer :: f_out_ddd                       ! ファイル出力(卓越流下方向フラグDdd0001)
  integer :: f_out_dda                       ! ファイル出力(全流下方向フラグDda0001)
  integer :: f_out_pre                       ! ファイル出力(降雨強度Pr0001)
  integer :: f_out_hrs                       ! ファイル出力(ため池水深Hrs0001)
  integer :: f_out_fr                        ! ファイル出力(フルード数Fr0001)
  integer :: f_out_cn                        ! ファイル出力(クーラン数Cn0001)
  integer :: f_out_hg                        ! ファイル出力(地下貯留水深Hg0001)
  integer :: f_out_hmax                      ! ファイル出力(最大水深H9999)
  integer :: f_out_hmaxt                     ! ファイル出力(最大水深発生時刻Ht9999)
  integer :: f_out_vvmax                     ! ファイル出力(最大流速V9999)
  integer :: f_out_qqmax                     ! ファイル出力(最大流量Q9999)
  integer :: f_out_qqmaxt                    ! ファイル出力(最大流量発生時刻Qt9999)
  integer :: f_out_qqmaxd                    ! ファイル出力(最大流量の流向Qt9999)
  integer :: f_out_hs                        ! ファイル出力(土砂柱状量Hs0001)
  integer :: f_out_fs                        ! ファイル出力(斜面安全率Fs0001/Fs9999)
  integer :: f_out_dmax                      ! ファイル出力(最大流動深D9999)
  integer :: f_out_dmaxt                     ! ファイル出力(最大流動深発生時刻Dt9999)
  integer :: f_out_fmax                      ! ファイル出力(最大流体力F9999)
  integer :: f_out_hd                        ! ファイル出力(流動流木Hd0001)
  integer :: f_out_wd                        ! ファイル出力(堆積流木Wd0001/Wd9999)
  integer :: f_disp_debug                    ! 画面表示(S 系列を全有効桁で表示)
  integer :: f_disp_h                        ! 画面表示(最大水深 h_max)
  integer :: f_disp_vv                       ! 画面表示(最大流速 V_max)
  integer :: f_disp_qq                       ! 画面表示(最大流量 Q_max)
  integer :: f_disp_cn                       ! 画面表示(最大クーラン数 Cn_max)
  character(:), allocatable :: fn_geoinfo    ! 地形条件設定ファイル
  character(:), allocatable :: fn_initial    ! 初期条件設定ファイル
  character(:), allocatable :: fn_precip     ! 降水条件設定ファイル
  character(:), allocatable :: fn_reservoir  ! ため池条件設定ファイル
  character(:), allocatable :: fn_tide       ! 潮位条件設定ファイル
  character(:), allocatable :: fn_boundary   ! 境界条件設定ファイル
  character(:), allocatable :: fn_structure  ! 内部水理構造物設定ファイル
  character(:), allocatable :: fn_record     ! 記録設定ファイル
  character(:), allocatable :: fn_geomorph   ! 地形変化条件設定ファイル
  character(:), allocatable :: fn_gwflow     ! 地下水条件設定ファイル
  character(:), allocatable :: fn_intercept  ! 降雨遮断条件設定ファイル
  character(:), allocatable :: fn_evap       ! 蒸発散条件設定ファイル
  character(:), allocatable :: fn_meteo      ! 気象強制場設定ファイル
  character(:), allocatable :: fn_wq         ! 水質(負荷流出)設定ファイル
  character(:), allocatable :: fn_snow       ! 積雪・融雪設定ファイル
  character(:), allocatable :: fn_glacier    ! 氷河設定ファイル
  character(:), allocatable :: fn_lavaflow   ! 溶岩流設定ファイル
  character(:), allocatable :: fn_salt       ! 淡塩2層設定ファイル
  character(:), allocatable :: fn_swi        ! 土壌雨量指数設定ファイル
  character(:), allocatable :: fn_driftwood  ! 流木設定ファイル
  character(:), allocatable :: fn_channel    ! 河道条件設定ファイル
  character(:), allocatable :: fn_enc        ! ENC設定ファイル
  character(:), allocatable :: fn_log        ! 状態ログファイル
  character(:), allocatable :: dir_data      ! 入力データディレクトリ
  character(:), allocatable :: dir_result    ! 結果出力ディレクトリ
  character(:), allocatable :: dir_save      ! 状態保存(save/restore)ディレクトリ
  character(:), allocatable :: outfn_suffix  ! 出力ファイル名のサフィックス
  integer :: un
  integer :: ios
  character(len=1024) :: iom
  namelist /list_sysparam/ t0, tt, dt, dt_disp, dt_file, dt_recrd, &
                        st_file, st_recrd, et_file, et_recrd, &
                        t0_c, date0_c, tt_c, dt_c, t_cycle_c, dt_disp_c, dt_file_c, dt_recrd_c, &
                        st_file_c, st_recrd_c, et_file_c, et_recrd_c, &
                        dd, dv, vv, gg, cm, cd, kk, &
                        f_gridsystem, f_govequation, f_check_cfl, f_state_save, &
                        f_state_restore, f_input_mode, f_output_mode, &
                        f_out_z, f_out_h, f_out_e, f_out_u, f_out_v, f_out_m, f_out_n, &
                        f_out_vv, f_out_qq, f_out_qc, f_out_qd, &
                        f_out_hmax, f_out_hmaxt, f_out_vvmax, f_out_qqmax, f_out_qqmaxt, f_out_qqmaxd, &
                        f_out_hs, f_out_fs, f_out_dmax, f_out_dmaxt, f_out_fmax, &
                        f_out_hd, f_out_wd, &
                        f_disp_debug, f_disp_h, f_disp_vv, f_disp_qq, f_disp_cn, &
                        f_out_ddd, f_out_dda, f_out_pre, f_out_hrs, f_out_fr, f_out_cn, f_out_hg, &
                        fn_geoinfo, fn_initial, fn_precip, fn_reservoir, fn_tide, fn_boundary, &
                        fn_structure, &
                        fn_record, fn_geomorph, fn_gwflow, fn_intercept, fn_evap, fn_meteo, fn_wq, fn_snow, fn_glacier, fn_lavaflow, fn_salt, fn_swi, fn_driftwood, fn_channel, fn_enc, &
                        fn_log, dir_data, dir_result, dir_save, outfn_suffix

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  t0 = list%t0
  tt = list%tt
  dt = list%dt
  dt_disp = list%dt_disp
  dt_file = list%dt_file
  dt_recrd = list%dt_recrd
  st_file = list%st_file
  st_recrd = list%st_recrd
  et_file = list%et_file
  et_recrd = list%et_recrd
  t0_c = list%t0_c
  t_cycle_c = list%t_cycle_c
  date0_c = list%date0_c
  tt_c = list%tt_c
  dt_c = list%dt_c
  dt_disp_c = list%dt_disp_c
  dt_file_c = list%dt_file_c
  dt_recrd_c = list%dt_recrd_c
  st_file_c = list%st_file_c
  st_recrd_c = list%st_recrd_c
  et_file_c = list%et_file_c
  et_recrd_c = list%et_recrd_c
  dd = list%dd
  dv = list%dv
  vv = list%vv
  gg = list%gg
  cm = list%cm
  cd = list%cd
  kk = list%kk
  f_gridsystem = list%f_gridsystem
  f_govequation = list%f_govequation
  f_check_cfl = list%f_check_cfl
  f_state_save = list%f_state_save
  f_state_restore = list%f_state_restore
  f_input_mode = list%f_input_mode
  f_output_mode = list%f_output_mode
  f_out_z = list%f_out_z
  f_out_h = list%f_out_h
  f_out_e = list%f_out_e
  f_out_u = list%f_out_u
  f_out_v = list%f_out_v
  f_out_m = list%f_out_m
  f_out_n = list%f_out_n
  f_out_vv = list%f_out_vv
  f_out_qq = list%f_out_qq
  f_out_qc = list%f_out_qc
  f_out_qd = list%f_out_qd
  f_out_ddd = list%f_out_ddd
  f_out_dda = list%f_out_dda
  f_out_pre = list%f_out_pre
  f_out_hrs = list%f_out_hrs
  f_out_cn = list%f_out_cn
  f_out_hg = list%f_out_hg
  f_out_fr = list%f_out_fr
  f_out_hmax = list%f_out_hmax
  f_out_hmaxt = list%f_out_hmaxt
  f_out_vvmax = list%f_out_vvmax
  f_out_qqmax = list%f_out_qqmax
  f_out_qqmaxt = list%f_out_qqmaxt
  f_out_qqmaxd = list%f_out_qqmaxd
  f_out_hs = list%f_out_hs
  f_out_fs = list%f_out_fs
  f_out_dmax = list%f_out_dmax
  f_out_dmaxt = list%f_out_dmaxt
  f_out_fmax = list%f_out_fmax
  f_out_hd = list%f_out_hd
  f_out_wd = list%f_out_wd
  f_disp_debug = list%f_disp_debug
  f_disp_h = list%f_disp_h
  f_disp_vv = list%f_disp_vv
  f_disp_qq = list%f_disp_qq
  f_disp_cn = list%f_disp_cn
  fn_geoinfo = list%fn_geoinfo
  fn_initial = list%fn_initial
  fn_precip = list%fn_precip
  fn_reservoir = list%fn_reservoir
  fn_tide = list%fn_tide
  fn_boundary = list%fn_boundary
  fn_structure = list%fn_structure
  fn_record = list%fn_record
  fn_geomorph = list%fn_geomorph
  fn_gwflow = list%fn_gwflow
  fn_intercept = list%fn_intercept
  fn_evap = list%fn_evap
  fn_meteo = list%fn_meteo
  fn_wq = list%fn_wq
  fn_snow = list%fn_snow
  fn_glacier = list%fn_glacier
  fn_lavaflow = list%fn_lavaflow
  fn_salt = list%fn_salt
  fn_swi = list%fn_swi
  fn_driftwood = list%fn_driftwood
  fn_channel = list%fn_channel
  fn_enc = list%fn_enc
  fn_log = list%fn_log
  dir_data = list%dir_data
  dir_result = list%dir_result
  dir_save = list%dir_save
  outfn_suffix = list%outfn_suffix

  call par_info("reading list_sysparam in "//trim(fn_sysparam))
  open(newunit=un, file=trim(fn_sysparam), status='old')
  read(un, nml=list_sysparam, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_sysparam: failed to read namelist: "//trim(iom))
  close(un)

  list%t0 = t0
  list%tt = tt
  list%dt = dt
  list%dt_disp = dt_disp
  list%dt_file = dt_file
  list%dt_recrd = dt_recrd
  list%st_file = st_file
  list%st_recrd = st_recrd
  list%et_file = et_file
  list%et_recrd = et_recrd
  list%t0_c = t0_c
  list%t_cycle_c = t_cycle_c
  list%date0_c = date0_c
  list%tt_c = tt_c
  list%dt_c = dt_c
  list%dt_disp_c = dt_disp_c
  list%dt_file_c = dt_file_c
  list%dt_recrd_c = dt_recrd_c
  list%st_file_c = st_file_c
  list%st_recrd_c = st_recrd_c
  list%et_file_c = et_file_c
  list%et_recrd_c = et_recrd_c
  list%dd = dd
  list%dv = dv
  list%vv = vv
  list%gg = gg
  list%cm = cm
  list%cd = cd
  list%kk = kk
  list%f_gridsystem = f_gridsystem
  list%f_govequation = f_govequation
  list%f_check_cfl = f_check_cfl
  list%f_state_save = f_state_save
  list%f_state_restore = f_state_restore
  list%f_input_mode = f_input_mode
  list%f_output_mode = f_output_mode
  list%f_out_z = f_out_z
  list%f_out_h = f_out_h
  list%f_out_e = f_out_e
  list%f_out_u = f_out_u
  list%f_out_v = f_out_v
  list%f_out_m = f_out_m
  list%f_out_n = f_out_n
  list%f_out_vv = f_out_vv
  list%f_out_qq = f_out_qq
  list%f_out_qc = f_out_qc
  list%f_out_qd = f_out_qd
  list%f_out_ddd = f_out_ddd
  list%f_out_dda = f_out_dda
  list%f_out_pre = f_out_pre
  list%f_out_hrs = f_out_hrs
  list%f_out_fr = f_out_fr
  list%f_out_cn = f_out_cn
  list%f_out_hg = f_out_hg
  list%f_out_hmax = f_out_hmax
  list%f_out_hmaxt = f_out_hmaxt
  list%f_out_vvmax = f_out_vvmax
  list%f_out_qqmax = f_out_qqmax
  list%f_out_qqmaxt = f_out_qqmaxt
  list%f_out_qqmaxd = f_out_qqmaxd
  list%f_out_hs = f_out_hs
  list%f_out_fs = f_out_fs
  list%f_out_dmax = f_out_dmax
  list%f_out_dmaxt = f_out_dmaxt
  list%f_out_fmax = f_out_fmax
  list%f_out_hd = f_out_hd
  list%f_out_wd = f_out_wd
  list%f_disp_debug = f_disp_debug
  list%f_disp_h = f_disp_h
  list%f_disp_vv = f_disp_vv
  list%f_disp_qq = f_disp_qq
  list%f_disp_cn = f_disp_cn
  list%fn_geoinfo = fn_geoinfo
  list%fn_initial = fn_initial
  list%fn_precip = fn_precip
  list%fn_reservoir = fn_reservoir
  list%fn_tide = fn_tide
  list%fn_boundary = fn_boundary
  list%fn_structure = fn_structure
  list%fn_record = fn_record
  list%fn_geomorph = fn_geomorph
  list%fn_gwflow = fn_gwflow
  list%fn_intercept = fn_intercept
  list%fn_evap = fn_evap
  list%fn_meteo = fn_meteo
  list%fn_wq = fn_wq
  list%fn_snow = fn_snow
  list%fn_glacier = fn_glacier
  list%fn_lavaflow = fn_lavaflow
  list%fn_salt = fn_salt
  list%fn_swi = fn_swi
  list%fn_driftwood = fn_driftwood
  list%fn_channel = fn_channel
  list%fn_enc = fn_enc
  list%fn_log = fn_log
  list%dir_data = dir_data
  list%dir_result = dir_result
  list%dir_save = dir_save
  list%outfn_suffix = outfn_suffix

  if (trim(list%fn_geoinfo) == "-") list%fn_geoinfo = trim(fn_sysparam)
  if (trim(list%fn_initial) == "-") list%fn_initial = trim(fn_sysparam)
  if (trim(list%fn_precip) == "-") list%fn_precip = trim(fn_sysparam)
  if (trim(list%fn_reservoir) == "-") list%fn_reservoir = trim(fn_sysparam)
  if (trim(list%fn_tide) == "-") list%fn_tide = trim(fn_sysparam)
  if (trim(list%fn_boundary) == "-") list%fn_boundary = trim(fn_sysparam)
  if (trim(list%fn_structure) == "-") list%fn_structure = trim(fn_sysparam)
  if (trim(list%fn_record) == "-") list%fn_record = trim(fn_sysparam)
  if (trim(list%fn_geomorph) == "-") list%fn_geomorph = trim(fn_sysparam)
  if (trim(list%fn_gwflow) == "-") list%fn_gwflow = trim(fn_sysparam)
  if (trim(list%fn_intercept) == "-") list%fn_intercept = trim(fn_sysparam)
  if (trim(list%fn_evap) == "-") list%fn_evap = trim(fn_sysparam)
  if (trim(list%fn_meteo) == "-") list%fn_meteo = trim(fn_sysparam)
  if (trim(list%fn_wq) == "-") list%fn_wq = trim(fn_sysparam)
  if (trim(list%fn_snow) == "-") list%fn_snow = trim(fn_sysparam)
  if (trim(list%fn_glacier) == "-") list%fn_glacier = trim(fn_sysparam)
  if (trim(list%fn_lavaflow) == "-") list%fn_lavaflow = trim(fn_sysparam)
  if (trim(list%fn_salt) == "-") list%fn_salt = trim(fn_sysparam)
  if (trim(list%fn_swi) == "-") list%fn_swi = trim(fn_sysparam)
  if (trim(list%fn_driftwood) == "-") list%fn_driftwood = trim(fn_sysparam)
  if (trim(list%fn_channel) == "-") list%fn_channel = trim(fn_sysparam)
  if (trim(list%fn_enc) == "-") list%fn_enc = trim(fn_sysparam)

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================
end module
