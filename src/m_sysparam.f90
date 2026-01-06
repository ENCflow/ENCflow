module m_sysparam
  use list_sysparam, only : t_list_sysparam, list_sysparam_read
  use m_util, only : util_str2sec
  implicit none
  private

  public :: t_sysparam
  public :: m_sysparam_init
  public :: m_sysparam_dispose


  type t_sysparam
    real :: t0                                 ! 計算開始時刻 (s)
    real :: tt                                 ! 計算終了時刻 (s)
    real :: dt_disp                            ! 画面表示時間刻み (s)
    real :: dt_file                            ! ファイル出力時間刻み (s)
    real :: dt_recrd                           ! プローブ出力時間刻み (s)
    real :: st_file                            ! ファイル出力開始時間 (s)
    real :: st_recrd                           ! プローブ出力開始時間 (s)
    integer :: nt                              ! 総時間ステップ数
    integer :: idt_disp                        ! 画面表示時間刻みの時間ステップ数
    integer :: idt_file                        ! ファイル出力時間刻みの時間ステップ数
    integer :: idt_recd                        ! プローブ出力時間刻みの時間ステップ数
    integer :: ist_file                        ! ファイル出力開始時間の時間ステップ数
    integer :: ist_recd                        ! プローブ出力開始時間の時間ステップ数
    real :: dt                                 ! 時間ステップ (s)
    integer :: nx                              ! x方向セル数
    integer :: ny                              ! y方向セル数
    real :: dx                                 ! 計算格子の大きさ (m)
    real :: dy                                 ! 計算格子の大きさ (m)
    real :: dr                                 ! 計算格子の対角線の長さ (m)
    real :: dtpdx                              ! dt / mean(dx, dy) 
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
    integer :: f_state_restore                 ! 状態保存ファイルからの初期条件設定
    integer :: f_input_mode                    ! matrix入力形式(1:text, 2:bil)
    integer :: f_output_mode                   ! matrix出力形式(1:text, 2:bil, 3:txt+bil)
    integer :: f_output_compress               ! 出力ファイルの圧縮(0:なし, 2:gzip)
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
    integer :: f_out_pre                       ! ファイル出力(降雨強度R0001)
    integer :: f_out_fr                        ! ファイル出力(フルード数Fr0001)
    integer :: f_out_cn                        ! ファイル出力(クーラン数Cn0001)
    integer :: f_out_hmax                      ! ファイル出力(最大水深H9999)
    integer :: f_out_hmaxt                     ! ファイル出力(最大水深発生時刻Ht9999)
    integer :: f_out_vvmax                     ! ファイル出力(最大流速V9999)
    integer :: f_out_qqmax                     ! ファイル出力(最大流量Q9999)
    integer :: f_out_qqmaxt                    ! ファイル出力(最大流量発生時刻Qt9999)
    integer :: f_out_qqmaxd                    ! ファイル出力(最大流量の流向Qt9999)
    character(:), allocatable :: fn_sysparam   ! システムパラメータ設定ファイル
    character(:), allocatable :: fn_geoinfo    ! 地形条件設定ファイル
    character(:), allocatable :: fn_initial    ! 初期条件設定ファイル
    character(:), allocatable :: fn_precip     ! 降水条件設定ファイル
    character(:), allocatable :: fn_tide       ! 潮位条件設定ファイル
    character(:), allocatable :: fn_boundary   ! 境界条件設定ファイル
    character(:), allocatable :: fn_record     ! 記録設定ファイル
    character(:), allocatable :: fn_enc        ! ENC設定ファイル
    character(:), allocatable :: fn_log        ! 状態ログファイル
    character(:), allocatable :: dir_data      ! 入力データディレクトリ
    character(:), allocatable :: dir_result    ! 結果出力ディレクトリ
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
  p%f_state_restore =  list%f_state_restore    ! 状態保存ファイルからの初期条件設定
  p%f_input_mode = list%f_input_mode           ! matrix入力形式(1:text, 2:bil)
  p%f_output_mode = list%f_output_mode         ! matrix出力形式(1:text, 2:bil, 3:txt+bil)
  p%f_output_compress = list%f_output_compress ! 出力ファイルの圧縮(0:なし, 2:gzip)
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
  p%f_out_pre = list%f_out_pre                 ! ファイル出力(降雨強度R0001)
  p%f_out_fr = list%f_out_fr                   ! ファイル出力(フルード数Fr0001)
  p%f_out_cn = list%f_out_cn                   ! ファイル出力(クーラン数Cn0001)
  p%f_out_hmax = list%f_out_hmax               ! ファイル出力(最大水深H9999)
  p%f_out_hmaxt = list%f_out_hmaxt             ! ファイル出力(最大水深発生時刻Ht9999)
  p%f_out_vvmax = list%f_out_vvmax             ! ファイル出力(最大流速V9999)
  p%f_out_qqmax = list%f_out_qqmax             ! ファイル出力(最大流量Q9999)
  p%f_out_qqmaxt = list%f_out_qqmaxt           ! ファイル出力(最大流量発生時刻Qt9999)
  p%f_out_qqmaxd = list%f_out_qqmaxd           ! ファイル出力(最大流量の流向Qt9999)
  p%fn_geoinfo = list%fn_geoinfo               ! 地形条件設定ファイル
  p%fn_initial = list%fn_initial               ! 初期条件設定ファイル
  p%fn_precip = list%fn_precip                 ! 降水条件設定ファイル
  p%fn_tide = list%fn_tide                     ! 潮位条件設定ファイル
  p%fn_boundary = list%fn_boundary             ! 境界条件設定ファイル
  p%fn_record = list%fn_record                 ! 記録設定ファイル
  p%fn_enc = list%fn_enc                       ! ENC設定ファイル
  p%fn_log = list%fn_log                       ! 状態ログファイル
  p%dir_data = list%dir_data                   ! 入力データディレクトリ
  p%dir_result = list%dir_result               ! 結果出力ディレクトリ
  p%outfn_suffix = list%outfn_suffix           ! 出力ファイル名のサフィックス

  if (len(trim(list%t0_c)) > 0) p%t0 = util_str2sec(list%t0_c, "bad t0_c in &list_sysparam")
  if (len(trim(list%tt_c)) > 0) p%tt = util_str2sec(list%tt_c, "bad tt_c in &list_sysparam")
  if (len(trim(list%dt_c)) > 0) p%dt = util_str2sec(list%dt_c, "bad dt_c in &list_sysparam")
  if (len(trim(list%dt_disp_c)) > 0) p%dt_disp = util_str2sec(list%dt_disp_c, "bad dt_disp_c in &list_sysparam")
  if (len(trim(list%dt_file_c)) > 0) p%dt_file = util_str2sec(list%dt_file_c, "bad dt_file_c in &list_sysparam")
  if (len(trim(list%dt_recrd_c)) > 0) p%dt_recrd = util_str2sec(list%dt_recrd_c, "bad dt_recrd_c in &list_sysparam")
  if (len(trim(list%st_file_c)) > 0) p%st_file = util_str2sec(list%st_file_c, "bad st_file_c in &list_sysparam")
  if (len(trim(list%st_recrd_c)) > 0) p%st_recrd = util_str2sec(list%st_recrd_c, "bad st_recrd_c in &list_sysparam")

  if (p%dt == 0.0) then
    print *, 'error: dt = 0.0'
    stop
  end if

  p%nt = ceiling((p%tt - p%t0) / p%dt)         ! 総時間ステップ数
  p%idt_disp = max(nint(p%dt_disp / p%dt), 1)  ! 画面表示時間刻みの時間ステップ数
  p%idt_file = max(nint(p%dt_file / p%dt), 1)  ! ファイル出力時間刻みの時間ステップ数
  p%idt_recd = max(nint(p%dt_recrd / p%dt), 1) ! プローブ出力時間刻みの時間ステップ数
  p%ist_file = max(nint(p%st_file / p%dt), 1)  ! ファイル出力開始時間の時間ステップ数
  p%ist_recd = max(nint(p%st_recrd / p%dt), 1) ! プローブ出力開始時間の時間ステップ数

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
