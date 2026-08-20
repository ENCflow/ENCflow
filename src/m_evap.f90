module m_evap
  ! ==================== 蒸発散プロセスモジュール(§27) ====================
  ! 気温(または直接指定)から可能蒸発散量 PET を暦日ごとに評価し、
  ! 毎ステップ、各セルの貯留から優先順位付きで減算する加算的プロセス。
  !   有効化: fn_evap の指定(&list_evap。f_evmodel=0 で一時無効化)
  !   PET:    1=一定速度, 2=月別気候値, 3=Hamon, 4=Thornthwaite(排他切替。
  !           式の追加は pet_mmday に case を足す)
  !   気温:   m_meteo(&list_meteo。§29)が提供(一様定数/一様時系列/
  !           分布時系列+標高減率)。モード3,4は fn_meteo が必須
  !   評価粒度: 暦日平均の思想で「日の先頭の気温」から1日1回更新、日内一定。
  !           気温式は本来日平均気温の式のため、日平均系列(日単位の点)を
  !           推奨する(疎な系列も線形補間・端値保持で機能する)
  !   減算:   樹冠保水(貯留型遮断の draw 口)→ 地表水 h → ため池 hrs →
  !           地下水 hg の順に「あるだけ引く」(供給制限のみ。乾燥抑制なし)。
  !           ダム・湖沼の捕捉帯(hrs)もため池と同様セル面積分ずつ引く
  !           (湛水面積=捕捉セル数×セル面積。湖面をラスタで塗れば実面積。
  !           旧 dam_area の一括評価は 2026-08-20 廃止。§27)。
  !   時刻:   暦は &list_sysparam の date0_c(t=0 の暦)を原点とする
  !           純関数。履歴状態なし = save/restore 対象外(復元後は現在時刻の
  !           暦日で再評価される)。診断 CSV(evap.csv)の累積量のみ
  !           ラン先頭からの積算(restore でリセット。§27)
  !   MPI:    PET は (t, z) の純関数で全ランク同値。分布気温は帯 scatter。
  !           累積診断は行部分和+par_sum_rows(決定的)
  ! ========================================================================
  use iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary
  use m_intercept, only : t_intercept
  use m_meteo, only : t_meteo, meteo_temp_set, meteo_temp_cell, meteo_temp_mean
  use list_evap, only : t_list_evap, list_evap_read
  use m_parallel, only : dcp, is_root, par_info, par_stop, par_sum_rows
  use m_util, only : itoa, jdn_to_ymd, ymd_to_jdn
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

  type t_evap
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    integer :: model = 0           ! f_evmodel
    real :: kc = 1.0
    real :: pet0 = 0.0             ! モード1: PET (mm/day)
    real :: pmon(1:12) = 0.0       ! モード2: 月別 PET (mm/day)
    integer :: jdn0 = 0            ! t=0 の日のユリウス通日(p から転記)
    real :: sec0 = 0.0             ! t=0 の日内秒(同上)
    real :: latrad = 0.0           ! 緯度 (rad)
    real :: tw_i = 0.0             ! Thornthwaite 熱指数 I
    real :: tw_a = 0.0             ! Thornthwaite 指数 a
    integer :: curday = -2147483647  ! 現在の暦日番号(t=0 の日 = 0)
    real, allocatable :: pet(:,:)  ! 現在日の PET (m/s)(帯。kc 適用済み)
    real :: petref = 0.0           ! 基準値 PET (mm/day。CSV 診断用。分布時は領域平均気温で評価)
    real(real64), allocatable :: vrow(:,:) ! 累積蒸発体積の行部分和 (js:je, 1:4) (m3)
                                           !   1=樹冠, 2=地表水 h, 3=hrs, 4=地下水 hg
    integer :: un = 0                      ! CSV 装置番号(rank0。open(newunit=) は負値。§22)
  end type

contains


!----------------------------------------------------------------------
! 蒸発散モジュールを初期化する
!   fn_evap 未指定 or f_evmodel=0 なら何もしない(enabled = .false.)。
!   検証はすべてここで行う(list_evap は読むだけ。§12)
!----------------------------------------------------------------------
subroutine m_evap_init(ev, p, g, b, s, mt)
  type(t_evap), intent(out) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(in) :: s
  type(t_meteo), intent(in) :: mt
  type(t_list_evap) :: list
  integer :: m
  if (allocated(b%struct) .or. allocated(s%h)) continue  ! 引数未使用の警告を抑制

  if (len_trim(p%fn_evap) == 0) return

  call list_evap_read(p, list)
  if (list%f_evmodel == 0) return    ! fn を書いたまま一時無効化する経路

  if (list%f_evmodel < 1 .or. list%f_evmodel > 4) then
    call par_stop("list_evap: f_evmodel must be 0(none), 1(constant), 2(monthly), " &
                  //"3(Hamon) or 4(Thornthwaite): "//itoa(list%f_evmodel))
  end if
  ev%model = list%f_evmodel
  if (list%evap_kc <= 0.0) call par_stop("list_evap: evap_kc must be > 0")
  ev%kc = list%evap_kc

  ! --- 暦の原点(モード2〜4で必須。正本は &list_sysparam の date0_c。§29) ---
  if (ev%model >= 2) then
    if (.not. p%has_date) then
      call par_stop("list_evap: f_evmodel>=2 requires date0_c in &list_sysparam " &
                    //'(calendar at t=0, "YYYY-MM-DD" or "YYYY-MM-DD hh:mm")')
    end if
    ev%jdn0 = p%jdn0
    ev%sec0 = p%sec0
  end if

  ! --- モード別の必須パラメータ ---
  select case (ev%model)
    case (1)
      if (list%evap0 < 0.0) call par_stop("list_evap: f_evmodel=1 requires " &
                                          //"evap0 >= 0 (mm/day)")
      ev%pet0 = list%evap0
    case (2)
      do m = 1, 12
        if (list%evap_monthly(m) < 0.0) then
          call par_stop("list_evap: f_evmodel=2 requires all 12 months of " &
                        //"evap_monthly (mm/day, non-negative)")
        end if
      end do
      ev%pmon = list%evap_monthly
    case (3, 4)
      if (list%lat < -90.0 .or. list%lat > 90.0) then
        call par_stop("list_evap: f_evmodel>=3 requires lat (-90 to 90 deg)")
      end if
      ev%latrad = list%lat * pi / 180.0
  end select

  ! --- Thornthwaite の熱指数(平年月平均気温から) ---
  if (ev%model == 4) then
    ev%tw_i = 0.0
    do m = 1, 12
      if (list%temp_normal(m) <= -9998.0) then
        call par_stop("list_evap: f_evmodel=4 requires temp_normal (12 monthly " &
                      //"normal air temperatures, degC)")
      end if
      ev%tw_i = ev%tw_i + (max(list%temp_normal(m), 0.0) / 5.0)**1.514
    end do
    if (ev%tw_i <= 0.0) then
      call par_stop("list_evap: Thornthwaite heat index I is 0 when temp_normal " &
                    //"is <= 0 degC for all months (use f_evmodel=3)")
    end if
    ev%tw_a = ((6.75e-7 * ev%tw_i - 7.71e-5) * ev%tw_i + 1.792e-2) * ev%tw_i + 0.49239
  end if

  ! --- 気温(モード3,4。&list_meteo が提供する。§29) ---
  if (ev%model >= 3) then
    if (.not. mt%enabled) then
      call par_stop("list_evap: f_evmodel>=3 requires air temperature input (&list_meteo, fn_meteo)")
    end if
  end if

  ! --- 作業配列と診断 ---
  allocate(ev%pet(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(ev%vrow(dcp%js:dcp%je, 1:4), source = 0.0_real64)

  ! --- 診断 CSV(rank0。累積はラン先頭からの積算 = restore でリセット) ---
  if (is_root) then
    open(newunit=ev%un, file=trim(p%dir_result)//"/evap.csv", status='replace')
    write(ev%un, '(a)') "time_s,pet_ref_mmday,ev_canopy_m3,ev_surface_m3," &
                        //"ev_pond_m3,ev_gw_m3,ev_total_m3"
  end if

  ev%enabled = .true.
  ev%initialized = .true.
  call par_info("evapotranspiration enabled (f_evmodel="//itoa(ev%model)//")")
end subroutine


!----------------------------------------------------------------------
! 蒸発散を適用する(毎ステップ。run_main が gwflow の後に呼ぶ。
! 無効時は no-op。冒頭の return 判定は全ランクで同一 = collective 安全)
!----------------------------------------------------------------------
subroutine m_evap_calc(ev, p, g, b, s, ic, mt, it)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  type(t_intercept), intent(in) :: ic
  type(t_meteo), intent(inout) :: mt
  integer, intent(in) :: it
  integer :: i, j, day
  real :: dem, w
  real(real64) :: acell
  logical :: canopy

  if (it < 0 .or. allocated(b%struct)) continue  ! 引数未使用の警告を抑制
  if (.not. ev%enabled) return

  ! 暦日が変わったら PET を再評価(t=0 の暦日を 0 とする通し日)
  day = floor((s%t + ev%sec0) / secday)
  if (day /= ev%curday) call update_pet(ev, p, g, s, day, mt)

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
      ! (3) ため池・ダム/湖沼捕捉帯の貯留 hrs
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

end subroutine


!----------------------------------------------------------------------
! 暦日の PET 評価(日1回。全ランクが同一の day で呼ぶ = collective 安全)
!----------------------------------------------------------------------
subroutine update_pet(ev, p, g, s, day, mt)
  type(t_evap), intent(inout) :: ev
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_meteo), intent(inout) :: mt   ! 分布気温の読み進みを含むため inout
  integer, intent(in) :: day
  integer :: i, j, y, mo, d, doy
  real :: tday, pref

  pref = 0.0
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
      ! 気温は m_meteo が提供する(評価時刻のセットは collective。§29)
      call meteo_temp_set(mt, p, g, tday)
      !$omp parallel do schedule(static) private(i, j)
      do j = dcp%js, dcp%je
        do i = g%wx(1,j), g%wx(2,j)
          if (g%x(i,j) <= 0) cycle
          ev%pet(i,j) = pet_mmday(ev, meteo_temp_cell(mt, i, j, s%z(i,j)), doy) &
                        * ev%kc * mmday2ms
        end do
      end do
      !$omp end parallel do
      ! 診断の基準値: 一様系は基準気温、分布は使用セル平均気温で評価(collective)
      pref = pet_mmday(ev, meteo_temp_mean(mt, g), doy)
  end select

  ev%petref = pref * ev%kc
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
  vtotal = v(1) + v(2) + v(3) + v(4)
  if (is_root .and. ev%un /= 0) then
    write(ev%un, '(f0.2,",",f0.4,5(",",es15.7))') &
          s%t, ev%petref, v(1), v(2), v(3), v(4), vtotal
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
  if (allocated(ev%pet)) deallocate(ev%pet)
  if (allocated(ev%vrow)) deallocate(ev%vrow)
  ev%enabled = .false.
  ev%initialized = .false.
end subroutine

end module
