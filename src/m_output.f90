module m_output
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_fileio, only : fileio_write_matrix, e_fmt_txt, e_fmt_bil, e_fmt_gtif
  use m_georef, only : georef_write_hdr, e_pix_float, e_pix_int
  use m_parallel

  implicit none
  private

  public :: output_init
  public :: output_dispose
  public :: output_chk_geoinfo
  public :: output_state
  public :: output_summary


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
! 
!----------------------------------------------------------------------
subroutine output_init(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=256) :: fname

  ! 出力集約バッファの確保(rank0 のみ全域。帯外行はゼロで不変に保たれ、
  ! 逐次出力(帯外=ゼロ)とバイト一致する)
  if (is_root) then
    allocate(wk_out(1:g%nx, 1:g%ny), source = 0.0)
    allocate(wk_out_i(1:g%nx, 1:g%ny), source = 0)
  else
    allocate(wk_out(1, 1), source = 0.0)
    allocate(wk_out_i(1, 1), source = 0)
  end if

  ! 計算結果ファイルの番号リスト用ファイルを開く
  if (is_root) then
    fname = trim(p%dir_result)//"/FILENUMBER.csv"
    open(newunit=un_fnolist, file=trim(fname), status='replace')
    write(un_fnolist, '(a)') "# No., time, t(s), it"
  end if
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine output_dispose()
  if (allocated(wk_out)) deallocate(wk_out)
  if (allocated(wk_out_i)) deallocate(wk_out_i)
  if (is_root) close(un_fnolist)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine output_chk_geoinfo(g)
  type(t_geoinfo), intent(in) :: g
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. is_root) return
  ! デバッグ用データ出力
  !call fileio_write_matrix("xxxx.txt", g%nx, g%ny, g%x(1:g%nx,1:g%ny), e_fmt_txt)
  !call fileio_write_matrix("xxxx.bil", g%nx, g%ny, g%x(1:g%nx,1:g%ny), e_fmt_bil)
  !call fileio_write_matrix("ssss.bil", g%nx, g%ny, g%sw(1:g%nx,1:g%ny), e_fmt_bil)
  !call fileio_write_matrix("rrrr.bil", g%nx, g%ny, g%rw(1:g%nx,1:g%ny), e_fmt_bil)
  !call fileio_write_matrix("ssss.txt", g%nx, g%ny, g%sw(1:g%nx,1:g%ny), e_fmt_txt)
  !call fileio_write_matrix("zzzz.bil", g%nx, g%ny, g%z(1:g%nx,1:g%ny), e_fmt_bil)
end subroutine


!----------------------------------------------------------------------
! 出力・計測対象の場を rank0 に集約する(dt_file / dt_recrd 間隔のみ。
! collective なので全ランクが揃って呼ぶこと)
!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力
!----------------------------------------------------------------------
subroutine output_state(p, g, s, k)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: k
  ! output_matrix は collective(内部で gather)。ガードしないこと
  if (p%f_out_z > 0 .or. k == 0) call output_matrix(p, g, "Z", s%z, k)  ! 地盤高
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
  if (p%f_out_hrs > 0) call output_matrix(p, g, "Hrs", s%hrs, k)    ! ため池水深
  if (p%f_out_fr > 0) call output_matrix(p, g, "Fr", s%fr, k)       ! フルード数
  if (p%f_out_cn > 0) call output_matrix(p, g, "Cn", s%cn, k)       ! クーラン数
  if (p%f_out_hg > 0) call output_matrix(p, g, "Hg", s%hg, k)       ! 地下貯留水深
  ! 風化基岩層の貯留水深(f_gwlayer2=1 のときのみ。フラグは Hg と共用)
  if (p%f_out_hg > 0 .and. allocated(s%hg2)) call output_matrix(p, g, "Hg2", s%hg2, k)
  if (s%wq_active) call output_matrix(p, g, "C", s%cqc, k)          ! 輸送物質濃度 (mg/L。§30)
  ! 積雪水量 SWE (mm。fn_snow 有効時のみ。§31)
  if (allocated(s%swe)) call output_matrix(p, g, "Sw", 1000.0*s%swe, k)
  ! 土層厚 (m。sd を実際に使うモデルの有効時のみ = require_sd 済み。§32)
  if (allocated(g%sd) .and. allocated(s%sd)) call output_matrix(p, g, "Sd", s%sd, k)
  ! 表面蓄積プール (kg/ha = g/m2 × 10。プール有効時のみ。§30)
  if (s%wq_active .and. allocated(s%bp)) call output_matrix(p, g, "B", 10.0*s%bp, k)
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


!======================================================================
!========================= PRIVATE ROUTINES ===========================
!======================================================================

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

  ! f_output_mode はビット和(1:txt, 2:bil, 4:geotiff)。組合せ出力可
  if (iand(p%f_output_mode, e_fmt_txt) /= 0) then
    call fileio_write_matrix(fn//".txt", g%nx, g%ny, wk_out, e_fmt_txt)
  end if
  if (iand(p%f_output_mode, e_fmt_bil) /= 0) then
    call fileio_write_matrix(fn//".bil", g%nx, g%ny, wk_out, e_fmt_bil)
    ! 地理座標を管理している場合のみ hdr を併記
    if (g%gr%active) call georef_write_hdr(fn//".hdr", g%gr, g%nx, g%ny, e_pix_float)
  end if
  if (iand(p%f_output_mode, e_fmt_gtif) /= 0) then
    call fileio_write_matrix(fn//".tif", g%nx, g%ny, wk_out, e_fmt_gtif, g%gr)
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

  if (iand(p%f_output_mode, e_fmt_txt) /= 0) then
    call fileio_write_matrix(fn//".txt", g%nx, g%ny, wk_out_i, e_fmt_txt)
  end if
  if (iand(p%f_output_mode, e_fmt_bil) /= 0) then
    call fileio_write_matrix(fn//".bil", g%nx, g%ny, wk_out_i, e_fmt_bil)
    if (g%gr%active) call georef_write_hdr(fn//".hdr", g%gr, g%nx, g%ny, e_pix_int)
  end if
  if (iand(p%f_output_mode, e_fmt_gtif) /= 0) then
    call fileio_write_matrix(fn//".tif", g%nx, g%ny, wk_out_i, e_fmt_gtif, g%gr)
  end if
end subroutine


end module
