module m_gwflow_greenampt
  ! ========= 鉛直浸透モデル: Green-Ampt(ピストン近似) =========
  ! 谷(Tani)型の鉛直浸透支配機構の中核(handoff_gwflow_tani.md §3.1)。
  ! 土層厚 s%sd(i,j)(動的共有状態。初期値は入力係数 g%sd)と比湧水量
  ! g%sy0(= 有効間隙率 n_e。同 §6.1 の統一)
  ! からセルごとの貯留容量 cap = sd * sy0 を決め、Green-Ampt 浸透能
  !   f_v = K_sv * (1 + psi_f * n_e / F)     (F: 累積浸透深)
  ! で表面水を地下貯留 s%hg へ移す。水平流なし・鉛直交換のみ。
  ! s%hg = cap に達したセルは飽和(土層厚ぶん湛水)し、以後の浸透は
  ! 止まる(超過分は表面水 s%h に残り m_swflow が扱う)。
  ! 実装契約(反対称適用・水位回復・owner-compute・柱状換算・リスタート)
  ! は m_gwflow_bucket ヘッダの5箇条に従う。
  !
  ! 【K_sv・ψf の面的分布(2026-08-18。§16)】
  !   透水性舗装・浸透施設・土地利用別の浸透能を表すため、K_sv と ψf は
  !   マップ入力(fn_gw_ksv / fn_gw_psif。rank0 読み+scatter の方式2)に
  !   対応する。カーネルは g%sd と同じ流儀で**常に帯配列を参照**し、
  !   分布/一様の分岐を持たない(一様指定ならスカラー値で充填 =
  !   スカラー時代とビット一致)。マップの K_sv は 0 を許す
  !   (K_sv = 0 のセルは不浸透 = 完全舗装。除算保護のため浸透計算を
  !   スキップする)。一様スカラー指定は従来どおり > 0 を要求する。
  !
  ! 【F := s%hg の閉包(重要)】
  !   鉛直のみの構成では、累積浸透深 F は柱状換算の地下貯留 s%hg と
  !   恒等なので、F のモデル私有配列は持たず s%hg をそのまま使う
  !   (リスタートも m_state の hg 保存で自動的に整合。契約5の私有保存は
  !   不要)。側方流動(f_gwlateral=1)併用時は s%hg が側方でも変化する
  !   ため F は「累積浸透深」ではなく「現在の貯留量」になるが、これは
  !   意図的な閉包として採用する(2026-08-05 決定): 吸引項が現在の
  !   水分状態に依存する Green-Ampt 変種に相当し、側方排水で乾いた
  !   セルの浸透能が回復する(累積 F を保持する古典形はイベント間の
  !   再配分・乾燥を表現できず、むしろ非物理的)。私有状態が不要になる
  !   ため save/restore も s%hg だけで閉じる。厳密な累積 F が必要に
  !   なったら私有状態への昇格と契約5の保存を検討する。
  !
  ! 【F→0 の特異性】
  !   f_v は F→0 で発散する。F_eff = max(F, K_sv*dts) で正則化し、
  !   初回ステップの浸透量を ~ K_sv*dts + psi_f*n_e に抑える
  !   (ソープティビティ律速の古典的近似)。
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_fileio, only : fileio_read_matrix
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_scatter_cell
  implicit none
  private
  public :: gwflow_greenampt_init
  public :: gwflow_greenampt_calc
  public :: gwflow_greenampt_dispose

  ! モデル私有の設定(単一インスタンス前提。developer.md §12)
  type t_greenampt
    real, allocatable :: ksv(:,:)    ! 鉛直飽和透水係数 (m/s。帯+ハロ。
                                     !   一様指定ならスカラー値で充填)
    real, allocatable :: psif(:,:)   ! 湿潤前線の毛管圧力水頭 (m。同上)
    real :: dtheta = 0.0             ! 水分不足量 Δθ(= g%sy0。init で転記)
    logical :: initialized = .false.
  end type
  type(t_greenampt) :: ga

contains


!----------------------------------------------------------------------
! Green-Ampt モデルの初期化(固有グループ &list_gwflow_greenampt を
! 自分で読む)。g%sd は m_gwflow_init が m_geoinfo_require_sd で確保済み
!----------------------------------------------------------------------
subroutine gwflow_greenampt_init(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: un, ios
  real :: gw_ksv_mmh, gw_psif
  character(len=1024) :: fn_gw_ksv, fn_gw_psif
  namelist /list_gwflow_greenampt/ gw_ksv_mmh, gw_psif, fn_gw_ksv, fn_gw_psif

  if (s%initialized) continue  ! 引数未使用の警告を抑制

  gw_ksv_mmh = 0.0
  gw_psif = 0.0
  fn_gw_ksv = ""
  fn_gw_psif = ""

  call par_info("reading list_gwflow_greenampt in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_greenampt: cannot open " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_greenampt, iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_greenampt: cannot read namelist")
  close(un)

  ! 一様スカラーは従来どおり > 0 を要求(マップ指定時は 0 = 不浸透を
  ! 許すため、マップ側の検査は read_map_scatter の非負検査のみ)
  if (len_trim(fn_gw_ksv) == 0 .and. gw_ksv_mmh <= 0.0) then
    call par_stop("list_gwflow_greenampt: gw_ksv_mmh must be > 0 (or give fn_gw_ksv)")
  end if
  if (gw_psif < 0.0) call par_stop("list_gwflow_greenampt: gw_psif must be >= 0")
  if (g%sy0 <= 0.0 .or. g%sy0 > 1.0) then
    call par_stop("list_geoinfo: sy0 must be in (0,1] for gwflow greenampt")
  end if
  ! 遅延確保口の呼び忘れ(m_gwflow_init の needs_sd)をここで検出する
  if (.not. allocated(g%sd)) call par_stop("gwflow_greenampt: g%sd (soil depth) is not allocated")

  ! 係数の帯配列(ヘッダ【K_sv・ψf の面的分布】。一様なら充填、
  ! マップなら rank0 読み+scatter で上書き)
  allocate(ga%ksv(1:g%nx, dcp%jsh:dcp%jeh), source = gw_ksv_mmh / 1000.0 / 3600.0)
  allocate(ga%psif(1:g%nx, dcp%jsh:dcp%jeh), source = gw_psif)
  if (len_trim(fn_gw_ksv) > 0) then
    call read_map_scatter(p, g, fn_gw_ksv, ga%ksv, "gw_ksv")
    ga%ksv(:,:) = ga%ksv(:,:) / 1000.0 / 3600.0   ! mm/h -> m/s
  end if
  if (len_trim(fn_gw_psif) > 0) then
    call read_map_scatter(p, g, fn_gw_psif, ga%psif, "gw_psif")
  end if

  ga%dtheta = g%sy0
  ga%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! rank0 が全域マップを読み par_scatter_cell で帯+ハロへ配布する(方式2)。
! 負値はデータ不良として停止(判定は全ランク同一 = 配布後の帯で検査)
!----------------------------------------------------------------------
subroutine read_map_scatter(p, g, fn, a, label)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, intent(inout) :: a(1:, dcp%jsh:)
  character(len=*), intent(in) :: label
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  integer :: i, j
  character(len=1024) :: msg

  fname = trim(p%dir_data) // "/" // trim(fn)
  call par_info(" reading " // fname)
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    call par_scatter_cell(wk, a)
  else
    call par_scatter_cell(dum, a)
  end if
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (g%x(i,j) <= 0) cycle
      if (a(i,j) < 0.0) then
        write(msg,'(a,2i7,es12.4)') "gwflow_greenampt: negative " // label // " at", &
                                    i, j, a(i,j)
        call par_stop(trim(msg))
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! Green-Ampt モデルの計算(1回の呼び出しで実効時間刻み dts ぶんの
! 鉛直交換)
!----------------------------------------------------------------------
subroutine gwflow_greenampt_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts
  integer :: i, j
  real :: cap, fv, fx

  if (it < 0) continue  ! 引数未使用の警告を抑制(独自周期を持つモデル用に供給)
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  !$omp parallel do schedule(static) private(i, j, cap, fv, fx)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      ! K_sv = 0(マップ指定の不浸透セル)は浸透なし(正則化 F_eff の
      ! 除算保護を兼ねる。一様指定では > 0 が保証されるため無縁)
      if (ga%ksv(i,j) <= 0.0) cycle
      ! 貯留容量(土層厚×水分不足量)。F ≡ s%hg(ヘッダ参照)
      cap = s%sd(i,j) * ga%dtheta
      ! Green-Ampt 浸透能(F_eff = max(F, ksv*dts) で F→0 を正則化)
      fv = ga%ksv(i,j) * (1.0 + ga%psif(i,j) * ga%dtheta &
                                / max(s%hg(i,j), ga%ksv(i,j) * dts))
      ! 浸透フラックス: 浸透能・表面水量・残容量の最小
      fx = min(fv * dts, s%h(i,j), cap - s%hg(i,j))
      fx = max(fx, 0.0)
      ! 反対称適用(契約1)と水位の回復(契約2)
      s%h(i,j) = s%h(i,j) - fx
      ! 地下側は実効平面積率で体積整合させる(§26。河道幅・断面 σ の
      ! 有効セルのみ af/gv < 1。無効時は af=gv で係数 1.0 =従来とビット一致)
      s%hg(i,j) = s%hg(i,j) + fx * (s%af(i,j) / g%gv(i,j))
      ! 浸透フラックスの記録(水質の濃度同伴用。m_wq が読んでゼロ戻し。§30)
      if (allocated(s%fxg)) s%fxg(i,j) = s%fxg(i,j) + fx
      s%e(i,j) = s%z(i,j) + s%h(i,j)
    end do
  end do
  !$omp end parallel do

  ! 鉛直交換のみのためハロ交換は不要(契約3)

end subroutine


!----------------------------------------------------------------------
! Green-Ampt モデルの破棄(現段階は F ≡ s%hg のため私有保存なし。
! 契約5とヘッダの昇格条件を参照)
!----------------------------------------------------------------------
subroutine gwflow_greenampt_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (allocated(ga%ksv)) deallocate(ga%ksv)
  if (allocated(ga%psif)) deallocate(ga%psif)
  ga%initialized = .false.
end subroutine

end module
