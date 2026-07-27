module m_main
  use, intrinsic :: iso_fortran_env, only: real64
  use m_sysparam
  use m_geoinfo
  use m_precip
  use m_tide
  use m_boundary
  use m_state
  use m_record
  use m_swflow
  use m_fileio
  use m_util, only : itoa
  use sysdep_util
  use m_parallel

  implicit none
  private

  public :: m_main_all


  interface output_matrix
    procedure :: output_matrix_int
    procedure :: output_matrix_real
  end interface

  integer :: un_fnolist    ! 出力ファイル番号リスト用ファイルの装置番号

  ! 出力集約用の全域バッファ(rank0 のみ実サイズ。run_main で確保)
  real, allocatable :: wk_out(:,:)
  integer, allocatable :: wk_out_i(:,:)

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
  type(t_swflow) :: sw
  character(len=256) :: fn_sysparam
  integer :: ierror

  ! MPIを初期化
  call par_init()

  ! コンパイル時にrealを倍精度として指定しているかチェック
  if (kind(1.0) /= real64) then
    call par_stop("compile with -r8 / -fdefault-real-8")
  end if

  ! システムパラメータファイル名を取得
  call get_fn_param(fn_sysparam)

  ! システムを初期化
  call m_sysparam_init(p, fn_sysparam)    ! sysparam を初期化
  call sysdep_create_resultdir(p)         ! 結果を保存するディレクトリを作成
  call sysdep_save_paramfile(p)           ! パラメータファイルを保存

  ! モジュールを初期化
  call m_geoinfo_init(g, p)               ! geoinfo を初期化
  call par_decomp_init(g%nx, g%ny, g%wy(1), g%wy(2))  ! 領域分割を決定(現段階は全域窓)
  call m_boundary_init(b, p, g)           ! boundary を初期化(geoinfoより後に)
  call m_state_init(s, p, g)              ! state を初期化(geoinfo, boundaryより後に)
  call m_record_init(r, p, g)             ! record を初期化(create_resultdirより後)
  call m_precip_init(pr, p, g)            ! precip を初期化
  call m_tide_init(ti, p, g)              ! tide を初期化
  call m_swflow_init(sw, p, g, b, s)      ! swflow を初期化

  ! 計算実行
  call run_main(p, g, b, pr, s, r, sw, ierror)  ! 計算本体

  ! モジュールを破棄
  call m_swflow_dispose(sw, p)
  call m_tide_dispose(ti)
  call m_precip_dispose(pr)
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
subroutine run_main(p, g, b, pr, s, r, sw, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  type(t_precip), intent(in) :: pr
  type(t_state), intent(inout) :: s
  type(t_record), intent(inout) :: r
  type(t_swflow), intent(in) :: sw
  integer, intent(out) :: ierror
  integer :: it            ! 時間ループのカウント
  integer :: ifn           ! 出力ファイル番号
  logical :: do_file       ! このステップでファイル出力するか
  logical :: do_recd       ! このステップでプローブ・フラックス出力するか

  call par_info("number of processes : "//itoa(nproc))
  call par_info("number of threads : "//itoa(p%num_threads))
  call par_info("number of valid cells : "//itoa(s%n_valcells))


  ! 出力集約バッファの確保(rank0 のみ全域。帯外行はゼロで不変に保たれ、
  ! 逐次出力(帯外=ゼロ)とバイト一致する)
  if (is_root) then
    allocate(wk_out(1:g%nx, 1:g%ny), source = 0.0)
    allocate(wk_out_i(1:g%nx, 1:g%ny), source = 0)
  else
    allocate(wk_out(1, 1), source = 0.0)
    allocate(wk_out_i(1, 1), source = 0)
  end if

  it = 0
  ifn = 0
  call m_state_updatetime(s, p, it)       ! 時刻情報を初期化
  call m_precip_makepre(pr, p, g, s)      ! 初期降水分布を作成　
  call m_state_calcstat(s, p, g)          ! 統計情報を計算

  ! 初期状態の出力(ファイルへの書き込みはランク0のみ)
  call m_state_printstate(p, s)         ! 途中経過を画面に出力
  call open_fnolist(p)                  ! ファイル番号リストをオープン　
  call output(p, g, s, ifn)             ! 初期状態をファイル出力(集約は output_matrix 内)
  call m_record_probe(r, p, s)          ! プローブの値を出力
  call m_record_flux(r, p, s)           ! フラックスの値を出力
  ierror = 0

  ! デバッグ用データ出力
  !call fileio_write_matrix("xxxx.txt", g%nx, g%ny, g%x(1:g%nx,1:g%ny), e_fmt_txt, e_cmp_off)
  !call fileio_write_matrix("xxxx.bil", g%nx, g%ny, g%x(1:g%nx,1:g%ny), e_fmt_bil, e_cmp_off)
  !call fileio_write_matrix("ssss.bil", g%nx, g%ny, g%sw(1:g%nx,1:g%ny), e_fmt_bil, e_cmp_off)
  !call fileio_write_matrix("rrrr.bil", g%nx, g%ny, g%rw(1:g%nx,1:g%ny), e_fmt_bil, e_cmp_off)
  !call fileio_write_matrix("ssss.txt", g%nx, g%ny, g%sw(1:g%nx,1:g%ny), e_fmt_txt, e_cmp_off)
  !call fileio_write_matrix("zzzz.bil", g%nx, g%ny, g%z(1:g%nx,1:g%ny), e_fmt_bil, e_cmp_off)


  !------ 時間ステップのループここから ------
  do it = 1, p%nt

    ! 時刻情報を更新
    call m_state_updatetime(s, p, it)

    ! dt_prupdate 間隔で降水分布を更新
    if (mod(it, pr%idt_prupdate) == 0) then
      call m_precip_makepre(pr, p, g, s)
    end if

    ! 境界条件を準備
    call m_boundary_makebdc(b, p, g, s)

    ! 地表水を計算
    call m_swflow_calc(sw, p, g, b, s, ierror)

    ! 発散検出はランク局所のため、判定に先立ち全ランク最大へ集約する
    call par_allreduce_maxi(ierror)

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

    ! dt_file 間隔で計算結果をファイルに出力
    if (do_file) then
      ifn = ifn + 1
      call output(p, g, s, ifn)
    end if

    ! dt_record 間隔でプローブとフラックスの値を出力
    if (do_recd) then
     call m_record_probe(r, p, s)
     call m_record_flux(r, p, s)
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
  call output(p, g, s, 9998)

  ! 統計量を出力
  call output_summary(p, g, s, 9999)

  ! 最大流量の一覧を出力
  call m_record_summary(r, p)

  ! エラー処理は m_main_all 側で行う(dispose と par_finalize を通すため
  ! ここでは error stop しない。ierror を返すのみ)

end subroutine


!----------------------------------------------------------------------
! 計算結果ファイルの番号リスト用ファイルを開く
!----------------------------------------------------------------------
subroutine open_fnolist(p)
  type(t_sysparam), intent(in) :: p
  character(len=256) :: fname
  if (.not. is_root) return
  fname = trim(p%dir_result)//"/FILENUMBER.csv"
  open(newunit=un_fnolist, file=trim(fname), status='replace')
  write(un_fnolist, '(a)') "# No., time, t(s), it"
end subroutine


!----------------------------------------------------------------------
! 出力・計測対象の場を rank0 に集約する(dt_file / dt_recrd 間隔のみ。
! collective なので全ランクが揃って呼ぶこと)
!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力
!----------------------------------------------------------------------
subroutine output(p, g, s, k)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: k
  ! output_matrix は collective(内部で gather)。ガードしないこと
  if (p%f_out_z > 0 .or. k == 0) call output_matrix_full(p, g, "Z", g%z, k)  ! 地盤高(静的・全域保持)
  if (p%f_out_h > 0) call output_matrix(p, g, "H", s%h, k)          ! 水深
  if (p%f_out_e > 0) call output_matrix(p, g, "E", s%e, k)          ! 水位
  if (p%f_out_u > 0) call output_matrix(p, g, "u", s%u, k)          ! x方向流速
  if (p%f_out_v > 0) call output_matrix(p, g, "v", s%v, k)          ! y方向流速
  if (p%f_out_m > 0) call output_matrix(p, g, "m", s%m, k)          ! x方向線流量
  if (p%f_out_n > 0) call output_matrix(p, g, "n", s%n, k)          ! y方向線流量
  if (p%f_out_vv > 0) call output_matrix(p, g, "V", s%vv, k)        ! 流速の絶対値
  if (p%f_out_qq > 0) call output_matrix(p, g, "Q", s%qq, k)        ! 線流量の絶対値
  if (p%f_out_qc > 0) call output_matrix(p, g, "Qc", s%qcum, k)     ! 積算線流量
  if (p%f_out_qd > 0) call output_matrix(p, g, "Qd", s%qdir, k)     ! 流向
  if (p%f_out_ddd > 0) call output_matrix(p, g, "Ddd", s%ddir1, k)  ! 卓越流下方向フラグ
  if (p%f_out_dda > 0) call output_matrix(p, g, "Dda", s%ddir8, k)  ! 全流下方向フラグ
  if (p%f_out_pre > 0) call output_matrix(p, g, "Pr", s%prh, k)     ! 降雨強度
  if (p%f_out_rsh > 0) call output_matrix(p, g, "Rsh", s%rsh, k)    ! ため池水深
  if (p%f_out_fr > 0) call output_matrix(p, g, "Fr", s%fr, k)       ! フルード数
  if (p%f_out_cn > 0) call output_matrix(p, g, "Cn", s%cn, k)       ! クーラン数
  if (is_root) write(un_fnolist, '(i5,a,a,a,f15.3,a,i10)') k, ",", s%ctime, ",", s%t, ",", s%it
end subroutine


!----------------------------------------------------------------------
! 統計量の配列をファイルに出力
!----------------------------------------------------------------------
subroutine output_summary(p, g, s, k)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: k
  ! output_matrix は collective(内部で gather)。ガードしないこと
  if (p%f_out_hmax > 0)  call output_matrix(p, g, "H", s%hmax, k)     ! 最大水深
  if (p%f_out_hmaxt > 0) call output_matrix(p, g, "Ht", s%hmaxt, k)   ! 最大水深の時刻
  if (p%f_out_vvmax > 0) call output_matrix(p, g, "V", s%vvmax, k)    ! 最大流速
  if (p%f_out_qqmax > 0) call output_matrix(p, g, "Q", s%qqmax, k)    ! 最大流量
  if (p%f_out_qqmaxt > 0) call output_matrix(p, g, "Qt", s%qqt, k)    ! 最大流量の時刻
  if (p%f_out_qqmaxd > 0) call output_matrix(p, g, "Qd", s%qqdir, k)  ! 最大流量の流向
  if (is_root) write(un_fnolist, '(i5,a,a,a,f15.3,a,i10)') k, ",", s%ctime, ",", s%t, ",", s%it
end subroutine


!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力(real)
!----------------------------------------------------------------------
subroutine output_matrix_real(p, g, prefix, a, k)
  ! 帯確保の配列を全域バッファへ集約して rank0 が書く(collective)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  real, intent(in) :: a(1:, dcp%jsh:)
  character(len=4) :: snum
  character(:), allocatable :: fn

  call par_gather_to(wk_out, a)
  if (.not. is_root) return

  write(snum, '(i4.4)') k
  fn = trim(p%dir_result)//"/"//trim(adjustl(prefix))//snum//trim(adjustl(p%outfn_suffix))

  if (p%f_output_mode == 1 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".txt", g%nx, g%ny, wk_out, e_fmt_txt, p%f_output_compress)
  end if
  if (p%f_output_mode == 2 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".bil", g%nx, g%ny, wk_out, e_fmt_bil, p%f_output_compress)
  end if

end subroutine


!----------------------------------------------------------------------
! 全域保持の静的配列をファイルに出力(g%z 等。rank0 が直接書く)
!----------------------------------------------------------------------
subroutine output_matrix_full(p, g, prefix, a, k)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  real, intent(in) :: a(1:g%nx,1:g%ny)
  character(len=4) :: snum
  character(:), allocatable :: fn

  if (.not. is_root) return
  write(snum, '(i4.4)') k
  fn = trim(p%dir_result)//"/"//trim(adjustl(prefix))//snum//trim(adjustl(p%outfn_suffix))

  if (p%f_output_mode == 1 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".txt", g%nx, g%ny, a, e_fmt_txt, p%f_output_compress)
  end if
  if (p%f_output_mode == 2 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".bil", g%nx, g%ny, a, e_fmt_bil, p%f_output_compress)
  end if

end subroutine


!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力(int)
!----------------------------------------------------------------------
subroutine output_matrix_int(p, g, prefix, a, k)
  ! 帯確保の整数配列を全域バッファへ集約して rank0 が書く(collective)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  integer, intent(in) :: a(1:, dcp%jsh:)
  character(len=4) :: snum
  character(:), allocatable :: fn

  call par_gather_to_i(wk_out_i, a)
  if (.not. is_root) return

  write(snum, '(i4.4)') k
  fn = trim(p%dir_result)//"/"//trim(adjustl(prefix))//snum//trim(adjustl(p%outfn_suffix))

  if (p%f_output_mode == 1 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".txt", g%nx, g%ny, wk_out_i, e_fmt_txt, p%f_output_compress)
  end if
  if (p%f_output_mode == 2 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".bil", g%nx, g%ny, wk_out_i, e_fmt_bil, p%f_output_compress)
  end if
end subroutine


!----------------------------------------------------------------------
! コマンドライン引数から設定ファイル名を取得する
!----------------------------------------------------------------------
subroutine get_fn_param(fn_param)
  character(len=*) :: fn_param

  ! コマンドライン引数の文字列を保存する構造体の宣言
  !  可変長文字列の配列が直接作れないため構造体の配列を利用
  type :: arguments
    character(:), allocatable :: v           ! 無指定文字長（可変長）文字列変数vを要素に持つ
  end type

  ! コマンドライン引数の数と文字列
  integer :: argc
  type(arguments), allocatable :: arg(:)

  
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
