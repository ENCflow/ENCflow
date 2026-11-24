!======================================================================
! m_geomorph の submodule: 混合粒径(f_bedmix)— 掃流砂の粒径階 × 交換層 1 枚・下層 1 枚(Hirano 型)
!   設計の正本は docs/mixed_sediment_plan.md、採る範囲は developer.md §84.19(基本方針 6 の例外)。
!   無効時は呼ばれない(配列は未確保、ハロ交換も増えない)。既存の掃流砂のループは calc_fluvial の先頭で
!   本 submodule の写しへ分けるだけで、命令列を変えない(無効時ビット一致。plan §4)。
!
!   状態: 交換層の組成 s%bmf(:,:,k)(帯±ハロ。近傍の組成を読むのでハロも保つ)、下層の組成
!     gm%bmx%fs(:,:,k)(自帯だけを読む)。交換層厚は領域で一様の L_a、実効の交換層厚 L_e = min(L_a, sd)、
!     下層厚 sd − L_e(sd は既存の土層厚 = 可動層厚。z と sd の共動更新は既存と同じ)。
!   ループ 1(calc_fluvial_bmix。calc_fluvial のループ 1 の写し): エッジごとに粒径階 k の流束を作る。
!     τ*_k = (既存と同じマニング閉じ・有効掃流力の比・斜面に沿うせん断)/ d_k、
!     限界 τ*c,k = τ*cm ξ_k(遮蔽係数 ξ_k は修正 Egiazaroff = 芦田・道上 1972 式 (31)、d_m は両セルの平均)、
!     流砂量 q_k = F_k(風上)Φ(τ*_k, τ*c,k) √(s g d_k³)(同 式 (32)。Φ は f_qbform の式)、
!     向き t̂ + r n̂ − γ_k ∇z(γ_k = (μs μk)^(−1/2) √(τ*c,k/τ*_k)。r は全粒径階で共通)。
!     河岸面の遮断(R1・R2)・定着・通過幅は既存と同じく粒径階ごとに掛け、変動上限 dzmax は
!     全粒径階の和に掛ける。粒径階ごとの流束は gm%bmx%qk に、等移動度の流束(側岸侵食が足す)は
!     wrk%q に置く(wrk%q は掃流砂の分を 0 で上書きする)。
!   適用(apply_edge_flux_bmix): 粒径階ごとの供給量制限(1 回の更新で流出 ≤ 交換層にある量 L_e F_k。
!     下層から入る分は数えない = 保守側。負の組成を構造的に防ぐ)→ 発散 → z・sd の共動更新と
!     Hirano の交換(界面が下がるとき下層から下層の組成で、上がるとき交換層から交換層の組成で)。
!     等移動度の流束(側岸侵食・安息角崩落)は供給側の交換層の組成で粒径階に分ける(plan §10 の 6)。
!   給砂: 区間流入の粒径階ごとの給砂 b%qbink(apply_bedfeed_bmix)、容量給砂は流入セルの
!     粒径階ごとの正味流出 × 倍率(feed_pass_bmix。入口の z と組成が固定)。
!   台帳: 粒径階ごとの在庫(初期・最終)、区間流入の給砂、開境界の正味の流出(容量給砂を負で含む)を
!     行部分和で決定的に集計し、終了時に収支の残差を表示する。
!   私有 save: geomorph_bedmix.dat(粒径階の数・粒径・L_a の見出しと、交換層 N 面・下層 N 面。
!     restart_write_cell。developer.md §83 の契約 5)。
!======================================================================
submodule(m_geomorph) m_geomorph_bedmix
  use m_parallel, only : par_info, par_warn, par_stop, dcp, is_root, par_halo_cell, par_sum_rows, &
                         par_allreduce_maxi
  use m_swflow_enc, only : chn, bcs, bc_open_face, bc_neumann_cell, bc_inflow_nooutflow, &
                          slope_shear_on, slope_shear_factor, slope_shear_factor_e
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : itoa, rtoa
  implicit none

contains

!----------------------------------------------------------------------
! 初期化(init_fluvial・init_bank・init_fixation の後。s%sd は setup_sd 済み)
!----------------------------------------------------------------------
module subroutine init_bedmix(gm, p, g, s, b, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_boundary), intent(in) :: b
  type(t_list_geomorph), intent(in) :: list
  integer :: nc, kc, ifl
  real :: fmean(1:nbmixmax), d90, la
  character(len=512) :: msg

  ! --- 粒径階(与えた個数 N = 2〜nbmixmax。細かい順。同じ値も許す = 検定の単一粒径の極限) ---
  nc = 0
  do kc = 1, nbmixmax
    if (list%bmix_d(kc) <= -9000.0) exit
    nc = nc + 1
  end do
  if (nc < 2) then
    call par_stop("list_geomorph: f_bedmix=1 requires 2 to " // itoa(nbmixmax) // " class diameters bmix_d " &
                  // "(for a single grain size use fluv_d50 without f_bedmix)")
  end if
  do kc = 1, nc
    if (list%bmix_d(kc) <= 0.0) call par_stop("list_geomorph: bmix_d must be > 0")
    if (kc > 1) then
      if (list%bmix_d(kc) < list%bmix_d(kc-1)) then
        call par_stop("list_geomorph: bmix_d must be in increasing order (fine to coarse; equal values allowed)")
      end if
    end if
  end do
  gm%bmx%nc = nc
  gm%bmx%d(1:nc) = list%bmix_d(1:nc)
  gm%bmx%qc(1:nc) = sqrt(gm%sgrav * p%gg * gm%bmx%d(1:nc)**3)
  if (list%bmix_hiding < 0 .or. list%bmix_hiding > 1) then
    call par_stop("list_geomorph: bmix_hiding must be 1 (modified Egiazaroff) or 0 (none)")
  end if
  gm%bmx%hiding = list%bmix_hiding
  ! 急勾配礫床の抵抗分割の D84 は、段 1 では粒径階から求めない(plan §3.7)
  if (list%f_taupart == 1 .and. list%fluv_d84 <= 0.0) then
    call par_stop("list_geomorph: f_taupart=1 with f_bedmix=1 requires fluv_d84 > 0 " &
                  // "(the D84 is not derived from the grain-size classes)")
  end if

  ! --- 状態(有効時のみ確保) ---
  allocate(s%bmf(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:nc), source = 0.0)
  allocate(s%bmdm(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%bmx%fs(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:nc), source = 0.0)
  allocate(gm%bmx%qk(1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh, 1:nc), source = 0.0)
  allocate(gm%bmx%fdk(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:nc), source = 1.0)
  allocate(gm%bmx%feedrow(dcp%js:dcp%je, 1:nc), source = 0.0_real64)
  allocate(gm%bmx%voutrow(dcp%js:dcp%je, 1:nc), source = 0.0_real64)

  ! --- 交換層・下層の初期の組成(一様値か粒径階ごとの分布ファイル。下層は未指定なら交換層と同じ) ---
  call init_composition(p, g, s, nc, list%bmix_frac0, list%fn_bmix, "bmix_frac0", "fn_bmix", s%bmf, .true.)
  if (.not. init_composition_given(nc, list%bmix_sub0, list%fn_bmixsub)) then
    gm%bmx%fs(:,:,1:nc) = s%bmf(:,:,1:nc)
  else
    call init_composition(p, g, s, nc, list%bmix_sub0, list%fn_bmixsub, "bmix_sub0", "fn_bmixsub", &
                          gm%bmx%fs, .false.)
  end if

  ! --- 交換層厚(既定は初期の交換層の領域平均の組成の D90 の 2 倍。plan §10 の 2) ---
  ! 既定と代表粒径は初期の組成(namelist の一様値か、読んだ分布と入力の土層厚)だけから決める。現在の
  ! 状態(再開なら復元した土層厚)から数えると、土層のあるセルの集合が変わって 1 ulp ずれ、再開が
  ! ビット一致しなくなる(実検出)
  if (list%bmix_frac0(1) > -9000.0) then
    fmean(1:nc) = list%bmix_frac0(1:nc) / sum(list%bmix_frac0(1:nc))
  else
    call domain_mean_composition(g, s, nc, fmean)
  end if
  d90 = bmix_dpct(nc, gm%bmx%d, fmean, 0.9)
  gm%bmx%dref = sum(fmean(1:nc) * gm%bmx%d(1:nc))
  la = gm_param("bmix_la", list%bmix_la, 2.0 * d90, " m")
  if (la <= 0.0) call par_stop("list_geomorph: bmix_la must be > 0")
  if (la < gm%bmx%d(nc)) then
    call par_warn("geomorph: bmix_la = " // rtoa(la) // " m is thinner than the largest class diameter " &
                  // rtoa(gm%bmx%d(nc)) // " m")
  end if
  gm%bmx%la = la
  ! 代表粒径(側岸侵食則の脚部の τ* が使う。段 1 は初期の交換層の領域平均の d_m。plan §3.7)
  gm%d50 = gm%bmx%dref
  gm%flv%qbcoef = sqrt(gm%sgrav * p%gg * gm%d50**3)
  write(msg, '(a,i0,a)') "geomorph: mixed-size bed on (", nc, " classes, d ="
  do kc = 1, nc
    msg = trim(msg) // " " // rtoa(gm%bmx%d(kc))
  end do
  msg = trim(msg) // " m, D90 of the initial exchange layer = " // rtoa(d90) // " m, mean d_m = " &
        // rtoa(gm%bmx%dref) // " m, hiding = " // trim(merge("modified Egiazaroff", "none               ", &
        gm%bmx%hiding == 1)) // ")"
  call par_info(trim(msg))

  ! --- 区間流入の給砂の組成(与件なので既定を置かない。plan §3.6・§10 の 3) ---
  do ifl = 1, b%ninflow
    if (b%inflow(ifl)%nqbval > 0 .and. b%inflow(ifl)%nqbfrac == 0) then
      call par_stop("list_bound_inflow: with f_bedmix=1 the bed-load feed of segment " // itoa(ifl) &
                    // " needs its composition (inflow_qbfrac) or a per-class series (fn_inflow_qbmix)")
    end if
  end do
  if (b%nqbclass > 0 .and. b%nqbclass /= nc) then
    call par_stop("list_bound_inflow: the bed-load feed has " // itoa(b%nqbclass) // " grain-size classes, " &
                  // "but bmix_d has " // itoa(nc))
  end if

  ! --- 再開(私有 save) ---
  if (p%f_state_restore > 0) call restore_bedmix(gm, p, s)
  do kc = 1, nc
    call par_halo_cell(s%bmf(:,:,kc))
  end do
  call bmix_update_dm(gm, s)
  ! 初期の在庫(台帳)は最初の更新の頭で数える(河道幅の係数 chn は swflow の init で確保されるため)
end subroutine


!----------------------------------------------------------------------
! 組成の初期値: 一様値(和が 1。N 個)か、粒径階ごとの分布ファイル(セルごとに和が 1 に近いこと)。
! 必須でないとき(下層)の未指定は呼び出し側が判定する
!----------------------------------------------------------------------
subroutine init_composition(p, g, s, nc, frac0, fnmap, name0, namemap, a, required)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: nc
  real, intent(in) :: frac0(:)
  character(len=*), intent(in) :: fnmap(:)
  character(len=*), intent(in) :: name0, namemap
  real, intent(inout) :: a(dcp%ish:, dcp%jsh:, 1:)
  logical, intent(in) :: required
  integer :: kc, i, j, n0, nm, bad
  real :: sm

  n0 = 0
  do kc = 1, size(frac0)
    if (frac0(kc) <= -9000.0) exit
    n0 = n0 + 1
  end do
  nm = 0
  do kc = 1, size(fnmap)
    if (len_trim(fnmap(kc)) == 0) exit
    nm = nm + 1
  end do
  if (n0 > 0 .and. nm > 0) call par_stop("list_geomorph: give either " // name0 // " or " // namemap // ", not both")
  if (n0 == 0 .and. nm == 0) then
    if (required) call par_stop("list_geomorph: f_bedmix=1 requires the initial composition of the exchange layer (" &
                                // name0 // " or " // namemap // ")")
    return
  end if
  if (n0 > 0) then
    if (n0 /= nc) call par_stop("list_geomorph: " // name0 // " needs " // itoa(nc) // " values (one per class of bmix_d)")
    if (any(frac0(1:nc) < 0.0)) call par_stop("list_geomorph: " // name0 // " must be >= 0")
    sm = sum(frac0(1:nc))
    if (abs(sm - 1.0) > 1.0e-6) call par_stop("list_geomorph: " // name0 // " must sum to 1")
    do kc = 1, nc
      a(:,:,kc) = frac0(kc) / sm
    end do
    return
  end if
  if (nm /= nc) call par_stop("list_geomorph: " // namemap // " needs " // itoa(nc) // " files (one per class)")
  do kc = 1, nc
    call read_cellmap(p, g, fnmap(kc), a(:,:,kc))
  end do
  ! セルごとの検査と正規化(自帯。土層のないセル・領域外は一様の組成で埋める = 使われない)
  bad = 0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      sm = sum(a(i,j,1:nc))
      if (g%x(i,j) > 0 .and. s%sd(i,j) > 0.0) then
        if (any(a(i,j,1:nc) < 0.0) .or. abs(sm - 1.0) > 1.0e-3) bad = 1
      end if
      if (sm > 0.0 .and. all(a(i,j,1:nc) >= 0.0)) then
        a(i,j,1:nc) = a(i,j,1:nc) / sm
      else
        a(i,j,1:nc) = 1.0 / nc
      end if
    end do
  end do
  call par_allreduce_maxi(bad)
  if (bad > 0) then
    call par_stop("list_geomorph: the class fractions of " // namemap // " must be >= 0 and sum to 1 " &
                  // "(within 1e-3) in every cell with soil (sd > 0)")
  end if
end subroutine


logical function init_composition_given(nc, frac0, fnmap) result(given)
  integer, intent(in) :: nc
  real, intent(in) :: frac0(:)
  character(len=*), intent(in) :: fnmap(:)
  if (nc < 0) continue
  given = (frac0(1) > -9000.0 .or. len_trim(fnmap(1)) > 0)
end function


!----------------------------------------------------------------------
! 交換層の初期の領域平均の組成(分布ファイルで与えたとき。入力の土層厚 g%sd が正の有効セル。決定的な
! 総和。init の中で、復元の前に呼ぶ = 再開でも同じ値)
!----------------------------------------------------------------------
subroutine domain_mean_composition(g, s, nc, fmean)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: nc
  real, intent(out) :: fmean(:)
  real(real64), allocatable :: rows(:,:)
  real(real64) :: tot(1:nbmixmax + 1)
  integer :: i, j, kc

  allocate(rows(dcp%js:dcp%je, 1:nc+1), source = 0.0_real64)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (allocated(g%sd)) then
        if (g%sd(i,j) <= 0.0) cycle
      end if
      rows(j,1:nc) = rows(j,1:nc) + real(s%bmf(i,j,1:nc), real64)
      rows(j,nc+1) = rows(j,nc+1) + 1.0_real64
    end do
  end do
  do kc = 1, nc + 1
    call par_sum_rows(rows(:,kc), tot(kc))
  end do
  if (tot(nc+1) > 0.0_real64) then
    fmean(1:nc) = real(tot(1:nc) / tot(nc+1))
  else
    fmean(1:nc) = 1.0 / nc
  end if
end subroutine


!----------------------------------------------------------------------
! 終了処理: 保存と台帳(粒径階ごとの収支)
!----------------------------------------------------------------------
module subroutine dispose_bedmix(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: v1(1:nbmixmax), vf, vo, res
  integer :: kc
  character(len=512) :: msg

  if (p%f_state_save > 0) call save_bedmix(gm, p, s)
  call bmix_stock(gm, g, s, v1)
  do kc = 1, gm%bmx%nc
    call par_sum_rows(gm%bmx%feedrow(:,kc), vf)
    call par_sum_rows(gm%bmx%voutrow(:,kc), vo)
    res = v1(kc) - (gm%bmx%v0(kc) + vf - vo)
    write(msg, '(a,i0,a,es12.5,a,4(a,es16.9),a)') "geomorph: bed mixture ledger class ", kc, " (d = ", &
          gm%bmx%d(kc), " m): stock", " initial ", gm%bmx%v0(kc), " final ", v1(kc), " feed ", vf, &
          " out ", vo, " m3 (solid)"
    call par_info(trim(msg))
    write(msg, '(a,i0,a,es12.5,a)') "geomorph: bed mixture ledger class ", kc, " residual ", res, &
          " m3 (final - initial - feed + out)"
    call par_info(trim(msg))
  end do
  ! ランク局所の診断
  if (gm%bmx%nlimk > 0) then
    call par_warn("geomorph: bed mixture class supply limiter (exchange layer) fired in " // itoa(gm%bmx%nlimk) &
                  // " cell-classes (shorten dt_geomorph or thicken bmix_la if frequent)")
  end if
  if (gm%bmx%nclip > 0) then
    call par_warn("geomorph: bed mixture dzmax clip fired on " // itoa(gm%bmx%nclip) // " edges")
  end if
  if (gm%bmx%vclip > 0.0) then
    call par_warn("geomorph: bed mixture rounding clip moved " // rtoa(gm%bmx%vclip) // " m3 (bulk)")
  end if
  if (gm%f_fixation > 0 .and. gm%bmx%nfix > 0) then
    call par_info("geomorph: bed mixture fixation raised the class thresholds on " // itoa(gm%bmx%nfix) // " fluxes")
  end if
end subroutine


!----------------------------------------------------------------------
! 最初の更新の頭: 河道平面積率の写しと初期の在庫(台帳)。chn は swflow の init で確保されるので、
! geomorph の init ではなくここで取る
!----------------------------------------------------------------------
subroutine bmix_first_step(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (chn%have_width) allocate(gm%bmx%wf, source = chn%wfrac)
  call bmix_stock(gm, g, s, gm%bmx%v0)
  gm%bmx%stock0 = .true.
end subroutine


!----------------------------------------------------------------------
! 粒径階ごとの在庫(固体体積 m3。全域。決定的な総和)
!----------------------------------------------------------------------
subroutine bmix_stock(gm, g, s, v)
  type(t_geomorph), intent(in) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64), intent(out) :: v(:)
  real(real64), allocatable :: rows(:,:)
  integer :: i, j, kc, nc
  real :: le, ls, w

  nc = gm%bmx%nc
  allocate(rows(dcp%js:dcp%je, 1:nc), source = 0.0_real64)
  !$omp parallel do schedule(static) private(i, j, kc, le, ls, w)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      le = min(gm%bmx%la, max(s%sd(i,j), 0.0))
      ls = max(s%sd(i,j), 0.0) - le
      w = 1.0
      if (allocated(gm%bmx%wf)) w = gm%bmx%wf(i,j)
      do kc = 1, nc
        rows(j,kc) = rows(j,kc) + real((le * s%bmf(i,j,kc) + ls * gm%bmx%fs(i,j,kc)) * w, real64)
      end do
    end do
  end do
  !$omp end parallel do
  v(:) = 0.0_real64
  do kc = 1, nc
    call par_sum_rows(rows(:,kc), v(kc))
    v(kc) = v(kc) / real(gm%wrk%ainv, real64) / real(gm%poroi, real64)
  end do
end subroutine


!----------------------------------------------------------------------
! 私有 save(geomorph_bedmix.dat。見出し = 粒径階の数と粒径・L_a。書き並びは restore と同時に更新)
!----------------------------------------------------------------------
subroutine save_bedmix(gm, p, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: un, kc

  un = -1
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/geomorph_bedmix.dat', form='unformatted', status='replace')
    write(un) gm%bmx%nc
    write(un) gm%bmx%d(1:gm%bmx%nc), gm%bmx%la
  end if
  do kc = 1, gm%bmx%nc
    call restart_write_cell(un, s%bmf(:,:,kc))
  end do
  do kc = 1, gm%bmx%nc
    call restart_write_cell(un, gm%bmx%fs(:,:,kc))
  end do
  if (is_root) close(un)
end subroutine


subroutine restore_bedmix(gm, p, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un, kc, ncr, bad
  real :: dr(1:nbmixmax), lar

  fname = trim(p%dir_save)//'/geomorph_bedmix.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("geomorph: mixed-size bed state file not found (was f_bedmix enabled when saving): " // fname)
  end if
  un = -1
  bad = 0
  if (is_root) then
    open(newunit=un, file=fname, form='unformatted', status='old')
    read(un) ncr
    if (ncr /= gm%bmx%nc) then
      bad = 1
    else
      read(un) dr(1:ncr), lar
      if (any(abs(dr(1:ncr) - gm%bmx%d(1:ncr)) > 1.0e-6 * gm%bmx%d(1:ncr)) &
          .or. abs(lar - gm%bmx%la) > 1.0e-6 * gm%bmx%la) bad = 1
    end if
  end if
  call par_allreduce_maxi(bad)
  if (bad > 0) then
    if (is_root) close(un)
    call par_stop("geomorph: the saved mixed-size bed (geomorph_bedmix.dat) has other classes (bmix_d) or " &
                  // "another exchange-layer thickness (bmix_la) than the current settings")
  end if
  do kc = 1, gm%bmx%nc
    call restart_read_cell(un, s%bmf(:,:,kc))
  end do
  do kc = 1, gm%bmx%nc
    call restart_read_cell(un, gm%bmx%fs(:,:,kc))
  end do
  if (is_root) close(un)
end subroutine


!----------------------------------------------------------------------
! 交換層の平均粒径 d_m = Σ F_k d_k(帯±ハロ。組成のハロは最新であること)
!----------------------------------------------------------------------
subroutine bmix_update_dm(gm, s)
  type(t_geomorph), intent(in) :: gm
  type(t_state), intent(inout) :: s
  integer :: i, j, kc
  real :: dm

  !$omp parallel do schedule(static) private(i, j, kc, dm)
  do j = dcp%jsh, dcp%jeh
    do i = dcp%ish, dcp%ieh
      dm = 0.0
      do kc = 1, gm%bmx%nc
        dm = dm + s%bmf(i,j,kc) * gm%bmx%d(kc)
      end do
      s%bmdm(i,j) = dm
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 掃流砂の 1 ステップ(混合粒径版。calc_fluvial の写し)
!   ループ 1 の判定・水理量・河岸面の遮断・定着・通過幅・開境界の扱いは calc_fluvial と同じ。
!   calc_fluvial のループ 1 を変えるときはこちらも同じく変えること(plan §4 の保守の約束)
!----------------------------------------------------------------------
module subroutine calc_fluvial_bmix(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, kc, nc, iu, ju
  real :: ue, vve, hhe, rne, base, taus, tsc, tsce, qbs, gq, sdze, winvd, afx, dze, capk
  real :: dxv, dyv, dirp0, dirp, ubar, vbar, re, gam, dme
  real :: gqk(1:nbmixmax)
  integer :: nclip, nfix
  logical :: okc, okbank, ssh

  nc = gm%bmx%nc
  nclip = 0
  nfix = 0
  ssh = slope_shear_on()
  if (.not. gm%bmx%stock0) call bmix_first_step(gm, g, s)

  ! --- ステップ頭のハロ交換(calc_fluvial と同じ理由) ---
  call par_halo_cell(s%h)
  call par_halo_cell(s%u)
  call par_halo_cell(s%v)
  call par_halo_cell(s%vv)
  if (gm%flv%f_sec) then
    call eval_secflow_bmix(gm, p, g, s)
    call par_halo_cell(gm%flv%rsec)
  end if
  ! 交換層の平均粒径(帯±ハロ。組成のハロは前回の適用・給砂の末尾で交換済み)
  call bmix_update_dm(gm, s)

  ! --- ループ1: エッジの粒径階ごとの掃流砂フラックス(各成分の書き手は一意) ---
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nclip, nfix) &
  !$omp   private(i, j, k, in, jn, kc, iu, ju, okc, okbank, ue, vve, hhe, rne, base, taus, tsc, tsce, &
  !$omp           qbs, gq, sdze, winvd, afx, dxv, dyv, dirp0, dirp, ubar, vbar, re, gam, dme, gqk, dze, capk)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gqk(1:nc) = 0.0
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            okbank = .true.
            if (g%bank_active) then
              okbank = ((g%rw(i,j) > 0) .eqv. (g%rw(in,jn) > 0))
            end if
            vve = (s%vv(i,j) + s%vv(in,jn)) / 2
            hhe = (s%h(i,j) + s%h(in,jn)) / 2
            if (okbank .and. vve > 0.0 .and. hhe > p%dd) then
              ue = (s%u(i,j) + s%u(in,jn)) / 2 * gm%flv%ex(k) &
                 + (s%v(i,j) + s%v(in,jn)) / 2 * gm%flv%ey(k)
              hhe = max(hhe, p%dv)
              rne = (g%rn(i,j) + g%rn(in,jn)) / 2
              ! 粒径によらない部分(τ*_k = base / d_k。calc_fluvial と同じ閉じと補正)
              base = taufac_h(gm%flv, hhe) * rne**2 * vve**2 / (gm%sgrav * hhe**(1.0/3.0))
              if (ssh) base = base * slope_shear_factor_e(g, s, i, j, in, jn)
              ! 遮蔽係数の d_m は両セルの平均。片側の土層厚が 0(岩盤・固定床)ならもう片側(plan §3.2)
              if (s%sd(i,j) <= 0.0) then
                dme = s%bmdm(in,jn)
              else if (s%sd(in,jn) <= 0.0) then
                dme = s%bmdm(i,j)
              else
                dme = 0.5 * (s%bmdm(i,j) + s%bmdm(in,jn))
              end if
              ! 向きの補正のうち粒径階によらない部分(t̂ + r n̂ の射影)
              if (gm%flv%f_dir) then
                ubar = (s%u(i,j) + s%u(in,jn)) / 2
                vbar = (s%v(i,j) + s%v(in,jn)) / 2
                dxv = ubar / vve
                dyv = vbar / vve
                if (gm%flv%f_sec) then
                  re = (gm%flv%rsec(i,j) + gm%flv%rsec(in,jn)) / 2
                  dxv = dxv - re * vbar / vve
                  dyv = dyv + re * ubar / vve
                end if
                dirp0 = dxv * gm%flv%ex(k) + dyv * gm%flv%ey(k)
              else
                dirp0 = ue / vve
              end if
              sdze = 0.0
              do kc = 1, nc
                taus = base / gm%bmx%d(kc)
                tsc = gm%tausc * bmix_xi(gm%bmx%hiding, gm%bmx%d(kc) / dme)
                if (taus <= tsc) cycle
                dirp = dirp0
                if (gm%flv%f_dir .and. gm%flv%f_slope) then
                  gam = gm%flv%gcoef * sqrt(tsc / taus)
                  dirp = dirp - gam * (s%z(in,jn) - s%z(i,j)) * gm%flv%rdist(k)
                end if
                if (dirp == 0.0) cycle
                qbs = bmix_qbs(gm%f_qbform, taus, tsc)
                gq = qbs * gm%bmx%qc(kc) * dirp * gm%flv%wl(k)
                ! 河岸面の遮断(§84.2)と供給側(風上)
                if (gq > 0.0) then
                  if (s%h(i,j) <= p%dd .or. s%z(in,jn) >= s%z(i,j) + s%h(i,j)) gq = 0.0
                  iu = i
                  ju = j
                else
                  if (s%h(in,jn) <= p%dd .or. s%z(i,j) >= s%z(in,jn) + s%h(in,jn)) gq = 0.0
                  iu = in
                  ju = jn
                end if
                if (gq == 0.0) cycle
                ! 利用可能率 = 供給側の交換層の粒径階の割合(芦田・道上 式 (32) の p_i)
                gq = gq * s%bmf(iu,ju,kc)
                ! 定着(§84.6): 供給側の定着度で粒径階の限界を τ*c,k (1 + c_τ a) に上げる
                if (gm%f_fixation > 0 .and. gq /= 0.0) then
                  afx = s%fx(iu,ju)
                  if (afx > 0.0) then
                    tsce = tsc * (1.0 + gm%fix%ctau * afx)
                    if (taus <= tsce) then
                      gq = 0.0
                    else
                      gq = gq * (bmix_qbs(gm%f_qbform, taus, tsce) / qbs)
                    end if
                    nfix = nfix + 1
                  end if
                end if
                ! 通過幅係数と動的振り替えの表(水と同じ。calc_fluvial と同じ)
                if (chn%have_frw) gq = gq * chn%frw(k, i+die(k), j+dje(k))
                if (chn%have_fwd) gq = gq * chn%fwd(k, i+die(k), j+dje(k))
                ! 可動層クランプ(calc_fluvial と同じ。粒径階版): 供給側の交換層にある粒径階 k の量
                ! L_e F_k を超える流出をこのエッジ単独で起こさない(複数エッジの同時流出の超過は
                ! apply_edge_flux_bmix の粒径階ごとの供給量制限が受ける)
                winvd = 1.0
                if (chn%have_width) winvd = 1.0 / chn%wfrac(iu,ju)
                dze = abs(gq) * dts * gm%wrk%ainv * winvd * gm%poroi
                capk = min(gm%bmx%la, max(s%sd(iu,ju), 0.0)) * s%bmf(iu,ju,kc)
                if (capk <= 0.0) then
                  gq = 0.0
                  dze = 0.0
                else if (dze > capk) then
                  gq = gq * (capk / dze)
                  dze = capk
                end if
                sdze = sdze + dze
                gqk(kc) = gq
              end do
              ! 変動上限(全粒径階の和で。流量段階のクリップ = 保存則は保つ)
              if (sdze > gm%dzmax) then
                gqk(1:nc) = gqk(1:nc) * (gm%dzmax / sdze)
                nclip = nclip + 1
              end if
            end if
          end if
        end if
        gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) = gqk(1:nc)
        gm%wrk%q(k, i+die(k), j+dje(k)) = 0.0          ! 等移動度の流束(側岸侵食が足す)
      end do

      ! --- 開境界面(流出は自セルの組成で容量輸送。流入は 0 を書き、容量給砂は feed_pass_bmix) ---
      if (bcs%have_open_bc .and. okc) then
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (g%x(in,jn) > 0) cycle
          if (.not. bc_open_face(in, jn)) cycle
          gqk(1:nc) = 0.0
          vve = s%vv(i,j)
          hhe = s%h(i,j)
          if (vve > 0.0 .and. hhe > p%dd) then
            ue = s%u(i,j) * gm%flv%ex(k) + s%v(i,j) * gm%flv%ey(k)   ! 正 = 域外へ
            if (ue > 0.0 .and. .not. bc_inflow_nooutflow(i, j, in, jn)) then
              hhe = max(hhe, p%dv)
              rne = g%rn(i,j)
              base = taufac_h(gm%flv, hhe) * rne**2 * vve**2 / (gm%sgrav * hhe**(1.0/3.0))
              if (ssh) base = base * slope_shear_factor(g, s, i, j)
              dme = s%bmdm(i,j)
              winvd = 1.0
              if (chn%have_width) winvd = 1.0 / chn%wfrac(i,j)
              sdze = 0.0
              do kc = 1, nc
                taus = base / gm%bmx%d(kc)
                tsc = gm%tausc * bmix_xi(gm%bmx%hiding, gm%bmx%d(kc) / dme)
                if (taus <= tsc) cycle
                qbs = bmix_qbs(gm%f_qbform, taus, tsc)
                gq = qbs * gm%bmx%qc(kc) * (ue / vve) * gm%flv%wl(k) * s%bmf(i,j,kc)
                if (gm%f_fixation > 0 .and. gq > 0.0) then
                  afx = s%fx(i,j)
                  if (afx > 0.0) then
                    tsce = tsc * (1.0 + gm%fix%ctau * afx)
                    if (taus <= tsce) then
                      gq = 0.0
                    else
                      gq = gq * (bmix_qbs(gm%f_qbform, taus, tsce) / qbs)
                    end if
                    nfix = nfix + 1
                  end if
                end if
                ! 流出: 供給側 = 自セルの可動層クランプ(粒径階版)
                dze = abs(gq) * dts * gm%wrk%ainv * winvd * gm%poroi
                capk = min(gm%bmx%la, max(s%sd(i,j), 0.0)) * s%bmf(i,j,kc)
                if (dze > capk) then
                  gq = gq * (max(capk, 0.0) / dze)
                  dze = max(capk, 0.0)
                end if
                sdze = sdze + dze
                gqk(kc) = gq
              end do
              if (sdze > gm%dzmax) then
                gqk(1:nc) = gqk(1:nc) * (gm%dzmax / sdze)
                nclip = nclip + 1
              end if
            end if
          end if
          ! 格納は所有者正準の向き(calc_fluvial と同じ)
          gm%bmx%qk(ke(k), i+die(k), j+dje(k), 1:nc) = sign_e(k) * gqk(1:nc)
          gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
        end do
      end if
    end do
  end do
  !$omp end parallel do

  ! --- 側方 Neumann の辺(粒径階ごとに内側の流束を写す) ---
  if (bcs%have_open_bc) call neumann_bed_pass_bmix(gm, g)
  ! --- 容量給砂(粒径階ごと。流入面の供給 = 倍率 × 流入セルの粒径階の正味流出) ---
  if (bcs%have_open_bc .and. gm%f_bcfeed > 0) call feed_pass_bmix(gm, p, g, s)
  ! --- 側岸侵食(等移動度の流束として wrk%q に加算。脚部の τ* は代表粒径 gm%d50) ---
  if (gm%f_berode > 0) call bank_edge_pass(gm, p, g, s, dts)
  ! --- 粒径階ごとの供給量制限 → 発散 → z・sd と交換層・下層の更新 ---
  call apply_edge_flux_bmix(gm, g, s, dts, .true.)

  gm%bmx%nclip = gm%bmx%nclip + nclip
  gm%bmx%nfix = gm%bmx%nfix + nfix
end subroutine


!----------------------------------------------------------------------
! calc_fluvial_bmix の写し: 芦田・道上 (1972) の有効掃流力(f_taupart = 2。§121)
!   式 (32) の先頭の τ*ei^(3/2) を式 (11) の u*e で求める = エッジごとに d = d_m で taueff_fac = (u*e/u*)^3 を
!   1 回求め、全粒径階の流束に掛ける(閾値・遮蔽係数・向きの係数は全 τ* のまま。d_m は原典に書かれて
!   いない ENCflow の選択。§121.2)。calc_fluvial_bmix との違いは fte を求める 2 か所と、それを掛ける 2 行だけ。
!   calc_fluvial_bmix のループ 1 を変えるときは、ここも同じく変える
!----------------------------------------------------------------------
module subroutine calc_fluvial_bmix_te(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, kc, nc, iu, ju
  real :: ue, vve, hhe, rne, base, taus, tsc, tsce, qbs, gq, sdze, winvd, afx, dze, capk
  real :: dxv, dyv, dirp0, dirp, ubar, vbar, re, gam, dme, fte
  real :: gqk(1:nbmixmax)
  integer :: nclip, nfix
  logical :: okc, okbank, ssh

  nc = gm%bmx%nc
  nclip = 0
  nfix = 0
  ssh = slope_shear_on()
  if (.not. gm%bmx%stock0) call bmix_first_step(gm, g, s)

  ! --- ステップ頭のハロ交換(calc_fluvial と同じ理由) ---
  call par_halo_cell(s%h)
  call par_halo_cell(s%u)
  call par_halo_cell(s%v)
  call par_halo_cell(s%vv)
  if (gm%flv%f_sec) then
    call eval_secflow_bmix(gm, p, g, s)
    call par_halo_cell(gm%flv%rsec)
  end if
  ! 交換層の平均粒径(帯±ハロ。組成のハロは前回の適用・給砂の末尾で交換済み)
  call bmix_update_dm(gm, s)

  ! --- ループ1: エッジの粒径階ごとの掃流砂フラックス(各成分の書き手は一意) ---
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: nclip, nfix) &
  !$omp   private(i, j, k, in, jn, kc, iu, ju, okc, okbank, ue, vve, hhe, rne, base, taus, tsc, tsce, &
  !$omp           qbs, gq, sdze, winvd, afx, dxv, dyv, dirp0, dirp, ubar, vbar, re, gam, dme, fte, gqk, dze, capk)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gqk(1:nc) = 0.0
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            okbank = .true.
            if (g%bank_active) then
              okbank = ((g%rw(i,j) > 0) .eqv. (g%rw(in,jn) > 0))
            end if
            vve = (s%vv(i,j) + s%vv(in,jn)) / 2
            hhe = (s%h(i,j) + s%h(in,jn)) / 2
            if (okbank .and. vve > 0.0 .and. hhe > p%dd) then
              ue = (s%u(i,j) + s%u(in,jn)) / 2 * gm%flv%ex(k) &
                 + (s%v(i,j) + s%v(in,jn)) / 2 * gm%flv%ey(k)
              hhe = max(hhe, p%dv)
              rne = (g%rn(i,j) + g%rn(in,jn)) / 2
              ! 粒径によらない部分(τ*_k = base / d_k。calc_fluvial と同じ閉じと補正)
              base = taufac_h(gm%flv, hhe) * rne**2 * vve**2 / (gm%sgrav * hhe**(1.0/3.0))
              if (ssh) base = base * slope_shear_factor_e(g, s, i, j, in, jn)
              ! 遮蔽係数の d_m は両セルの平均。片側の土層厚が 0(岩盤・固定床)ならもう片側(plan §3.2)
              if (s%sd(i,j) <= 0.0) then
                dme = s%bmdm(in,jn)
              else if (s%sd(in,jn) <= 0.0) then
                dme = s%bmdm(i,j)
              else
                dme = 0.5 * (s%bmdm(i,j) + s%bmdm(in,jn))
              end if
              ! 有効掃流力(§121): 粒径階によらない比 (u*e/u*)^3(d = d_m)
              fte = 1.0
              if (dme > 0.0) fte = taueff_fac(p%gg, rne, hhe, base / dme, dme)
              ! 向きの補正のうち粒径階によらない部分(t̂ + r n̂ の射影)
              if (gm%flv%f_dir) then
                ubar = (s%u(i,j) + s%u(in,jn)) / 2
                vbar = (s%v(i,j) + s%v(in,jn)) / 2
                dxv = ubar / vve
                dyv = vbar / vve
                if (gm%flv%f_sec) then
                  re = (gm%flv%rsec(i,j) + gm%flv%rsec(in,jn)) / 2
                  dxv = dxv - re * vbar / vve
                  dyv = dyv + re * ubar / vve
                end if
                dirp0 = dxv * gm%flv%ex(k) + dyv * gm%flv%ey(k)
              else
                dirp0 = ue / vve
              end if
              sdze = 0.0
              do kc = 1, nc
                taus = base / gm%bmx%d(kc)
                tsc = gm%tausc * bmix_xi(gm%bmx%hiding, gm%bmx%d(kc) / dme)
                if (taus <= tsc) cycle
                dirp = dirp0
                if (gm%flv%f_dir .and. gm%flv%f_slope) then
                  gam = gm%flv%gcoef * sqrt(tsc / taus)
                  dirp = dirp - gam * (s%z(in,jn) - s%z(i,j)) * gm%flv%rdist(k)
                end if
                if (dirp == 0.0) cycle
                qbs = bmix_qbs(gm%f_qbform, taus, tsc)
                gq = qbs * gm%bmx%qc(kc) * dirp * gm%flv%wl(k)
                gq = gq * fte                                    ! 有効掃流力(§121)
                ! 河岸面の遮断(§84.2)と供給側(風上)
                if (gq > 0.0) then
                  if (s%h(i,j) <= p%dd .or. s%z(in,jn) >= s%z(i,j) + s%h(i,j)) gq = 0.0
                  iu = i
                  ju = j
                else
                  if (s%h(in,jn) <= p%dd .or. s%z(i,j) >= s%z(in,jn) + s%h(in,jn)) gq = 0.0
                  iu = in
                  ju = jn
                end if
                if (gq == 0.0) cycle
                ! 利用可能率 = 供給側の交換層の粒径階の割合(芦田・道上 式 (32) の p_i)
                gq = gq * s%bmf(iu,ju,kc)
                ! 定着(§84.6): 供給側の定着度で粒径階の限界を τ*c,k (1 + c_τ a) に上げる
                if (gm%f_fixation > 0 .and. gq /= 0.0) then
                  afx = s%fx(iu,ju)
                  if (afx > 0.0) then
                    tsce = tsc * (1.0 + gm%fix%ctau * afx)
                    if (taus <= tsce) then
                      gq = 0.0
                    else
                      gq = gq * (bmix_qbs(gm%f_qbform, taus, tsce) / qbs)
                    end if
                    nfix = nfix + 1
                  end if
                end if
                ! 通過幅係数と動的振り替えの表(水と同じ。calc_fluvial と同じ)
                if (chn%have_frw) gq = gq * chn%frw(k, i+die(k), j+dje(k))
                if (chn%have_fwd) gq = gq * chn%fwd(k, i+die(k), j+dje(k))
                ! 可動層クランプ(calc_fluvial と同じ。粒径階版): 供給側の交換層にある粒径階 k の量
                ! L_e F_k を超える流出をこのエッジ単独で起こさない(複数エッジの同時流出の超過は
                ! apply_edge_flux_bmix の粒径階ごとの供給量制限が受ける)
                winvd = 1.0
                if (chn%have_width) winvd = 1.0 / chn%wfrac(iu,ju)
                dze = abs(gq) * dts * gm%wrk%ainv * winvd * gm%poroi
                capk = min(gm%bmx%la, max(s%sd(iu,ju), 0.0)) * s%bmf(iu,ju,kc)
                if (capk <= 0.0) then
                  gq = 0.0
                  dze = 0.0
                else if (dze > capk) then
                  gq = gq * (capk / dze)
                  dze = capk
                end if
                sdze = sdze + dze
                gqk(kc) = gq
              end do
              ! 変動上限(全粒径階の和で。流量段階のクリップ = 保存則は保つ)
              if (sdze > gm%dzmax) then
                gqk(1:nc) = gqk(1:nc) * (gm%dzmax / sdze)
                nclip = nclip + 1
              end if
            end if
          end if
        end if
        gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) = gqk(1:nc)
        gm%wrk%q(k, i+die(k), j+dje(k)) = 0.0          ! 等移動度の流束(側岸侵食が足す)
      end do

      ! --- 開境界面(流出は自セルの組成で容量輸送。流入は 0 を書き、容量給砂は feed_pass_bmix) ---
      if (bcs%have_open_bc .and. okc) then
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (g%x(in,jn) > 0) cycle
          if (.not. bc_open_face(in, jn)) cycle
          gqk(1:nc) = 0.0
          vve = s%vv(i,j)
          hhe = s%h(i,j)
          if (vve > 0.0 .and. hhe > p%dd) then
            ue = s%u(i,j) * gm%flv%ex(k) + s%v(i,j) * gm%flv%ey(k)   ! 正 = 域外へ
            if (ue > 0.0 .and. .not. bc_inflow_nooutflow(i, j, in, jn)) then
              hhe = max(hhe, p%dv)
              rne = g%rn(i,j)
              base = taufac_h(gm%flv, hhe) * rne**2 * vve**2 / (gm%sgrav * hhe**(1.0/3.0))
              if (ssh) base = base * slope_shear_factor(g, s, i, j)
              dme = s%bmdm(i,j)
              fte = 1.0
              if (dme > 0.0) fte = taueff_fac(p%gg, rne, hhe, base / dme, dme)   ! 有効掃流力(§121)
              winvd = 1.0
              if (chn%have_width) winvd = 1.0 / chn%wfrac(i,j)
              sdze = 0.0
              do kc = 1, nc
                taus = base / gm%bmx%d(kc)
                tsc = gm%tausc * bmix_xi(gm%bmx%hiding, gm%bmx%d(kc) / dme)
                if (taus <= tsc) cycle
                qbs = bmix_qbs(gm%f_qbform, taus, tsc)
                gq = qbs * gm%bmx%qc(kc) * (ue / vve) * gm%flv%wl(k) * s%bmf(i,j,kc)
                gq = gq * fte                                    ! 有効掃流力(§121)
                if (gm%f_fixation > 0 .and. gq > 0.0) then
                  afx = s%fx(i,j)
                  if (afx > 0.0) then
                    tsce = tsc * (1.0 + gm%fix%ctau * afx)
                    if (taus <= tsce) then
                      gq = 0.0
                    else
                      gq = gq * (bmix_qbs(gm%f_qbform, taus, tsce) / qbs)
                    end if
                    nfix = nfix + 1
                  end if
                end if
                ! 流出: 供給側 = 自セルの可動層クランプ(粒径階版)
                dze = abs(gq) * dts * gm%wrk%ainv * winvd * gm%poroi
                capk = min(gm%bmx%la, max(s%sd(i,j), 0.0)) * s%bmf(i,j,kc)
                if (dze > capk) then
                  gq = gq * (max(capk, 0.0) / dze)
                  dze = max(capk, 0.0)
                end if
                sdze = sdze + dze
                gqk(kc) = gq
              end do
              if (sdze > gm%dzmax) then
                gqk(1:nc) = gqk(1:nc) * (gm%dzmax / sdze)
                nclip = nclip + 1
              end if
            end if
          end if
          ! 格納は所有者正準の向き(calc_fluvial と同じ)
          gm%bmx%qk(ke(k), i+die(k), j+dje(k), 1:nc) = sign_e(k) * gqk(1:nc)
          gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
        end do
      end if
    end do
  end do
  !$omp end parallel do

  ! --- 側方 Neumann の辺(粒径階ごとに内側の流束を写す) ---
  if (bcs%have_open_bc) call neumann_bed_pass_bmix(gm, g)
  ! --- 容量給砂(粒径階ごと。流入面の供給 = 倍率 × 流入セルの粒径階の正味流出) ---
  if (bcs%have_open_bc .and. gm%f_bcfeed > 0) call feed_pass_bmix(gm, p, g, s)
  ! --- 側岸侵食(等移動度の流束として wrk%q に加算。脚部の τ* は代表粒径 gm%d50) ---
  if (gm%f_berode > 0) call bank_edge_pass(gm, p, g, s, dts)
  ! --- 粒径階ごとの供給量制限 → 発散 → z・sd と交換層・下層の更新 ---
  call apply_edge_flux_bmix(gm, g, s, dts, .true.)

  gm%bmx%nclip = gm%bmx%nclip + nclip
  gm%bmx%nfix = gm%bmx%nfix + nfix
end subroutine


!----------------------------------------------------------------------
! 側方 Neumann の辺(neumann_bed_pass の粒径階版)
!----------------------------------------------------------------------
subroutine neumann_bed_pass_bmix(gm, g)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, k, in, jn, im, jm, it, jt, nc
  logical :: nmn

  nc = gm%bmx%nc
  !$omp parallel do schedule(static) private(i, j, k, in, jn, im, jm, it, jt, nmn)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) > 0) cycle
        call bc_neumann_cell(in, jn, nmn, im, jm)
        if (.not. nmn) cycle
        it = i + (im - in)
        jt = j + (jm - jn)
        if (it < 1 .or. it > dcp%nx_g .or. jt < 1 .or. jt > dcp%ny_g) cycle
        if (g%x(it,jt) <= 0 .or. g%x(im,jm) <= 0) cycle
        if (g%sw(it,jt) > 0 .or. g%sw(im,jm) > 0) cycle
        gm%bmx%qk(ke(k), i+die(k), j+dje(k), 1:nc) = gm%bmx%qk(ke(k), it+die(k), jt+dje(k), 1:nc)
      end do
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 容量給砂(feed_pass の粒径階版。§84.9): 流入面の粒径階 k の供給 = 倍率 × 流入セルの k の正味流出 /
! 流入面の数。倍率 1 で流入セルの z と組成が固定される(f_bedfines の容量給砂と同じ考え方)。供給は
! 開境界の流入(負の流出)として台帳 voutrow に入る
!----------------------------------------------------------------------
subroutine feed_pass_bmix(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, k, in, jn, nin, m, im, jm, nc
  integer :: kin(1:8)
  real :: ue
  real :: dvk(1:nbmixmax)
  logical :: nmn

  nc = gm%bmx%nc
  !$omp parallel do schedule(static) private(i, j, k, in, jn, nin, m, kin, dvk, ue, im, jm, nmn)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd) cycle
      nin = 0
      dvk(1:nc) = 0.0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        dvk(1:nc) = dvk(1:nc) + sign_e(k) * gm%bmx%qk(ke(k), i+die(k), j+dje(k), 1:nc)
        if (g%x(in,jn) > 0) cycle
        if (.not. bc_open_face(in, jn)) cycle
        call bc_neumann_cell(in, jn, nmn, im, jm)
        if (nmn) cycle
        ue = s%u(i,j) * gm%flv%ex(k) + s%v(i,j) * gm%flv%ey(k)   ! 正 = 域外へ
        if (ue < 0.0) then
          nin = nin + 1
          kin(nin) = k
        end if
      end do
      if (nin == 0) cycle
      do m = 1, nin
        k = kin(m)
        gm%bmx%qk(ke(k), i+die(k), j+dje(k), 1:nc) = sign_e(k) * (-(gm%flv%bcfac * dvk(1:nc) / nin))
      end do
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! エッジ流量の適用(混合粒径版)。with_classes = .true.: 掃流砂(bmx%qk の粒径階ごとの流束 +
! wrk%q の等移動度の流束)、.false.: 崩落(wrk%q だけ)。
!   ループ 1.4: 等移動度の流束(側岸侵食・崩落)を、供給側の交換層の更新前の組成で粒径階ごとの流束に
!     直して bmx%qk に足す(.false. のときは qk を上書きし、領域外へ向く面は 0)。ループ 2 は組成を
!     その場で書き換えるので、近傍の組成をループ 2 で読むと、先に更新された組成で流入を数えて保存が
!     破れる(実検出: 河岸のある構成で収支が 1e-8 m3 ずれた)
!   ループ 1.5: 粒径階ごとの供給量制限(流出 ≤ 交換層にある量 L_e F_k)。縮小率 fdk をハロ交換して
!     エッジの両側が同じ値を読む(反対称性 = 粒径階ごとの保存)
!   ループ 2: 発散 → z・sd の共動更新 → Hirano の交換(bmix_update)→ 地下水容量の整合(apply_edge_flux と同じ)
!----------------------------------------------------------------------
module subroutine apply_edge_flux_bmix(gm, g, s, dts, with_classes)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  logical, intent(in) :: with_classes
  integer :: i, j, k, in, jn, jt, kc, nc, istep, nlim
  real :: qe, qq, winv, cvt, le, sd0, dz, cap, fx, vc, vclip, dm
  real :: outk(1:nbmixmax), ink(1:nbmixmax), a(1:nbmixmax), fa(1:nbmixmax), fb(1:nbmixmax)

  nc = gm%bmx%nc
  nlim = 0
  vclip = 0.0

  ! --- ループ 1.4: 等移動度の流束を粒径階ごとの流束に直す(所有成分 k = 1..4。帯界面の je+1 行は冗長計算) ---
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, qe)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        qe = gm%wrk%q(k, i+die(k), j+dje(k))                 ! 正 = (i,j) → 近傍
        if (.not. with_classes) gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) = 0.0
        if (qe > 0.0) then
          gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) = gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) &
                                                   + qe * s%bmf(i,j,1:nc)
        else if (qe < 0.0 .and. g%x(in,jn) > 0) then
          gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) = gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) &
                                                   + qe * s%bmf(in,jn,1:nc)
        end if
      end do
      ! 崩落(.false.)では領域外へ向く面の粒径階の流束を 0 にする(前回の掃流砂の値を残さない)
      if (.not. with_classes) then
        do k = 5, 8
          in = i + din(k)
          jn = j + djn(k)
          if (g%x(in,jn) <= 0) gm%bmx%qk(ke(k), i+die(k), j+dje(k), 1:nc) = 0.0
        end do
        do k = 1, 4
          in = i + din(k)
          jn = j + djn(k)
          if (g%x(in,jn) <= 0) gm%bmx%qk(k, i+die(k), j+dje(k), 1:nc) = 0.0
        end do
      end if
    end do
  end do
  !$omp end parallel do

  ! --- ループ 1.5: 粒径階ごとの供給量制限 ---
  !$omp parallel do schedule(static) reduction(+: nlim) private(i, j, k, kc, qq, winv, cvt, le, cap, outk)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%bmx%fdk(i,j,1:nc) = 1.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      outk(1:nc) = 0.0
      do k = 1, 8
        do kc = 1, nc
          qq = sign_e(k) * gm%bmx%qk(ke(k), i+die(k), j+dje(k), kc)     ! 正 = 流出
          if (qq > 0.0) outk(kc) = outk(kc) + qq
        end do
      end do
      winv = 1.0
      if (chn%have_width) winv = 1.0 / chn%wfrac(i,j)
      cvt = dts * gm%wrk%ainv * winv * gm%poroi            ! 流量 (m3/s) → 厚さ (m)
      le = min(gm%bmx%la, max(s%sd(i,j), 0.0))
      do kc = 1, nc
        if (outk(kc) > 0.0) then
          cap = le * s%bmf(i,j,kc) / cvt
          if (outk(kc) > cap) then
            gm%bmx%fdk(i,j,kc) = cap / outk(kc)
            nlim = nlim + 1
          end if
        end if
      end do
    end do
  end do
  !$omp end parallel do
  do kc = 1, nc
    call par_halo_cell(gm%bmx%fdk(:,:,kc))
  end do

  ! --- ループ 2: 発散 → z・sd と交換層・下層の更新 ---
  !$omp parallel do schedule(static) reduction(+: vclip) &
  !$omp   private(i, j, k, in, jn, kc, qq, winv, cvt, le, sd0, dz, cap, fx, vc, dm, outk, ink, a, fa, fb)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      outk(1:nc) = 0.0
      ink(1:nc) = 0.0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        do kc = 1, nc
          qq = sign_e(k) * gm%bmx%qk(ke(k), i+die(k), j+dje(k), kc)
          if (qq > 0.0) then
            outk(kc) = outk(kc) + qq * gm%bmx%fdk(i,j,kc)
          else if (qq < 0.0) then
            if (g%x(in,jn) > 0) then
              ink(kc) = ink(kc) - qq * gm%bmx%fdk(in,jn,kc)
            else
              ink(kc) = ink(kc) - qq                       ! 開境界からの流入(容量給砂・Neumann)
            end if
          end if
        end do
      end do
      winv = 1.0
      if (chn%have_width) winv = 1.0 / chn%wfrac(i,j)
      cvt = dts * gm%wrk%ainv * winv * gm%poroi
      outk(1:nc) = outk(1:nc) * cvt
      ink(1:nc) = ink(1:nc) * cvt
      sd0 = s%sd(i,j)
      le = min(gm%bmx%la, max(sd0, 0.0))
      a(1:nc) = le * s%bmf(i,j,1:nc) - outk(1:nc) + ink(1:nc)
      dz = sum(ink(1:nc)) - sum(outk(1:nc))
      ! 岩盤床クリップ(粒径階の供給量制限の後は丸め誤差分しか残らない最終防衛。台帳に計上)
      if (dz < -max(sd0, 0.0)) then
        vclip = vclip + (-dz - max(sd0, 0.0)) / gm%wrk%ainv / winv
        dz = -max(sd0, 0.0)
      end if
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      s%z(i,j) = s%z(i,j) + dz
      s%sd(i,j) = s%sd(i,j) + dz
      ! Hirano の交換と組成の更新
      fa(1:nc) = s%bmf(i,j,1:nc)
      fb(1:nc) = gm%bmx%fs(i,j,1:nc)
      call bmix_update(nc, gm%bmx%la, sd0, dz, a, fa, fb, vc)
      s%bmf(i,j,1:nc) = fa(1:nc)
      gm%bmx%fs(i,j,1:nc) = fb(1:nc)
      vclip = vclip + vc / gm%wrk%ainv / winv
      dm = 0.0
      do kc = 1, nc
        dm = dm + fa(kc) * gm%bmx%d(kc)
      end do
      s%bmdm(i,j) = dm
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す(apply_edge_flux と同じ)
      if (s%gw_active) then
        cap = s%sd(i,j) * g%sy0
        if (s%hg(i,j) > cap) then
          fx = s%hg(i,j) - cap
          s%hg(i,j) = cap
          if (sect_cell(s, i, j)) then
            call sect_add_vh(s, i, j, fx * gw_to_h(s, i, j))
          else
            s%h(i,j) = s%h(i,j) + fx * gw_to_h(s, i, j)
          end if
        end if
      end if
    end do
  end do
  !$omp end parallel do

  ! --- 台帳: 開境界を通った粒径階ごとの正味の固体体積(流出 − 流入。容量給砂は負の流出) ---
  if (with_classes .and. bcs%have_open_bc) then
    !$omp parallel do schedule(static) private(i, j, k, in, jn, kc, istep, qq)
    do j = dcp%js, dcp%je
      istep = 1
      if (j /= 1 .and. j /= dcp%ny_g) istep = max(1, dcp%nx_g - 1)
      do i = 1, dcp%nx_g, istep
        if (i < g%wx(1,j) .or. i > g%wx(2,j)) cycle
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (in >= 1 .and. in <= dcp%nx_g .and. jn >= 1 .and. jn <= dcp%ny_g) cycle
          do kc = 1, nc
            qq = sign_e(k) * gm%bmx%qk(ke(k), i+die(k), j+dje(k), kc)
            if (qq > 0.0) qq = qq * gm%bmx%fdk(i,j,kc)
            if (qq /= 0.0) gm%bmx%voutrow(j,kc) = gm%bmx%voutrow(j,kc) + real(qq * dts, real64)
          end do
        end do
      end do
    end do
    !$omp end parallel do
  end if

  do kc = 1, nc
    call par_halo_cell(s%bmf(:,:,kc))
  end do
  gm%bmx%nlimk = gm%bmx%nlimk + nlim
  gm%bmx%vclip = gm%bmx%vclip + vclip
end subroutine


!----------------------------------------------------------------------
! 区間流入の粒径階ごとの給砂(apply_bedfeed の粒径階版。§84.9): 流入セルの交換層に入れ、
! z・sd を共動更新する(土層厚 0 のセルでは給砂の組成で交換層を作る)
!----------------------------------------------------------------------
module subroutine apply_bedfeed_bmix(gm, g, s, b, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_boundary), intent(in) :: b
  real, intent(in) :: dts
  integer :: i, j, kc, nc
  real :: winvd, cvt, sd0, dz, le, vc, vclip, dm
  real :: a(1:nbmixmax), fa(1:nbmixmax), fb(1:nbmixmax), dzk(1:nbmixmax)

  nc = gm%bmx%nc
  vclip = 0.0
  if (.not. gm%bmx%stock0) call bmix_first_step(gm, g, s)
  !$omp parallel do schedule(static) reduction(+: vclip) private(i, j, kc, winvd, cvt, sd0, dz, le, vc, dm, a, fa, fb, dzk)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (all(b%qbink(i,j,1:nc) <= 0.0)) cycle
      winvd = 1.0
      if (chn%have_width) winvd = 1.0 / chn%wfrac(i,j)
      cvt = dts * gm%wrk%ainv * winvd * gm%poroi
      dzk(1:nc) = max(b%qbink(i,j,1:nc), 0.0) * cvt
      dz = sum(dzk(1:nc))
      sd0 = s%sd(i,j)
      le = min(gm%bmx%la, max(sd0, 0.0))
      a(1:nc) = le * s%bmf(i,j,1:nc) + dzk(1:nc)
      s%z(i,j) = s%z(i,j) + dz
      s%sd(i,j) = s%sd(i,j) + dz
      fa(1:nc) = s%bmf(i,j,1:nc)
      fb(1:nc) = gm%bmx%fs(i,j,1:nc)
      call bmix_update(nc, gm%bmx%la, sd0, dz, a, fa, fb, vc)
      s%bmf(i,j,1:nc) = fa(1:nc)
      gm%bmx%fs(i,j,1:nc) = fb(1:nc)
      vclip = vclip + vc / gm%wrk%ainv / winvd
      dm = 0.0
      do kc = 1, nc
        dm = dm + fa(kc) * gm%bmx%d(kc)
      end do
      s%bmdm(i,j) = dm
      do kc = 1, nc
        gm%bmx%feedrow(j,kc) = gm%bmx%feedrow(j,kc) + real(max(b%qbink(i,j,kc), 0.0) * dts, real64)
      end do
    end do
  end do
  !$omp end parallel do
  gm%bmx%vclip = gm%bmx%vclip + vclip
  call par_halo_cell(s%z)
  call par_halo_cell(s%sd)
  do kc = 1, nc
    call par_halo_cell(s%bmf(:,:,kc))
  end do
end subroutine


!----------------------------------------------------------------------
! Hirano の交換と組成の更新(1 セル。plan §3.4)
!   a: 交換層の内容(厚さ。流出入・給砂を反映した後。和 = L_e + dz)
!   界面(z − L_e)が上がるとき: 交換層の余り t を交換層の組成で下層へ(下層は一様に混ぜる)
!   下がるとき: 不足 dd を下層から下層の組成で交換層へ
!   土層がなくなったら組成は前の値のまま(次に積もるとき入る土砂の組成で作り直す)。
!   丸めの負の内容は 0 にして、動かした厚さを vc に返す
!----------------------------------------------------------------------
pure subroutine bmix_update(nc, la, sd0, dz, a, fa, fb, vc)
  integer, intent(in) :: nc
  real, intent(in) :: la, sd0, dz
  real, intent(inout) :: a(:)
  real, intent(inout) :: fa(:), fb(:)
  real, intent(out) :: vc
  real :: le, ls, sd1, le1, ls1, tot, t, dd, sm
  integer :: kc

  vc = 0.0
  le = min(la, max(sd0, 0.0))
  ls = max(sd0, 0.0) - le
  sd1 = max(sd0, 0.0) + dz
  if (sd1 <= 0.0) return
  le1 = min(la, sd1)
  ls1 = sd1 - le1
  do kc = 1, nc
    if (a(kc) < 0.0) then
      vc = vc - a(kc)
      a(kc) = 0.0
    end if
  end do
  tot = sum(a(1:nc))
  if (tot >= le1) then
    if (tot > 0.0) fa(1:nc) = a(1:nc) / tot
    t = tot - le1
    if (t > 0.0 .and. ls1 > 0.0) fb(1:nc) = (ls * fb(1:nc) + t * fa(1:nc)) / (ls + t)
  else
    dd = le1 - tot
    fa(1:nc) = (a(1:nc) + dd * fb(1:nc)) / le1
  end if
  sm = sum(fa(1:nc))
  if (sm > 0.0) fa(1:nc) = fa(1:nc) / sm
  sm = sum(fb(1:nc))
  if (sm > 0.0) fb(1:nc) = fb(1:nc) / sm
end subroutine


!----------------------------------------------------------------------
! 遮蔽係数 ξ = τ*c,k / τ*cm(修正 Egiazaroff。芦田・道上 1972 式 (31))。r = d_k / d_m
!   r < 0.4: ξ = 0.85 / r、r ≥ 0.4: ξ = {log10 19 / log10(19 r)}²。hid = 0 は遮蔽なし(ξ = 1)
!   原典の式 (31) は u*c,k² / u*cm² = τc,k / τcm(r < 0.4 で 0.85、r ≥ 0.4 で {log10 19 / log10(19 r)}² r)で
!   書かれ、ξ はその無次元形(1/r 倍)。境界 r = 0.4 は原典どおり対数の側(本文で確認。2026-11-23)
!----------------------------------------------------------------------
pure function bmix_xi(hid, r) result(xi)
  integer, intent(in) :: hid
  real, intent(in) :: r
  real :: xi
  if (hid == 0) then
    xi = 1.0
  else if (r < 0.4) then
    xi = 0.85 / r
  else
    xi = (log10(19.0) / log10(19.0 * r))**2
  end if
end function


!----------------------------------------------------------------------
! 無次元流砂量(qbs_form と同じ式。芦田・道上 / MPM)
!----------------------------------------------------------------------
pure function bmix_qbs(form, taus, tsc) result(qbs)
  integer, intent(in) :: form
  real, intent(in) :: taus, tsc
  real :: qbs
  if (form == 1) then
    qbs = 17.0 * taus**1.5 * (1.0 - tsc / taus) * (1.0 - sqrt(tsc / taus))
  else
    qbs = 8.0 * (taus - tsc)**1.5
  end if
end function


!----------------------------------------------------------------------
! 累積割合 pct の粒径(粒径階の累積を粒径の対数で補間。最初の粒径階で届けばその粒径)
!----------------------------------------------------------------------
pure function bmix_dpct(nc, d, f, pct) result(dp)
  integer, intent(in) :: nc
  real, intent(in) :: d(:), f(:), pct
  real :: dp
  real :: cum, cprev, w
  integer :: kc
  cum = 0.0
  dp = d(nc)
  do kc = 1, nc
    cprev = cum
    cum = cum + f(kc)
    if (cum >= pct) then
      if (kc == 1 .or. cum <= cprev) then
        dp = d(kc)
      else
        w = (pct - cprev) / (cum - cprev)
        dp = exp(log(d(kc-1)) + w * (log(d(kc)) - log(d(kc-1))))
      end if
      return
    end if
  end do
end function


!----------------------------------------------------------------------
! 平衡二次流の河床近傍横断流速比 r = N* h κ(eval_secflow の写し。§84.3)
!----------------------------------------------------------------------
subroutine eval_secflow_bmix(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j
  real :: ux, uy, vx, vy, kap, r

  !$omp parallel do schedule(static) private(i, j, ux, uy, vx, vy, kap, r)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      r = 0.0
      if (g%x(i,j) > 0) then
        if (g%sw(i,j) <= 0 .and. s%h(i,j) > p%dd .and. s%vv(i,j) > gm%flv%vmin) then
          if (wet4_bmix(p, g, s, i, j)) then
            ux = (s%u(i+1,j) - s%u(i-1,j)) / (2 * g%dx)
            vx = (s%v(i+1,j) - s%v(i-1,j)) / (2 * g%dx)
            uy = (s%u(i,j+1) - s%u(i,j-1)) / (2 * g%dy)
            vy = (s%v(i,j+1) - s%v(i,j-1)) / (2 * g%dy)
            kap = (s%u(i,j)**2 * vx - s%v(i,j)**2 * uy &
                   + s%u(i,j) * s%v(i,j) * (vy - ux)) / s%vv(i,j)**3
            r = gm%flv%nstar * s%h(i,j) * kap
            r = max(-gm%flv%rmax, min(gm%flv%rmax, r))
          end if
        end if
      end if
      gm%flv%rsec(i,j) = r
    end do
  end do
  !$omp end parallel do
end subroutine


pure function wet4_bmix(p, g, s, i, j) result(ok)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  logical :: ok
  integer :: k, in, jn
  ok = .true.
  do k = 2, 7, 5               ! k = 2 (j-1), 7 (j+1)
    in = i + din(k); jn = j + djn(k)
    if (g%x(in,jn) <= 0) then
      ok = .false.; return
    end if
    if (g%sw(in,jn) > 0 .or. s%h(in,jn) <= p%dd) then
      ok = .false.; return
    end if
  end do
  do k = 4, 5                  ! k = 4 (i-1), 5 (i+1)
    in = i + din(k); jn = j + djn(k)
    if (g%x(in,jn) <= 0) then
      ok = .false.; return
    end if
    if (g%sw(in,jn) > 0 .or. s%h(in,jn) <= p%dd) then
      ok = .false.; return
    end if
  end do
end function

end submodule
