module m_main
  use m_sysparam
  use m_geoinfo
  use m_precip
  use m_tide
  use m_boundary
  use m_state
  use m_record
  use m_swflow
  use m_fileio
  use sysdep_util

  implicit none
  private

  public :: m_main_all


  interface output_matrix
    procedure :: output_matrix_int
    procedure :: output_matrix_real
  end interface

  integer :: un_fnolist    ! 出力ファイル番号リスト用ファイルの装置番号

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! メインルーチン
!----------------------------------------------------------------------
subroutine m_main_all(fn_sysparam)
  character(len=*), intent(in) :: fn_sysparam
  type(t_sysparam) :: p
  type(t_geoinfo) :: g
  type(t_precip) :: pr
  type(t_tide) :: ti
  type(t_boundary) :: b
  type(t_state) :: s
  type(t_record) :: r
  type(t_swflow) :: sw

  ! システムを初期化
  call m_sysparam_init(p, fn_sysparam)    ! sysparam を初期化
  call sysdep_create_resultdir(p)         ! 結果を保存するディレクトリを作成
  call sysdep_save_paramfile(p)           ! パラメータファイルを保存

  ! モジュールを初期化
  call m_geoinfo_init(g, p)               ! geoinfo を初期化
  call m_boundary_init(b, p, g)           ! boundary を初期化(geoinfoより後に)
  call m_state_init(s, p, g)              ! state を初期化(geoinfo, boundaryより後に)
  call m_record_init(r, p, g)             ! record を初期化(create_resultdirより後)
  call m_precip_init(pr, p)               ! precip を初期化
  call m_tide_init(ti, p, g)              ! tide を初期化
  call m_swflow_init(sw, p, g, s)         ! swflow を初期化

  ! 計算実行
  call run_main(p, g, b, pr, s, r, sw)    ! 計算本体

  ! モジュールを破棄
  call m_swflow_dispose(sw, p)
  call m_tide_dispose(ti)
  call m_precip_dispose(pr)
  call m_record_dispose(r)
  call m_state_dispose(s, p)
  call m_boundary_dispose(b)
  call m_geoinfo_dispose(g)
  call m_sysparam_dispose(p)
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 計算本体
!----------------------------------------------------------------------
subroutine run_main(p, g, b, pr, s, r, sw)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_precip), intent(in) :: pr
  type(t_state), intent(inout) :: s
  type(t_record), intent(inout) :: r
  type(t_swflow), intent(in) :: sw
  integer :: ierror
  integer :: it            ! 時間ループのカウント
  integer :: ifn           ! 出力ファイル番号

  print *, "number of threads :", p%num_threads
  print *, "number of valid cells :", s%n_valcells


  it = 0
  ifn = 0
  call m_state_updatetime(s, p, it)       ! 時刻情報を初期化
  call m_precip_makepre(pr, p, g, s)      ! 初期降水分布を作成　
  call m_state_calcstat(s, p, g)          ! 統計情報を計算
  call m_state_printstate(p, s)           ! 途中経過を画面に出力
  call open_fnolist(p)                    ! ファイル番号リストをオープン　
  call output(p, g, s, ifn)               ! 初期状態をファイル出力
  call m_record_probe(r, p, s)            ! プローブの値を出力
  call m_record_flux(r, p, s)             ! フラックスの値を出力
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
    endif

    ! 地表水を計算
    call m_swflow_calc(sw, p, g, b, s, ierror)

    ! 統計情報を計算
    call m_state_calcstat(s, p, g)

    ! dt_disp 間隔で途中経過を画面に出力
    if (mod(it, p%idt_disp) == 0) then
      call m_state_printstate(p, s)
    endif

    ! dt_file 間隔で計算結果をファイルに出力 
    if (it >= p%ist_file .and. it <= p%iet_file .and. mod(it, p%idt_file) == 0) then
      ifn = ifn + 1
      call output(p, g, s, ifn)
    endif

    ! dt_record 間隔でプローブとフラックスの値を出力
    if (it >= p%ist_recd .and. it <= p%iet_recd .and. mod(it, p%idt_recd) == 0) then
     call m_record_probe(r, p, s)
     call m_record_flux(r, p, s)
    endif

    ! CFL条件のチェック
    if (p%f_check_cfl > 0 .and. s%cnmax > 1.) then
      print *, "********************************************"
      print *, "******** Courant number exceeds 1.0 ********"
      print *, "********************************************"
      call m_state_printstate(p, s)
      exit
    end if

    ! オーバーフローを回避するためにチェック
    if (s%cnmax > 100.) then
      print *, "**********************************************************************"
      print *, "******** Unrealistic calculation (Courant number exceeds 100) ********"
      print *, "**********************************************************************"
      call m_state_printstate(p, s)
      exit
    end if

    ! サブルーチンからのエラーをチェック
    if (ierror > 0) then
      call m_state_printstate(p, s)
      exit
    end if

  end do
  !------ 時間ステップのループここまで ------


  ! 最終状態を出力
  call output(p, g, s, 9998)

  ! 統計量を出力
  call output_summary(p, s, 9999)

  ! 最大流量の一覧を出力
  call m_record_summary(r, p)

end subroutine


!----------------------------------------------------------------------
! 計算結果ファイルの番号リスト用ファイルを開く
!----------------------------------------------------------------------
subroutine open_fnolist(p)
  type(t_sysparam), intent(in) :: p
  character(len=256) :: fname
  fname = trim(p%dir_result)//"/FILENUMBER.csv"
  open(newunit=un_fnolist, file=trim(fname), status='replace')
  write(un_fnolist, '(a)') "# No., time, t(s), it"
end subroutine


!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力
!----------------------------------------------------------------------
subroutine output(p, g, s, k)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: k
  if (p%f_out_z > 0 .or. k == 0) call output_matrix(p, "Z", g%z, k)  ! 地盤高
  if (p%f_out_h > 0) call output_matrix(p, "H", s%h, k)          ! 水深
  if (p%f_out_e > 0) call output_matrix(p, "E", s%e, k)          ! 水位
  if (p%f_out_u > 0) call output_matrix(p, "u", s%u, k)          ! x方向流速
  if (p%f_out_v > 0) call output_matrix(p, "v", s%v, k)          ! y方向流速
  if (p%f_out_m > 0) call output_matrix(p, "m", s%m, k)          ! x方向線流量
  if (p%f_out_n > 0) call output_matrix(p, "n", s%n, k)          ! y方向線流量
  if (p%f_out_vv > 0) call output_matrix(p, "V", s%vv, k)        ! 流速の絶対値
  if (p%f_out_qq > 0) call output_matrix(p, "Q", s%qq, k)        ! 線流量の絶対値
  if (p%f_out_qc > 0) call output_matrix(p, "Qc", s%qcum, k)     ! 積算線流量
  if (p%f_out_qd > 0) call output_matrix(p, "Qd", s%qdir, k)     ! 流向
  if (p%f_out_ddd > 0) call output_matrix(p, "Ddd", s%ddir1, k)  ! 卓越流下方向フラグ
  if (p%f_out_dda > 0) call output_matrix(p, "Dda", s%ddir8, k)  ! 全流下方向フラグ
  if (p%f_out_pre > 0) call output_matrix(p, "P", s%prh, k)      ! 降雨強度
  if (p%f_out_fr > 0) call output_matrix(p, "Fr", s%fr, k)       ! フルード数
  if (p%f_out_cn > 0) call output_matrix(p, "Cn", s%cn, k)       ! クーラン数
  write(un_fnolist, '(i5,a,a,a,f15.3,a,i10)') k, ",", s%ctime, ",", s%t, ",", s%it
end subroutine


!----------------------------------------------------------------------
! 統計量の配列をファイルに出力
!----------------------------------------------------------------------
subroutine output_summary(p, s, k)
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer, intent(in) :: k
  if (p%f_out_hmax > 0)  call output_matrix(p, "H", s%hmax, k)     ! 最大水深
  if (p%f_out_hmaxt > 0) call output_matrix(p, "Ht", s%hmaxt, k)   ! 最大水深の時刻
  if (p%f_out_vvmax > 0) call output_matrix(p, "V", s%vvmax, k)    ! 最大流速
  if (p%f_out_qqmax > 0) call output_matrix(p, "Q", s%qqmax, k)    ! 最大流量
  if (p%f_out_qqmaxt > 0) call output_matrix(p, "Qt", s%qqt, k)    ! 最大流量の時刻
  if (p%f_out_qqmaxd > 0) call output_matrix(p, "Qd", s%qqdir, k)  ! 最大流量の流向
  write(un_fnolist, '(i5,a,a,a,f15.3,a,i10)') k, ",", s%ctime, ",", s%t, ",", s%it
end subroutine


!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力(real)
!----------------------------------------------------------------------
subroutine output_matrix_real(p, prefix, a, k)
  type(t_sysparam), intent(in) :: p
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  real, intent(in) :: a(1:p%nx,1:p%ny)
  character(len=4) :: snum
  character(:), allocatable :: fn

  write(snum, '(i4.4)') k
  fn = trim(p%dir_result)//"/"//trim(adjustl(prefix))//snum//trim(adjustl(p%outfn_suffix))

  if (p%f_output_mode == 1 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".txt", p%nx, p%ny, a, e_fmt_txt, p%f_output_compress)
  end if
  if (p%f_output_mode == 2 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".bil", p%nx, p%ny, a, e_fmt_bil, p%f_output_compress)
  end if

end subroutine


!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力(int)
!----------------------------------------------------------------------
subroutine output_matrix_int(p, prefix, a, k)
  type(t_sysparam), intent(in) :: p
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  integer, intent(in) :: a(1:p%nx,1:p%ny)
  character(len=4) :: snum
  character(:), allocatable :: fn

  write(snum, '(i4.4)') k
  fn = trim(p%dir_result)//"/"//trim(adjustl(prefix))//snum//trim(adjustl(p%outfn_suffix))

  if (p%f_output_mode == 1 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".txt", p%nx, p%ny, a, e_fmt_txt, p%f_output_compress)
  end if
  if (p%f_output_mode == 2 .or. p%f_output_mode == 3) then
    call fileio_write_matrix(fn//".bil", p%nx, p%ny, a, e_fmt_bil, p%f_output_compress)
  end if
end subroutine


end module
