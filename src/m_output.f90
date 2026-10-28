module m_output
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_swflow_enc, only : chn       ! 河道平面積率 wfrac(読み取り専用。実効面積率 A0000)
  use m_fileio, only : fileio_write_matrix, fileio_write_window, e_fmt_txt, e_fmt_bil, e_fmt_gtif
  use m_georef, only : georef_write_hdr, e_pix_float, e_pix_int
  use m_parallel

  implicit none
  private

  public :: t_output
  public :: output_init
  public :: output_dispose
  public :: output_chk_geoinfo
  public :: output_state
  public :: output_summary


  interface output_matrix
    procedure :: output_matrix_int
    procedure :: output_matrix_real
  end interface

  ! 分布出力の状態(1 ランあたり 1 個。m_main の t_encflow が所有し、
  ! 公開手続きの第 1 引数で受ける。モジュール変数を持たない = 複数
  ! インスタンスに開いた形。nesting_plan.md §3.2 の A 群)
  type t_output
    integer :: un_fnolist = 0           ! 出力ファイル番号リスト用ファイルの装置番号(rank0)
    ! 出力集約用の全域バッファ(rank0 のみ実サイズ。output_init で確保)
    real, allocatable :: wk_out(:,:)
    integer, allocatable :: wk_out_i(:,:)
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine output_init(o, p, g)
  ! 契約: m_geoinfo_band_shrink より前に呼ぶこと(領域マスク X0000 の
  ! 出力が g%x, g%sw の全域確保を前提とするため。m_main の呼び出し順)
  type(t_output), intent(inout) :: o
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=256) :: fname

  ! 出力集約バッファの確保(rank0 のみ。窓形 (ish:ieh, jw1:jw2)。全ランクの帯が
  ! 窓を覆うので全要素が gather で埋まる。窓外は書き出し時に p%out_fill で
  ! 充填する(§81)。gather の集約先そのものなので全域の一時は持たない)
  if (is_root) then
    allocate(o%wk_out(dcp%ish:dcp%ieh, dcp%jw1:dcp%jw2), source = 0.0)
    allocate(o%wk_out_i(dcp%ish:dcp%ieh, dcp%jw1:dcp%jw2), source = 0)
  else
    allocate(o%wk_out(1, 1), source = 0.0)
    allocate(o%wk_out_i(1, 1), source = 0)
  end if

  ! 計算結果ファイルの番号リスト用ファイルを開く
  if (is_root) then
    fname = trim(p%dir_result)//"/FILENUMBER.csv"
    open(newunit=o%un_fnolist, file=trim(fname), status='replace')
    write(o%un_fnolist, '(a)') "# No., time, t(s), it"
  end if

  ! 領域マスク X0000 を常時出力(Z0000 と同じ扱い。時系列ではないので
  ! FILENUMBER.csv には載せない。可視化(utils/out2vtk)・GIS での
  ! 使用領域確認用。§44)
  call output_maskfile(p, g)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine output_dispose(o)
  type(t_output), intent(inout) :: o
  if (allocated(o%wk_out)) deallocate(o%wk_out)
  if (allocated(o%wk_out_i)) deallocate(o%wk_out_i)
  if (is_root) close(o%un_fnolist)
  o%un_fnolist = 0
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
subroutine output_state(o, p, g, s, k)
  type(t_output), intent(inout) :: o
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: k
  ! output_matrix は collective(内部で gather)。ガードしないこと
  if (p%f_out_z > 0 .or. k == 0) call output_matrix(o, p, g, "Z", s%z, k)  ! 地盤高
  ! 実効面積率 A0000(= 家屋空隙率 gv × 河道平面積率 wfrac。開始時のみ。
  ! 分布出力の柱状量(H・Hs・cq 等)をセル平均・体積・濡れ面積に換算する
  ! 係数。どちらかが有効なときだけ出す = それ以外は全セル 1 で情報がない。
  ! 断面形 σ の体積比は水深依存なので含めない。users_guide/io.md)
  if (k == 0 .and. (g%gv_active .or. chn%have_width)) call output_areafactor(o, p, g, s)
  if (p%f_out_h > 0) call output_matrix(o, p, g, "H", s%h, k)          ! 水深
  if (p%f_out_e > 0) call output_matrix(o, p, g, "E", s%e, k)          ! 水位
  if (p%f_out_u > 0) call output_matrix(o, p, g, "u", s%u, k)          ! x方向流速
  if (p%f_out_v > 0) call output_matrix(o, p, g, "v", s%v, k)          ! y方向流速
  if (p%f_out_m > 0) call output_matrix(o, p, g, "m", s%m, k)          ! x方向線流量
  if (p%f_out_n > 0) call output_matrix(o, p, g, "n", s%n, k)          ! y方向線流量
  if (p%f_out_vv > 0) call output_matrix(o, p, g, "V", s%vv, k)        ! 流速の絶対値
  if (p%f_out_qq > 0) call output_matrix(o, p, g, "Q", s%qq, k)        ! 線流量の絶対値
  if (p%f_out_qc > 0) call output_matrix(o, p, g, "Qc", s%qcum, k)     ! 積算線流量
  if (p%f_out_qd > 0) call output_matrix(o, p, g, "Qd", s%qdir, k)     ! 流向
  if (p%f_out_ddd > 0) call output_matrix(o, p, g, "Ddd", s%ddir1, k)  ! 卓越流下方向フラグ
  if (p%f_out_dda > 0) call output_matrix(o, p, g, "Dda", s%ddir8, k)  ! 全流下方向フラグ
  if (p%f_out_pre > 0) call output_matrix(o, p, g, "Pr", s%prh, k)     ! 降雨強度
  if (p%f_out_hrs > 0) call output_matrix(o, p, g, "Hrs", s%hrs, k)    ! ため池水深
  if (p%f_out_fr > 0) call output_matrix(o, p, g, "Fr", s%fr, k)       ! フルード数
  if (p%f_out_cn > 0) call output_matrix(o, p, g, "Cn", s%cn, k)       ! クーラン数
  if (p%f_out_hg > 0) call output_matrix(o, p, g, "Hg", s%hg, k)       ! 地下貯留水深
  ! 風化基岩層の貯留水深(f_gwlayer2=1 のときのみ。フラグは Hg と共用)
  if (p%f_out_hg > 0 .and. allocated(s%hg2)) call output_matrix(o, p, g, "Hg2", s%hg2, k)
  ! 管路連続体層の貯留水量(f_gwconduit=1 のときのみ。フラグは Hg と共用)
  if (p%f_out_hg > 0 .and. allocated(s%hgc)) call output_matrix(o, p, g, "Hgc", s%hgc, k)
  ! 地表塩水層厚(fn_salt 有効時のみ。フラグは H と共用。§47)
  if (p%f_out_h > 0 .and. allocated(s%hss)) call output_matrix(o, p, g, "Hss", s%hss, k)
  ! 地下塩水貯留(fn_salt 有効時のみ。フラグは Hg と共用。§47)
  if (p%f_out_hg > 0 .and. allocated(s%hgs)) call output_matrix(o, p, g, "Hgs", s%hgs, k)
  if (s%wq_active) call output_matrix(o, p, g, "C", s%cqc, k)          ! 輸送物質濃度 (mg/L。§30)
  ! 地下質量プール (g/m2。幾何面積基底 = セル内質量 cg×A。f_wq_infil=1 の
  ! ときのみ確保。フラグは Hg と共用 = 地下水の状態量の一員。§30 W3)
  if (p%f_out_hg > 0 .and. allocated(s%cg)) call output_matrix(o, p, g, "Cg", s%cg, k)
  if (p%f_out_hs > 0) call output_matrix(o, p, g, "Hs", s%hs, k)       ! 土砂柱状量 (m。§28.9)
  ! 流動流木・堆積流木 (m3/m2。fn_driftwood 有効時のみ = 前提検証は
  ! m_driftwood_init。§50)
  if (p%f_out_hd > 0 .and. allocated(s%hd)) call output_matrix(o, p, g, "Hd", s%hd, k)
  if (p%f_out_wd > 0 .and. allocated(s%wd)) call output_matrix(o, p, g, "Wd", s%wd, k)
  ! 流動瓦礫・堆積瓦礫・家屋の破壊率(fn_bldgdebris 有効時のみ = 前提検証は
  ! m_bldgdebris_init。§63)
  if (p%f_out_hbd > 0 .and. allocated(s%hbd)) call output_matrix(o, p, g, "Bf", s%hbd, k)
  if (p%f_out_wbd > 0 .and. allocated(s%wbd)) call output_matrix(o, p, g, "Bd", s%wbd, k)
  if (p%f_out_bds > 0 .and. allocated(s%bds)) call output_matrix(o, p, g, "Bs", s%bds, k)
  ! 斜面安全率 Fs(-1 = 評価対象外。slide_pass1 が dt_geomorph 周期で
  ! 更新するため t=0 フレームは全域 -1。§28.9)
  if (p%f_out_fs > 0 .and. allocated(s%fs)) call output_matrix(o, p, g, "Fs", s%fs, k)
  ! 積雪水量 SWE (mm。fn_snow 有効時のみ。§31)
  if (allocated(s%swe)) call output_matrix(o, p, g, "Sw", 1000.0*s%swe, k)
  ! 土壌雨量指数 SWI (mm。fn_swi 有効時のみ。§49)
  if (allocated(s%swi)) call output_matrix(o, p, g, "Swi", s%swi, k)
  if (allocated(s%frofac)) call output_matrix(o, p, g, "Ff", s%frofac, k)
  ! 氷河の氷厚 (m 氷柱。fn_glacier 有効時のみ。§45)
  if (allocated(s%hi)) call output_matrix(o, p, g, "Hi", s%hi, k)
  ! 溶岩厚 (m 溶岩柱。fn_lavaflow 有効時のみ。lava_plan.md)
  if (allocated(s%hl)) call output_matrix(o, p, g, "Hl", s%hl, k)
  ! 動く底層の厚さ (m。f_bedslide 有効時のみ。landslide_tsunami_plan.md)
  if (allocated(s%hb)) call output_matrix(o, p, g, "Hb", s%hb, k)
  ! 動く底層の速度 (m/s。診断。同上)
  if (allocated(s%vb)) call output_matrix(o, p, g, "Vb", s%vb, k)
  ! 定着度 a(0〜1。f_fixation 有効時のみ。§84.6)
  if (allocated(s%fx)) call output_matrix(o, p, g, "Fx", s%fx, k)
  ! 崖錐の厚さ (m。f_rockfall 有効時のみ。§48.7)
  if (allocated(s%ht)) call output_matrix(o, p, g, "Ht", s%ht, k)
  ! 河床の細粒分の厚さ (m。f_bedfines 有効時のみ。§84.10)
  if (allocated(s%sf)) call output_matrix(o, p, g, "Sf", s%sf, k)
  ! 土層厚 (m。sd を実際に使うモデルの有効時のみ = require_sd 済み。§32)
  if (allocated(g%sd) .and. allocated(s%sd)) call output_matrix(o, p, g, "Sd", s%sd, k)
  ! 表面蓄積プール (kg/ha = g/m2 × 10。プール有効時のみ。§30)
  if (s%wq_active .and. allocated(s%bp)) call output_matrix(o, p, g, "B", 10.0*s%bp, k)
  ! 沿岸の波浪場(fn_wavefield 有効時のみ。§88): 波高 Wh(不規則波は H_m0、規則波は H)・
  ! 平均波向 Wa(deg。進む向き、x 軸から反時計回り。無波セルは −9999)。f_wf_outdiag = 1
  ! のとき底面軌道流速 Wu(u_rms。m/s)・砕波散逸 Wb(W/m2)も。段 W2(wf_flow >= 1)は
  ! 外力 Wfx・Wfy(N/m2)、GLM(wf_flow = 2)は Stokes 輸送 Wsx・Wsy(m/s)、ローラーは
  ! そのエネルギー Wr(J/m2)も(向きは流速 u・v と同じ)。fn_geomorph の f_wfsed = 1 なら
  ! 漂砂 Qbx・Qby・Qsx・Qsy と岸向きの輸送速度 Wua も
  if (s%wv_active) then
    call output_matrix(o, p, g, "Wh", s%wvh, k)
    call output_matrix(o, p, g, "Wa", s%wvdir, k)
    if (s%wv_outdiag) then
      ! 砕波の乱れによる攪拌(f_wfsed_turb)では wvub が攪拌の速さなので、純粋な u_rms(wvub0)を出す
      if (allocated(s%wvub0)) then
        call output_matrix(o, p, g, "Wu", s%wvub0, k)
      else
        call output_matrix(o, p, g, "Wu", s%wvub, k)
      end if
      call output_matrix(o, p, g, "Wb", s%wvdw, k)
      if (allocated(s%wvfx)) call output_matrix(o, p, g, "Wfx", s%wvfx, k)
      if (allocated(s%wvfy)) call output_matrix(o, p, g, "Wfy", s%wvfy, k)
      if (allocated(s%wvus)) call output_matrix(o, p, g, "Wsx", s%wvus, k)
      if (allocated(s%wvvs)) call output_matrix(o, p, g, "Wsy", s%wvvs, k)
      if (allocated(s%wver)) call output_matrix(o, p, g, "Wr", s%wver, k)
      ! 波浪場が駆動する漂砂(fn_geomorph の f_wfsed = 1。段 W4): 掃流砂の推定 Qbx・Qby と
      ! 浮遊砂の輸送量 Qsx・Qsy(m2/s。固体体積。向きは流速 u・v と同じ)
      if (allocated(s%sqbx)) call output_matrix(o, p, g, "Qbx", s%sqbx, k)
      if (allocated(s%sqby)) call output_matrix(o, p, g, "Qby", s%sqby, k)
      if (allocated(s%sqsx)) call output_matrix(o, p, g, "Qsx", s%sqsx, k)
      if (allocated(s%sqsy)) call output_matrix(o, p, g, "Qsy", s%sqsy, k)
      ! 波の歪度・非対称による岸向きの輸送速度 u_a(m/s。平均波向の向きが正。段 W5)
      if (allocated(s%wvua)) call output_matrix(o, p, g, "Wua", s%wvua, k)
      ! 砕波による水平混合の渦動粘性 ν_w(m2/s。list_enc の wf_break_visc > 0。§88)
      if (allocated(s%wvnub)) call output_matrix(o, p, g, "Wnu", s%wvnub, k)
      ! 底面の乱れのエネルギー k_b(m2/s2。geomorph の f_wfsed_turb = 1。§88)
      if (allocated(s%wvkb)) call output_matrix(o, p, g, "Wkb", s%wvkb, k)
    end if
  end if
  if (is_root) write(o%un_fnolist, '(i5,a,a,a,f15.3,a,i10)') k, ",", s%ctime, ",", s%t, ",", s%it
end subroutine


!----------------------------------------------------------------------
! 実効面積率 A0000 = gv × wfrac を帯で組み立てて書く(collective。
! 計算対象外のセルは 0)
!----------------------------------------------------------------------
subroutine output_areafactor(o, p, g, s)
  type(t_output), intent(inout) :: o
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  integer :: i, j
  allocate(wk(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      wk(i,j) = s%gv(i,j)
      if (chn%have_width) wk(i,j) = wk(i,j) * chn%wfrac(i,j)
    end do
  end do
  call output_matrix(o, p, g, "A", wk, 0)
  deallocate(wk)
end subroutine


!----------------------------------------------------------------------
! 統計量の配列をファイルに出力
!----------------------------------------------------------------------
subroutine output_summary(o, p, g, s, k)
  type(t_output), intent(inout) :: o
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: k
  ! output_matrix は collective(内部で gather)。ガードしないこと
  if (p%f_out_hmax > 0)  call output_matrix(o, p, g, "H", s%hmax, k)     ! 最大水深
  if (p%f_out_hmaxt > 0) call output_matrix(o, p, g, "Ht", s%hmaxt, k)   ! 最大水深の時刻
  if (p%f_out_vvmax > 0) call output_matrix(o, p, g, "V", s%vvmax, k)    ! 最大流速
  if (p%f_out_qqmax > 0) call output_matrix(o, p, g, "Q", s%qqmax, k)    ! 最大流量
  if (p%f_out_qqmaxt > 0) call output_matrix(o, p, g, "Qt", s%qqt, k)    ! 最大流量の時刻
  if (p%f_out_qqmaxd > 0) call output_matrix(o, p, g, "Qd", s%qqdir, k)  ! 最大流量の流向
  ! 土砂災害の危険度統計(§28.9)
  if (p%f_out_dmax > 0)  call output_matrix(o, p, g, "D", s%dmax, k)     ! 最大流動深 h+hs
  if (p%f_out_dmaxt > 0) call output_matrix(o, p, g, "Dt", s%dmaxt, k)   ! 最大流動深の時刻
  if (p%f_out_fmax > 0)  call output_matrix(o, p, g, "F", s%fmax, k)     ! 最大流体力 (h+hs)V²
  if (p%f_out_fs > 0 .and. allocated(s%fsmin)) &
    call output_matrix(o, p, g, "Fs", s%fsmin, k)                        ! 期間最小の安全率
  ! 流木の期間最大到達量 max(hd+wd)(f_out_wd。§50)
  if (p%f_out_wd > 0 .and. allocated(s%wdmax)) &
    call output_matrix(o, p, g, "Wd", s%wdmax, k)
  ! 瓦礫の期間最大到達量 max(hbd+wbd)と流木・瓦礫込み最大流体力(§63)
  if (p%f_out_wbd > 0 .and. allocated(s%wbdmax)) &
    call output_matrix(o, p, g, "Bd", s%wbdmax, k)
  if (p%f_out_fdmax > 0 .and. allocated(s%fdmax)) &
    call output_matrix(o, p, g, "Fd", s%fdmax, k)
  ! 土壌雨量指数の期間最大と発生時刻(fn_swi 有効時のみ。§49)
  if (allocated(s%swimax)) call output_matrix(o, p, g, "Swi", s%swimax, k)
  if (allocated(s%swimaxt)) call output_matrix(o, p, g, "Swit", s%swimaxt, k)
  if (is_root) write(o%un_fnolist, '(i5,a,a,a,f15.3,a,i10)') k, ",", s%ctime, ",", s%t, ",", s%it
end subroutine


!======================================================================
!========================= PRIVATE ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 領域マスクファイル X0000 を出力(rank0 のみ。output_init から)
!   値: 0 = 領域外、1 = 陸域(x=1 かつ sw=0)、2 = 海域(x=1 かつ sw=1)。
!   有効マスク(f_masktype=2 の自動生成・海接続の1セル拡張を含む)の
!   記録であり、入力の fn_mask とは一般に一致しない。
!   全ランクが全域の g%x, g%sw を保持している段階(band_shrink 前)で
!   呼ぶこと。collective なし(is_root ガード内は書き込みのみ。§5)
!----------------------------------------------------------------------
subroutine output_maskfile(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  ! 全域スケールの作業配列はヒープに置く(§42)
  integer, allocatable :: wk(:,:)
  character(:), allocatable :: fn
  integer :: i, j

  if (.not. is_root) return

  allocate(wk(1:g%nx, 1:g%ny))
  do j = 1, g%ny
    do i = 1, g%nx
      if (g%x(i,j) <= 0) then
        wk(i,j) = 0
      else if (g%sw(i,j) == 1) then
        wk(i,j) = 2
      else
        wk(i,j) = 1
      end if
    end do
  end do

  fn = trim(p%dir_result)//"/X0000"//trim(adjustl(p%outfn_suffix))
  if (iand(p%f_output_mode, e_fmt_txt) /= 0) then
    call fileio_write_matrix(fn//".txt", g%nx, g%ny, wk, e_fmt_txt)
  end if
  if (iand(p%f_output_mode, e_fmt_bil) /= 0) then
    call fileio_write_matrix(fn//".bil", g%nx, g%ny, wk, e_fmt_bil)
    if (g%gr%active) call georef_write_hdr(fn//".hdr", g%gr, g%nx, g%ny, e_pix_int)
  end if
  if (iand(p%f_output_mode, e_fmt_gtif) /= 0) then
    call fileio_write_matrix(fn//".tif", g%nx, g%ny, wk, e_fmt_gtif, g%gr)
  end if
end subroutine


!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力(real)
!----------------------------------------------------------------------
subroutine output_matrix_real(o, p, g, prefix, a, k)
  ! 帯確保の配列を全域バッファへ集約して rank0 が書く(collective)
  type(t_output), intent(inout) :: o
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  real, intent(in) :: a(dcp%ish:, dcp%jsh:)
  character(len=4) :: snum
  character(:), allocatable :: fn

  call par_gather_win(o%wk_out, a)
  if (.not. is_root) return

  write(snum, '(i4.4)') k
  fn = trim(p%dir_result)//"/"//trim(adjustl(prefix))//snum//trim(adjustl(p%outfn_suffix))

  ! f_output_mode はビット和(1:txt, 2:bil, 4:geotiff)。組合せ出力可。
  ! 窓つき書き出し: 全域の形式のまま窓外は p%out_fill(既定 0)で充填(§81)
  associate (i1 => dcp%ish, i2 => dcp%ieh, j1 => dcp%jw1, j2 => dcp%jw2)
  if (iand(p%f_output_mode, e_fmt_txt) /= 0) then
    call fileio_write_window(fn//".txt", g%nx, g%ny, i1, i2, j1, j2, o%wk_out, p%out_fill, e_fmt_txt)
  end if
  if (iand(p%f_output_mode, e_fmt_bil) /= 0) then
    call fileio_write_window(fn//".bil", g%nx, g%ny, i1, i2, j1, j2, o%wk_out, p%out_fill, e_fmt_bil)
    ! 地理座標を管理している場合のみ hdr を併記
    if (g%gr%active) call georef_write_hdr(fn//".hdr", g%gr, g%nx, g%ny, e_pix_float)
  end if
  if (iand(p%f_output_mode, e_fmt_gtif) /= 0) then
    call fileio_write_window(fn//".tif", g%nx, g%ny, i1, i2, j1, j2, o%wk_out, p%out_fill, e_fmt_gtif, g%gr)
  end if
  end associate

end subroutine


!----------------------------------------------------------------------
! 計算結果の配列をファイルに出力(int)
!----------------------------------------------------------------------
subroutine output_matrix_int(o, p, g, prefix, a, k)
  ! 帯確保の整数配列を全域バッファへ集約して rank0 が書く(collective)
  type(t_output), intent(inout) :: o
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: prefix
  integer, intent(in) :: k
  integer, intent(in) :: a(dcp%ish:, dcp%jsh:)
  character(len=4) :: snum
  character(:), allocatable :: fn

  call par_gather_win_i(o%wk_out_i, a)
  if (.not. is_root) return

  write(snum, '(i4.4)') k
  fn = trim(p%dir_result)//"/"//trim(adjustl(prefix))//snum//trim(adjustl(p%outfn_suffix))

  ! 窓外の充填値は nint(p%out_fill)(§81)
  associate (i1 => dcp%ish, i2 => dcp%ieh, j1 => dcp%jw1, j2 => dcp%jw2, ifill => nint(p%out_fill))
  if (iand(p%f_output_mode, e_fmt_txt) /= 0) then
    call fileio_write_window(fn//".txt", g%nx, g%ny, i1, i2, j1, j2, o%wk_out_i, ifill, e_fmt_txt)
  end if
  if (iand(p%f_output_mode, e_fmt_bil) /= 0) then
    call fileio_write_window(fn//".bil", g%nx, g%ny, i1, i2, j1, j2, o%wk_out_i, ifill, e_fmt_bil)
    if (g%gr%active) call georef_write_hdr(fn//".hdr", g%gr, g%nx, g%ny, e_pix_int)
  end if
  if (iand(p%f_output_mode, e_fmt_gtif) /= 0) then
    call fileio_write_window(fn//".tif", g%nx, g%ny, i1, i2, j1, j2, o%wk_out_i, ifill, e_fmt_gtif, g%gr)
  end if
  end associate
end subroutine


end module
