module m_evap
  ! ==================== 蒸発散プロセスモジュール(§27) ====================
  ! 気温(または直接指定)から可能蒸発散量 PET を暦日ごとに評価し、
  ! 毎ステップ、各セルの貯留から優先順位付きで減算する加算的プロセス。
  !   有効化: fn_evap の指定(&list_evap。f_evmodel=0 で一時無効化)
  !   PET:    1=一定速度, 2=月別気候値, 3=Hamon, 4=Thornthwaite(排他切替。
  !           式の追加は pet_mmday に case を足す)
  !   気温:   一様定数 / 一様時系列(経過日, ℃)/ 分布時系列(ファイルリスト)。
  !           オプションで標高減率(一様入力のみ。基準標高の既定=領域最低標高)
  !   評価粒度: 暦日平均の思想で「日の先頭の気温」から1日1回更新、日内一定。
  !           気温式は本来日平均気温の式のため、日平均系列(日単位の点)を
  !           推奨する(疎な系列も線形補間・端値保持で機能する)
  !   減算:   樹冠保水(貯留型遮断の draw 口)→ 地表水 h → ため池 hrs →
  !           地下水 hg の順に「あるだけ引く」(供給制限のみ。乾燥抑制なし)。
  !           ダムは dam_area(湛水面積)指定時、貯水量から E×面積 を
  !           比例配分で引き、捕捉帯セルの個別蒸発は止める(二重計上防止)。
  !           未指定ダムの捕捉帯はため池と同様セル面積分。
  !   時刻:   暦は date0_c(シミュレーション時刻 t=0 の暦)を原点とする
  !           純関数。履歴状態なし = save/restore 対象外(復元後は現在時刻の
  !           暦日で再評価される)。診断 CSV(evap.csv)の累積量のみ
  !           ラン先頭からの積算(restore でリセット。§27)
  !   MPI:    PET は (t, z) の純関数で全ランク同値。分布気温は帯 scatter。
  !           ダムの貯水量集計は par_sum_rows(決定的)、代表セル値の共有は
  !           単一寄与の allreduce(総和順によらず厳密)
  ! ========================================================================
  use iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary, e_struct_dam, interp_series
  use m_intercept, only : t_intercept
  use list_evap, only : t_list_evap, list_evap_read, nevmax
  use m_fileio, only : fileio_read_matrix
  use m_parallel, only : dcp, is_root, par_info, par_stop, par_abort, &
                         par_allreduce_min, par_allreduce_sumr, par_sum_rows, &
                         par_scatter_cell
  use m_util, only : str2sec, itoa
  implicit none
  private
  public :: t_evap
  public :: m_evap_init
  public :: m_evap_calc
  public :: m_evap_record
  public :: m_evap_dispose

  real, parameter :: pi = acos(-1.0)
  real, parameter :: secday = 86400.0            ! 1日の秒数
  real, parameter :: mmday2ms = 1.0e-3 / 86400.0 ! mm/day -> m/s

  ! 気温入力の種別
  integer, parameter :: e_tsrc_const = 1, e_tsrc_series = 2, e_tsrc_map = 3

  ! ダム湛水面積蒸発の管理(§27)
  type t_evdam
    integer :: ist = 0       ! b%struct のインデックス
    real :: area = 0.0       ! 湛水面積 (m2)
    real :: zrep = 0.0       ! 代表セル(捕捉帯先頭)の標高(減率評価用)
    real :: trep = 0.0       ! 代表セルの気温(分布時系列時に更新)
    real :: petd = 0.0       ! 現在日の PET (m/s)
    integer :: nc = 0        ! 自帯内の捕捉帯セル数
    integer, allocatable :: cells(:,:)   ! 自帯内の捕捉帯セル (1:2, 1:nc)
  end type

  type t_evap
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    integer :: model = 0           ! f_evmodel
    real :: kc = 1.0
    real :: pet0 = 0.0             ! モード1: PET (mm/day)
    real :: pmon(1:12) = 0.0       ! モード2: 月別 PET (mm/day)
    integer :: jdn0 = 0            ! t=0 の日のユリウス通日
    real :: sec0 = 0.0             ! t=0 の日内秒
    real :: latrad = 0.0           ! 緯度 (rad)
    real :: tw_i = 0.0             ! Thornthwaite 熱指数 I
    real :: tw_a = 0.0             ! Thornthwaite 指数 a
    integer :: tsrc = 0            ! 気温入力の種別 (e_tsrc_*)
    real :: t0c = 0.0              ! 一様定数気温 (℃)
    integer :: ntser = 0
    real, allocatable :: tser(:,:) ! 一様時系列 (1:2,1:ntser) = (s, ℃)
    integer :: nmap = 0
    character(len=1024), allocatable :: mapfiles(:)  ! 分布ファイル名(dir_data 込み)
    real :: dtmap = 86400.0        ! 分布の時間間隔 (s)
    integer :: imap = -1           ! 読み込み済みファイル番号(1-based。-1=未読)
    real, allocatable :: tmap(:,:) ! 現在の気温分布 (℃)(帯)
    logical :: lapse = .false.
    real :: gam = 0.0              ! 気温減率 (℃/m)
    real :: zref = 0.0             ! 減率の基準標高 (m)
    integer :: curday = -2147483647  ! 現在の暦日番号(t=0 の日 = 0)
    real, allocatable :: pet(:,:)  ! 現在日の PET (m/s)(帯。kc 適用済み)
    real :: petref = 0.0           ! 基準値 PET (mm/day。CSV 診断用。分布時は領域平均気温で評価)
    integer :: ndam = 0
    type(t_evdam), allocatable :: dam(:)
    logical, allocatable :: skip(:,:)      ! 個別蒸発を止めるセル(dam_area 指定ダムの捕捉帯)
    real(real64), allocatable :: vrow(:,:) ! 累積蒸発体積の行部分和 (js:je, 1:4) (m3)
                                           !   1=樹冠, 2=地表水 h, 3=hrs, 4=地下水 hg
    real(real64) :: vdam = 0.0             ! ダム湛水面積蒸発の累積 (m3。全ランク同値)
    integer :: un = 0                      ! CSV 装置番号(rank0。open(newunit=) は負値。§22)
  end type

contains


!----------------------------------------------------------------------
! 蒸発散モジュールを初期化する
!   fn_evap 未指定 or f_evmodel=0 なら何もしない(enabled = .false.)。
!   検証はすべてここで行う(list_evap は読むだけ。§12)
!----------------------------------------------------------------------
subroutine m_evap_init(ev, p, g, b, s)
  type(t_evap), intent(out) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(in) :: s
  type(t_list_evap) :: list
  integer :: k, m, nsrc
  real :: zmin

  if (len_trim(p%fn_evap) == 0) return

  call list_evap_read(p, list)
  if (list%f_evmodel == 0) return    ! fn を書いたまま一時無効化する経路

  if (list%f_evmodel < 1 .or. list%f_evmodel > 4) then
    call par_stop("list_evap: f_evmodel は 0(無効), 1(一定), 2(月別), 3(Hamon), " &
                  //"4(Thornthwaite) のいずれかです: "//itoa(list%f_evmodel))
  end if
  ev%model = list%f_evmodel
  if (list%evap_kc <= 0.0) call par_stop("list_evap: evap_kc は正のみです")
  ev%kc = list%evap_kc

  ! --- 暦の原点(モード2〜4で必須) ---
  if (ev%model >= 2) then
    if (len_trim(list%date0_c) == 0) then
      call par_stop("list_evap: f_evmodel>=2 には date0_c(t=0 の暦。" &
                    //'"YYYY-MM-DD" または "YYYY-MM-DD hh:mm")が必要です')
    end if
    call parse_date0(trim(list%date0_c), ev%jdn0, ev%sec0)
  end if

  ! --- モード別の必須パラメータ ---
  select case (ev%model)
    case (1)
      if (list%evap0 < 0.0) call par_stop("list_evap: f_evmodel=1 には evap0 >= 0 " &
                                          //"(mm/day)が必要です")
      ev%pet0 = list%evap0
    case (2)
      do m = 1, 12
        if (list%evap_monthly(m) < 0.0) then
          call par_stop("list_evap: f_evmodel=2 には evap_monthly の12ヶ月分" &
                        //"(mm/day, 非負)が必要です")
        end if
      end do
      ev%pmon = list%evap_monthly
    case (3, 4)
      if (list%lat < -90.0 .or. list%lat > 90.0) then
        call par_stop("list_evap: f_evmodel>=3 には lat(-90〜90 deg)が必要です")
      end if
      ev%latrad = list%lat * pi / 180.0
  end select

  ! --- Thornthwaite の熱指数(平年月平均気温から) ---
  if (ev%model == 4) then
    ev%tw_i = 0.0
    do m = 1, 12
      if (list%temp_normal(m) <= -9998.0) then
        call par_stop("list_evap: f_evmodel=4 には temp_normal(月平均気温の平年値" &
                      //"12ヶ月分, ℃)が必要です")
      end if
      ev%tw_i = ev%tw_i + (max(list%temp_normal(m), 0.0) / 5.0)**1.514
    end do
    if (ev%tw_i <= 0.0) then
      call par_stop("list_evap: temp_normal が全月 0℃ 以下では Thornthwaite の" &
                    //"熱指数 I が 0 になります(f_evmodel=3 を使ってください)")
    end if
    ev%tw_a = ((6.75e-7 * ev%tw_i - 7.71e-5) * ev%tw_i + 1.792e-2) * ev%tw_i + 0.49239
  end if

  ! --- 気温入力(モード3,4。ちょうど1つを指定) ---
  if (ev%model >= 3) then
    nsrc = 0
    if (list%temp0 > -9998.0) then
      nsrc = nsrc + 1
      ev%tsrc = e_tsrc_const
      ev%t0c = list%temp0
    end if
    if (list%tempval(1,1) > -9998.0) then
      nsrc = nsrc + 1
      ev%tsrc = e_tsrc_series
      call setup_tseries(ev, list)
    end if
    if (len_trim(list%fn_tempmap) > 0) then
      nsrc = nsrc + 1
      ev%tsrc = e_tsrc_map
      call setup_tmaplist(ev, p, g, list)
    end if
    if (nsrc /= 1) then
      call par_stop("list_evap: 気温入力は temp0 / tempval / fn_tempmap の" &
                    //"いずれか1つを指定してください")
    end if

    ! --- 標高減率(一様入力のみ) ---
    if (list%f_temp_lapse > 0) then
      if (ev%tsrc == e_tsrc_map) then
        call par_stop("list_evap: f_temp_lapse は一様気温(temp0 / tempval)専用です" &
                      //"(分布気温には適用できません)")
      end if
      ev%lapse = .true.
      ev%gam = list%temp_lapse / 100.0            ! ℃/100m -> ℃/m
      if (list%temp_zref > -9998.0) then
        ev%zref = list%temp_zref
      else
        ! 既定 = 領域(使用セル)の最低標高。min は演算順によらず厳密 = 決定的
        zmin = huge(zmin)
        do k = dcp%js, dcp%je
          zmin = min(zmin, minval(s%z(g%wx(1,k):g%wx(2,k), k), &
                                  mask = g%x(g%wx(1,k):g%wx(2,k), k) > 0))
        end do
        call par_allreduce_min(zmin)
        ev%zref = zmin
      end if
    end if
  end if

  ! --- ダム湛水面積蒸発の登録と捕捉帯マスク(§27) ---
  call setup_dams(ev, g, b, s)

  ! --- 作業配列と診断 ---
  allocate(ev%pet(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(ev%vrow(dcp%js:dcp%je, 1:4), source = 0.0_real64)
  ev%vdam = 0.0_real64

  ! --- 診断 CSV(rank0。累積はラン先頭からの積算 = restore でリセット) ---
  if (is_root) then
    open(newunit=ev%un, file=trim(p%dir_result)//"/evap.csv", status='replace')
    write(ev%un, '(a)') "time_s,pet_ref_mmday,ev_canopy_m3,ev_surface_m3," &
                        //"ev_pond_m3,ev_gw_m3,ev_dam_m3,ev_total_m3"
  end if

  ev%enabled = .true.
  ev%initialized = .true.
  call par_info("evapotranspiration enabled (f_evmodel="//itoa(ev%model)//")")
end subroutine


!----------------------------------------------------------------------
! 一様気温時系列の変換(経過日 -> 秒。interp_series の規約に合わせる)
!----------------------------------------------------------------------
subroutine setup_tseries(ev, list)
  type(t_evap), intent(inout) :: ev
  type(t_list_evap), intent(in) :: list
  integer :: k, n
  n = 0
  do k = 1, nevmax
    if (list%tempval(1,k) <= -9998.0) exit     ! 番兵で終端
    n = n + 1
  end do
  if (n < 1) call par_stop("list_evap: tempval が空です")
  do k = 2, n
    if (list%tempval(1,k) <= list%tempval(1,k-1)) then
      call par_stop("list_evap: tempval の時刻(経過日)は単調増加で指定してください")
    end if
  end do
  allocate(ev%tser(1:2, 1:n))
  ev%tser(1,1:n) = list%tempval(1,1:n) * secday    ! 日 -> 秒
  ev%tser(2,1:n) = list%tempval(2,1:n)
  ev%ntser = n
end subroutine


!----------------------------------------------------------------------
! 気温分布ファイルリストの読み込み(1行1ファイル名。等間隔で順次適用、
! リストを過ぎたら最終ファイルを保持=端値保持)
!----------------------------------------------------------------------
subroutine setup_tmaplist(ev, p, g, list)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_evap), intent(in) :: list
  character(:), allocatable :: fname
  character(len=1024) :: line
  integer :: un, ios, n
  logical :: found

  ev%dtmap = str2sec(trim(list%dt_tempmap_c), "bad dt_tempmap_c in &list_evap")
  if (ev%dtmap <= 0.0) call par_stop("list_evap: dt_tempmap_c は正の時間です")

  fname = trim(p%dir_data)//"/"//trim(list%fn_tempmap)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_evap: fn_tempmap が見つかりません: "//fname)

  ! 1回目: 行数を数える / 2回目: 取り込む(全ランク冗長・同一)
  open(newunit=un, file=fname, status='old', action='read')
  n = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (len_trim(line) == 0) cycle
    n = n + 1
  end do
  if (n < 1) call par_stop("list_evap: fn_tempmap にファイル名がありません: "//fname)
  allocate(ev%mapfiles(1:n))
  rewind(un)
  n = 0
  do
    read(un, '(a)', iostat=ios) line
    if (ios /= 0) exit
    if (len_trim(line) == 0) cycle
    n = n + 1
    ev%mapfiles(n) = trim(p%dir_data)//"/"//trim(adjustl(line))
  end do
  close(un)
  ev%nmap = n

  allocate(ev%tmap(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
end subroutine


!----------------------------------------------------------------------
! ダム湛水面積蒸発の登録(dam_area = geom(9) > 0 のダム)。
!   捕捉帯の自帯内セル一覧・スキップマスク・代表セル標高(単一寄与の
!   allreduce = 総和順によらず厳密)を構築する
!----------------------------------------------------------------------
subroutine setup_dams(ev, g, b, s)
  type(t_evap), intent(inout) :: ev
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(in) :: s
  integer :: ist, n, k, i, j, nd

  nd = 0
  if (allocated(b%struct)) then
    do ist = 1, size(b%struct)
      if (b%struct(ist)%kind /= e_struct_dam) cycle
      if (b%struct(ist)%geom(9) <= 0.0) cycle
      nd = nd + 1
    end do
  end if
  ev%ndam = nd
  if (nd == 0) return

  allocate(ev%dam(1:nd))
  allocate(ev%skip(1:g%nx, dcp%jsh:dcp%jeh), source = .false.)
  nd = 0
  do ist = 1, size(b%struct)
    if (b%struct(ist)%kind /= e_struct_dam) cycle
    if (b%struct(ist)%geom(9) <= 0.0) cycle
    nd = nd + 1
    ev%dam(nd)%ist = ist
    ev%dam(nd)%area = b%struct(ist)%geom(9)
    ! 自帯内の捕捉帯セル一覧とスキップマスク
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j >= dcp%js .and. j <= dcp%je) n = n + 1
    end do
    ev%dam(nd)%nc = n
    allocate(ev%dam(nd)%cells(1:2, 1:max(n,1)), source = 0)
    n = 0
    do k = 1, b%struct(ist)%ncin
      i = b%struct(ist)%cin(1,k)
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      n = n + 1
      ev%dam(nd)%cells(1,n) = i
      ev%dam(nd)%cells(2,n) = j
      ev%skip(i,j) = .true.
    end do
    ! 代表セル(捕捉帯先頭)の標高: 所有ランクだけが寄与する allreduce
    ! (単一寄与の総和 = 順序によらず厳密)
    block
      real :: w1(1)
      w1(1) = 0.0
      j = b%struct(ist)%cin(2,1)
      if (j >= dcp%js .and. j <= dcp%je) then
        w1(1) = s%z(b%struct(ist)%cin(1,1), j)
      end if
      call par_allreduce_sumr(w1)
      ev%dam(nd)%zrep = w1(1)
    end block
  end do
end subroutine


!----------------------------------------------------------------------
! 蒸発散を適用する(毎ステップ。run_main が gwflow の後に呼ぶ。
! 無効時は no-op。冒頭の return 判定は全ランクで同一 = collective 安全)
!----------------------------------------------------------------------
subroutine m_evap_calc(ev, p, g, b, s, ic, it)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  type(t_intercept), intent(in) :: ic
  integer, intent(in) :: it
  integer :: i, j, day
  real :: dem, w
  real(real64) :: acell
  logical :: canopy

  if (it < 0 .or. allocated(b%struct)) continue  ! 引数未使用の警告を抑制
  if (.not. ev%enabled) return

  ! 暦日が変わったら PET を再評価(t=0 の暦日を 0 とする通し日)
  day = floor((s%t + ev%sec0) / secday)
  if (day /= ev%curday) call update_pet(ev, p, g, s, day)

  canopy = ic%enabled .and. associated(ic%draw)
  acell = real(g%dx, real64) * real(g%dy, real64)

  ! 優先順位付き減算: 樹冠保水 → 地表水 h → hrs → 地下水 hg(§27)。
  ! 体積診断の面積基底: 樹冠 = セル面積(pre と同基底)、h = af(σ・幅・
  ! 空隙を含む実効面積)、hrs / hg = gv 面積(それぞれの貯留の意味論)
  !$omp parallel do schedule(static) private(i, j, dem, w)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (ev%ndam > 0) then
        if (ev%skip(i,j)) cycle    ! dam_area 指定ダムの捕捉帯(湛水面で一括評価)
      end if
      dem = ev%pet(i,j) * p%dt
      if (dem <= 0.0) cycle
      ! (1) 樹冠保水(貯留型遮断モデルのみ。draw が状態を減じる)
      if (canopy) then
        w = ic%draw(i, j, dem)
        dem = dem - w
        ev%vrow(j,1) = ev%vrow(j,1) + real(w, real64) * acell
        if (dem <= 0.0) cycle
      end if
      ! (2) 地表水 h(σ 有効セルは dV = σ(h)dh の関係により、真水深から
      !     引くこと自体が現在の水面幅に比例した体積減で厳密。§26/§27)
      if (s%h(i,j) > 0.0) then
        w = min(s%h(i,j), dem)
        s%h(i,j) = s%h(i,j) - w
        s%e(i,j) = s%z(i,j) + s%h(i,j)
        dem = dem - w
        ev%vrow(j,2) = ev%vrow(j,2) + real(w, real64) * real(s%af(i,j), real64) * acell
        if (dem <= 0.0) cycle
      end if
      ! (3) ため池・非 dam_area ダム捕捉帯の貯留 hrs
      if (s%hrs(i,j) > 0.0) then
        w = min(s%hrs(i,j), dem)
        s%hrs(i,j) = s%hrs(i,j) - w
        dem = dem - w
        ev%vrow(j,3) = ev%vrow(j,3) + real(w, real64) * real(g%gv(i,j), real64) * acell
        if (dem <= 0.0) cycle
      end if
      ! (4) 地下水 hg(gwflow 無効時は 0 のまま = 何も起きない)
      if (s%hg(i,j) > 0.0) then
        w = min(s%hg(i,j), dem)
        s%hg(i,j) = s%hg(i,j) - w
        ev%vrow(j,4) = ev%vrow(j,4) + real(w, real64) * real(g%gv(i,j), real64) * acell
      end if
    end do
  end do
  !$omp end parallel do

  ! ダム湛水面積蒸発: 貯水量(捕捉帯 hrs の総和)から E×面積 を比例配分で
  ! 引く(dam_operate の引き落としと同じ決定的方式。§22/§27)
  if (ev%ndam > 0) call dam_evap(ev, p, g, s)

end subroutine


!----------------------------------------------------------------------
! ダム湛水面積蒸発(collective: 全ダムを全ランクが同順で処理すること)
!----------------------------------------------------------------------
subroutine dam_evap(ev, p, g, s)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: nd, k, i, j
  real(real64) :: rows(dcp%js:dcp%je), vtot, vdem, fac
  real(real64) :: acell

  acell = real(g%dx, real64) * real(g%dy, real64)
  do nd = 1, ev%ndam
    ! 現在貯水量(m3。決定的総和)
    rows(:) = 0.0_real64
    do k = 1, ev%dam(nd)%nc
      i = ev%dam(nd)%cells(1,k)
      j = ev%dam(nd)%cells(2,k)
      rows(j) = rows(j) + real(s%hrs(i,j), real64) * real(g%gv(i,j), real64) * acell
    end do
    call par_sum_rows(rows, vtot)
    if (vtot <= 0.0_real64) cycle
    vdem = real(ev%dam(nd)%petd, real64) * real(p%dt, real64) &
           * real(ev%dam(nd)%area, real64)
    vdem = min(vdem, vtot)
    if (vdem <= 0.0_real64) cycle
    fac = (vtot - vdem) / vtot        ! 全ランク同値(vtot・vdem とも同値)
    do k = 1, ev%dam(nd)%nc
      i = ev%dam(nd)%cells(1,k)
      j = ev%dam(nd)%cells(2,k)
      s%hrs(i,j) = s%hrs(i,j) * real(fac)
    end do
    ev%vdam = ev%vdam + vdem
  end do
end subroutine


!----------------------------------------------------------------------
! 暦日の PET 評価(日1回。全ランクが同一の day で呼ぶ = collective 安全)
!----------------------------------------------------------------------
subroutine update_pet(ev, p, g, s, day)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: day
  integer :: i, j, y, mo, d, doy, nd
  real :: tday, tb, pref, tsum, tnum
  real(real64) :: rows(dcp%js:dcp%je), rsum

  ev%curday = day
  tday = real(day) * secday - ev%sec0     ! この暦日の先頭のシミュレーション時刻

  ! 暦(モード2〜4)
  y = 0; mo = 1; d = 1; doy = 1
  if (ev%model >= 2) then
    call jdn_to_ymd(ev%jdn0 + day, y, mo, d)
    doy = (ev%jdn0 + day) - ymd_to_jdn(y, 1, 1) + 1
  end if

  select case (ev%model)
    case (1)
      pref = ev%pet0
      ev%pet(:,:) = pref * ev%kc * mmday2ms
    case (2)
      pref = ev%pmon(mo)
      ev%pet(:,:) = pref * ev%kc * mmday2ms
    case (3, 4)
      select case (ev%tsrc)
        case (e_tsrc_const, e_tsrc_series)
          if (ev%tsrc == e_tsrc_const) then
            tb = ev%t0c
          else
            tb = interp_series(ev%tser, ev%ntser, tday)
          end if
          if (ev%lapse) then
            ! T(i,j) = tb - γ(z - zref)。PET は (z) の純関数 = 全ランク同値
            !$omp parallel do schedule(static) private(i, j)
            do j = dcp%js, dcp%je
              do i = g%wx(1,j), g%wx(2,j)
                if (g%x(i,j) <= 0) cycle
                ev%pet(i,j) = pet_mmday(ev, tb - ev%gam * (s%z(i,j) - ev%zref), doy) &
                              * ev%kc * mmday2ms
              end do
            end do
            !$omp end parallel do
            pref = pet_mmday(ev, tb, doy)     ! 基準標高での値
          else
            pref = pet_mmday(ev, tb, doy)
            ev%pet(:,:) = pref * ev%kc * mmday2ms
          end if
          ! ダムの代表気温
          do nd = 1, ev%ndam
            if (ev%lapse) then
              ev%dam(nd)%trep = tb - ev%gam * (ev%dam(nd)%zrep - ev%zref)
            else
              ev%dam(nd)%trep = tb
            end if
          end do
        case (e_tsrc_map)
          call update_tmap(ev, p, g, tday)
          !$omp parallel do schedule(static) private(i, j)
          do j = dcp%js, dcp%je
            do i = g%wx(1,j), g%wx(2,j)
              if (g%x(i,j) <= 0) cycle
              ev%pet(i,j) = pet_mmday(ev, ev%tmap(i,j), doy) * ev%kc * mmday2ms
            end do
          end do
          !$omp end parallel do
          ! 診断の基準値は領域(使用セル)平均気温で評価(決定的総和。
          ! セル数は整数値の実数和 = 丸め順不問で厳密)
          rows(:) = 0.0_real64
          tnum = 0.0
          do j = dcp%js, dcp%je
            tsum = 0.0
            do i = g%wx(1,j), g%wx(2,j)
              if (g%x(i,j) <= 0) cycle
              tsum = tsum + ev%tmap(i,j)
              tnum = tnum + 1.0
            end do
            rows(j) = real(tsum, real64)
          end do
          call par_sum_rows(rows, rsum)
          block
            real :: w1(1)
            w1(1) = tnum
            call par_allreduce_sumr(w1)
            tnum = w1(1)
          end block
          if (tnum > 0.0) then
            pref = pet_mmday(ev, real(rsum) / tnum, doy)
          else
            pref = 0.0
          end if
      end select
      ! ダムの PET
      do nd = 1, ev%ndam
        ev%dam(nd)%petd = pet_mmday(ev, ev%dam(nd)%trep, doy) * ev%kc * mmday2ms
      end do
  end select

  ! モード1,2のダム PET(気温式でない場合は一様値)
  if (ev%model <= 2) then
    do nd = 1, ev%ndam
      ev%dam(nd)%petd = pref * ev%kc * mmday2ms
    end do
  end if

  ev%petref = pref * ev%kc
end subroutine


!----------------------------------------------------------------------
! 気温分布ファイルの更新(必要なファイル番号に達していなければ読み進める。
! リスト終端後は最終ファイルを保持 = 端値保持)
!----------------------------------------------------------------------
subroutine update_tmap(ev, p, g, tday)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: tday
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  integer :: need
  logical :: found

  need = min(max(int(floor(max(tday, 0.0) / ev%dtmap)) + 1, 1), ev%nmap)
  if (need == ev%imap) return

  inquire(file=trim(ev%mapfiles(need)), exist=found)
  if (.not. found) then
    call par_stop("list_evap: 気温分布ファイルが見つかりません: "//trim(ev%mapfiles(need)))
  end if
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny))
    call par_info(" reading "//trim(ev%mapfiles(need)))
    call fileio_read_matrix(trim(ev%mapfiles(need)), g%nx, g%ny, wk, p%f_input_mode)
    call par_scatter_cell(wk, ev%tmap)
  else
    call par_scatter_cell(dum, ev%tmap)
  end if
  ev%imap = need

  ! ダム代表セルの気温: 所有ランクだけが寄与する allreduce(単一寄与 = 厳密)
  block
    integer :: nd
    real :: w1(1)
    do nd = 1, ev%ndam
      w1(1) = 0.0
      if (ev%dam(nd)%nc > 0) w1(1) = ev%tmap(ev%dam(nd)%cells(1,1), ev%dam(nd)%cells(2,1))
      call par_allreduce_sumr(w1)
      ev%dam(nd)%trep = w1(1)
    end do
  end block
end subroutine


!----------------------------------------------------------------------
! PET の式 (mm/day)。式の追加はここに case を足し、§27 に記録する
!----------------------------------------------------------------------
function pet_mmday(ev, tc, doy) result(petd)
  type(t_evap), intent(in) :: ev
  real, intent(in) :: tc          ! 気温 (℃)
  integer, intent(in) :: doy      ! 通日 (1-366)
  real :: petd
  real :: dn, es

  dn = daylight_hours(ev%latrad, doy)
  select case (ev%model)
    case (3)
      ! Hamon (1961): 0.1651・(N/12)・飽和水蒸気密度 216.7 es/(T+273.3)
      !   es (hPa) = 6.108 exp(17.27 T / (T + 237.3))(Tetens)
      es = 6.108 * exp(17.27 * tc / (tc + 237.3))
      petd = 0.1651 * (dn / 12.0) * 216.7 * es / (tc + 273.3)
    case (4)
      ! Thornthwaite (1948) の日割り: 16・(10 T+/I)^a・(N/12)/30
      !   高温域(>26.5℃)の修正式は省略(§27 既知の妥協)
      petd = 16.0 * (10.0 * max(tc, 0.0) / ev%tw_i)**ev%tw_a * (dn / 12.0) / 30.0
    case default
      petd = 0.0
  end select
end function


!----------------------------------------------------------------------
! 可照時間 N (hour)。太陽赤緯は Cooper の近似
!----------------------------------------------------------------------
function daylight_hours(latrad, doy) result(dn)
  real, intent(in) :: latrad
  integer, intent(in) :: doy
  real :: dn
  real :: dec, x
  dec = (23.45 * pi / 180.0) * sin(2.0 * pi * real(284 + doy) / 365.0)
  x = -tan(latrad) * tan(dec)
  x = min(max(x, -1.0), 1.0)      ! 高緯度の白夜・極夜のクランプ
  dn = 24.0 * acos(x) / pi
end function


!----------------------------------------------------------------------
! date0_c の解析("YYYY-MM-DD" または "YYYY-MM-DD hh:mm"。区切りは - : / 可)
!----------------------------------------------------------------------
subroutine parse_date0(str, jdn, sec)
  character(len=*), intent(in) :: str
  integer, intent(out) :: jdn
  real, intent(out) :: sec
  character(len=len(str)) :: buf
  integer :: y, mo, d, hh, mi, k, ios
  buf = str
  do k = 1, len_trim(buf)
    if (buf(k:k) == '-' .or. buf(k:k) == ':' .or. buf(k:k) == '/') buf(k:k) = ' '
  end do
  hh = 0
  mi = 0
  read(buf, *, iostat=ios) y, mo, d, hh, mi
  if (ios /= 0) then
    hh = 0
    mi = 0
    read(buf, *, iostat=ios) y, mo, d
    if (ios /= 0) call par_stop("list_evap: date0_c を解釈できません: "//trim(str))
  end if
  if (mo < 1 .or. mo > 12 .or. d < 1 .or. d > 31 .or. &
      hh < 0 .or. hh > 23 .or. mi < 0 .or. mi > 59) then
    call par_stop("list_evap: date0_c の値が不正です: "//trim(str))
  end if
  jdn = ymd_to_jdn(y, mo, d)
  sec = real(hh) * 3600.0 + real(mi) * 60.0
end subroutine


!----------------------------------------------------------------------
! 暦(グレゴリオ暦)とユリウス通日の相互変換(Fliegel & Van Flandern)
!----------------------------------------------------------------------
pure function ymd_to_jdn(y, mo, d) result(jdn)
  integer, intent(in) :: y, mo, d
  integer :: jdn
  integer :: a
  a = (mo - 14) / 12
  jdn = (1461 * (y + 4800 + a)) / 4 + (367 * (mo - 2 - 12 * a)) / 12 &
        - (3 * ((y + 4900 + a) / 100)) / 4 + d - 32075
end function

pure subroutine jdn_to_ymd(jdn, y, mo, d)
  integer, intent(in) :: jdn
  integer, intent(out) :: y, mo, d
  integer :: l, n, i, j
  l = jdn + 68569
  n = (4 * l) / 146097
  l = l - (146097 * n + 3) / 4
  i = (4000 * (l + 1)) / 1461001
  l = l - (1461 * i) / 4 + 31
  j = (80 * l) / 2447
  d = l - (2447 * j) / 80
  l = j / 11
  mo = j + 2 - 12 * l
  y = 100 * (n - 49) + i + l
end subroutine


!----------------------------------------------------------------------
! 診断 CSV の出力(record 間隔で run_main から呼ばれる。collective:
! par_sum_rows を全ランクで呼び、書き込みは rank0 のみ)
!----------------------------------------------------------------------
subroutine m_evap_record(ev, p, s)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  real(real64) :: v(1:4), vtotal
  integer :: k
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. ev%enabled) return
  do k = 1, 4
    call par_sum_rows(ev%vrow(:,k), v(k))
  end do
  vtotal = v(1) + v(2) + v(3) + v(4) + ev%vdam
  if (is_root .and. ev%un /= 0) then
    write(ev%un, '(f0.2,",",f0.4,6(",",es15.7))') &
          s%t, ev%petref, v(1), v(2), v(3), v(4), ev%vdam, vtotal
    flush(ev%un)
  end if
end subroutine


!----------------------------------------------------------------------
! 蒸発散モジュールを破棄する
!----------------------------------------------------------------------
subroutine m_evap_dispose(ev, p)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. ev%enabled) return
  if (is_root .and. ev%un /= 0) close(ev%un)
  ev%un = 0
  if (allocated(ev%tser)) deallocate(ev%tser)
  if (allocated(ev%mapfiles)) deallocate(ev%mapfiles)
  if (allocated(ev%tmap)) deallocate(ev%tmap)
  if (allocated(ev%pet)) deallocate(ev%pet)
  if (allocated(ev%dam)) deallocate(ev%dam)
  if (allocated(ev%skip)) deallocate(ev%skip)
  if (allocated(ev%vrow)) deallocate(ev%vrow)
  ev%enabled = .false.
  ev%initialized = .false.
end subroutine

end module
