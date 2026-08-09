module m_main
  use m_sysparam, only : t_sysparam, m_sysparam_init, m_sysparam_dispose
  use m_geoinfo, only : t_geoinfo, m_geoinfo_init, m_geoinfo_dispose, m_geoinfo_scatter_coeffs, m_geoinfo_band_shrink, m_geoinfo_row_ncells
  use m_precip, only : t_precip, m_precip_init, m_precip_dispose, m_precip_makepre
  use m_tide, only : t_tide, m_tide_init, m_tide_calc, m_tide_dispose
  use m_boundary, only : t_boundary, m_boundary_init, m_boundary_set_etaref, m_boundary_dispose, m_boundary_makebdc, &
                         m_boundary_dam_seed, m_boundary_dam_record
  use m_state, only : t_state, m_state_init, m_state_dispose, m_state_updatetime, m_state_calcstat, m_state_printstate
  use m_record, only : t_record, m_record_init, m_record_dispose, m_record_probe, m_record_flux, m_record_summary
  use m_geomorph, only : t_geomorph, m_geomorph_init, m_geomorph_calc, m_geomorph_dispose
  use m_gwflow, only : t_gwflow, m_gwflow_init, m_gwflow_calc, m_gwflow_dispose
  use m_evap, only : t_evap, m_evap_init, m_evap_calc, m_evap_record, m_evap_dispose
  use m_intercept, only : t_intercept, m_intercept_init, m_intercept_calc, m_intercept_step, &
                        m_intercept_dispose
  use m_swflow, only : t_swflow, m_swflow_init, m_swflow_dispose, m_swflow_calc, m_swflow_post
  use m_output, only : output_init, output_dispose, output_chk_geoinfo, output_state, output_summary
  use m_util, only : itoa
  use m_sysdep_util, only : sysdep_mkdir, sysdep_copy_to_dir
  use m_parallel

  implicit none
  private

  public :: m_main_all

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! メインルーチン
!----------------------------------------------------------------------
subroutine m_main_all()
  type(t_sysparam) :: p
  type(t_geoinfo) :: g
  type(t_precip) :: pr
  type(t_tide) :: ti
  type(t_boundary) :: b
  type(t_state) :: s
  type(t_record) :: r
  type(t_geomorph) :: gm
  type(t_gwflow) :: gw
  type(t_evap) :: ev
  type(t_intercept) :: ic
  type(t_swflow) :: sw
  character(len=256) :: fn_sysparam
  integer :: ierror

  ! MPIを初期化
  call par_init()

  ! システムパラメータファイル名を取得
  call get_fn_param(fn_sysparam)

  ! システムを初期化
  call m_sysparam_init(p, fn_sysparam)    ! sysparam を初期化
  ! 結果を保存するディレクトリを作成してパラメータファイルを保存
  call init_resultdir(p)

  ! モジュールを初期化
  ! ==== 初期化ゾーン1: 地形・マスク類(z,x,sw,rw)は全ランク全域、
  !      物性係数(rn,gv,bb,lm,rscap,lu)は rank0 のみ全域(方式2)。
  !      係数を使うフック・前処理は rank0 実行(m_geoinfo_init 内) ====
  call m_geoinfo_init(g, p)               ! geoinfo を初期化
  ! 全域窓を帯分割(行ごとの有効セル数を重みとして帯幅を調整。
  ! 列島形状の行間偏りによるランク間不均衡の対策。§11)
  decomp: block
    integer, allocatable :: rowwork(:)
    allocate(rowwork(1:g%ny))
    call m_geoinfo_row_ncells(g, rowwork)
    call par_decomp_init(g%nx, g%ny, g%wy(1), g%wy(2), rowwork)
  end block decomp
  call m_geoinfo_scatter_coeffs(g)        ! 物性係数を rank0 から帯+ハロへ配布

  ! ==== 初期化ゾーン2: 地形とマスク類(z, x, sw, rw)のみ全域
  !      (fill_depression, user_initial, record/boundary の検証はこの範囲) ====
  call m_boundary_init(b, p, g)           ! boundary を初期化(geoinfoより後に)
  call m_state_init(s, p, g)              ! state を初期化(geoinfo, boundaryより後に)
  call m_boundary_set_etaref(b, p, g, s)  ! 放射境界の基準水位を確定(stateより後に)
  call m_boundary_dam_seed(b, p, g, s)    ! ダム初期貯留を hrs へ(フレッシュラン時のみ。§22)
  call m_record_init(r, p, g)             ! record を初期化(create_resultdirより後)
  call m_precip_init(pr, p, g)            ! precip を初期化
  call m_intercept_init(ic, p, g)         ! intercept を初期化(fn_intercept 指定時のみ有効)
  call m_geomorph_init(gm, p, g, s)       ! geomorph を初期化(fn_geomorph 指定時のみ有効。
                                          ! s%sed_active を設定するため swflow init より前)
  call m_gwflow_init(gw, p, g, s)         ! gwflow を初期化(fn_gwflow 指定時のみ有効)
  call m_tide_init(ti, p, g, s)           ! tide を初期化(state より後・swflow より
                                          ! 前: 海セルの初期状態(z, h)をセットする)
  call m_swflow_init(sw, p, g, b, s)      ! swflow を初期化
  call m_evap_init(ev, p, g, b, s)        ! evap を初期化(fn_evap 指定時のみ有効。
                                          ! ダム湛水面積の登録に boundary、基準標高に
                                          ! state の z を使うため両者より後に)
  call output_init(p, g)                  ! ファイル出力の準備(geoinfoより後に)

  ! 地理情報を各ランクに合わせて縮小
  call m_geoinfo_band_shrink(g)           ! マスク類(x,sw,rw)と z(rank0以外)を帯に縮小

  ! ==== 時間ループ: すべて帯確保(z のみ rank0 が全域を保持) ====
  call run_main(p, g, b, pr, ti, ic, s, r, sw, gm, gw, ev, ierror)  ! 計算本体

  ! モジュールを破棄
  call output_dispose()
  call m_swflow_dispose(sw, p)
  call m_tide_dispose(ti)
  call m_precip_dispose(pr)
  call m_intercept_dispose(ic, p)
  call m_geomorph_dispose(gm)
  call m_gwflow_dispose(gw, p)
  call m_evap_dispose(ev, p)
  call m_record_dispose(r)
  call m_state_dispose(s, p)
  call m_boundary_dispose(b)
  call m_geoinfo_dispose(g)
  call m_sysparam_dispose(p)

  ! MPIを終了
  call par_finalize()

  ! エラーがあった場合は異常終了コードを返して停止
  ! (error stop でなく、dispose と par_finalize を通してから stop する)
  if (ierror > 0) then
    stop 1
  end if

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 計算本体
!----------------------------------------------------------------------
subroutine run_main(p, g, b, pr, ti, ic, s, r, sw, gm, gw, ev, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  type(t_precip), intent(in) :: pr
  type(t_tide), intent(inout) :: ti    ! titype=4 の分布バッファを更新するため inout
  type(t_intercept), intent(in) :: ic
  type(t_state), intent(inout) :: s
  type(t_record), intent(inout) :: r
  type(t_geomorph), intent(in) :: gm
  type(t_gwflow), intent(in) :: gw
  type(t_swflow), intent(in) :: sw
  type(t_evap), intent(inout) :: ev    ! 蒸発散(PET の日次更新・累積診断を保持)
  integer, intent(out) :: ierror
  integer :: it            ! 時間ループのカウント
  logical :: do_file       ! このステップでファイル出力するか
  logical :: do_recd       ! このステップでプローブ・フラックス出力するか
  logical :: pr_updated    ! このコールで降雨分布が実際に更新されたか

  call par_info("number of processes : "//itoa(nproc))
  call par_info("number of threads : "//itoa(p%num_threads))
  call par_info("real precision : "//itoa(storage_size(1.0))//" bit")
  call par_info("number of valid cells : "//itoa(s%n_valcells))

  ! 諸情報を初期化
  !   時間軸は絶対時刻1本(s%t = t0 + dt*it)。フレッシュランは it=0 から、
  !   restore 時は save 記録の it(s%it0)から継続する(§7)。
  !   出力ファイル番号 s%ifn も restore 時は続き番号(m_state_init が設定済み)
  call m_state_updatetime(s, p, s%it0)    ! 時刻情報を初期化
  call m_precip_makepre(pr, p, g, s, pr_updated)  ! 初期降水分布を作成　
  if (pr_updated) call m_intercept_calc(ic, p, g, s, 0)  ! 遮断による有効雨量化(fn_intercept 未指定なら no-op)
  call m_state_calcstat(s, p, g)          ! 統計情報を計算

  ! 初期状態の出力(ファイルへの書き込みはランク0のみ。番号 0 は
  ! 「このランの開始状態」の固定スロット: restore 時は復元状態が書かれる)
  call m_state_printstate(p, s)         ! 途中経過を画面に出力
  call output_state(p, g, s, 0)         ! 初期状態をファイル出力(集約は output_matrix 内)
  call m_record_probe(r, p, s)          ! プローブの値を出力
  call m_record_flux(r, p, s)           ! フラックスの値を出力
  call m_boundary_dam_record(b, p, s)   ! ダム CSV(ダムがなければ no-op)
  call m_evap_record(ev, p, s)          ! 蒸発散 CSV(fn_evap 未指定なら no-op)
  ierror = 0                            ! エラー数をリセット

  ! デバッグ用データを出力
  call output_chk_geoinfo(g)


  !------ 時間ステップのループここから ------
  do it = s%it0 + 1, p%nt

    ! 時刻情報を更新
    call m_state_updatetime(s, p, it)

    ! dt_prupdate 間隔で降水分布を更新し、更新時のみ遮断を適用する
    ! (prtype=3 は makepre が呼ばれても分布を更新しないステップがあり、
    !  そこで遮断を再適用すると二重減衰になる。updated が正本)
    if (mod(it, pr%idt_prupdate) == 0) then
      call m_precip_makepre(pr, p, g, s, pr_updated)
      if (pr_updated) call m_intercept_calc(ic, p, g, s, it)
    end if

    ! 貯留型遮断モデルの毎ステップ更新(swflow が s%pre を読む前に呼ぶ。
    ! step 口を持たないモデル(固定遮断率)や無効時は何もしない)
    call m_intercept_step(ic, p, g, s, it)

    ! 境界条件を準備
    call m_boundary_makebdc(b, p, g, s)

    ! 潮位を更新して海セルへ適用(fn_tide 未指定なら no-op。更新間隔は
    ! dt_tiupdate。s%z の変更はステップ頭のハロ交換が運ぶので swflow より前に)
    call m_tide_calc(ti, p, g, s)

    ! 地表水を計算
    call m_swflow_calc(sw, p, g, b, s, ierror)

    ! 発散検出はランク局所のため、判定に先立ち全ランク最大へ集約する
    call par_allreduce_maxi(ierror)

    ! 地下水を計算(fn_gwflow 未指定なら no-op。流れ→水収支→地形の順)
    call m_gwflow_calc(gw, p, g, s, it)

    ! 蒸発散を適用(fn_evap 未指定なら no-op。樹冠→地表水→hrs→地下水の
    ! 優先順位減算とダム湛水面蒸発。浸透後の状態に作用させる。§27)
    call m_evap_calc(ev, p, g, b, s, ic, it)

    ! ステップ末尾パス: σ 有効時の u,v 正規化を最終確定 h で行う
    ! (gwflow・evap の後、geomorph・統計・出力の前。σ 無効・STG では
    ! no-op。§26)
    call m_swflow_post(sw, p, g, s)

    ! 地形変化を計算(fn_geomorph 未指定なら no-op。s%z と s%e を更新し、
    ! 末尾で s%z のハロ交換まで済ませる)
    call m_geomorph_calc(gm, p, g, s, it)

    ! 統計情報を計算
    call m_state_calcstat(s, p, g)


    ! dt_disp 間隔で途中経過を画面に出力
    if (mod(it, p%idt_disp) == 0) then
      call m_state_printstate(p, s)
    end if

    ! 出力の判定(集約は output_matrix 内で行う。collective なので
    ! output の呼び出し自体を全ランクで同一に判定すること)
    do_file = (it >= p%ist_file .and. it <= p%iet_file .and. mod(it, p%idt_file) == 0)
    do_recd = (it >= p%ist_recd .and. it <= p%iet_recd .and. mod(it, p%idt_recd) == 0)

    ! dt_file 間隔で計算結果をファイルに出力(通し番号は s%ifn。
    ! save に記録され、restore 時は続き番号から再開する)
    if (do_file) then
      s%ifn = s%ifn + 1
      call output_state(p, g, s, s%ifn)
    end if

    ! dt_record 間隔でプローブとフラックスの値を出力
    if (do_recd) then
     call m_record_probe(r, p, s)
     call m_record_flux(r, p, s)
     call m_boundary_dam_record(b, p, s)
     call m_evap_record(ev, p, s)
    end if


    ! --- エラー判定(全ランクで同一の判定を行い、同時にループを抜ける) ---
    ! 注意: 判定は必ず全ランクで実行すること。ランク0だけが exit すると
    !       他ランクが回り続け、par_finalize で整合しなくなる。
    !       ierror は swflow_calc 直後に、cnmax は calcstat 内で全ランク
    !       集約済みなので、以下の判定は全ランクで同一になる。

    ! CFL条件のチェック
    if (p%f_check_cfl > 0 .and. s%cnmax > 1.) then
      call par_info("********************************************")
      call par_info("******** Courant number exceeds 1.0 ********")
      call par_info("********************************************")
      call m_state_printstate(p, s)
      ierror = ierror + 1
    end if

    ! オーバーフローを回避するためにチェック
    if (s%cnmax > 100.) then
      call par_info("**********************************************************************")
      call par_info("******** Unrealistic calculation (Courant number exceeds 100) ********")
      call par_info("**********************************************************************")
      ierror = ierror + 1
    end if

    ! サブルーチンからのエラーも含めてエラーがあれば終了
    if (ierror > 0) then
      call m_state_printstate(p, s)
      exit
    end if

  end do
  !------ 時間ステップのループここまで ------


  ! 最終状態を出力
  call output_state(p, g, s, 9998)

  ! 統計量を出力
  call output_summary(p, g, s, 9999)

  ! 最大流量の一覧を出力
  call m_record_summary(r, p)


  ! エラー処理は m_main_all 側で行う(dispose と par_finalize を通すため
  ! ここでは error stop しない。ierror を返すのみ)

end subroutine


!----------------------------------------------------------------------
! 計算結果保存ディレクトリを作成してパラメータファイルを保存する
!----------------------------------------------------------------------
subroutine init_resultdir(p)
  type(t_sysparam), intent(in) :: p
  call sysdep_mkdir(p%dir_result)                       ! 結果を保存するディレクトリを作成
  call sysdep_copy_to_dir(p%fn_sysparam, p%dir_result)  ! パラメータファイルを保存
  call sysdep_copy_to_dir(p%fn_geoinfo, p%dir_result)
  call sysdep_copy_to_dir(p%fn_initial, p%dir_result)
  call sysdep_copy_to_dir(p%fn_precip, p%dir_result)
  call sysdep_copy_to_dir(p%fn_tide, p%dir_result)
  call sysdep_copy_to_dir(p%fn_boundary, p%dir_result)
  call sysdep_copy_to_dir(p%fn_record, p%dir_result)
  call sysdep_copy_to_dir(p%fn_enc, p%dir_result)
end subroutine


!----------------------------------------------------------------------
! コマンドライン引数から設定ファイル名を取得する
!----------------------------------------------------------------------
subroutine get_fn_param(fn_param)
  character(len=*) :: fn_param

  ! コマンドライン引数の文字列を保存する構造体の宣言
  !  可変長文字列の配列が直接作れないため構造体の配列を利用
  type :: t_arguments
    character(:), allocatable :: v           ! 無指定文字長（可変長）文字列変数vを要素に持つ
  end type

  ! コマンドライン引数の数と文字列
  integer :: argc
  type(t_arguments), allocatable :: arg(:)

  
  !--- コマンドライン引数取得の準備 ---
  argc = command_argument_count()            ! 引数の数を取得
  allocate(arg(0:argc))                      ! 構造体のメモリを確保

  !--- コマンドライン引数を取得 ---
  get_arguments: block
    integer :: i, l
    do i = 0, argc
      call get_command_argument(number=i, length=l)         ! i番目の引数の長さを取得
      allocate(character(l) :: arg(i)%v)                    ! 構造体中の文字列用メモリを確保
      call get_command_argument(number=i, value=arg(i)%v)   ! 引数の文字列を取得
    end do
  end block get_arguments

  if (argc >= 1) then
    fn_param = arg(1)%v
  else
    call par_stop("usage: "//arg(0)%v//" parameterfile")
  end if
end subroutine


end module
