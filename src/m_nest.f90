!**********************************************************************
!
! m_nest: 多段ネスティングの格子木・幾何・親→子の帯 Dirichlet
!   (docs/nesting_plan.md。Phase 1 = 一方向・同一 dt・nest_bc=2)
!
!   位置づけ: m_main より下、物理モジュールより上。状態の所有は各格子の
!   t_encflow(m_main)にあり、本モジュールは「親の窓の写し」と「子の帯の
!   作業配列」だけを持つ。B 群(m_swflow_enc のエッジ量)に触る手続き
!   (nest_capture / nest_prolong / nest_setup_child)は、呼び出し側
!   (m_main)が当該格子を select(bind)した状態で呼ぶこと。
!
!   幾何(§3.3): 子セル (1,1) の左上隅(i, j の小さい側)が親セル (i0, j0)
!   の左上隅に一致し、子の dx = 親の dx / r。子の全格子 1..nxc × 1..nyc が
!   親セル i0..i0+nxc/r-1 × j0..j0+nyc/r-1(足元)を覆う。帯 = 子の外周
!   nb セル。足元の外側に補間用の親セル 1 個分の余裕を要求する。
!
!   時間進行(§3.4。Phase 1 は r_t = 1): 親が 1 歩進む前に親の窓を t^n で
!   写し(nest_capture)、親の 1 歩の後、子のサブステップ開始時刻 = t^n の
!   窓から子の帯を埋め(nest_prolong)、子を 1 歩進める。子の内部セルの更新
!   が読む入力(2 セル先までのセル量とそのエッジ量)が全て親由来になる
!   ので、比 1:1 では子の内部が親の同領域とビット一致する(§9 の 4)。
!
!   MPI(§3.7): 窓は「自帯の行(セル)/自帯のセルが所有するスロット(エッジ)
!   だけを埋めたゼロ初期化配列」を 1 要素 1 寄与の allreduce で全ランクに
!   配る(ビット決定的)。各ランクは自分の子帯(確保範囲 jsh..jeh)の行だけ
!   を補間する(通信なし。ハロ行も同じ値を各自が書く)。
!
!**********************************************************************
module m_nest
  use m_parallel, only : dcp, nproc, par_info, par_stop, par_allreduce_sumr, par_sum_rows
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary
  use m_swflow_enc, only : m_swflow_enc_nest_export, m_swflow_enc_nest_import, bcs, opt, e_bc_wall
  use list_nest, only : t_list_nest, list_nest_read
  use m_util, only : itoa, rtoa
  implicit none
  private

  public :: t_nest, t_nest_grid
  public :: nest_read_list, nest_setup_child, nest_record_band, nest_capture, nest_prolong, &
            nest_restrict, nest_summary, nest_dispose

  ! 親→子で渡すセル量(窓の写しの第 1 添字)
  integer, parameter :: ncq = 7
  integer, parameter :: q_h = 1, q_e = 2, q_u = 3, q_v = 4, q_vv = 5, q_m = 6, q_n = 7

  ! 8 近傍とエッジのスロット規約(m_swflow_enc と同一。§3.5)
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]
  integer, parameter :: ke(1:8)  = [  1,  2,  3,  4,  4,  3,  2,  1]

  type t_nest_grid
    integer :: id = 0                 ! 格子番号(= 一覧の行順 = m_main のインスタンス番号)
    integer :: parent = 0             ! 親の格子番号(ルートは 0)
    integer :: r = 1                  ! 空間比(親 dx / 子 dx。正の整数)
    integer :: rt = 1                 ! 時間比(親 dt / 子 dt。Phase 1 は 1 のみ)
    integer :: i0 = 0, j0 = 0         ! 子セル (1,1) が整列する親セル
    character(len=256) :: fn_param = ""
    integer :: nchild = 0
    integer, allocatable :: child(:)
    ! 子としての設定(&list_nest)
    integer :: nb = 0                 ! 境界帯の幅(セル。0 = 自動。nest_setup_child が確定)
    integer :: nest_bc = 2            ! 親→子の方式
    integer :: nest_fb = 0            ! 子→親の方式(0: なし, 1: 面積平均, 2: 湿潤判定付き平均〔既定〕)
    integer :: js = 1, je = 0         ! この格子の自ランクの担当帯(nest_setup_* が記録。select に依らず参照するため)
    ! 子→親の統計(Phase 2。全ランク同値)
    integer(8) :: n_restrict = 0      ! 置換の回数
    real(8) :: dvol_sum = 0.0d0       ! 置換による親の水柱体積の変化の累計 (m³。dx·dy·Σdh)
    real(8) :: dvol_abs = 0.0d0       ! 同、絶対値の累計
    ! 子としての幾何(nest_setup_child が確定)
    logical :: ready = .false.
    integer :: nxc = 0, nyc = 0       ! 子格子の寸法
    integer :: pi1 = 0, pi2 = 0       ! 足元(親セル範囲)
    integer :: pj1 = 0, pj2 = 0
    real :: dd = 0.0                  ! 子の乾燥判定水深(p%dd)
    ! 親の窓の写し(t^n。全ランク同値)
    real, allocatable :: wc(:,:,:)    ! セル量 (ncq, pi1-1:pi2+1, pj1-1:pj2+1)
    real, allocatable :: we(:,:,:,:)  ! エッジ量 (1:2 = uv,mn, 1:4, pi1-2:pi2+1, pj1-2:pj2+1)
    real, allocatable :: wr(:,:,:)    ! 子→親の作業配列(1:8, 足元。nest_restrict が使う)
    ! 子側の作業配列(自ランクの確保範囲の行)
    integer :: jlo = 1, jhi = 0       ! 子の確保範囲を 1..nyc に切った行範囲
    logical, allocatable :: inband(:,:)   ! 帯セルか (1:nxc, jlo:jhi)
    real, allocatable :: ev(:,:,:,:)      ! 帯のエッジ量 (1:2, 1:4, 0:nxc, jlo-1:jhi)
  end type

  type t_nest
    integer :: ng = 1                 ! 格子数(1 = ネストなし)
    integer :: root = 1
    type(t_nest_grid), allocatable :: g(:)
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 格子一覧(fn_nest)を読む(§3.3 / §4)。1 行 1 格子:
!   id  parent  param_file  [r  r_t  [i0  j0]]
!   # で始まる行と空行は無視。id は行順に 1, 2, ...(親は自分より小さい
!   番号 = 親が先に並ぶ)。1 行目がルート(parent は 0 または 1、param は
!   コマンドラインのルートのパラメータと同一であること)。子は i0, j0
!   (子セル (1,1) が整列する親セル)を必須とする(地理参照からの導出は
!   未実装: Phase 2 以降)。各子のパラメータファイルから &list_nest を読む。
!----------------------------------------------------------------------
subroutine nest_read_list(fn, fn_root, nt)
  character(len=*), intent(in) :: fn        ! 一覧ファイル
  character(len=*), intent(in) :: fn_root   ! ルートのパラメータファイル(整合確認)
  type(t_nest), intent(inout) :: nt
  integer :: un, ios, n, k, id, parent, r, rt, i0, j0, nc, c
  character(len=1024) :: line, iom
  character(len=256) :: fnp
  type(t_list_nest) :: lst

  call par_info("reading nest grid list in "//trim(fn))
  open(newunit=un, file=trim(fn), status='old', action='read', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("nest: cannot open "//trim(fn)//": "//trim(iom))
  ! 1 回目: 行数
  n = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (is_blank(line)) cycle
    n = n + 1
  end do
  if (n < 1) call par_stop("nest: grid list is empty: "//trim(fn))
  nt%ng = n
  nt%root = 1
  if (allocated(nt%g)) deallocate(nt%g)
  allocate(nt%g(n))
  ! 2 回目: 解釈
  rewind(un)
  k = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (is_blank(line)) cycle
    k = k + 1
    r = 1; rt = 1; i0 = 0; j0 = 0
    read(line, *, iostat=ios) id, parent, fnp, r, rt, i0, j0
    if (ios > 0) call par_stop("nest: cannot parse line "//itoa(k)//" of "//trim(fn)//": "//trim(line))
    if (ios < 0) then
      ! 省略形(r 以降なし / i0 j0 なし)を順に試す
      r = 1; rt = 1; i0 = 0; j0 = 0
      read(line, *, iostat=ios) id, parent, fnp, r, rt
      if (ios /= 0) then
        r = 1; rt = 1
        read(line, *, iostat=ios) id, parent, fnp
        if (ios /= 0) call par_stop("nest: cannot parse line "//itoa(k)//" of "//trim(fn)//": "//trim(line))
      end if
    end if
    if (id /= k) call par_stop("nest: grid id must be the line number ("//itoa(k)//") but got "//itoa(id))
    if (k == 1) then
      if (parent /= 0 .and. parent /= 1) call par_stop("nest: the first grid is the root; parent must be 0")
      parent = 0
      if (trim(fnp) /= trim(fn_root)) then
        call par_info("nest: note: root param in the list ("//trim(fnp)//") differs from the command line ("// &
                      trim(fn_root)//"); the command line is used")
      end if
    else
      if (parent < 1 .or. parent >= k) then
        call par_stop("nest: parent of grid "//itoa(k)//" must be an earlier grid (1.."//itoa(k-1)//")")
      end if
      if (r < 1) call par_stop("nest: grid "//itoa(k)//": r must be a positive integer")
      if (rt < 1) call par_stop("nest: grid "//itoa(k)//": r_t must be a positive integer")
      if (i0 < 1 .or. j0 < 1) then
        call par_stop("nest: grid "//itoa(k)//": i0 j0 (parent cell of the child's corner) are required "// &
                      "(derivation from georeferencing is not implemented yet)")
      end if
    end if
    nt%g(k)%id = k
    nt%g(k)%parent = parent
    nt%g(k)%r = r
    nt%g(k)%rt = rt
    nt%g(k)%i0 = i0
    nt%g(k)%j0 = j0
    nt%g(k)%fn_param = fnp
  end do
  close(un)
  ! 子リスト
  do k = 1, n
    nc = count(nt%g(:)%parent == k)
    nt%g(k)%nchild = nc
    allocate(nt%g(k)%child(max(nc, 1)))
    nc = 0
    do c = 1, n
      if (nt%g(c)%parent == k) then
        nc = nc + 1
        nt%g(k)%child(nc) = c
      end if
    end do
  end do
  ! 子の &list_nest(読むだけ。検証はここで)
  do k = 2, n
    lst = t_list_nest()
    call list_nest_read(nt%g(k)%fn_param, lst)
    nt%g(k)%nb = lst%nest_nb
    nt%g(k)%nest_bc = lst%nest_bc
    nt%g(k)%nest_fb = lst%nest_fb
    if (lst%nest_nb /= 0 .and. lst%nest_nb < 2) call par_stop("list_nest: nest_nb must be 0 (auto) or >= 2")
    if (lst%nest_bc /= 2) then
      call par_stop("list_nest: nest_bc="//itoa(lst%nest_bc)//" is not implemented yet (Phase 1 supports 2)")
    end if
    if (lst%nest_fb < 0 .or. lst%nest_fb > 2) then
      call par_stop("list_nest: nest_fb="//itoa(lst%nest_fb)//" is not implemented (0: one-way, 1: area "// &
                    "average, 2: wet-aware average; 3 = conservative correction is Phase 4)")
    end if
    if (nt%g(k)%rt /= 1) call par_stop("nest: r_t > 1 is not implemented yet (Phase 3); use r_t = 1")
  end do
  call par_info("nest: "//itoa(n)//" grids (root = 1)")
  do k = 2, n
    call par_info("nest:   grid "//itoa(k)//": parent "//itoa(nt%g(k)%parent)//", r = "//itoa(nt%g(k)%r)// &
                  ", r_t = "//itoa(nt%g(k)%rt)//", corner at parent cell ("//itoa(nt%g(k)%i0)//", "// &
                  itoa(nt%g(k)%j0)//"), "//trim(fb_name(nt%g(k)%nest_fb))//", param "//trim(nt%g(k)%fn_param))
  end do
end subroutine

!----------------------------------------------------------------------
! 子格子 c の幾何の確定と整合検査(親子とも initialize 済み。子を
! select した状態で呼ぶ: dcp と bcs が子のもの)
!----------------------------------------------------------------------
subroutine nest_setup_child(nt, c, pp, gp, pc, gc, bc)
  type(t_nest), intent(inout) :: nt
  integer, intent(in) :: c
  type(t_sysparam), intent(in) :: pp, pc      ! 親・子のパラメータ
  type(t_geoinfo), intent(in) :: gp, gc       ! 親・子の地理情報
  type(t_boundary), intent(in) :: bc          ! 子の境界条件
  integer :: r, i, j, nb_req
  character(len=32) :: tag
  associate (n => nt%g(c))
    tag = "nest: grid "//itoa(c)
    r = n%r
    ! 解像度・時間刻み
    if (abs(gc%dx * r - gp%dx) > 1.0e-6 * gp%dx .or. abs(gc%dy * r - gp%dy) > 1.0e-6 * gp%dy) then
      call par_stop(trim(tag)//": child dx*r must equal parent dx (child "//trim(rtoa(gc%dx))// &
                    " x "//itoa(r)//", parent "//trim(rtoa(gp%dx))//")")
    end if
    if (abs(pc%dt * n%rt - pp%dt) > 1.0e-9 * pp%dt) then
      call par_stop(trim(tag)//": child dt*r_t must equal parent dt")
    end if
    if (pc%t0 /= pp%t0 .or. pc%nt /= pp%nt * n%rt) then
      call par_stop(trim(tag)//": child t0/tt must match the parent (same t0, nt_child = nt_parent*r_t)")
    end if
    if (pc%f_gridsystem /= 0) call par_stop(trim(tag)//": nesting requires ENC (f_gridsystem=0)")
    ! 寸法と足元
    if (mod(gc%nx, r) /= 0 .or. mod(gc%ny, r) /= 0) then
      call par_stop(trim(tag)//": child nx, ny must be multiples of r")
    end if
    n%nxc = gc%nx
    n%nyc = gc%ny
    n%pi1 = n%i0
    n%pi2 = n%i0 + gc%nx / r - 1
    n%pj1 = n%j0
    n%pj2 = n%j0 + gc%ny / r - 1
    if (n%pi1 < 2 .or. n%pj1 < 2 .or. n%pi2 > gp%nx - 1 .or. n%pj2 > gp%ny - 1) then
      call par_stop(trim(tag)//": child footprint (parent cells "//itoa(n%pi1)//".."//itoa(n%pi2)//" x "// &
                    itoa(n%pj1)//".."//itoa(n%pj2)//") must leave >= 1 parent cell to the parent edges")
    end if
    ! 帯の幅: 子の内部セルの更新が読む入力が全て帯(とその内側)に収まる幅。
    ! セル量のステンシルは 2(ハロ幅)。運動量保存形移流(f_advection_scheme
    ! >= 2)は風上側 2 本目のエッジまで読む(uv のハロ 2)ので、帯 2 では
    ! 帯の外側(子の壁面)のエッジを読んでしまう → 3 が必要。
    ! 恒等テスト(test/nest_identity)で確認: wave(スキーム 1)= 2、
    ! chichibu(スキーム 3)= 3 で全ステップビット一致、2 では不一致
    nb_req = 2
    if (opt%f_advection_scheme >= 2) nb_req = 3
    if (n%nb == 0) then
      n%nb = nb_req
    else if (n%nb < nb_req) then
      call par_stop(trim(tag)//": nest_nb = "//itoa(n%nb)//" is too narrow for f_advection_scheme = "// &
                    itoa(opt%f_advection_scheme)//" (needs >= "//itoa(nb_req)//"; 0 = auto)")
    end if
    if (gc%nx <= 2 * n%nb + 2 .or. gc%ny <= 2 * n%nb + 2) then
      call par_stop(trim(tag)//": child grid too small for the boundary band (nb = "//itoa(n%nb)//")")
    end if
    ! 子の外縁は壁(帯の外向き面)。流入区間も不可
    if (any(bcs%f_bc_side /= e_bc_wall) .or. bc%ninflow > 0) then
      call par_stop(trim(tag)//": the child's outer boundary must be closed (f_bc_w/e/n/s = 0, no inflow); "// &
                    "the band receives the parent's values")
    end if
    n%dd = pc%dd
    ! 親の窓の写し
    if (allocated(n%wc)) deallocate(n%wc)
    if (allocated(n%we)) deallocate(n%we)
    allocate(n%wc(ncq, n%pi1-1:n%pi2+1, n%pj1-1:n%pj2+1), source = 0.0)
    allocate(n%we(2, 4, n%pi1-2:n%pi2+1, n%pj1-2:n%pj2+1), source = 0.0)
    if (allocated(n%wr)) deallocate(n%wr)
    allocate(n%wr(8, n%pi1:n%pi2, n%pj1:n%pj2), source = 0.0)
    ! 子側の作業配列(自ランクの確保範囲)
    n%jlo = max(dcp%jsh, 1)
    n%jhi = min(dcp%jeh, gc%ny)
    if (allocated(n%inband)) deallocate(n%inband)
    if (allocated(n%ev)) deallocate(n%ev)
    allocate(n%inband(1:gc%nx, n%jlo:n%jhi))
    allocate(n%ev(2, 4, 0:gc%nx, n%jlo-1:n%jhi), source = 0.0)
    do j = n%jlo, n%jhi
      do i = 1, gc%nx
        n%inband(i, j) = (i <= n%nb .or. i > gc%nx - n%nb .or. j <= n%nb .or. j > gc%ny - n%nb)
      end do
    end do
    n%js = dcp%js
    n%je = dcp%je
    n%ready = .true.
    call par_info(trim(tag)//": "//itoa(gc%nx)//" x "//itoa(gc%ny)//" cells, dx = "//trim(rtoa(gc%dx))// &
                  ", footprint in parent = cells "//itoa(n%pi1)//".."//itoa(n%pi2)//" x "// &
                  itoa(n%pj1)//".."//itoa(n%pj2)//", band width nb = "//itoa(n%nb))
  end associate
end subroutine

!----------------------------------------------------------------------
! 格子 k(親。select 済み)の窓を t^n で写す(全ての子について)
!----------------------------------------------------------------------
subroutine nest_capture(nt, k, s)
  type(t_nest), intent(inout) :: nt
  integer, intent(in) :: k
  type(t_state), intent(in) :: s
  integer :: ic, c, i, j
  do ic = 1, nt%g(k)%nchild
    c = nt%g(k)%child(ic)
    associate (n => nt%g(c))
      n%wc = 0.0
      do j = max(dcp%js, n%pj1 - 1), min(dcp%je, n%pj2 + 1)
        do i = n%pi1 - 1, n%pi2 + 1
          n%wc(q_h,  i, j) = s%h(i, j)
          n%wc(q_e,  i, j) = s%e(i, j)
          n%wc(q_u,  i, j) = s%u(i, j)
          n%wc(q_v,  i, j) = s%v(i, j)
          n%wc(q_vv, i, j) = s%vv(i, j)
          n%wc(q_m,  i, j) = s%m(i, j)
          n%wc(q_n,  i, j) = s%n(i, j)
        end do
      end do
      n%we = 0.0
      call m_swflow_enc_nest_export(n%pi1 - 2, n%pi2 + 1, n%pj1 - 2, n%pj2 + 1, n%we)
      if (nproc > 1) then
        call share(n%wc, size(n%wc))
        call share(n%we, size(n%we))
      end if
    end associate
  end do
end subroutine

!----------------------------------------------------------------------
! 子格子 c(select 済み)の帯を親の窓(t^n)から埋める(§3.5。nest_bc=2)
!   比 1 は複写(乾湿規則を適用しない = 恒等テストの前提)。比 > 1 は
!   η 基準の双線形補間と §3.5 のセル単位の乾湿規則(未検証。Phase 3 で
!   比 3・5 の収束試験を行う)
!----------------------------------------------------------------------
subroutine nest_prolong(nt, c, g, s)
  type(t_nest), intent(inout) :: nt
  integer, intent(in) :: c
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, k, kk, ie, je, ip, jp, in, jn
  real :: hc, hn
  associate (n => nt%g(c))
    if (.not. n%ready) call par_stop("nest_prolong: grid "//itoa(c)//" is not set up")
    ! --- セル量 ---
    do j = n%jlo, n%jhi
      do i = 1, n%nxc
        if (.not. n%inband(i, j)) cycle
        if (g%x(i, j) <= 0) cycle
        if (n%r == 1) then
          ip = n%i0 + i - 1
          jp = n%j0 + j - 1
          s%h(i, j)  = n%wc(q_h,  ip, jp)
          s%u(i, j)  = n%wc(q_u,  ip, jp)
          s%v(i, j)  = n%wc(q_v,  ip, jp)
          s%vv(i, j) = n%wc(q_vv, ip, jp)
          s%m(i, j)  = n%wc(q_m,  ip, jp)
          s%n(i, j)  = n%wc(q_n,  ip, jp)
          s%e(i, j)  = s%z(i, j) + s%h(i, j)
        else
          call interp_cell(n, i, j, s)
        end if
      end do
    end do
    ! --- エッジ量(帯セルに接する全スロット)---
    do j = n%jlo, n%jhi
      do i = 1, n%nxc
        if (.not. n%inband(i, j)) cycle
        do k = 1, 8
          kk = ke(k)
          ie = i + die(k)
          je = j + dje(k)
          if (ie < 0 .or. ie > n%nxc .or. je < n%jlo - 1 .or. je > n%jhi) cycle
          if (n%r == 1) then
            n%ev(1:2, kk, ie, je) = n%we(1:2, kk, ie + n%i0 - 1, je + n%j0 - 1)
          else
            call interp_edge(n, kk, ie, je, n%ev(1:2, kk, ie, je))
            ! 受け側の子セルが乾いていればゼロ(§3.5 規則 3)
            in = i + din(k)
            jn = j + djn(k)
            hc = s%h(i, j)
            hn = hc
            if (in >= 1 .and. in <= n%nxc .and. jn >= n%jlo .and. jn <= n%jhi) hn = s%h(in, jn)
            if (min(hc, hn) < n%dd) n%ev(1:2, kk, ie, je) = 0.0
          end if
        end do
      end do
    end do
    call m_swflow_enc_nest_import(n%nxc, n%nyc, n%jlo, n%jhi, n%inband, n%ev)
  end associate
end subroutine

!----------------------------------------------------------------------
! 格子 k(select 済み)の担当帯を記録する(ルート用。子は nest_setup_child が記録)
!----------------------------------------------------------------------
subroutine nest_record_band(nt, k)
  type(t_nest), intent(inout) :: nt
  integer, intent(in) :: k
  nt%g(k)%js = dcp%js
  nt%g(k)%je = dcp%je
end subroutine

!----------------------------------------------------------------------
! 子 c の内部(帯を除く)を親 p のセルへ置換する(§3.6。子→親)
!   親を select した状態で呼ぶ(状態は A 群だけを読み書きするが、統計の
!   par_sum_rows が現在の dcp = 親の帯を前提にする。担当帯は setup で記録した
!   js/je を使う)。
!   nest_fb = 1: r×r の子セルの h, m, n の面積平均。u, v は m/h, n/h。
!   nest_fb = 2: 湿潤(h > dd)な子セルの η と h の平均から
!                h_p = min(h_av, max(η_av − z_p, 0))。m, n は湿潤セルの平均を
!                h_p/h_av 倍に縮小、u, v は m/h, n/h(GeoClaw 型)。
!                湿潤セルがなければ親は乾き。
!   比 1 はどちらも複写(恒等テストの前提。e は z + h で回復)。
!   MPI: 子の帯境界は r の倍数行に整列しているので(par_decomp_init の align)
!   親セル 1 個分の子ブロックは 1 ランクに収まる。各ランクが自分の子帯の
!   ブロックを平均してゼロ初期化の足元配列に書き、1 要素 1 寄与の allreduce
!   で共有してから、自分の親帯の行だけを書き換える(決定的)。
!   親のエッジ量(uv, mn)は置換しない(次ステップの冒頭で再計算される。
!   界面の保存修正は Phase 4)。
!----------------------------------------------------------------------
subroutine nest_restrict(nt, c, sc, sp, gp)
  type(t_nest), intent(inout) :: nt
  integer, intent(in) :: c
  type(t_state), intent(in) :: sc          ! 子の状態
  type(t_state), intent(inout) :: sp       ! 親の状態
  type(t_geoinfo), intent(in) :: gp        ! 親の地理情報(マスク・寸法)
  ! 作業配列 wr の第 1 添字: 1 h(比 1)/h の平均, 2 η の平均, 3 m, 4 n, 5 u, 6 v, 7 vv, 8 書込み印
  integer, parameter :: w_h = 1, w_e = 2, w_m = 3, w_n = 4, w_u = 5, w_v = 6, w_vv = 7, w_set = 8
  integer :: ip, jp, i1, j1, i2, j2, r, nw, ic, jc, nin, ipa, ipb, jpa, jpb, pjs, pje
  real :: hav, eav, mav, nav, hp
  real(8) :: dv, dva
  real(8), allocatable :: rowdv(:), rowdva(:)
  associate (n => nt%g(c))
    if (n%nest_fb == 0) return
    r = n%r
    ! 置換する親セルの範囲: 子の内部(帯を除く)に完全に含まれるブロック
    nin = (n%nb + r - 1) / r          ! 帯を含む親セル数(切り上げ)
    ipa = n%pi1 + nin
    ipb = n%pi2 - nin
    jpa = n%pj1 + nin
    jpb = n%pj2 - nin
    if (ipa > ipb .or. jpa > jpb) return
    n%wr = 0.0
    ! --- 子側: 自分の帯にあるブロックを平均する(1 ブロック = 1 ランク。整列による)---
    do jp = jpa, jpb
      j1 = (jp - n%j0) * r + 1
      j2 = j1 + r - 1
      if (j1 < n%js .or. j2 > n%je) cycle
      do ip = ipa, ipb
        i1 = (ip - n%i0) * r + 1
        i2 = i1 + r - 1
        n%wr(w_set, ip, jp) = 1.0
        if (r == 1) then                        ! 比 1 は複写
          n%wr(w_h,  ip, jp) = sc%h(i1, j1)
          n%wr(w_m,  ip, jp) = sc%m(i1, j1)
          n%wr(w_n,  ip, jp) = sc%n(i1, j1)
          n%wr(w_u,  ip, jp) = sc%u(i1, j1)
          n%wr(w_v,  ip, jp) = sc%v(i1, j1)
          n%wr(w_vv, ip, jp) = sc%vv(i1, j1)
          cycle
        end if
        nw = 0
        do jc = j1, j2
          do ic = i1, i2
            if (n%nest_fb == 2 .and. sc%h(ic, jc) <= n%dd) cycle   ! 湿潤判定付き: 乾きは除く
            n%wr(w_h, ip, jp) = n%wr(w_h, ip, jp) + sc%h(ic, jc)
            n%wr(w_e, ip, jp) = n%wr(w_e, ip, jp) + sc%h(ic, jc) + sc%z(ic, jc)
            n%wr(w_m, ip, jp) = n%wr(w_m, ip, jp) + sc%m(ic, jc)
            n%wr(w_n, ip, jp) = n%wr(w_n, ip, jp) + sc%n(ic, jc)
            nw = nw + 1
          end do
        end do
        if (nw > 0) n%wr(w_h:w_n, ip, jp) = n%wr(w_h:w_n, ip, jp) / real(nw)
        n%wr(w_u, ip, jp) = real(nw)            ! 湿潤セル数(親側の判定に使う)
      end do
    end do
    if (nproc > 1) call share(n%wr, size(n%wr))
    ! --- 親側: 自分の帯の行を書き換える(親の z は親側で読む)---
    pjs = nt%g(n%parent)%js
    pje = nt%g(n%parent)%je
    allocate(rowdv(pjs:pje), source = 0.0d0)
    allocate(rowdva(pjs:pje), source = 0.0d0)
    do jp = max(jpa, pjs), min(jpb, pje)
      do ip = ipa, ipb
        if (n%wr(w_set, ip, jp) == 0.0) cycle
        if (gp%x(ip, jp) <= 0) cycle
        if (r == 1) then
          hp = n%wr(w_h, ip, jp)
          mav = n%wr(w_m, ip, jp); nav = n%wr(w_n, ip, jp)
          sp%u(ip, jp) = n%wr(w_u, ip, jp); sp%v(ip, jp) = n%wr(w_v, ip, jp); sp%vv(ip, jp) = n%wr(w_vv, ip, jp)
        else
          nw = nint(n%wr(w_u, ip, jp))
          hav = n%wr(w_h, ip, jp); eav = n%wr(w_e, ip, jp); mav = n%wr(w_m, ip, jp); nav = n%wr(w_n, ip, jp)
          if (nw == 0) then
            hp = 0.0; mav = 0.0; nav = 0.0                    ! 湿潤セルなし → 親は乾き
          else if (n%nest_fb == 1) then
            hp = hav                                          ! 面積平均(体積厳密)
          else
            hp = min(hav, max(eav - sp%z(ip, jp), 0.0))       ! 湿潤判定付き(GeoClaw 型)
            if (hav > 0.0) then
              mav = mav * (hp / hav); nav = nav * (hp / hav)
            end if
          end if
          if (hp > n%dd) then
            sp%u(ip, jp) = mav / hp; sp%v(ip, jp) = nav / hp
            sp%vv(ip, jp) = sqrt(sp%u(ip, jp)**2 + sp%v(ip, jp)**2)
          else
            mav = 0.0; nav = 0.0
            sp%u(ip, jp) = 0.0; sp%v(ip, jp) = 0.0; sp%vv(ip, jp) = 0.0
          end if
        end if
        dv = real(hp, 8) - real(sp%h(ip, jp), 8)
        rowdv(jp) = rowdv(jp) + dv
        rowdva(jp) = rowdva(jp) + abs(dv)
        sp%h(ip, jp) = hp
        sp%m(ip, jp) = mav
        sp%n(ip, jp) = nav
        sp%e(ip, jp) = sp%z(ip, jp) + sp%h(ip, jp)
      end do
    end do
    ! 統計(行和 → 決定的総和。par_sum_rows は親を select した状態で呼ばれる前提)
    call par_sum_rows(rowdv, dv)
    call par_sum_rows(rowdva, dva)
    n%n_restrict = n%n_restrict + 1
    n%dvol_sum = n%dvol_sum + dv * real(gp%dx, 8) * real(gp%dy, 8)
    n%dvol_abs = n%dvol_abs + dva * real(gp%dx, 8) * real(gp%dy, 8)
  end associate
end subroutine

!----------------------------------------------------------------------
! ネスト系の要約を画面に出す(finalize 時。Log.txt の列は変えない)
!----------------------------------------------------------------------
subroutine nest_summary(nt)
  type(t_nest), intent(in) :: nt
  integer :: k
  character(len=256) :: msg
  if (nt%ng <= 1) return
  call par_info("nest: summary")
  do k = 2, nt%ng
    associate (n => nt%g(k))
      if (n%nest_fb == 0) then
        write(msg, '(a,i0,a,i0,a)') "nest:   grid ", k, " <- parent ", n%parent, ": one-way (no feedback)"
      else
        write(msg, '(a,i0,a,i0,a,a,a,i0,a,es12.4,a,es12.4,a)') "nest:   grid ", k, " -> parent ", n%parent, &
              ": ", trim(fb_name(n%nest_fb)), ", ", n%n_restrict, " replacements, volume change sum = ", &
              n%dvol_sum, " m3, |sum| = ", n%dvol_abs, " m3"
      end if
      call par_info(trim(msg))
    end associate
  end do
end subroutine

subroutine nest_dispose(nt)
  type(t_nest), intent(inout) :: nt
  if (allocated(nt%g)) deallocate(nt%g)
  nt%ng = 1
  nt%root = 1
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

function fb_name(fb) result(name)
  integer, intent(in) :: fb
  character(len=40) :: name
  select case (fb)
  case (0); name = "one-way"
  case (1); name = "two-way (area average)"
  case (2); name = "two-way (wet-aware average)"
  case default; name = "two-way (?)"
  end select
end function

logical function is_blank(line)
  character(len=*), intent(in) :: line
  character(len=len(line)) :: t
  t = adjustl(line)
  is_blank = (len_trim(t) == 0)
  if (.not. is_blank) is_blank = (t(1:1) == '#' .or. t(1:1) == '!')
end function

!----------------------------------------------------------------------
! 窓の写しを全ランクで共有する(1 要素 1 寄与のゼロ初期化配列の総和。
! 配列は任意形状なので連番の作業配列を介す)
!----------------------------------------------------------------------
subroutine share(a, nelem)
  integer, intent(in) :: nelem
  real, intent(inout) :: a(nelem)      ! 並び結合(連続配列の全要素)
  call par_allreduce_sumr(a)
end subroutine

!----------------------------------------------------------------------
! 比 > 1 のセル量の補間(§3.5): 親セル中心の格子で双線形。親の 2×2 が
! 全て湿っていれば η を補間して h = max(η − z_子, 0)、u, v, m, n, vv も
! 双線形。親に乾きがあれば子セルは乾き(h = 0、速度・流量 0)
!----------------------------------------------------------------------
subroutine interp_cell(n, i, j, s)
  type(t_nest_grid), intent(in) :: n
  integer, intent(in) :: i, j
  type(t_state), intent(inout) :: s
  real :: xc, yc, wx, wy, eta, hmin
  integer :: ia, ja
  real :: w(2,2)
  ! 子セル中心の親セル座標(親セル ip の中心を ip - 0.5 とする連続座標)
  xc = real(n%i0 - 1) + (real(i) - 0.5) / real(n%r)
  yc = real(n%j0 - 1) + (real(j) - 0.5) / real(n%r)
  ia = floor(xc + 0.5)        ! 中心が xc 以下で最大の親セル
  ja = floor(yc + 0.5)
  wx = xc - (real(ia) - 0.5)
  wy = yc - (real(ja) - 0.5)
  w(1,1) = (1.0 - wx) * (1.0 - wy)
  w(2,1) = wx * (1.0 - wy)
  w(1,2) = (1.0 - wx) * wy
  w(2,2) = wx * wy
  hmin = min(n%wc(q_h, ia, ja), n%wc(q_h, ia+1, ja), n%wc(q_h, ia, ja+1), n%wc(q_h, ia+1, ja+1))
  if (hmin > n%dd) then
    eta = bil(q_e)
    s%h(i, j) = max(eta - s%z(i, j), 0.0)
    if (s%h(i, j) > 0.0) then
      s%u(i, j)  = bil(q_u)
      s%v(i, j)  = bil(q_v)
      s%vv(i, j) = bil(q_vv)
      s%m(i, j)  = bil(q_m)
      s%n(i, j)  = bil(q_n)
    else
      s%u(i, j) = 0.0; s%v(i, j) = 0.0; s%vv(i, j) = 0.0; s%m(i, j) = 0.0; s%n(i, j) = 0.0
    end if
  else
    s%h(i, j) = 0.0
    s%u(i, j) = 0.0; s%v(i, j) = 0.0; s%vv(i, j) = 0.0; s%m(i, j) = 0.0; s%n(i, j) = 0.0
  end if
  s%e(i, j) = s%z(i, j) + s%h(i, j)
contains
  real function bil(q)
    integer, intent(in) :: q
    bil = w(1,1) * n%wc(q, ia, ja) + w(2,1) * n%wc(q, ia+1, ja) + &
          w(1,2) * n%wc(q, ia, ja+1) + w(2,2) * n%wc(q, ia+1, ja+1)
  end function
end subroutine

!----------------------------------------------------------------------
! 比 > 1 のエッジ量の補間: 同方位 kk の親エッジの中点格子で双線形
!   子スロット (kk, ie, je) の所有セル (ic, jc) の中心 + 0.5·(din, djn) が
!   エッジの中点。親の同方位スロットの中点は親セル中心 + 0.5·(din, djn)
!   なので、中点格子は親セル中心格子を半セル平行移動したもの
!----------------------------------------------------------------------
subroutine interp_edge(n, kk, ie, je, val)
  type(t_nest_grid), intent(in) :: n
  integer, intent(in) :: kk, ie, je
  real, intent(out) :: val(2)
  integer :: ic, jc, ia, ja, q
  real :: xm, ym, ox, oy, wx, wy
  ic = ie - die(kk)
  jc = je - dje(kk)
  ox = 0.5 * real(din(kk))
  oy = 0.5 * real(djn(kk))
  ! 子エッジ中点の親座標
  xm = real(n%i0 - 1) + (real(ic) - 0.5 + ox) / real(n%r)
  ym = real(n%j0 - 1) + (real(jc) - 0.5 + oy) / real(n%r)
  ! 親の同方位スロット(所有セル ia)の中点 = ia - 0.5 + ox
  ia = floor(xm - ox + 0.5)
  ja = floor(ym - oy + 0.5)
  wx = xm - (real(ia) - 0.5 + ox)
  wy = ym - (real(ja) - 0.5 + oy)
  do q = 1, 2
    val(q) = (1.0 - wx) * (1.0 - wy) * pe(ia,   ja)   + wx * (1.0 - wy) * pe(ia+1, ja) + &
             (1.0 - wx) * wy         * pe(ia,   ja+1) + wx * wy         * pe(ia+1, ja+1)
  end do
contains
  real function pe(ip, jp)
    integer, intent(in) :: ip, jp
    pe = n%we(q, kk, ip + die(kk), jp + dje(kk))
  end function
end subroutine

end module
