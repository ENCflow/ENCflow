module m_intercept_fixed
  ! ========== 遮断モデル実装の見本: 固定遮断率モデル ==========
  ! 降雨の一定割合 ic_alpha を遮断し、有効雨量 (1-α)P を地表に与える
  ! 最簡モデル(I = αP)。貯留容量・蒸発・降雨強度依存は表現しない。
  ! 遮断率は一様値(ic_alpha)または分布ファイル(fn_icalpha)で与える
  ! (fn_icalpha 指定時は ic_alpha を使わない)。
  !
  ! 【モデル実装者への契約(新モデルを書くときはこの見本に倣う)】
  !  (1) makepre が作った s%pre(m/s)と s%prh(mm/h)を同率で減じる
  !      (出力 Pr と地表水への入力が常に「地表到達雨量」で揃う)
  !  (2) 更新は自帯 js..je のみ(owner-compute)。makepre と同じ
  !      窓・マスク(x>0 かつ sw=0)で回す。近傍参照はないため
  !      ハロ交換は不要
  !  (3) calc が呼ばれるのは降雨分布の更新直後のみ(m_intercept ヘッダの
  !      契約)。同じ分布に再適用されない前提で破壊的に減じてよい。
  !      毎ステップ発展する状態を持つモデルは step 口を使う
  !      (見本は m_intercept_initloss)
  !  (4) モデル固有の内部状態(貯留量等)を持つ場合、リスタート保存は
  !      p%dir_save 下のモデル私有ファイル(intercept_<モデル名>.dat)で
  !      行う(m_gwflow_bucket の契約5と同じ流儀)。本モデルは内部状態を
  !      持たないため save/restore 不要
  !  (5) パラメータの分布ファイルは「全ランクで存在確認(par_stop)→
  !      rank0 が全域に読んで検証(par_abort)→ par_scatter_cell で
  !      帯配布」で読む(方式2。read_alpha_map が見本)。検証は使用セル
  !      (x>0 かつ sw=0)に限る(領域外の nodata 値を弾かないため)。
  !      土地利用からの構築(lu2rn 同型)を足す場合も init で行い、
  !      g%lu 等の係数は帯確保なので帯添字で読むこと(§11)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_fileio, only : fileio_read_matrix
  use m_parallel, only : par_info, par_stop, par_abort, dcp, is_root, &
                       par_scatter_cell
  implicit none
  private
  public :: intercept_fixed_init
  public :: intercept_fixed_calc
  public :: intercept_fixed_dispose

  ! モデル私有の設定(単一インスタンス前提。developer.md §12)
  type t_icfix
    real :: passrate = 1.0                 ! 通過率 1-α(一様指定時)
    real, allocatable :: passmap(:,:)      ! 通過率の分布(分布指定時のみ確保。帯)
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
  character(len=256) :: fn_icalpha
  namelist /list_intercept_fixed/ ic_alpha, fn_icalpha

  ic_alpha = -1.0
  fn_icalpha = ""

  call par_info("reading list_intercept_fixed in " // trim(p%fn_intercept))
  open(newunit=un, file=trim(p%fn_intercept), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_intercept_fixed: cannot open " // trim(p%fn_intercept))
  read(un, nml=list_intercept_fixed, iostat=ios)
  if (ios /= 0) call par_stop("list_intercept_fixed: cannot read namelist")
  close(un)

  if (len_trim(fn_icalpha) > 0) then
    ! 分布指定: 遮断率マップを読み、通過率 1-α の帯配列にして保持
    call read_alpha_map(p, g, trim(fn_icalpha))
  else
    ! 一様指定
    if (ic_alpha <= 0.0 .or. ic_alpha >= 1.0) then
      call par_stop("list_intercept_fixed: ic_alpha must be 0 < ic_alpha < 1 (or specify fn_icalpha)")
    end if
    icf%passrate = 1.0 - ic_alpha
  end if

  icf%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 遮断率の分布ファイルを読む(契約5の見本)
!   rank0 が全域に読んで使用セルを検証し、通過率 1-α に変換してから
!   par_scatter_cell で帯配布する。非 root は全域配列を確保しない
!----------------------------------------------------------------------
subroutine read_alpha_map(p, g, fn)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, allocatable :: amap(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  fname = trim(p%dir_data) // "/" // trim(fn)

  ! 存在確認は全ランクで(par_stop は collective)
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("list_intercept_fixed: fn_icalpha not found: " // fname)
  end if

  allocate(icf%passmap(1:g%nx, dcp%jsh:dcp%jeh))
  if (is_root) then
    allocate(amap(1:g%nx, 1:g%ny))
    call par_info(" reading " // fname)
    call fileio_read_matrix(fname, g%nx, g%ny, amap, p%f_input_mode)
    ! 検証は使用セルのみ(領域外・海域の nodata 値は関知しない)。
    ! rank0 単独経路のため par_abort(§5)。この時点ではマスク類は
    ! まだ全域(band_shrink 前)なので全域添字で読める
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
        if (amap(i,j) < 0.0 .or. amap(i,j) >= 1.0) then
          write(msg,'(a,2i7,es12.4)') &
                "list_intercept_fixed: fn_icalpha has a value outside [0,1) at cell", i, j, amap(i,j)
          call par_abort(trim(msg))
        end if
      end do
    end do
    amap(:,:) = 1.0 - amap(:,:)          ! 通過率に変換してから配布
    call par_scatter_cell(amap, icf%passmap)
  else
    call par_scatter_cell(dum, icf%passmap)
  end if
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
  logical :: use_map
  real :: f

  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (it < 0) continue         ! 引数未使用の警告を抑制(時刻依存モデル用に供給)

  use_map = allocated(icf%passmap)

  !$omp parallel do schedule(static) private(i, j, f)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
      if (use_map) then
        f = icf%passmap(i,j)
      else
        f = icf%passrate
      end if
      s%pre(i,j) = s%pre(i,j) * f
      s%prh(i,j) = s%prh(i,j) * f
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
  if (allocated(icf%passmap)) deallocate(icf%passmap)
  icf%initialized = .false.
end subroutine

end module
