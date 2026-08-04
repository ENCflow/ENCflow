module m_intercept_fixed
  ! ========== 遮断モデル実装の見本: 固定遮断率モデル ==========
  ! 降雨の一定割合 ic_alpha を遮断し、有効雨量 (1-α)P を地表に与える
  ! 最簡モデル(I = αP)。貯留容量・蒸発・降雨強度依存は表現しない。
  !
  ! 【モデル実装者への契約(新モデルを書くときはこの見本に倣う)】
  !  (1) makepre が作った s%pre(m/s)と s%prh(mm/h)を同率で減じる
  !      (出力 Pr と地表水への入力が常に「地表到達雨量」で揃う)
  !  (2) 更新は自帯 js..je のみ(owner-compute)。makepre と同じ
  !      窓・マスク(x>0 かつ sw=0)で回す。近傍参照はないため
  !      ハロ交換は不要
  !  (3) calc が呼ばれるのは降雨分布の更新直後のみ(m_intercept ヘッダの
  !      契約)。同じ分布に再適用されない前提で破壊的に減じてよい
  !  (4) モデル固有の内部状態(林冠貯留量等)を持つ場合、リスタート保存は
  !      p%dir_save 下のモデル私有ファイル(intercept_<モデル名>.dat)で
  !      行う(m_gwflow_bucket の契約5と同じ流儀)。本モデルは内部状態を
  !      持たないため save/restore 不要
  !  (5) 遮断率の分布ファイル読み込みや土地利用からの構築(粗度係数の
  !      lu2rn と同型)は init で行う。g%lu 等の係数は帯確保なので
  !      帯添字で読むこと(developer.md §11。全域添字は不可)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : par_info, par_stop, dcp
  implicit none
  private
  public :: intercept_fixed_init
  public :: intercept_fixed_calc
  public :: intercept_fixed_dispose

  ! モデル私有の設定(単一インスタンス前提。developer.md §12)
  type t_icfix
    real :: passrate = 1.0           ! 通過率 1-α(地表到達分の割合)
    logical :: initialized = .false.
  end type
  type(t_icfix) :: icf

contains


!----------------------------------------------------------------------
! 固定遮断率モデルの初期化(固有グループ &list_intercept_fixed を自分で読む)
!----------------------------------------------------------------------
subroutine intercept_fixed_init(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer :: un, ios
  real :: ic_alpha
  namelist /list_intercept_fixed/ ic_alpha

  if (g%initialized) continue  ! 引数未使用の警告を抑制

  ic_alpha = -1.0

  call par_info("reading list_intercept_fixed in " // trim(p%fn_intercept))
  open(newunit=un, file=trim(p%fn_intercept), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("cannot open file: " // trim(p%fn_intercept))
  read(un, nml=list_intercept_fixed, iostat=ios)
  if (ios /= 0) call par_stop("error in reading list_intercept_fixed")
  close(un)

  if (ic_alpha <= 0.0 .or. ic_alpha >= 1.0) then
    call par_stop("list_intercept_fixed: ic_alpha must be 0 < ic_alpha < 1")
  end if

  icf%passrate = 1.0 - ic_alpha
  icf%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 固定遮断率モデルの適用(更新直後の s%pre / s%prh を有効雨量に減じる)
!----------------------------------------------------------------------
subroutine intercept_fixed_calc(p, g, s, it)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j

  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (it < 0) continue         ! 引数未使用の警告を抑制(時刻依存モデル用に供給)

  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
      s%pre(i,j) = s%pre(i,j) * icf%passrate
      s%prh(i,j) = s%prh(i,j) * icf%passrate
    end do
  end do
  !$omp end parallel do

  ! 近傍参照なしのためハロ交換は不要(契約2)

end subroutine


!----------------------------------------------------------------------
! 固定遮断率モデルの破棄(内部状態を持たないため保存もなし。契約4)
!----------------------------------------------------------------------
subroutine intercept_fixed_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  icf%initialized = .false.
end subroutine

end module
