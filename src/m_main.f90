module m_main
  use m_sysparam, only : t_sysparam, m_sysparam_init, m_sysparam_dispose
  use m_geoinfo, only : t_geoinfo, m_geoinfo_init, m_geoinfo_dispose, m_geoinfo_scatter_coeffs, m_geoinfo_band_shrink, m_geoinfo_row_ncells
  use m_precip, only : t_precip, m_precip_init, m_precip_dispose, m_precip_makepre
  use m_tide, only : t_tide, m_tide_init, m_tide_calc, m_tide_dispose
  use m_saltwater, only : t_saltwater, m_saltwater_init, m_saltwater_calc, &
                          m_saltwater_dispose
  use m_boundary, only : t_boundary, m_boundary_init, m_boundary_set_etaref, m_boundary_dispose, m_boundary_makebdc, &
                         m_boundary_dam_seed, m_boundary_dam_record, &
                         m_boundary_dam_gwcheck, m_boundary_dam_gwforce
  use m_state, only : t_state, m_state_init, m_state_dispose, m_state_updatetime, m_state_calcstat, m_state_printstate
  use m_record, only : t_record, m_record_init, m_record_dispose, m_record_probe, m_record_flux, m_record_summary
  use m_geomorph, only : t_geomorph, m_geomorph_init, m_geomorph_calc, m_geomorph_dispose
  use m_gwflow, only : t_gwflow, m_gwflow_init, m_gwflow_check_meteo, &
                       m_gwflow_calc, m_gwflow_dispose
  use m_evap, only : t_evap, m_evap_init, m_evap_calc, m_evap_record, m_evap_dispose
  use m_meteo, only : t_meteo, m_meteo_init, m_meteo_dispose
  use m_wq, only : t_wq, m_wq_init, m_wq_calc, m_wq_derive, m_wq_record, m_wq_dispose
  use m_driftwood, only : t_driftwood, m_driftwood_init, m_driftwood_calc, &
                          m_driftwood_record, m_driftwood_dispose
  use m_snow, only : t_snow, m_snow_init, m_snow_calc, m_snow_dispose
  use m_swi, only : t_swi, m_swi_init, m_swi_calc, m_swi_dispose
  use m_glacier, only : t_glacier, m_glacier_init, m_glacier_calc, m_glacier_dispose
  use m_lavaflow, only : t_lavaflow, m_lavaflow_init, m_lavaflow_calc, m_lavaflow_dispose
  use m_intercept, only : t_intercept, m_intercept_init, m_intercept_calc, m_intercept_step, &
                        m_intercept_has_step, m_intercept_dispose
  use m_swflow, only : t_swflow, m_swflow_init, m_swflow_dispose, m_swflow_calc, m_swflow_post
  use m_output, only : output_init, output_dispose, output_chk_geoinfo, output_state, output_summary
  use m_util, only : itoa
  use m_sysdep_util, only : sysdep_mkdir, sysdep_copy_to_dir
  use m_parallel

  implicit none
  private

  public :: m_main_all
  public :: m_main_initialize
  public :: m_main_update
  public :: m_main_finished
  public :: m_main_finalize

  !----------------------------------------------------------------------
  ! ENCflow 全体を表す派生型(ライフサイクル API の内部状態)
  !   型もインスタンスも m_main の実装詳細として非公開。外部(将来の
  !   BMI アダプタ等)には m_main_* の公開手続きだけを見せる。
  !   単一インスタンス(1プロセス=1モデル)。複数インスタンスが必要に
  !   なったら型を公開せずに handle 方式へ拡張する(docs/bmi_plan.md §5)
  !----------------------------------------------------------------------
  type :: t_encflow
    type(t_sysparam) :: p
    type(t_geoinfo) :: g
    type(t_precip) :: pr
    type(t_tide) :: ti
    type(t_saltwater) :: sl
    type(t_boundary) :: b
    type(t_state) :: s
    type(t_record) :: r
    type(t_geomorph) :: gm
    type(t_gwflow) :: gw
    type(t_evap) :: ev
    type(t_meteo) :: mt
    type(t_wq) :: wq
    type(t_driftwood) :: dw
    type(t_snow) :: sn
    type(t_swi) :: si
    type(t_glacier) :: gl
    type(t_lavaflow) :: lv
    type(t_intercept) :: ic
    type(t_swflow) :: sw
    integer :: ierror = 0            ! 累積エラー数(>0 で時間ループ終了)
    logical :: initialized = .false.
  end type t_encflow

  type(t_encflow), save :: enc

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! メインルーチン(従来どおりの一括実行)
!   initialize → update ループ → finalize の合成。main.f90 からの
!   呼び出しはこれまでと変わらない
!----------------------------------------------------------------------
subroutine m_main_all()

  call m_main_initialize()

  do while (.not. m_main_finished())
    call m_main_update()
  end do

  call m_main_finalize()

  ! エラーがあった場合は異常終了コードを返して停止
  ! (error stop でなく、dispose と par_finalize を通してから stop する)
  if (enc%ierror > 0) then
    stop 1
  end if

end subroutine


!----------------------------------------------------------------------
! ライフサイクル: 初期化
!   MPI 初期化から時間ループ前の初期出力までを行う。
!   fn_sysparam 省略時はコマンドライン引数から取得する(従来動作)
!----------------------------------------------------------------------
subroutine m_main_initialize(fn_sysparam)
  character(len=*), intent(in), optional :: fn_sysparam
  character(len=256) :: fn_param

  ! MPIを初期化
  call par_init()

  ! システムパラメータファイル名を取得
  if (present(fn_sysparam)) then
    fn_param = fn_sysparam
  else
    call get_fn_param(fn_param)
  end if

  associate (p => enc%p, g => enc%g, pr => enc%pr, ti => enc%ti, &
             sl => enc%sl, b => enc%b, s => enc%s, r => enc%r, &
             gm => enc%gm, gw => enc%gw, ev => enc%ev, mt => enc%mt, &
             wq => enc%wq, dw => enc%dw, sn => enc%sn, si => enc%si, &
             gl => enc%gl, lv => enc%lv, ic => enc%ic, sw => enc%sw)

    ! システムを初期化
    call m_sysparam_init(p, fn_param)       ! sysparam を初期化
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
    call m_wq_init(wq, p, g, b, s)          ! wq を初期化(fn_wq 指定時のみ有効。
                                            ! s%wq_active を立てるため swflow・record init
                                            ! より前、セル検証にゾーン2の全域マスクを使う)
    call m_record_init(r, p, g, s)          ! record を初期化(create_resultdirより後。
                                            ! wq の追加列判定に state を使う)
    call m_precip_init(pr, p, g)            ! precip を初期化
    call m_intercept_init(ic, p, g)         ! intercept を初期化(fn_intercept 指定時のみ有効)
    call m_geomorph_init(gm, p, g, s)       ! geomorph を初期化(fn_geomorph 指定時のみ有効。
                                            ! s%sed_active を設定するため swflow init より前)
    call m_driftwood_init(dw, p, g, b, s)   ! driftwood を初期化(fn_driftwood 指定時のみ
                                            ! 有効。s%dw_active を立てるため swflow init
                                            ! より前、morfac 検査(s%geo_morfac)のため
                                            ! geomorph init より後に。§50)
    call m_gwflow_init(gw, p, g, s)         ! gwflow を初期化(fn_gwflow 指定時のみ有効)
    call m_saltwater_init(sl, p, g, s)      ! saltwater を初期化(fn_salt 指定時のみ
                                            ! 有効。s%salt_active を立てるため swflow init
                                            ! より前、層1側方の係数取得のため gwflow より後)
    call m_tide_init(ti, p, g, s)           ! tide を初期化(state より後・swflow より
                                            ! 前: 海セルの初期状態(z, h)をセットする)
    call m_swflow_init(sw, p, g, b, s)      ! swflow を初期化
    call m_meteo_init(mt, p, g, s)          ! meteo を初期化(fn_meteo 指定時のみ有効。
                                            ! 基準標高の既定に state の z を使うため後に)
    call m_gwflow_check_meteo(gw, mt)       ! 凍土(f_gwfrost)の気温入力検査(gwflow init は
                                            ! meteo より先に走るため、ここで検査する)
    call m_boundary_dam_gwcheck(b, gw%enabled .and. gw%lat_enabled)
                                            ! 湖水位の地下水頭強制(dam_gw)の前提検査
                                            ! (boundary init は gwflow より先に走るため、
                                            ! ここで検査する。§22 第3弾)
    call m_evap_init(ev, p, g, b, s, mt)    ! evap を初期化(fn_evap 指定時のみ有効。
                                            ! ダム湛水面積の登録に boundary、基準標高に
                                            ! state の z を使うため両者より後に)
    call m_snow_init(sn, p, g, s, mt)       ! snow を初期化(fn_snow 指定時のみ有効。
                                            ! 気温が必須のため meteo より後に)
    call m_glacier_init(gl, p, g, s, mt)    ! glacier を初期化(fn_glacier 指定時のみ有効。
                                            ! 気温と積雪(涵養源)が必須のため
                                            ! meteo・snow より後に。§45)
    call m_lavaflow_init(lv, p, g, s)       ! lavaflow を初期化(fn_lavaflow 指定時のみ
                                            ! 有効。morfac 検査(s%geo_morfac)のため
                                            ! geomorph init より後に。lava_plan.md)
    call m_swi_init(si, p, g, s)            ! swi を初期化(fn_swi 指定時のみ有効。
                                            ! 排他検査に他モジュールの fn_* を使う。§49)
    call output_init(p, g)                  ! ファイル出力の準備(geoinfoより後に)

    ! 地理情報を各ランクに合わせて縮小
    call m_geoinfo_band_shrink(g)           ! マスク類(x,sw,rw)と z(rank0以外)を帯に縮小

    ! ==== 時間ループ: すべて帯確保(z のみ rank0 が全域を保持) ====
    ! ループ前の初期化・初期出力(従来 run_main の前半)
    call run_init(p, g, b, pr, ic, s, r, ev, mt, wq, dw, enc%ierror)

  end associate

  enc%initialized = .true.

end subroutine


!----------------------------------------------------------------------
! ライフサイクル: 1時間ステップ進める
!   従来 run_main の時間ループ本体1回分。終了判定は m_main_finished
!----------------------------------------------------------------------
subroutine m_main_update()

  associate (p => enc%p, g => enc%g, pr => enc%pr, ti => enc%ti, &
             sl => enc%sl, b => enc%b, s => enc%s, r => enc%r, &
             gm => enc%gm, gw => enc%gw, ev => enc%ev, mt => enc%mt, &
             wq => enc%wq, dw => enc%dw, sn => enc%sn, si => enc%si, &
             gl => enc%gl, lv => enc%lv, ic => enc%ic, sw => enc%sw)

    call run_step(p, g, b, pr, ti, ic, s, r, sw, gm, gw, sl, ev, mt, &
                  wq, dw, sn, gl, lv, si, enc%ierror)

  end associate

end subroutine


!----------------------------------------------------------------------
! ライフサイクル: 終了判定
!   時間ループの継続条件の否定(全ステップ完了またはエラー)。
!   判定材料(s%it, ierror)は全ランクで同一なので collective 安全(§5)
!----------------------------------------------------------------------
logical function m_main_finished()
  m_main_finished = (enc%ierror > 0 .or. enc%s%it >= enc%p%nt)
end function


!----------------------------------------------------------------------
! ライフサイクル: 終了処理
!   最終出力(従来 run_main の後半)とモジュール破棄、MPI 終了。
!   エラー時の stop は行わない(呼び出し側 = m_main_all が行う)
!----------------------------------------------------------------------
subroutine m_main_finalize()

  associate (p => enc%p, g => enc%g, pr => enc%pr, ti => enc%ti, &
             sl => enc%sl, b => enc%b, s => enc%s, r => enc%r, &
             gm => enc%gm, gw => enc%gw, ev => enc%ev, mt => enc%mt, &
             wq => enc%wq, dw => enc%dw, sn => enc%sn, si => enc%si, &
             gl => enc%gl, lv => enc%lv, ic => enc%ic, sw => enc%sw)

    ! 最終出力(従来 run_main の末尾)
    call run_close(p, g, s, r)

    ! モジュールを破棄
    call output_dispose()
    call m_swflow_dispose(sw, p)
    call m_tide_dispose(ti)
    call m_saltwater_dispose(sl, p, g, s)   ! save は dispose で(契約5)
    call m_precip_dispose(pr)
    call m_intercept_dispose(ic, p)
    call m_geomorph_dispose(gm)
    call m_gwflow_dispose(gw, p, g, s)      ! 層2の save は dispose で(契約5)
    call m_evap_dispose(ev, p)
    call m_meteo_dispose(mt)
    call m_wq_dispose(wq, p, g, s)          ! save は dispose で(m_state より先に走る)
    call m_driftwood_dispose(dw, p, g, s)   ! save は dispose で(m_state より先に走る)
    call m_snow_dispose(sn, p, g, s)        ! save は dispose で(契約5)
    call m_glacier_dispose(gl, p, g, s)     ! save は dispose で(契約5)
    call m_lavaflow_dispose(lv, p, g, s)    ! save は dispose で(契約5)
    call m_swi_dispose(si, p, g)            ! save は dispose で(契約5。§49)
    call m_record_dispose(r)
    call m_state_dispose(s, p)
    call m_boundary_dispose(b)
    call m_geoinfo_dispose(g)
    call m_sysparam_dispose(p)

  end associate

  ! 終了メッセージ(画面のみ。Log には書かない = 回帰基準の Log.txt を
  ! 不変に保つ。最終の状態表示行で切れたように見えるのを防ぐ)
  if (enc%ierror > 0) then
    call par_info("main: program terminated with error(s)")
  else
    call par_info("main: program terminated normally")
  end if

  ! MPIを終了
  call par_finalize()

  enc%initialized = .false.

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 時間ループ前の初期化・初期出力(従来 run_main の前半)
!----------------------------------------------------------------------
subroutine run_init(p, g, b, pr, ic, s, r, ev, mt, wq, dw, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  type(t_precip), intent(in) :: pr
  type(t_intercept), intent(in) :: ic
  type(t_state), intent(inout) :: s
  type(t_record), intent(inout) :: r
  type(t_evap), intent(inout) :: ev    ! 蒸発散(PET の日次更新・累積診断を保持)
  type(t_meteo), intent(inout) :: mt   ! 気象強制場(分布気温の読み進みを保持)
  type(t_wq), intent(inout) :: wq      ! 水質(発生源・台帳を保持)
  type(t_driftwood), intent(inout) :: dw  ! 流木(立木ストック・台帳を保持。§50)
  integer, intent(out) :: ierror
  logical :: pr_updated    ! このコールで降雨分布が実際に更新されたか

  call par_info("main: number of processes: "//itoa(nproc))
  call par_info("main: number of threads: "//itoa(p%num_threads))
  call par_info("main: real precision: "//itoa(storage_size(1.0))//" bit")
  call par_info("main: number of valid cells: "//itoa(s%n_valcells))

  ! 諸情報を初期化
  !   時間軸は絶対時刻1本(s%t = t0 + dt*it)。フレッシュランは it=0 から、
  !   restore 時は save 記録の it(s%it0)から継続する(§7)。
  !   出力ファイル番号 s%ifn も restore 時は続き番号(m_state_init が設定済み)
  call m_state_updatetime(s, p, s%it0)    ! 時刻情報を初期化
  call m_precip_makepre(pr, p, g, s, mt, pr_updated)  ! 初期降水分布を作成
  if (pr_updated) call m_intercept_calc(ic, p, g, s, 0)  ! 遮断による有効雨量化(fn_intercept 未指定なら no-op)
  call m_state_calcstat(s, p, g)          ! 統計情報を計算
  call m_wq_derive(wq, p, g, s)           ! 初期濃度場の導出(初期出力・プローブより
                                          ! 前に。fn_wq 未指定なら no-op。§30)

  ! 初期状態の出力(ファイルへの書き込みはランク0のみ。番号 0 は
  ! 「このランの開始状態」の固定スロット: restore 時は復元状態が書かれる)
  call m_state_printstate(p, s)         ! 途中経過を画面に出力
  call output_state(p, g, s, 0)         ! 初期状態をファイル出力(集約は output_matrix 内)
  call m_record_probe(r, p, s)          ! プローブの値を出力
  call m_record_flux(r, p, s)           ! フラックスの値を出力
  call m_boundary_dam_record(b, p, s)   ! ダム CSV(ダムがなければ no-op)
  call m_evap_record(ev, p, s)          ! 蒸発散 CSV(fn_evap 未指定なら no-op)
  call m_wq_record(wq, p, g, s)         ! 水質 CSV(fn_wq 未指定なら no-op)
  call m_driftwood_record(dw, p, g, s)  ! 流木 CSV(fn_driftwood 未指定なら no-op)
  ierror = 0                            ! エラー数をリセット

  ! デバッグ用データを出力
  call output_chk_geoinfo(g)

end subroutine


!----------------------------------------------------------------------
! 計算本体: 時間ステップ1回分(従来 run_main のループ本体)
!   進行位置は s%it が正本(m_state_updatetime が更新)。エラーは
!   ierror に累積し、継続判定は呼び出し側(m_main_finished)が行う
!----------------------------------------------------------------------
subroutine run_step(p, g, b, pr, ti, ic, s, r, sw, gm, gw, sl, ev, mt, wq, dw, sn, gl, lv, si, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  type(t_precip), intent(in) :: pr
  type(t_tide), intent(inout) :: ti    ! titype=4 の分布バッファを更新するため inout
  type(t_saltwater), intent(in) :: sl
  type(t_intercept), intent(in) :: ic
  type(t_state), intent(inout) :: s
  type(t_record), intent(inout) :: r
  type(t_geomorph), intent(in) :: gm
  type(t_gwflow), intent(in) :: gw
  type(t_swflow), intent(in) :: sw
  type(t_evap), intent(inout) :: ev    ! 蒸発散(PET の日次更新・累積診断を保持)
  type(t_meteo), intent(inout) :: mt   ! 気象強制場(分布気温の読み進みを保持)
  type(t_wq), intent(inout) :: wq      ! 水質(発生源・台帳を保持)
  type(t_driftwood), intent(inout) :: dw  ! 流木(立木ストック・台帳を保持。§50)
  type(t_snow), intent(inout) :: sn    ! 積雪・融雪(SWE とスナップショットを保持)
  type(t_glacier), intent(in) :: gl    ! 氷河(氷厚 s%hi と作業台帳を保持)
  type(t_lavaflow), intent(in) :: lv   ! 溶岩流(溶岩厚 s%hl と作業台帳を保持)
  type(t_swi), intent(inout) :: si     ! 土壌雨量指数(タンク貯留を保持。§49)
  integer, intent(inout) :: ierror
  integer :: it            ! このステップの時間カウント(= s%it + 1)
  logical :: do_file       ! このステップでファイル出力するか
  logical :: do_recd       ! このステップでプローブ・フラックス出力するか
  logical :: pr_updated    ! このコールで降雨分布が実際に更新されたか

  it = s%it + 1
  pr_updated = .false.     ! makepre 未実行ステップの参照を定義済みにする
                           ! (読むのは makepre 実行ステップのみ = 挙動不変)

  ! 時刻情報を更新
  call m_state_updatetime(s, p, it)

  ! dt_prupdate 間隔で降水分布を更新し、更新時のみ遮断を適用する
  ! (prtype=3 は makepre が呼ばれても分布を更新しないステップがあり、
  !  そこで遮断を再適用すると二重減衰になる。updated が正本)
  if (mod(it, pr%idt_prupdate) == 0) then
    call m_precip_makepre(pr, p, g, s, mt, pr_updated)
    if (pr_updated) call m_intercept_calc(ic, p, g, s, it)
  end if

  ! 貯留型遮断モデルの毎ステップ更新(swflow が s%pre を読む前に呼ぶ。
  ! step 口を持たないモデル(固定遮断率)や無効時は何もしない)
  call m_intercept_step(ic, p, g, s, it)

  ! 積雪・融雪(fn_snow 未指定なら no-op。遮断後降水の雨/雪分離で
  ! s%pre を液体分に減じ、融雪を h へ直接投入する。swflow より前。
  ! pr_fresh = 上流が s%pre を書き直したステップ(スナップショット契約。§31)
  call m_snow_calc(sn, p, g, s, mt, &
                   (mod(it, pr%idt_prupdate) == 0 .and. pr_updated) &
                   .or. m_intercept_has_step(ic))

  ! 土壌雨量指数(fn_swi 未指定なら no-op。遮断適用後の地上雨量 s%pre を
  ! 読む純診断。どの物理場にも書かない。§49)
  call m_swi_calc(si, p, g, s)

  ! 氷河(fn_glacier 未指定なら no-op。氷面の度日融解を毎ステップ h へ
  ! 投入し、雪崩再配分・氷化・SIA 流動・氷河侵食を dt_glacier 間隔で
  ! 行う。侵食時は s%z / s%sd の更新と e 回復・ハロ交換まで済ませる。
  ! snow の後(SWE を受ける)・swflow の前(融解水を流す)。§45)
  call m_glacier_calc(gl, p, g, s, mt, it)

  ! 境界条件を準備
  call m_boundary_makebdc(b, p, g, s)

  ! 潮位を更新して海セルへ適用(fn_tide 未指定なら no-op。更新間隔は
  ! dt_tiupdate。s%z の変更はステップ頭のハロ交換が運ぶので swflow より前に)
  call m_tide_calc(ti, p, g, s)

  ! 地表水を計算
  call m_swflow_calc(sw, p, g, b, s, ierror)

  ! 発散検出はランク局所のため、判定に先立ち全ランク最大へ集約する
  call par_allreduce_maxi(ierror)

  ! 湖水位の地下水頭強制(dam_gw 指定の湖沼のみ。gwflow と同周期で
  ! m_gwflow_calc の直前に湖面セルの hg を規定し、交換量を湖の貯留と
  ! やり取りする。未指定なら実質 no-op。§22 第3弾)
  if (gw%enabled .and. gw%lat_enabled) then
    if (mod(it, gw%idt_gwflow) == 0) then
      call m_boundary_dam_gwforce(b, p, g, s, gw%dts)
    end if
  end if

  ! 地下水を計算(fn_gwflow 未指定なら no-op。流れ→水収支→地形の順)
  call m_gwflow_calc(gw, p, g, s, mt, it)

  ! 淡塩2層を適用(fn_salt 未指定なら no-op。地表重力流・地下塩水 zone・
  ! 海側境界。合計 h/hg の確定後に塩水層厚を追随させる。§47)
  call m_saltwater_calc(sl, p, g, s, it)

  ! 水質過程を適用(fn_wq 未指定なら no-op。境界流入濃度の更新・
  ! 浸透同伴・発生源投入・ダム捕捉。gwflow が記録した浸透量 fxg を
  ! 消費するため直後に置く。§30)
  call m_wq_calc(wq, p, g, b, s, it)

  ! 蒸発散を適用(fn_evap 未指定なら no-op。樹冠→地表水→hrs→地下水の
  ! 優先順位減算とダム湛水面蒸発。浸透後の状態に作用させる。§27)
  call m_evap_calc(ev, p, g, b, s, ic, mt, it)

  ! ステップ末尾パス: σ 有効時の u,v 正規化を最終確定 h で行う
  ! (gwflow・evap の後、geomorph・統計・出力の前。σ 無効・STG では
  ! no-op。§26)
  call m_swflow_post(sw, p, g, s)

  ! 導出濃度場の更新(確定 h に対する cqc。統計・出力より前。§30)
  call m_wq_derive(wq, p, g, s)

  ! 地形変化を計算(fn_geomorph 未指定なら no-op。s%z と s%e を更新し、
  ! 末尾で s%z のハロ交換まで済ませる)
  call m_geomorph_calc(gm, p, g, s, it)

  ! 流木過程を適用(fn_driftwood 未指定なら no-op。発生・停止・再流動・
  ! ダム捕捉。geomorph の後 = 同一ステップの z 更新を見た侵食連行。
  ! セル局所のみでハロ交換なし。§50)
  call m_driftwood_calc(dw, p, g, s, it)

  ! 溶岩流を計算(fn_lavaflow 未指定なら no-op。噴火口ソース →
  ! Bingham 拡散流動 → 固化。固化時は s%z の更新と e 回復・ハロ交換
  ! まで済ませる。z 更新プロセスの末尾 = geomorph・driftwood の後。
  ! lava_plan.md)
  call m_lavaflow_calc(lv, p, g, s, it)

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
   call m_wq_record(wq, p, g, s)
   call m_driftwood_record(dw, p, g, s)
  end if


  ! --- エラー判定(全ランクで同一の判定を行い、同時にループを抜ける) ---
  ! 注意: 判定は必ず全ランクで実行すること。ランク0だけが exit すると
  !       他ランクが回り続け、par_finalize で整合しなくなる。
  !       ierror は swflow_calc 直後に、cnmax は calcstat 内で全ランク
  !       集約済みなので、以下の判定は全ランクで同一になる。
  !       (ループ継続判定そのものは m_main_finished が行う)

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

  ! サブルーチンからのエラーも含めてエラーがあれば時間ループを終了
  ! (m_main_finished が ierror > 0 を検出して止める)
  if (ierror > 0) then
    call m_state_printstate(p, s)
  end if

end subroutine


!----------------------------------------------------------------------
! 時間ループ後の最終出力(従来 run_main の末尾)
!----------------------------------------------------------------------
subroutine run_close(p, g, s, r)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_record), intent(inout) :: r

  ! 最終状態を出力
  call output_state(p, g, s, 9998)

  ! 統計量を出力
  call output_summary(p, g, s, 9999)

  ! 最大流量の一覧を出力
  call m_record_summary(r, p)

  ! エラー処理は m_main_all 側で行う(dispose と par_finalize を通すため
  ! ここでは error stop しない)

end subroutine


!----------------------------------------------------------------------
! 計算結果保存ディレクトリを作成してパラメータファイルを保存する
!----------------------------------------------------------------------
subroutine init_resultdir(p)
  type(t_sysparam), intent(in) :: p
  ! 設定ファイル一式を結果ディレクトリへ保存する(計算の再現記録)。
  ! t_sysparam に設定ファイルを追加したらここにも追加すること。
  ! "-"(fn_sysparam と同一)は読込前に正規化済みのため全て実在ファイル。
  call sysdep_mkdir(p%dir_result)                       ! 結果を保存するディレクトリを作成
  call sysdep_copy_to_dir(p%fn_sysparam, p%dir_result)  ! パラメータファイルを保存
  call sysdep_copy_to_dir(p%fn_geoinfo, p%dir_result)
  call sysdep_copy_to_dir(p%fn_initial, p%dir_result)
  call sysdep_copy_to_dir(p%fn_precip, p%dir_result)
  call sysdep_copy_to_dir(p%fn_reservoir, p%dir_result)
  call sysdep_copy_to_dir(p%fn_tide, p%dir_result)
  call sysdep_copy_to_dir(p%fn_boundary, p%dir_result)
  call sysdep_copy_to_dir(p%fn_structure, p%dir_result)
  call sysdep_copy_to_dir(p%fn_record, p%dir_result)
  call sysdep_copy_to_dir(p%fn_geomorph, p%dir_result)
  call sysdep_copy_to_dir(p%fn_gwflow, p%dir_result)
  call sysdep_copy_to_dir(p%fn_intercept, p%dir_result)
  call sysdep_copy_to_dir(p%fn_evap, p%dir_result)
  call sysdep_copy_to_dir(p%fn_meteo, p%dir_result)
  call sysdep_copy_to_dir(p%fn_wq, p%dir_result)
  call sysdep_copy_to_dir(p%fn_driftwood, p%dir_result)
  call sysdep_copy_to_dir(p%fn_snow, p%dir_result)
  call sysdep_copy_to_dir(p%fn_glacier, p%dir_result)
  call sysdep_copy_to_dir(p%fn_lavaflow, p%dir_result)
  call sysdep_copy_to_dir(p%fn_salt, p%dir_result)
  call sysdep_copy_to_dir(p%fn_channel, p%dir_result)
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
