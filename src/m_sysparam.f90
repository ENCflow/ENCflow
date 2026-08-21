module m_sysparam
  use list_sysparam, only : t_list_sysparam, list_sysparam_read
  use m_util, only : str2sec, itoa, parse_datetime
  use m_fileio, only : e_fmt_txt, e_fmt_bil, e_fmt_gtif
  use m_parallel, only : par_stop
  implicit none
  private

  public :: t_sysparam
  public :: m_sysparam_init
  public :: m_sysparam_dispose


  type t_sysparam
    real :: t0                                 ! 計算開始時刻 (s)
    logical :: has_date = .false.              ! t=0 の暦(date0_c)が指定されたか
    integer :: jdn0 = 0                        ! t=0 の日のユリウス通日(has_date 時のみ有効)
    real :: sec0 = 0.0                         ! t=0 の日内秒(同上)
    real :: tt                                 ! 計算終了時刻 (s)
    real :: dt_disp                            ! 画面表示時間刻み (s)
    real :: dt_file                            ! ファイル出力時間刻み (s)
    real :: dt_recrd                           ! プローブ出力時間刻み (s)
    real :: st_file                            ! ファイル出力開始時間 (s)
    real :: st_recrd                           ! プローブ出力開始時間 (s)
    real :: et_file                            ! ファイル出力終了時間 (s)
    real :: et_recrd                           ! プローブ出力終了時間 (s)
    integer :: nt                              ! 総時間ステップ数
    integer :: idt_disp                        ! 画面表示時間刻みの時間ステップ数
    integer :: idt_file                        ! ファイル出力時間刻みの時間ステップ数
    integer :: idt_recd                        ! プローブ出力時間刻みの時間ステップ数
    integer :: ist_file                        ! ファイル出力開始時間の時間ステップ数
    integer :: ist_recd                        ! プローブ出力開始時間の時間ステップ数
    integer :: iet_file                        ! ファイル出力終了時間の時間ステップ数
    integer :: iet_recd                        ! プローブ出力終了時間の時間ステップ数
    real :: dt                                 ! 時間ステップ (s)
    real :: dd                                 ! この水深以上なら水の移動を計算する(限界水深)
    real :: dv                                 ! これ以下なら強制的にこの水深にする(仮想水深)
    real :: vv                                 ! これ以下なら摩擦項計算時の流速をこの流速に
    real :: gg                                 ! 重力加速度 (m/s^2)
    real :: cm                                 ! 家屋の付加質量力係数
    real :: cd                                 ! 家屋の抗力係数
    real :: kk                                 ! 抗力係数補正係数
    integer :: f_gridsystem                    ! 格子システム
    integer :: f_govequation                   ! 基礎方程式
    integer :: f_check_cfl                     ! CFL条件による実行停止
    integer :: f_state_save                    ! 状態保存ファイルの出力
    integer :: f_state_restore                 ! 状態保存ファイルの利用 (0:なし, 1:再開=時刻継続, 2:初期条件として利用=新しい t0 から)
    integer :: f_input_mode                    ! matrix入力形式(1:text, 2:bil, 4:geotiff)
    integer :: f_output_mode                   ! matrix出力形式のビット和(1:text, 2:bil, 4:geotiff)
    integer :: num_threads                     ! スレッド数
    integer :: real_precision                  ! 実数変数の有効数字桁数
    integer :: f_out_z                         ! ファイル出力(地盤高Z0001)
    integer :: f_out_h                         ! ファイル出力(水深H0001)
    integer :: f_out_e                         ! ファイル出力(水位E0001)
    integer :: f_out_u                         ! ファイル出力(x方向流速u0001)
    integer :: f_out_v                         ! ファイル出力(y方向流速v0001)
    integer :: f_out_m                         ! ファイル出力(x方向線流量m0001)
    integer :: f_out_n                         ! ファイル出力(y方向線流量n0001)
    integer :: f_out_vv                        ! ファイル出力(流量絶対値Q0001)
    integer :: f_out_qq                        ! ファイル出力(流速絶対値V0001)
    integer :: f_out_qc                        ! ファイル出力(積算流量Qc0001)
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
    integer :: f_out_hd                        ! ファイル出力(流動流木Hd0001。§50)
    integer :: f_out_wd                        ! ファイル出力(堆積流木Wd0001/Wd9999)
    integer :: f_disp_debug                    ! 画面表示(S 系列を全有効桁で表示)
    integer :: f_disp_h                        ! 画面表示(最大水深 h_max)
    integer :: f_disp_vv                       ! 画面表示(最大流速 V_max)
    integer :: f_disp_qq                       ! 画面表示(最大流量 Q_max)
    integer :: f_disp_cn                       ! 画面表示(最大クーラン数 Cn_max)
    character(:), allocatable :: fn_sysparam   ! システムパラメータ設定ファイル
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
    character(:), allocatable :: fn_salt       ! 淡塩2層設定ファイル
    character(:), allocatable :: fn_swi        ! 土壌雨量指数設定ファイル(§49)
    character(:), allocatable :: fn_driftwood  ! 流木設定ファイル(§50)
    real :: t_cycle = 0.0                      ! 強制の反復周期 (s。0=なし。§32.4)
    character(:), allocatable :: fn_channel    ! 河道条件設定ファイル
    character(:), allocatable :: fn_enc        ! ENC設定ファイル
    character(:), allocatable :: fn_log        ! 状態ログファイル
    character(:), allocatable :: dir_data      ! 入力データディレクトリ
    character(:), allocatable :: dir_result    ! 結果出力ディレクトリ
    character(:), allocatable :: dir_save      ! 状態保存(save/restore)ディレクトリ
    character(:), allocatable :: outfn_suffix  ! 出力ファイル名のサフィックス
    logical :: initialized = .false.           ! 初期化済みフラグ
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================
!----------------------------------------------------------------------
! システムパラメータ構造体を初期化する
!----------------------------------------------------------------------
subroutine m_sysparam_init(p, fn_sysparam)
  type(t_sysparam), intent(inout) :: p            ! システムパラメータ構造体
  character(len=*), intent(in) :: fn_sysparam     ! システムパラメータファイル名
  type(t_list_sysparam) :: list                   ! パラメータファイル中の変数

  !p%fn_sysparam = 'param.txt'
  p%fn_sysparam = trim(fn_sysparam)
  call list_sysparam_read(list, fn_sysparam)

  p%t0 = list%t0                               ! 計算開始時刻 (s)
  p%tt = list%tt                               ! 計算終了時刻 (s)
  p%dt_disp = list%dt_disp                     ! 画面表示時間刻み (s)
  p%dt_file = list%dt_file                     ! ファイル出力時間刻み (s)
  p%dt_recrd = list%dt_recrd                   ! プローブ出力時間刻み (s)
  p%st_file = list%st_file                     ! ファイル出力開始時間 (s)
  p%st_recrd = list%st_recrd                   ! プローブ出力開始時間 (s)
  p%et_file = list%et_file                     ! ファイル出力終了時間 (s)
  p%et_recrd = list%et_recrd                   ! プローブ出力終了時間 (s)
  p%dt = list%dt                               ! 時間ステップ (s)
  p%dd = list%dd                               ! この水深以上なら移流項を計算する(限界水深)
  p%dv = list%dv                               ! これ以下なら強制的にこの水深にする(仮想水深)
  p%vv = list%vv                               ! この流速以下なら摩擦項計算時の流速を陰解法に
  p%gg = list%gg                               ! 重力加速度 (m/s^2)
  p%cm = list%cm                               ! 家屋の付加質量力係数
  p%cd = list%cd                               ! 家屋の抗力係数
  p%kk = list%kk                               ! 抗力係数補正係数
  p%f_gridsystem = list%f_gridsystem           ! 格子システム
  p%f_govequation = list%f_govequation         ! 基礎方程式
  p%f_check_cfl =  list%f_check_cfl            ! CFL条件による実行停止
  p%f_state_save =  list%f_state_save          ! 状態保存ファイルの出力
  p%f_state_restore =  list%f_state_restore    ! 状態保存ファイルの利用 (0/1/2)
  if (p%f_state_restore < 0 .or. p%f_state_restore > 2) then
    call par_stop("list_sysparam: f_state_restore must be 0(none), 1(restart) or " &
                  //"2(use as initial condition): "//itoa(p%f_state_restore))
  end if
  ! matrix入力形式(1:text, 2:bil, 4:geotiff。値は f_output_mode のビットと共通)
  if (list%f_input_mode == 1) then
    p%f_input_mode = e_fmt_txt
  else if (list%f_input_mode == 2) then
    p%f_input_mode = e_fmt_bil
  else if (list%f_input_mode == 4) then
    p%f_input_mode = e_fmt_gtif
  else if (list%f_input_mode == 3) then
    ! 出力の 3=text+bil との混同を疑う(入力は単一形式のみ)
    call par_stop("list_sysparam: f_input_mode=3 is not allowed; input must be a single " &
                  //"format (1:text, 2:bil, 4:geotiff)")
  else
    call par_stop("list_sysparam: unknown f_input_mode: "//itoa(list%f_input_mode))
  end if
  ! matrix出力形式はビット和(1:text, 2:bil, 4:geotiff。3=text+bil は従来互換)
  if (list%f_output_mode >= 1 .and. list%f_output_mode <= 7) then
    p%f_output_mode = list%f_output_mode
  else
    call par_stop("list_sysparam: f_output_mode must be a bit sum in 1-7 " &
                  //"(1:text, 2:bil, 4:geotiff): "//itoa(list%f_output_mode))
  end if
  p%f_out_z = list%f_out_z                     ! ファイル出力(地盤高Z0001)
  p%f_out_h = list%f_out_h                     ! ファイル出力(水深H0001)
  p%f_out_e = list%f_out_e                     ! ファイル出力(水位E0001)
  p%f_out_u = list%f_out_u                     ! ファイル出力(x方向流速u0001)
  p%f_out_v = list%f_out_v                     ! ファイル出力(y方向流速v0001)
  p%f_out_m = list%f_out_m                     ! ファイル出力(x方向線流量m0001)
  p%f_out_n = list%f_out_n                     ! ファイル出力(y方向線流量n0001)
  p%f_out_vv = list%f_out_vv                   ! ファイル出力(流量絶対値Q0001)
  p%f_out_qq = list%f_out_qq                   ! ファイル出力(流速絶対値V0001)
  p%f_out_qc = list%f_out_qc                   ! ファイル出力(積算流量Qc0001)
  p%f_out_qd = list%f_out_qd                   ! ファイル出力(流向Qd0001)  rerecordで必要
  p%f_out_ddd = list%f_out_ddd                 ! ファイル出力(卓越流下方向Ddd0001)
  p%f_out_dda = list%f_out_dda                 ! ファイル出力(全流下方向Dda0001)
  p%f_out_pre = list%f_out_pre                 ! ファイル出力(降雨強度Pr0001)
  p%f_out_hrs = list%f_out_hrs                 ! ファイル出力(ため池水深Hrs0001)
  p%f_out_fr = list%f_out_fr                   ! ファイル出力(フルード数Fr0001)
  p%f_out_cn = list%f_out_cn                   ! ファイル出力(クーラン数Cn0001)
  p%f_out_hg = list%f_out_hg                   ! ファイル出力(地下貯留水深Hg0001)
  p%f_out_hmax = list%f_out_hmax               ! ファイル出力(最大水深H9999)
  p%f_out_hmaxt = list%f_out_hmaxt             ! ファイル出力(最大水深発生時刻Ht9999)
  p%f_out_vvmax = list%f_out_vvmax             ! ファイル出力(最大流速V9999)
  p%f_out_qqmax = list%f_out_qqmax             ! ファイル出力(最大流量Q9999)
  p%f_out_qqmaxt = list%f_out_qqmaxt           ! ファイル出力(最大流量発生時刻Qt9999)
  p%f_out_qqmaxd = list%f_out_qqmaxd           ! ファイル出力(最大流量の流向Qt9999)
  p%f_out_hs = list%f_out_hs                   ! ファイル出力(土砂柱状量Hs0001)
  p%f_out_fs = list%f_out_fs                   ! ファイル出力(斜面安全率Fs0001/Fs9999)
  p%f_out_dmax = list%f_out_dmax               ! ファイル出力(最大流動深D9999)
  p%f_out_dmaxt = list%f_out_dmaxt             ! ファイル出力(最大流動深発生時刻Dt9999)
  p%f_out_fmax = list%f_out_fmax               ! ファイル出力(最大流体力F9999)
  p%f_out_hd = list%f_out_hd                   ! ファイル出力(流動流木Hd0001)
  p%f_out_wd = list%f_out_wd                   ! ファイル出力(堆積流木Wd0001/Wd9999)
  p%f_disp_debug = list%f_disp_debug           ! 画面表示(S 系列を全有効桁で表示)
  p%f_disp_h = list%f_disp_h                   ! 画面表示(最大水深 h_max)
  p%f_disp_vv = list%f_disp_vv                 ! 画面表示(最大流速 V_max)
  p%f_disp_qq = list%f_disp_qq                 ! 画面表示(最大流量 Q_max)
  p%f_disp_cn = list%f_disp_cn                 ! 画面表示(最大クーラン数 Cn_max)
  p%fn_geoinfo = list%fn_geoinfo               ! 地形条件設定ファイル
  p%fn_initial = list%fn_initial               ! 初期条件設定ファイル
  p%fn_precip = list%fn_precip                 ! 降水条件設定ファイル
  p%fn_reservoir = list%fn_reservoir           ! ため池条件設定ファイル
  p%fn_tide = list%fn_tide                     ! 潮位条件設定ファイル
  p%fn_boundary = list%fn_boundary             ! 境界条件設定ファイル
  p%fn_structure = list%fn_structure           ! 内部水理構造物設定ファイル
  p%fn_record = list%fn_record                 ! 記録設定ファイル
  p%fn_geomorph = list%fn_geomorph             ! 地形変化条件設定ファイル
  p%fn_gwflow = list%fn_gwflow                 ! 地下水条件設定ファイル
  p%fn_intercept = list%fn_intercept           ! 降雨遮断条件設定ファイル
  p%fn_evap = list%fn_evap                     ! 蒸発散条件設定ファイル
  p%fn_meteo = list%fn_meteo                   ! 気象強制場設定ファイル
  p%fn_wq = list%fn_wq                         ! 水質(負荷流出)設定ファイル
  p%fn_snow = list%fn_snow                     ! 積雪・融雪設定ファイル
  p%fn_glacier = list%fn_glacier               ! 氷河設定ファイル
  p%fn_salt = list%fn_salt                     ! 淡塩2層設定ファイル
  p%fn_swi = list%fn_swi                       ! 土壌雨量指数設定ファイル
  p%fn_driftwood = list%fn_driftwood           ! 流木設定ファイル
  p%fn_channel = list%fn_channel               ! 河道条件設定ファイル
  p%fn_enc = list%fn_enc                       ! ENC設定ファイル
  p%fn_log = list%fn_log                       ! 状態ログファイル
  p%dir_data = list%dir_data                   ! 入力データディレクトリ
  p%dir_result = list%dir_result               ! 結果出力ディレクトリ
  p%dir_save = list%dir_save                   ! 状態保存(save/restore)ディレクトリ
  p%outfn_suffix = list%outfn_suffix           ! 出力ファイル名のサフィックス

  if (len(trim(list%t0_c)) > 0) p%t0 = str2sec(list%t0_c, "list_sysparam: bad t0_c")
  ! t=0 の暦(蒸発散・水質など暦を使う機能の正本。§27)
  if (len(trim(list%date0_c)) > 0) then
    call parse_datetime(trim(list%date0_c), p%jdn0, p%sec0, "list_sysparam: bad date0_c")
    p%has_date = .true.
  end if
  if (len(trim(list%tt_c)) > 0) p%tt = str2sec(list%tt_c, "list_sysparam: bad tt_c")
  ! 強制の反復周期(降雨・気温の時系列参照を mod(t, T) で折り返す。§32.4)
  if (len(trim(list%t_cycle_c)) > 0) then
    p%t_cycle = str2sec(list%t_cycle_c, "list_sysparam: bad t_cycle_c")
    if (p%t_cycle <= 0.0) call par_stop("list_sysparam: t_cycle_c must be a positive period")
  end if
  if (len(trim(list%dt_c)) > 0) p%dt = str2sec(list%dt_c, "list_sysparam: bad dt_c")
  if (len(trim(list%dt_disp_c)) > 0) p%dt_disp = str2sec(list%dt_disp_c, "list_sysparam: bad dt_disp_c")
  if (len(trim(list%dt_file_c)) > 0) p%dt_file = str2sec(list%dt_file_c, "list_sysparam: bad dt_file_c")
  if (len(trim(list%dt_recrd_c)) > 0) p%dt_recrd = str2sec(list%dt_recrd_c, "list_sysparam: bad dt_recrd_c")
  if (len(trim(list%st_file_c)) > 0) p%st_file = str2sec(list%st_file_c, "list_sysparam: bad st_file_c")
  if (len(trim(list%st_recrd_c)) > 0) p%st_recrd = str2sec(list%st_recrd_c, "list_sysparam: bad st_recrd_c")
  if (len(trim(list%et_file_c)) > 0) p%et_file = str2sec(list%et_file_c, "list_sysparam: bad et_file_c")
  if (len(trim(list%et_recrd_c)) > 0) p%et_recrd = str2sec(list%et_recrd_c, "list_sysparam: bad et_recrd_c")

  if (p%dt == 0.0) then
    call par_stop("list_sysparam: dt is not set (specify dt or dt_c)")
    stop
  end if

  if (p%et_file < 0) p%et_file = p%tt
  if (p%et_recrd < 0) p%et_recrd = p%tt

  p%nt = ceiling((p%tt - p%t0) / p%dt)         ! 総時間ステップ数
  p%idt_disp = max(nint(p%dt_disp / p%dt), 1)  ! 画面表示時間刻みの時間ステップ数
  p%idt_file = max(nint(p%dt_file / p%dt), 1)  ! ファイル出力時間刻みの時間ステップ数
  p%idt_recd = max(nint(p%dt_recrd / p%dt), 1) ! プローブ出力時間刻みの時間ステップ数
  p%ist_file = max(nint(p%st_file / p%dt), 1)  ! ファイル出力開始時間の時間ステップ数
  p%ist_recd = max(nint(p%st_recrd / p%dt), 1) ! プローブ出力開始時間の時間ステップ数
  p%iet_file = max(nint(p%et_file / p%dt), 1)  ! ファイル出力終了時間の時間ステップ数
  p%iet_recd = max(nint(p%et_recrd / p%dt), 1) ! プローブ出力終了時間の時間ステップ数

  p%num_threads = get_numthreads()             ! スレッド数を取得
  p%real_precision = precision(p%dt)           ! 実数変数の有効桁数を取得

  p%dd = max(p%dd, tiny(p%dd))    ! ddにゼロが指定された場合は表現可能な最小値とする
  p%dv = max(p%dv, 0.00001)       ! dvにゼロが指定された場合は
  p%vv = max(p%vv, tiny(p%vv))    ! vvにゼロが指定された場合は表現可能な最小値とする

  p%initialized = .true.

end subroutine


!----------------------------------------------------------------------
! システムパラメータ構造体を削除する
!----------------------------------------------------------------------
subroutine m_sysparam_dispose(p)
  type(t_sysparam), intent(inout) :: p
  p%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================
!----------------------------------------------------------------------
! OpenMPで並列化されたスレッド数を取得する
!----------------------------------------------------------------------
function get_numthreads() result(nth)
  integer :: nth
  nth = 0
  !$omp parallel
  !$omp critical
  nth = nth + 1
  !$omp end critical
  !$omp end parallel
end function

!----------------------------------------------------------------------
end module
