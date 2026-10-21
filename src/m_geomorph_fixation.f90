!======================================================================
! m_geomorph の submodule: 定着(f_fixation)
!   蛇行発達への拡張の段 3(docs/meander_plan.md §3.4 改訂版、developer.md §84.6)。
!   内岸の砂州は掃流砂では供給セルの水面までしか堆積しない(§84.2 R2)ため、
!   一定流量では陸地にならず横移動が拡幅で止まる。低水期に露出した砂州に
!   植生等の定着が進み、出水時の再侵食に抵抗する過程を、セルスカラーの
!   定着度 a ∈ [0,1](s%fx。出力 Fx)で表す。
!
!   発展(地形時間 dts = dt·idt·morfac で評価。定着は地形変化と同じ時間軸):
!     乾燥(h <= dd): a ← 1 − (1 − a)·exp(−dts/T_fix)、zref = z
!     湿潤(h >  dd): a ← a·exp(−dts/T_dec)(fix_tdec > 0 のとき。冠水の継続で
!                    定着が失われる = 植生の枯死・表層の軟化。§84.12)、
!                    zref = max(zref, z)(定着面への堆積は表層を更新)、
!                    zref − z > dz_reset なら a = 0、zref = z(表層が剥がれる)
!   効果(標高・体積には触れない):
!     τ*c,eff = τ*c·(1 + c_τ·a_donor) を供給(風上)側セルの掃流砂の閾値と
!     流砂量式に(calc_fluvial ループ 1)、τ*c,b·(1 + c_τ,b·a_b) を側岸侵食の
!     河岸セルに(bank_edge_pass)適用する(c_τ,b = fix_ctau_bank。負なら c_τ と
!     同じ、0 で河岸には効かせない。根系は表層の河床材料を固めるが河岸脚部の
!     洗掘には効きにくい、という非対称を表す。§84.12)。受け手側の a は見ない(定着面への
!     堆積は妨げない)。浮遊砂 E-D(calc_suspend)では浸食項(平衡濃度)だけを
!     減らし沈降は変えない(§84.8: f_esform=1 は τ*c,s (1 + c_τ a)、2 は
!     ceq/(1 + c_τ a))。安息角崩落には効かせない。
!   粗度(fix_cn > 0。§84.8): 流れの摩擦項の Manning n を n (1 + c_n a) にする。
!     受け渡しは t_state の動的粗度 s%rnv(本 submodule が確保・更新し、
!     m_swflow_enc は allocated なら g%rn の代わりに読む)。流砂の τ* は g%rn の
!     まま(植生の抵抗は形状抵抗で粒子にかかるせん断ではない)。a の純関数なので
!     save せず、restore 後は a から作り直す。
!   状態: s%fx(帯±ハロ。更新は自帯、末尾で par_halo_cell)と基準高 zref
!     (私有。自帯のみ使用)。私有 save geomorph_fixation.dat(契約 5。
!     m_restart の restart_write/read_cell で 2 面。§83)。
!   無効時は配列未確保・呼び出しなし(ゼロコスト)。
!======================================================================
submodule(m_geomorph) m_geomorph_fixation
  use m_parallel, only : par_info, par_warn, par_stop, dcp, is_root, par_halo_cell
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : itoa, rtoa
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_fixation(gm, p, g, s, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_geomorph), intent(in) :: list
  real, parameter :: hr_s = 3600.0

  if (g%initialized) continue  ! 引数未使用の警告を抑制
  ! 文献照合待ちの係数は既定を置かず明示指定を要求する(§19.8。N*・μ と同じ)
  if (list%fix_tfix <= 0.0) then
    call par_stop("list_geomorph: f_fixation=1 requires fix_tfix > 0 (fixation time scale, h)")
  end if
  if (list%fix_ctau <= 0.0) then
    call par_stop("list_geomorph: f_fixation=1 requires fix_ctau > 0 (critical shear increase ratio)")
  end if
  gm%fix%tfix = list%fix_tfix * hr_s
  gm%fix%ctau = list%fix_ctau
  ! 既定 0.1 m(定着面 = 根系層の厚さの目安。構造的パラメータ)
  gm%fix%dzreset = gm_param("fix_dzreset", list%fix_dzreset, 0.1, " m")
  if (gm%fix%dzreset <= 0.0) call par_stop("list_geomorph: fix_dzreset must be > 0")
  if (list%fix_cn < 0.0) call par_stop("list_geomorph: fix_cn must be >= 0")
  gm%fix%cn = list%fix_cn
  ! 冠水時の減衰(0 = なし = 従来)と河岸専用の増分比(負 = c_τ と同じ = 従来)。§84.12
  if (list%fix_tdec < 0.0) call par_stop("list_geomorph: fix_tdec must be >= 0 (0 = no decay)")
  gm%fix%tdec = list%fix_tdec * hr_s
  if (list%fix_ctau_bank < 0.0) then
    gm%fix%ctaub = gm%fix%ctau
  else
    gm%fix%ctaub = list%fix_ctau_bank
  end if
  call par_info("geomorph: fixation on (T_fix = " // rtoa(list%fix_tfix) &
                // " h, c_tau = " // rtoa(list%fix_ctau) // ", c_n = " // rtoa(list%fix_cn) // ")")
  if (gm%fix%tdec > 0.0) then
    call par_info("geomorph: fixation decays while submerged (T_dec = " // rtoa(list%fix_tdec) // " h)")
  end if
  if (list%fix_ctau_bank >= 0.0) then
    call par_info("geomorph: fixation on banks uses c_tau_bank = " // rtoa(gm%fix%ctaub))
  end if

  ! --- 状態(有効時のみ確保 = 無効時ゼロコスト) ---
  if (.not. allocated(s%fx)) allocate(s%fx(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  ! 基準高は番兵 −huge で始める: 最初の更新で乾燥なら zref = z、湿潤なら
  ! max(zref, z) = z が入り、どちらも分岐なしで初期化される
  allocate(gm%fix%zref(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = -huge(1.0))
  if (p%f_state_restore > 0) call restore_fixation(gm, p, g, s)
  ! 動的粗度(fix_cn > 0 のときだけ確保 = 0 なら流れ側は g%rn のまま厳密に不変)。
  ! 初期値(restore 後は復元した a から)をここで作る
  if (gm%fix%cn > 0.0) then
    allocate(s%rnv(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    call set_rough(gm, g, s)
  end if
end subroutine


!----------------------------------------------------------------------
! 動的粗度 n_eff = n (1 + c_n a) を自帯で作りハロを交換する(全ランク同一判定)
!----------------------------------------------------------------------
subroutine set_rough(gm, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      s%rnv(i,j) = g%rn(i,j) * (1.0 + gm%fix%cn * s%fx(i,j))
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(s%rnv)
end subroutine


!----------------------------------------------------------------------
! 定着度・基準高の更新(calc の末尾。z 更新プロセス群の後)
!----------------------------------------------------------------------
module subroutine update_fixation(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, nreset
  real :: ef, ed
  logical :: decay

  ef = exp(-dts / gm%fix%tfix)
  ! 冠水時の減衰係数(fix_tdec = 0 なら乗算しない = 従来とビット一致)
  decay = (gm%fix%tdec > 0.0)
  ed = 1.0
  if (decay) ed = exp(-dts / gm%fix%tdec)
  nreset = 0
  !$omp parallel do schedule(static) private(i, j) reduction(+: nreset)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd) then
        ! 乾燥: 定着が育つ(厳密解)。定着面 = 現在の地盤
        s%fx(i,j) = 1.0 - (1.0 - s%fx(i,j)) * ef
        gm%fix%zref(i,j) = s%z(i,j)
      else
        ! 湿潤: 冠水の継続で定着が減衰し(T_dec)、堆積は定着面を押し上げ、
        ! 定着面からの累積浸食が閾値を超えると表層が剥がれて定着が失われる
        if (decay) then
          if (s%fx(i,j) > 0.0) s%fx(i,j) = s%fx(i,j) * ed
        end if
        if (s%z(i,j) > gm%fix%zref(i,j)) gm%fix%zref(i,j) = s%z(i,j)
        if (gm%fix%zref(i,j) - s%z(i,j) > gm%fix%dzreset) then
          if (s%fx(i,j) > 0.0) nreset = nreset + 1
          s%fx(i,j) = 0.0
          gm%fix%zref(i,j) = s%z(i,j)
        end if
      end if
    end do
  end do
  !$omp end parallel do
  gm%fix%nreset = gm%fix%nreset + nreset
  ! 供給側の a はエッジの両側(ハロ行 je+1 の冗長計算を含む)で読まれる
  call par_halo_cell(s%fx)
  if (gm%fix%cn > 0.0) call set_rough(gm, g, s)
end subroutine


!----------------------------------------------------------------------
module subroutine dispose_fixation(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (p%f_state_save > 0) call save_fixation(gm, p, g, s)
  ! ランク局所の台帳
  call par_warn("geomorph: fixation reduced the bed load on " // itoa(gm%fix%nfix) &
                // " edge-updates and was reset by erosion in " // itoa(gm%fix%nreset) // " cell-updates")
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル geomorph_fixation.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_fixation(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/geomorph_fixation.dat', form='unformatted', &
         status='replace')
  end if
  ! 帯配列を窓形に集約しながら rank0 が RLE で書く(§83。書き並びは restore と同時に更新)
  call restart_write_cell(un, s%fx)
  call restart_write_cell(un, gm%fix%zref)
  if (is_root) close(un)
end subroutine


subroutine restore_fixation(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制

  fname = trim(p%dir_save)//'/geomorph_fixation.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("geomorph: fixation state file not found (was f_fixation enabled when saving): " &
                  // fname)
  end if
  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, s%fx)
  call restart_read_cell(un, gm%fix%zref)
  if (is_root) close(un)
  call par_halo_cell(s%fx)
end subroutine

end submodule
