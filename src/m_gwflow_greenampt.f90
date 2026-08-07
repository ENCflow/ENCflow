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
  use m_parallel, only : par_info, par_stop, dcp
  implicit none
  private
  public :: gwflow_greenampt_init
  public :: gwflow_greenampt_calc
  public :: gwflow_greenampt_dispose

  ! モデル私有の設定(単一インスタンス前提。developer.md §12)
  type t_greenampt
    real :: ksv = 0.0                ! 鉛直飽和透水係数 (m/s)
    real :: psif = 0.0               ! 湿潤前線の毛管圧力水頭 (m)
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
  namelist /list_gwflow_greenampt/ gw_ksv_mmh, gw_psif

  if (s%initialized) continue  ! 引数未使用の警告を抑制

  gw_ksv_mmh = 0.0
  gw_psif = 0.0

  call par_info("reading list_gwflow_greenampt in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_greenampt, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_gwflow_greenampt")
  close(un)

  if (gw_ksv_mmh <= 0.0) call par_stop("list_gwflow_greenampt: gw_ksv_mmh must be > 0")
  if (gw_psif < 0.0) call par_stop("list_gwflow_greenampt: gw_psif must be >= 0")
  if (g%sy0 <= 0.0 .or. g%sy0 > 1.0) then
    call par_stop("list_geoinfo: sy0 must be in (0,1] for gwflow greenampt")
  end if
  ! 遅延確保口の呼び忘れ(m_gwflow_init の needs_sd)をここで検出する
  if (.not. allocated(g%sd)) call par_stop("gwflow_greenampt: g%sd is not allocated")

  ga%ksv = gw_ksv_mmh / 1000.0 / 3600.0   ! mm/h -> m/s
  ga%psif = gw_psif
  ga%dtheta = g%sy0
  ga%initialized = .true.
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
      ! 貯留容量(土層厚×水分不足量)。F ≡ s%hg(ヘッダ参照)
      cap = s%sd(i,j) * ga%dtheta
      ! Green-Ampt 浸透能(F_eff = max(F, ksv*dts) で F→0 を正則化)
      fv = ga%ksv * (1.0 + ga%psif * ga%dtheta / max(s%hg(i,j), ga%ksv * dts))
      ! 浸透フラックス: 浸透能・表面水量・残容量の最小
      fx = min(fv * dts, s%h(i,j), cap - s%hg(i,j))
      fx = max(fx, 0.0)
      ! 反対称適用(契約1)と水位の回復(契約2)
      s%h(i,j) = s%h(i,j) - fx
      s%hg(i,j) = s%hg(i,j) + fx
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
  ga%initialized = .false.
end subroutine

end module
