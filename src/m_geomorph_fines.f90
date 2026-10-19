!======================================================================
! m_geomorph の submodule: 河床の細粒分の帳簿(f_bedfines)
!   蛇行発達への拡張の段 5c(docs/meander_plan.md §3.6c、developer.md §84.10)。
!   浮遊砂(susp_d50)の浸食は土層 s%sd をそのまま細粒分として巻き上げるため、
!   掃流砂の河床(fluv_d50)が細粒分の速さで削られる。既存の 2 成分の区別
!   (掃流砂 1 粒径・浮遊砂 1 粒径)を河床側にも持たせ、「河床のうち浮遊砂として
!   動く成分の厚さ」s%sf(m。0 <= sf <= sd。出力 Sf)を柱状量 1 枚で帳簿づけする。
!   一般の混合粒径(交換層 × 粒径階)は採らない(方針 §0。遮蔽・露出関数なし)。
!
!   利用可能率 f = min(1, sf / L_a)(L_a = 交換層厚 fines_la。交換層に占める
!   細粒分の割合とみなす):
!     - 浮遊砂 E-D(calc_suspend): 浸食 E = f・w_f・C_eq、浸食量 <= sf。
!       沈降・乾燥時の全量堆積は sd・sf を同じ Δz で増やす
!     - 掃流砂・側岸侵食・崩落・容量給砂(apply_edge_flux): 細粒分は掃流砂と
!       一緒に動く(等移動度)。流出 q の ff_own 倍が供給側の sf から出て、受け手の
!       sf に入る(z・sd は従来どおり q の全量で動く)。ff はループ 1.5 で
!       「細粒分の流出 <= sf、粗粒分の流出 <= sd − sf」を満たす範囲に入れる
!       (0 <= sf <= sd が構造的に成立)。域外(開境界 = 容量給砂)からの流入は
!       受け手自身の ff の組成(給砂 = 流入セルが出すものと同じ → 入口の z・sf
!       とも固定)。浮遊砂との交換は calc_suspend の E-D だけが担う(解放された
!       細粒分をその場で懸濁させる案は、浮遊の容量と無関係に hs が増えて
!       滞水域に積もり発散した。§84.10)
!     - 斜面浸食 f_wash: 浸食率に f を乗じ sf から減らす
!     - f_splash・f_bedslide・f_wthr・inflow_qb: 粗粒として扱う(sf <= sd の
!       クリップのみ)。f_debris は f_suspend と排他
!   状態: s%sf(帯±ハロ。更新は自帯のみ。近傍は読まない = ハロ交換不要)。
!     初期値は fines_frac0 × sd(一様割合)。私有 save geomorph_fines.dat
!     (契約 5。restart_write_cell 1 面。§83)。作業配列 ff(帯±ハロ。
!     ループ 1.5 で作り fdon と同様にハロ交換)。台帳 vfree(掃流砂に同伴して
!     動いた細粒分の固体体積。ランク局所)。
!   無効時は配列未確保・呼び出しなし(ゼロコスト。既存 reference 不変)。
!======================================================================
submodule(m_geomorph) m_geomorph_fines
  use m_parallel, only : par_info, par_warn, par_stop, dcp, is_root, par_halo_cell
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : rtoa
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_fines(gm, p, g, s, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_geomorph), intent(in) :: list

  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (gm%f_suspend <= 0) then
    call par_stop("list_geomorph: f_bedfines=1 requires f_suspend=1 (the fines are the suspended class)")
  end if
  if (list%fines_la <= 0.0) then
    call par_stop("list_geomorph: f_bedfines=1 requires fines_la > 0 (exchange layer thickness, m)")
  end if
  if (list%fines_frac0 < 0.0 .or. list%fines_frac0 > 1.0) then
    call par_stop("list_geomorph: fines_frac0 must be in [0,1]")
  end if
  gm%fin%la = list%fines_la
  gm%fin%lainv = 1.0 / list%fines_la
  gm%fin%frac0 = list%fines_frac0
  call par_info("geomorph: bed fines ledger on (L_a = " // rtoa(list%fines_la) &
                // " m, initial fines fraction = " // rtoa(list%fines_frac0) // ")")

  ! --- 状態(有効時のみ確保 = 無効時ゼロコスト)。sd は setup_sd 転記済み ---
  if (.not. allocated(s%sf)) allocate(s%sf(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%fin%ff(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_state_restore > 0) then
    call restore_fines(gm, p, g, s)
  else
    s%sf(:,:) = gm%fin%frac0 * s%sd(:,:)
  end if
end subroutine


!----------------------------------------------------------------------
module subroutine dispose_fines(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (p%f_state_save > 0) call save_fines(gm, p, g, s)
  ! ランク局所の台帳
  call par_warn("geomorph: bed load carried " // rtoa(gm%fin%vfree) &
                // " m3 (solid) of bed fines along with it")
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル geomorph_fines.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_fines(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: un
  if (g%initialized .or. gm%initialized) continue  ! 引数未使用の警告を抑制
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/geomorph_fines.dat', form='unformatted', &
         status='replace')
  end if
  ! 帯配列を窓形に集約しながら rank0 が RLE で書く(§83。書き並びは restore と同時に更新)
  call restart_write_cell(un, s%sf)
  if (is_root) close(un)
end subroutine


subroutine restore_fines(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un
  if (g%initialized .or. gm%initialized) continue  ! 引数未使用の警告を抑制

  fname = trim(p%dir_save)//'/geomorph_fines.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("geomorph: bed fines state file not found (was f_bedfines enabled when saving): " &
                  // fname)
  end if
  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, s%sf)
  if (is_root) close(un)
  call par_halo_cell(s%sf)
end subroutine

end submodule
