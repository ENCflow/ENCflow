!======================================================================
! 規定底面運動(fn_bedmotion。断層津波などの地盤変位の時刻歴で s%z を強制)
!   設計の正本は docs/bedmotion_plan.md、規約の記録は developer.md §70。
!
!   【入力】スナップショット表(fn_bmlist): 1 行に「時刻 ファイル名 [i1 j1 ni nj]」。
!   時刻は t0 からの相対(単位 bm_tscale 秒)、昇順。ファイルは累積変位 d [m]
!   (初期地形からの変位。z と同じ形式・同じ行順)。4 整数を省略すると全域
!   (nx, ny)、与えると全域格子の列 i1.. i1+ni−1・行 j1.. j1+nj−1 の窓だけを
!   持つ ni × nj の行列で、窓の外は 0(広域の計算で変位がゼロでない矩形だけを
!   書く。utils/fault2disp の f_window)。本体は適用ループを全窓の和集合に
!   限定する。表の最初の時刻より前は先頭の値、最後より後は末尾の値を保持する。
!
!   【適用の契約】ステップ頭(API の extz と同じ位置 = swflow の前)で、
!   そのステップ末尾の時刻 t^{n+1} の変位 d を時間補間し、前回適用した
!   d_prev との差分 Δd を陸セル(x > 0, sw = 0)の z に加える。h は変えず
!   e = z + h を回復し、z のハロを交換する(geomorph・extz と同じ契約)。
!   増分適用なので geomorph・lavaflow・bedslide と同じランで z を動かして
!   も衝突しない。sd は変えない(岩盤面 z − sd が変位する)。
!   運動量(u, v, m, n)は触らない。
!
!   【時刻歴の持ち方】帯形状の 3 枚(da: 直前のスナップショット、db: 次、
!   dprev: 適用済み)。各ランクが全域を冗長に読んで自帯を切り出す
!   (m_precip の分布リストと同じ。developer.md §11。scatter も collective
!   判定の追加もない)。段階: 0 = 最初の時刻より前(先頭の値を 1 回だけ
!   適用し以後は何もしない)、1 = 変位中(毎ステップ補間・適用・ハロ交換)、
!   2 = 末尾の値を適用済み(以後ゼロコスト)。
!
!   【restart】私有状態を save しない。フレッシュランは d_prev = 0、restore
!   (s%it0 > 0)は d_prev = d(t_r)(save の z は t_r までの変位を含む)。
!   補間が時刻だけの関数なので中断なしランと同じ増分列になる。
!
!   【無効時】配列未確保、calc は logical 1 つで return(ゼロ追加)。
!   【API との排他】fn_bedmotion 有効時は m_main_set_value('z') を拒否する
!   (生産者は変数ごとに一人)。
!======================================================================
module m_bedmotion
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_bedmotion, only : t_list_bedmotion, list_bedmotion_read
  use m_fileio, only : fileio_read_matrix
  use m_parallel, only : dcp, par_info, par_stop, par_halo_cell, par_allreduce_max
  use m_util, only : itoa, rtoa
  implicit none
  private
  public :: t_bedmotion, m_bedmotion_init, m_bedmotion_calc, m_bedmotion_dispose

  integer, parameter :: maxpathlen = 256

  type t_bedmotion
    logical :: enabled = .false.
    integer :: nsnap = 0                    ! スナップショット数
    integer :: f_interp = 1                 ! 1: 線形、0: 階段
    integer :: ia = 0                       ! da のスナップショット番号(db は min(ia+1, nsnap))
    integer :: stage = 0                    ! 0: 未適用(フレッシュランの開始)、1: 変位中、
                                            ! 2: 完了(末尾の値を適用済み。以後ゼロコスト)、
                                            ! 3: 最初の時刻まで待ち(先頭の値は適用済み)
    real, allocatable :: tsnap(:)           ! スナップショットの時刻 (s。絶対 = t0 + 表 × bm_tscale)
    character(len=maxpathlen), allocatable :: fsnap(:)  ! ファイル名(dir_data 相対)
    integer, allocatable :: win(:,:)        ! 窓 (4, nsnap): i1, j1, ni, nj(i1 = 0 は全域)
    integer :: iw1 = 1, iw2 = 0, jw1 = 1, jw2 = 0  ! 全スナップショットの窓の和集合(全域格子)
    real, allocatable :: da(:,:), db(:,:)   ! 直前・次のスナップショット (1:nx, jsh:jeh)
    real, allocatable :: dprev(:,:)         ! 適用済みの変位 (1:nx, jsh:jeh)
    integer :: nload = 0                    ! 読み込んだスナップショット数(統計)
    integer :: napply = 0                   ! 変位を適用したステップ数(統計)
  end type

contains

!----------------------------------------------------------------------
! 初期化: 表の読み込み・検証、現在時刻を挟むスナップショットの読み込み、
!   d_prev の設定(フレッシュラン 0 / restore は d(t_r))
!----------------------------------------------------------------------
subroutine m_bedmotion_init(bm, p, g, s)
  type(t_bedmotion), intent(out) :: bm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_list_bedmotion) :: list
  character(:), allocatable :: fname
  character(len=1024) :: line
  integer :: un, ios, n, k, ip, iq
  real :: tcur, tk
  character(len=1024) :: rest

  if (len_trim(p%fn_bedmotion) == 0) return

  call list_bedmotion_read(p, list)
  if (list%f_bedmotion == 0) return         ! fn を書いたまま一時無効化する経路

  if (p%f_gridsystem /= 0) then
    call par_stop("list_bedmotion: bed motion (fn_bedmotion) is not supported with STG (f_gridsystem=1)")
  end if
  if (len_trim(list%fn_bmlist) == 0) call par_stop("list_bedmotion: fn_bmlist is required")
  if (list%f_bminterp /= 0 .and. list%f_bminterp /= 1) call par_stop("list_bedmotion: f_bminterp must be 0 or 1")
  if (list%bm_tscale <= 0.0) call par_stop("list_bedmotion: bm_tscale must be > 0")
  bm%f_interp = list%f_bminterp

  ! --- スナップショット表(空行・# ! 行は無視) ---
  fname = trim(p%dir_data)//"/"//trim(list%fn_bmlist)
  call par_info("bedmotion: reading snapshot list "//trim(fname))
  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_bedmotion: cannot open "//trim(fname))
  n = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (is_blank(line)) cycle
    n = n + 1
  end do
  if (n < 1) call par_stop("list_bedmotion: snapshot list is empty: "//trim(fname))
  allocate(bm%tsnap(n), bm%fsnap(n), bm%win(4, n))
  bm%win = 0
  bm%iw1 = g%nx + 1; bm%iw2 = 0; bm%jw1 = g%ny + 1; bm%jw2 = 0
  rewind(un)
  k = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (is_blank(line)) cycle
    k = k + 1
    ! 「時刻 ファイル名」。ファイル名に '/' を含むので list-directed では読めない
    ! (スラッシュが入力終端)。先頭の語を時刻、残りをファイル名として切る
    line = adjustl(line)
    do ip = 1, len_trim(line)
      if (line(ip:ip) == char(9)) line(ip:ip) = ' '
    end do
    ip = index(line, ' ')
    ios = 1
    if (ip > 1) read(line(1:ip-1), *, iostat=ios) tk
    if (ios /= 0) call par_stop("list_bedmotion: cannot parse line "//itoa(k)//" of "//trim(fname)//": "//trim(line))
    rest = adjustl(line(ip+1:))
    if (len_trim(rest) == 0) call par_stop("list_bedmotion: missing file name on line "//itoa(k)//" of "//trim(fname))
    iq = index(rest, ' ')
    bm%fsnap(k) = rest(1:iq-1)
    rest = adjustl(rest(iq+1:))
    if (len_trim(rest) > 0) then
      ! 窓 i1 j1 ni nj(全域格子の列・行。1 始まり)
      read(rest, *, iostat=ios) bm%win(1:4, k)
      if (ios /= 0) call par_stop("list_bedmotion: window must be 4 integers (i1 j1 ni nj) on line "// &
                                  itoa(k)//" of "//trim(fname))
      if (bm%win(1,k) < 1 .or. bm%win(2,k) < 1 .or. bm%win(3,k) < 1 .or. bm%win(4,k) < 1 .or. &
          bm%win(1,k) + bm%win(3,k) - 1 > g%nx .or. bm%win(2,k) + bm%win(4,k) - 1 > g%ny) then
        call par_stop("list_bedmotion: window outside the grid on line "//itoa(k)//" of "//trim(fname))
      end if
      bm%iw1 = min(bm%iw1, bm%win(1,k)); bm%iw2 = max(bm%iw2, bm%win(1,k) + bm%win(3,k) - 1)
      bm%jw1 = min(bm%jw1, bm%win(2,k)); bm%jw2 = max(bm%jw2, bm%win(2,k) + bm%win(4,k) - 1)
    else
      bm%iw1 = 1; bm%iw2 = g%nx; bm%jw1 = 1; bm%jw2 = g%ny
    end if
    bm%tsnap(k) = p%t0 + tk * list%bm_tscale
    if (k > 1) then
      if (bm%tsnap(k) <= bm%tsnap(k-1)) call par_stop("list_bedmotion: snapshot times must increase (line "//itoa(k)//")")
    end if
  end do
  close(un)
  bm%nsnap = n

  ! --- 帯形状の確保と、現在時刻を挟むスナップショットの読み込み ---
  allocate(bm%da(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(bm%db(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(bm%dprev(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  tcur = p%t0 + p%dt * s%it0                ! restore 時は復元時刻(init 時点で有効なのは it0。
                                            !   s%it は時間ループが設定する)
  bm%ia = 1
  do k = 1, n - 1
    if (tcur >= bm%tsnap(k+1)) bm%ia = k + 1
  end do
  call load_snapshot(bm, p, g, bm%ia, bm%da)
  if (bm%ia < n) then
    call load_snapshot(bm, p, g, bm%ia + 1, bm%db)
  else
    bm%db = bm%da
  end if
  ! d_prev: フレッシュランは 0(まだ何も適用していない → 段階 0)、
  !   restore は d(t_r)(save の z は t_r までの変位を含む)
  if (s%it0 > 0) then
    call interp(bm, tcur, bm%dprev)
    if (tcur < bm%tsnap(1)) then
      bm%stage = 3
    else if (bm%ia == n) then
      bm%stage = 2
    else
      bm%stage = 1
    end if
  else
    bm%dprev = 0.0
    bm%stage = 0
  end if

  bm%enabled = .true.
  call par_info("bedmotion enabled: "//itoa(n)//" snapshot(s), t = "//trim(rtoa(bm%tsnap(1)))//" .. "// &
                trim(rtoa(bm%tsnap(n)))//" s, interpolation = "//merge("linear", "step  ", bm%f_interp == 1))
  if (bm%iw1 > 1 .or. bm%iw2 < g%nx .or. bm%jw1 > 1 .or. bm%jw2 < g%ny) then
    call par_info("  window of the displacement (union): columns "//itoa(bm%iw1)//".."//itoa(bm%iw2)// &
                  ", rows "//itoa(bm%jw1)//".."//itoa(bm%jw2))
  end if

contains

  logical function is_blank(str)
    character(len=*), intent(in) :: str
    character(len=len(str)) :: w
    w = adjustl(str)
    is_blank = (len_trim(w) == 0)
    if (.not. is_blank) is_blank = (w(1:1) == '#' .or. w(1:1) == '!')
  end function

end subroutine


!----------------------------------------------------------------------
! スナップショット k を全域で読み(各ランク冗長)、帯に切り出す
!----------------------------------------------------------------------
subroutine load_snapshot(bm, p, g, k, d)
  type(t_bedmotion), intent(inout) :: bm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: k
  real, intent(out) :: d(1:, dcp%jsh:)
  real, allocatable :: wk(:,:)
  integer :: j, i1, j1, ni, nj
  if (bm%win(1,k) == 0) then
    allocate(wk(1:g%nx, 1:g%ny))
    call fileio_read_matrix(trim(p%dir_data)//"/"//trim(bm%fsnap(k)), g%nx, g%ny, wk, p%f_input_mode)
    do j = dcp%jsh, dcp%jeh
      d(:,j) = wk(1:g%nx, j)
    end do
  else
    ! 窓だけのファイル: 外は 0。帯に掛かる行だけ写す
    i1 = bm%win(1,k); j1 = bm%win(2,k); ni = bm%win(3,k); nj = bm%win(4,k)
    allocate(wk(1:ni, 1:nj))
    call fileio_read_matrix(trim(p%dir_data)//"/"//trim(bm%fsnap(k)), ni, nj, wk, p%f_input_mode)
    do j = dcp%jsh, dcp%jeh
      d(:,j) = 0.0
      if (j >= j1 .and. j <= j1 + nj - 1) d(i1:i1+ni-1, j) = wk(1:ni, j - j1 + 1)
    end do
  end if
  bm%nload = bm%nload + 1
end subroutine


!----------------------------------------------------------------------
! 時刻 t の変位(da, db の補間。範囲外は端の値)
!----------------------------------------------------------------------
subroutine interp(bm, t, d)
  type(t_bedmotion), intent(in) :: bm
  real, intent(in) :: t
  real, intent(out) :: d(1:, dcp%jsh:)
  real :: w
  integer :: j
  if (bm%ia >= bm%nsnap .or. t <= bm%tsnap(bm%ia) .or. bm%f_interp == 0) then
    do j = dcp%jsh, dcp%jeh
      d(:,j) = bm%da(:,j)
    end do
    return
  end if
  w = (t - bm%tsnap(bm%ia)) / (bm%tsnap(bm%ia+1) - bm%tsnap(bm%ia))
  w = max(0.0, min(1.0, w))
  do j = dcp%jsh, dcp%jeh
    d(:,j) = bm%da(:,j) + w * (bm%db(:,j) - bm%da(:,j))
  end do
end subroutine


!----------------------------------------------------------------------
! ステップ頭: t^{n+1} = t0 + dt·it の変位を補間し、増分を z に適用する
!----------------------------------------------------------------------
subroutine m_bedmotion_calc(bm, p, g, s, it)
  type(t_bedmotion), intent(inout) :: bm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real, allocatable :: d(:,:)
  real :: t, dd
  integer :: i, j
  logical :: last

  if (.not. bm%enabled) return
  if (bm%stage == 2) return
  t = p%t0 + p%dt * it
  if (bm%stage == 3) then
    if (t < bm%tsnap(1)) return           ! 先頭の値は適用済み。最初の時刻まで待つ
    bm%stage = 1
  end if

  ! スナップショットの進行(判定は時刻だけ = 全ランク同一)
  do while (bm%ia < bm%nsnap)
    if (t <= bm%tsnap(bm%ia+1)) exit
    bm%ia = bm%ia + 1
    bm%da = bm%db
    if (bm%ia < bm%nsnap) then
      call load_snapshot(bm, p, g, bm%ia + 1, bm%db)
    end if
  end do
  last = (bm%ia == bm%nsnap)              ! 末尾の値(範囲外は端の値を保持)

  allocate(d(1:g%nx, dcp%jsh:dcp%jeh))
  call interp(bm, t, d)

  ! 適用は窓の和集合(全域なら帯全体)に限定する
  !$omp parallel do private(i, j, dd)
  do j = max(dcp%js, bm%jw1), min(dcp%je, bm%jw2)
    do i = max(g%wx(1,j), bm%iw1), min(g%wx(2,j), bm%iw2)
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
      dd = d(i,j) - bm%dprev(i,j)
      if (dd /= 0.0) s%z(i,j) = s%z(i,j) + dd
      bm%dprev(i,j) = d(i,j)
    end do
  end do
  !$omp end parallel do
  ! e の整合回復(extz・geomorph と同じ範囲 = x > 0 のセル。窓の外は z が変わらない)
  !$omp parallel do private(i, j)
  do j = max(dcp%js, bm%jw1), min(dcp%je, bm%jw2)
    do i = max(g%wx(1,j), bm%iw1), min(g%wx(2,j), bm%iw2)
      if (g%x(i,j) <= 0) cycle
      s%e(i,j) = s%z(i,j) + s%h(i,j)
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(s%z)
  bm%napply = bm%napply + 1

  ! 段階の更新: 末尾の値を適用したら完了(以後ゼロコスト)。最初の時刻より
  !   前なら先頭の値を適用した状態で待つ
  if (last) then
    bm%stage = 2
  else if (t < bm%tsnap(1)) then
    bm%stage = 3
  else
    bm%stage = 1
  end if
end subroutine


!----------------------------------------------------------------------
! 破棄: 適用した変位の最大・最小(全ランク)を報告し、配列を解放する
!----------------------------------------------------------------------
subroutine m_bedmotion_dispose(bm, g)
  type(t_bedmotion), intent(inout) :: bm
  type(t_geoinfo), intent(in) :: g
  real :: v(2)
  integer :: i, j
  if (.not. bm%enabled) return
  v = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
      v(1) = max(v(1), bm%dprev(i,j))
      v(2) = max(v(2), -bm%dprev(i,j))
    end do
  end do
  call par_allreduce_max(v)
  call par_info("bedmotion: applied displacement max "//trim(rtoa(v(1)))//" m, min "//trim(rtoa(-v(2)))// &
                " m, snapshots read "//itoa(bm%nload)//", steps applied "//itoa(bm%napply))
  deallocate(bm%tsnap, bm%fsnap, bm%win, bm%da, bm%db, bm%dprev)
  bm%enabled = .false.
end subroutine

end module
