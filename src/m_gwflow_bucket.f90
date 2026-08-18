module m_gwflow_bucket
  ! ============ 地下水モデル実装の見本: バケツモデル ============
  ! セルごとの貯留(容量 cap)へ一定浸透能 rate で表面水を移す最簡モデル。
  ! 水平流なし・鉛直交換のみ。geoinfo の土壌設定(sd, sy0)に依存しない
  ! 「依存ゼロの実験用」であることが存在価値(容量は gw_capacity で直接
  ! 指定する抽象貯留)。このため側方流動(f_gwlateral=1)とは組めない
  ! (容量の二重定義。m_gwflow_init が停止する。土層厚を容量とする定数
  ! 浸透能モデルは m_gwflow_greenampt の gw_psif=0 で表現できる)。
  !
  ! 【モデル実装者への契約(新モデルを書くときはこの見本に倣う)】
  !  (1) 表面との交換は「1つのフラックス fx を s%h から引き s%hg に足す」
  !      反対称適用で行う(質量保存が構造的に成立する)
  !  (2) s%h を変更したら同じループで s%e = s%z + s%h を回復する
  !  (3) 更新は自帯 js..je のみ(owner-compute)。近傍セルの s%hg を読む
  !      モデル(側方ダルシー流)は calc の末尾で par_halo_cell(s%hg) を
  !      呼ぶこと。本モデルは鉛直のみなのでハロ交換は一切不要
  !  (4) 内部表現が層別水分など複雑な場合も、毎ステップ柱状換算値を
  !      s%hg に反映すること(質量台帳・出力・計測が共通で動く契約)
  !  (5) モデル固有の内部状態を持つ場合、リスタート保存は p%dir_save 下の
  !      モデル私有ファイル(gwflow_<モデル名>.dat)で行う(init で復元、
  !      dispose で保存。m_swflow_enc と同じ流儀)。restore では自ファイルの
  !      有無のみ確認し、無ければ par_stop(版・格子・精度の検証は m_state が
  !      済ませている。developer.md §7)。本モデルは内部状態を持たないため
  !      save/restore 不要(s%hg 自体は m_state の save_state が面倒を見る)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : par_info, par_stop, dcp
  implicit none
  private
  public :: gwflow_bucket_init
  public :: gwflow_bucket_calc
  public :: gwflow_bucket_dispose

  ! モデル私有の設定(単一インスタンス前提。developer.md §12)
  type t_bucket
    real :: rate = 0.0               ! 浸透能 (m/s)
    real :: cap = 0.0                ! 貯留容量 (m)
    logical :: initialized = .false.
  end type
  type(t_bucket) :: gwb

contains


!----------------------------------------------------------------------
! バケツモデルの初期化(固有グループ &list_gwflow_bucket を自分で読む)
!----------------------------------------------------------------------
subroutine gwflow_bucket_init(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: un, ios
  real :: gw_infil_mmh, gw_capacity
  namelist /list_gwflow_bucket/ gw_infil_mmh, gw_capacity

  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (s%initialized) continue  ! 引数未使用の警告を抑制

  gw_infil_mmh = 0.0
  gw_capacity = 0.0

  call par_info("reading list_gwflow_bucket in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_bucket: cannot open " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_bucket, iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_bucket: cannot read namelist")
  close(un)

  if (gw_infil_mmh <= 0.0) call par_stop("list_gwflow_bucket: gw_infil_mmh must be > 0")
  if (gw_capacity <= 0.0) call par_stop("list_gwflow_bucket: gw_capacity must be > 0")

  gwb%rate = gw_infil_mmh / 1000.0 / 3600.0   ! mm/h -> m/s
  gwb%cap = gw_capacity
  gwb%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! バケツモデルの計算(1回の呼び出しで実効時間刻み dts ぶんの鉛直交換。
! dt_gwflow による間引き時は dts = p%dt * idt_gwflow が渡される)
!----------------------------------------------------------------------
subroutine gwflow_bucket_calc(p, g, s, it, dts)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, intent(in) :: dts
  integer :: i, j
  real :: rt, fx

  if (it < 0) continue  ! 引数未使用の警告を抑制(独自周期を持つモデル用に供給)
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  !$omp parallel do schedule(static) private(i, j, rt, fx)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      ! 実効浸透能: 凍土有効時は低減係数を乗じる(§16.4。無効時は
      ! rt = rate で従来とビット一致)
      rt = gwb%rate
      if (allocated(s%frofac)) rt = rt * s%frofac(i,j)
      ! 浸透フラックス: 浸透能・表面水量・残容量の最小
      fx = min(rt * dts, s%h(i,j), gwb%cap - s%hg(i,j))
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
! バケツモデルの破棄(内部状態を持たないため保存もなし。契約5)
!----------------------------------------------------------------------
subroutine gwflow_bucket_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  gwb%initialized = .false.
end subroutine

end module
