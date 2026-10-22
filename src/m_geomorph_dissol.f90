!======================================================================
! m_geomorph の submodule: 石灰岩の溶食(f_dissol。化学的削剥)
!   設計の正本は docs/karst_plan.md、決定の記録は developer.md §86。
!
!   水に溶けて岩が消える更新(土砂は出ない)。風化 f_wthr(sd を増やし z を
!   保つ)の対になる「z を下げ sd を保つ」プロセス。
!     w = k_d · f_sol · (F_r + f_sink · F_sink) · morfac   (溶ける岩の厚さ)
!     z  ← z − (1 − f_res) w,   sd ← sd + f_res w   (f_res > 0 のときのみ sd)
!   k_d = c_eq / ρ_r(水 1 m あたり溶ける岩の厚さ。c_eq は有効溶解能
!   mg/L = g/m3、ρ_r は岩の密度 kg/m3)。F_r は地形更新の間隔に積算された
!   面的涵養水量 (m)、F_sink は吸込穴(管路層の枡)流入水量 (m)。
!
!   記録場(fxg と同型の契約。§30・§86):
!     s%fxd  — 涵養量の積算。dissol_src=1: gwflow の鉛直交換(bucket /
!              greenampt)が allocated 判定で書く。dissol_src=2: 本 submodule
!              が毎ステップ s%pre·dt を積む(accum_dissol_rain)
!     s%fxdi — 吸込穴流入量の積算。m_gwflow_conduit の枡流入が書く
!     どちらも calc_dissol が読んでゼロ戻し。確保は init_dissol(無効時は
!     未確保 = 書き手の分岐は allocated 判定のみ = ゼロコスト)
!   更新間隔の途中で save されると積算が失われるため、モジュール私有
!   ファイル geomorph_dissol.dat(契約 5。fxd、sink 有効時は fxdi も)で
!   save/restore する → リスタート往復が ULP=0 で閉じる。
!
!   局所更新(近傍参照なし)・線形で無条件安定。海セル(侵食基準面)と無効
!   セルは対象外。台帳: 溶けた岩の体積を行部分和(real64)で積み、dispose で
!   par_sum_rows(決定的)により総括して報告する。
!   MPI: 更新は自帯 js..je のみ。z・sd のハロ交換は親の calc 末尾が担う。
!
!   側方溶食(dissol_lat = p > 0。karst_plan.md §2.5): 湛水セル w(h > dd)の
!   溶解能 W_w = k_d·F_w·morfac のうち p を、w の水面 e_w より床が高い 8 近傍の
!   陸セル(岩壁)へ接触幅 L_k(軸 Δx、斜め Δx·2/(2+√2))比で配り、残り 1−p を
!   床へ。壁のない湛水セル・乾いたセルは床に全量。壁の後退は壁セルの z の
!   低下で表す(berode と同じ慣習)。3 パス(owner-compute):
!     (1) 自帯の各セルで W を作り、壁の有無で qw(壁向け)/ wfl(床向け)へ
!         (先頭で z・h のハロを交換し、時刻 n の z・h で判定)
!     (2) qw のハロを交換し、各セル n が 8 近傍 w の qw から分け前を dzl(n) に
!         集める(w の壁集合の重み和は n から ±2 行以内 = ハロ幅 2 で足りる。
!         z は読むだけ = OpenMP の競合なし。順序固定 = ランク数不変)
!     (3) wfl + dzl を z(・sd)に適用
!   p = 0 では従来の 1 パスのまま(ビット一致)。
!======================================================================
submodule(m_geomorph) m_geomorph_dissol
  use, intrinsic :: iso_fortran_env, only : real64
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_scatter_cell, par_sum_rows
  use m_fileio, only : fileio_read_matrix
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : rtoa
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_dissol(gm, p, g, s, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_geomorph), intent(in) :: list
  real :: ceq, rho

  ! 既定 100 mg/L(土壌 CO2 を経た涵養水の CaCO3 溶解能の代表。裸岩の雨水は
  ! 50〜80、土層下は 100〜300)、岩の密度 2500 kg/m3(石灰岩 2500〜2700)。§62
  ceq = gm_param("dissol_ceq", list%dissol_ceq, 100.0, " mg/L", unset=-9999.0)
  if (ceq <= 0.0) call par_stop("list_geomorph: dissol_ceq must be > 0")
  rho = gm_param("dissol_rho", list%dissol_rho, 2500.0, " kg/m3")
  if (rho <= 0.0) call par_stop("list_geomorph: dissol_rho must be > 0")
  gm%dis%kd = ceq * 1.0e-3 / rho                   ! (g/m3) / (kg/m3) = 1e-3 m/m

  gm%dis%src = list%dissol_src
  select case (gm%dis%src)
    case (1)
      ! 浸透量の記録は gwflow の鉛直交換が書く。fn_gwflow 未指定なら記録は
      ! 恒久 0 = 溶食が起きない設定齟齬なので停止(降雨源を案内)
      if (len_trim(p%fn_gwflow) == 0) then
        call par_stop("list_geomorph: dissol_src=1 (infiltration) requires fn_gwflow; " &
                      // "use dissol_src=2 (rainfall) without groundwater")
      end if
    case (2)
      ! 地上降雨量(遮断後の s%pre)。浸透の有無によらない最大削剥速度モデル
    case default
      call par_stop("list_geomorph: dissol_src must be 1 (infiltration) or 2 (rainfall)")
  end select

  select case (list%dissol_sink)
    case (0)
      gm%dis%sink = .false.
    case (1)
      gm%dis%sink = .true.
      if (len_trim(p%fn_gwflow) == 0) then
        call par_stop("list_geomorph: dissol_sink=1 requires fn_gwflow with f_gwconduit=1 " &
                      // "and an inlet density (gwc_inlet / fn_gwc_inlet)")
      end if
    case default
      call par_stop("list_geomorph: dissol_sink must be 0 or 1")
  end select
  if (list%dissol_fsink < 0.0) call par_stop("list_geomorph: dissol_fsink must be >= 0")
  gm%dis%fsink = list%dissol_fsink
  if (list%dissol_fres < 0.0 .or. list%dissol_fres > 1.0) then
    call par_stop("list_geomorph: dissol_fres must be in [0, 1]")
  end if
  gm%dis%fres = list%dissol_fres
  gm%dis%res = (gm%dis%fres > 0.0)
  if (list%dissol_lat < 0.0 .or. list%dissol_lat > 1.0) then
    call par_stop("list_geomorph: dissol_lat must be in [0, 1]")
  end if
  gm%dis%plat = list%dissol_lat
  gm%dis%lat = (gm%dis%plat > 0.0)
  if (gm%dis%lat) then
    allocate(gm%dis%qw(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(gm%dis%wfl(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
    allocate(gm%dis%dzl(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
  end if

  ! 可溶率の分布(石灰岩の分布マスク。rank0 が全域を読んで帯配布 = 方式2。§12)
  gm%dis%map = (len_trim(list%fn_dissol) > 0)
  if (gm%dis%map) then
    allocate(gm%dis%fsol(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    call read_solmap(gm, p, g, list%fn_dissol)
  end if

  ! 記録場(有効時のみ確保 = 無効時ゼロコスト。書き手は allocated 判定)
  allocate(s%fxd(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (gm%dis%sink) allocate(s%fxdi(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%dis%vrow(dcp%js:dcp%je), source = 0.0_real64)
  if (p%f_state_restore > 0) call restore_dissol(gm, p, g, s)

  call par_info("geomorph: limestone dissolution on (k_d = " // rtoa(gm%dis%kd) &
                // " m/m, source = " // trim(merge("infiltration", "rainfall    ", gm%dis%src == 1)) &
                // ", sink term = " // trim(merge("on ", "off", gm%dis%sink)) &
                // ", residue = " // rtoa(gm%dis%fres) // ")")
  if (gm%dis%lat) then
    call par_info("geomorph: lateral dissolution on (wall share dissol_lat = " &
                  // rtoa(gm%dis%plat) // ")")
  end if
  if (gm%dis%sink) then
    call par_info("geomorph: dissolution sink term reads the conduit inlet inflow " &
                  // "(zero unless f_gwconduit=1 with inlets)")
  end if
end subroutine


!----------------------------------------------------------------------
! 可溶率 0〜1 の分布を読む(rank0 が全域を読み par_scatter_cell で帯配布。
! 値域外は設定誤りとして停止)
!----------------------------------------------------------------------
subroutine read_solmap(gm, p, g, fn)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  integer :: i, j

  fname = trim(p%dir_data) // "/" // trim(fn)
  call par_info(" reading " // fname)
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    call par_scatter_cell(wk, gm%dis%fsol)
  else
    call par_scatter_cell(dum, gm%dis%fsol)
  end if
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (gm%dis%fsol(i,j) < 0.0 .or. gm%dis%fsol(i,j) > 1.0) then
        call par_stop("list_geomorph: fn_dissol must be in [0, 1]: " // fname)
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 降雨源(dissol_src=2)の毎ステップ積算: fxd += pre·dt(遮断後の地上降雨)
!----------------------------------------------------------------------
module subroutine accum_dissol_rain(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  if (gm%initialized) continue  ! 引数未使用の警告を抑制
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      s%fxd(i,j) = s%fxd(i,j) + s%pre(i,j) * p%dt
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 溶食の適用(地形更新ごと。積算水量を消費してゼロ戻し)
!----------------------------------------------------------------------
module subroutine calc_dissol(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: fw, w
  real(real64) :: rsum

  if (gm%dis%lat) then
    call calc_dissol_lat(gm, p, g, s)
    return
  end if

  !$omp parallel do schedule(static) private(i, j, fw, w, rsum)
  do j = dcp%js, dcp%je
    rsum = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      ! 積算水量は海セルでも消費して捨てる(次の間隔へ持ち越さない)
      fw = s%fxd(i,j)
      s%fxd(i,j) = 0.0
      if (gm%dis%sink) then
        fw = fw + gm%dis%fsink * s%fxdi(i,j)
        s%fxdi(i,j) = 0.0
      end if
      if (g%sw(i,j) > 0) cycle
      if (fw <= 0.0) cycle
      w = gm%dis%kd * fw * gm%morfac
      if (gm%dis%map) w = w * gm%dis%fsol(i,j)
      if (w <= 0.0) cycle
      if (gm%dis%res) then
        s%z(i,j) = s%z(i,j) - (1.0 - gm%dis%fres) * w
        s%sd(i,j) = s%sd(i,j) + gm%dis%fres * w
      else
        s%z(i,j) = s%z(i,j) - w
      end if
      rsum = rsum + real(w, real64)
    end do
    gm%dis%vrow(j) = gm%dis%vrow(j) + rsum * g%dx * g%dy
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 側方溶食つきの適用(3 パス。ヘッダ参照)
!----------------------------------------------------------------------
subroutine calc_dissol_lat(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, parameter :: wdiag = 2.0 / (2.0 + sqrt(2.0))   ! 斜め接触幅の比(p_diagratio の既定と同値)
  real, parameter :: lk(1:8) = [wdiag, 1.0, wdiag, 1.0, 1.0, wdiag, 1.0, wdiag]
  integer :: i, j, k, in, jn, m, im, jm
  real :: fw, wcap, ew, sumw, fs
  logical :: wall
  real(real64) :: rsum

  ! 壁判定は時刻 n の z・h で行う(ハロ行を含めて最新化。collective)
  call par_halo_cell(s%z)
  call par_halo_cell(s%h)
  gm%dis%qw(:,:) = 0.0

  ! (1) 湛水セルの溶解能を壁向け / 床向けに分ける(自帯のみ書く)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, fw, wcap, ew, wall)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%dis%wfl(i,j) = 0.0
      gm%dis%dzl(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      fw = s%fxd(i,j)
      s%fxd(i,j) = 0.0
      if (gm%dis%sink) then
        fw = fw + gm%dis%fsink * s%fxdi(i,j)
        s%fxdi(i,j) = 0.0
      end if
      if (g%sw(i,j) > 0) cycle
      if (fw <= 0.0) cycle
      wcap = gm%dis%kd * fw * gm%morfac
      wall = .false.
      if (s%h(i,j) > p%dd) then
        ew = s%z(i,j) + s%h(i,j)
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (in < dcp%ish .or. in > dcp%ieh .or. jn < dcp%jsh .or. jn > dcp%jeh) cycle
          if (g%x(in,jn) <= 0) cycle
          if (g%sw(in,jn) > 0) cycle
          if (s%z(in,jn) > ew) then
            wall = .true.
            exit
          end if
        end do
      end if
      if (wall) then
        gm%dis%qw(i,j) = gm%dis%plat * wcap
        gm%dis%wfl(i,j) = (1.0 - gm%dis%plat) * wcap
      else
        gm%dis%wfl(i,j) = wcap
      end if
    end do
  end do
  !$omp end parallel do

  ! (2) 壁セル n が 8 近傍の湛水セル w から分け前を集める(近傍の z・h は読むだけ)
  call par_halo_cell(gm%dis%qw)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, m, im, jm, ew, sumw)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (in < dcp%ish .or. in > dcp%ieh .or. jn < dcp%jsh .or. jn > dcp%jeh) cycle
        if (gm%dis%qw(in,jn) <= 0.0) cycle
        ew = s%z(in,jn) + s%h(in,jn)
        if (.not. (s%z(i,j) > ew)) cycle           ! 自分は w の壁ではない
        ! w の壁集合の重みの和(w の 8 近傍。n から ±2 行以内 = ハロ幅 2)
        sumw = 0.0
        do m = 1, 8
          im = in + din(m)
          jm = jn + djn(m)
          if (im < dcp%ish .or. im > dcp%ieh .or. jm < dcp%jsh .or. jm > dcp%jeh) cycle
          if (g%x(im,jm) <= 0) cycle
          if (g%sw(im,jm) > 0) cycle
          if (s%z(im,jm) > ew) sumw = sumw + lk(m)
        end do
        ! n は w から見て方向 9-k(din(9-k) = -din(k))。接触幅は同じ lk(k)
        gm%dis%dzl(i,j) = gm%dis%dzl(i,j) + gm%dis%qw(in,jn) * lk(k) / sumw
      end do
    end do
  end do
  !$omp end parallel do

  ! (3) 床と壁の量をまとめて適用し、台帳に積む
  !$omp parallel do schedule(static) private(i, j, fs, rsum)
  do j = dcp%js, dcp%je
    rsum = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      fs = gm%dis%wfl(i,j) + gm%dis%dzl(i,j)
      if (fs <= 0.0) cycle
      if (gm%dis%map) fs = fs * gm%dis%fsol(i,j)
      if (fs <= 0.0) cycle
      if (gm%dis%res) then
        s%z(i,j) = s%z(i,j) - (1.0 - gm%dis%fres) * fs
        s%sd(i,j) = s%sd(i,j) + gm%dis%fres * fs
      else
        s%z(i,j) = s%z(i,j) - fs
      end if
      rsum = rsum + real(fs, real64)
    end do
    gm%dis%vrow(j) = gm%dis%vrow(j) + rsum * g%dx * g%dy
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
module subroutine dispose_dissol(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: vtot
  if (p%f_state_save > 0) call save_dissol(gm, p, g, s)
  ! 溶けた岩の体積の総括(par_sum_rows = 決定的。collective は全ランクが呼ぶ)
  call par_sum_rows(gm%dis%vrow, vtot)
  call par_info("geomorph: dissolution removed " // rtoa(real(vtot)) // " m3 of rock")
end subroutine


!----------------------------------------------------------------------
! 記録場の保存・復元(モデル私有ファイル geomorph_dissol.dat。契約5。§7)
!   書き並びは restore と同時に更新する。sink の有無で面数が変わるため
!   restore 側は同じ設定であることを前提とする(他の私有ファイルと同じ)
!----------------------------------------------------------------------
subroutine save_dissol(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/geomorph_dissol.dat', form='unformatted', &
         status='replace')
  end if
  call restart_write_cell(un, s%fxd)
  if (gm%dis%sink) call restart_write_cell(un, s%fxdi)
  if (is_root) close(un)
end subroutine


subroutine restore_dissol(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制

  fname = trim(p%dir_save)//'/geomorph_dissol.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("geomorph: dissolution state file not found (was f_dissol enabled when saving): " &
                  // fname)
  end if
  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, s%fxd)
  if (gm%dis%sink) call restart_read_cell(un, s%fxdi)
  if (is_root) close(un)
end subroutine

end submodule
