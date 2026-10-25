module m_gwflow_bed
  ! ========= 河床交換能(河道セルと地下水の交換の上限。f_gwbed) =========
  ! 河道マスク(fn_rw。rw > 0)のセルについて、河床・河岸を通る地表水と
  ! 層1(土層)地下水の交換に単位面積あたりの上限 k_bed (m/s) を与える
  ! (developer.md §16.5。2026-10-25)。MODFLOW RIV の河床コンダクタンスに
  ! 相当する役を、柱状量の枠組みに合う「交換能 = 上限」の形(管路層の
  ! 層間交換 gwc_leak と同型)で表す。Δh/M に比例する Darcy 形は採らない
  ! (河床層厚 M の追加入力と M→0 の発散回避が要る。独自の簡略化)。
  !
  ! 【作用点】
  !   (1) 鉛直: 河道セルの鉛直浸透能(バケツ gw_infil_mmh / Green-Ampt の
  !       K_sv)を k_bed で置き換える(失水側。地下水頭が容量に達しない間の
  !       片方向浸透 = 河床から切り離された perched 河川に相当)。
  !       k_bed = 0 のセルは不浸透(ライニング水路)。
  !   (2) 側方: 層1の側方流動(m_gwflow_lateral の lateral_core)で、河道
  !       セルと非河道セルの間のエッジ流量を |q| <= k_bed·l_k·h_e に抑える
  !       (l_k: 通過幅、h_e: 界面飽和帯厚 = 流量を運ぶ面の面積)。
  !       両向きに同じ上限 = 得水(湧出)側も k_bed で律速される。河道同士・
  !       非河道同士のエッジは対象外。層2・管路層・塩水は対象外。
  !   いずれも減らす側の作用のみなので、陽解法の安定条件は変わらない。
  !
  ! 【結合】
  !   s%kbed(帯+ハロ。m/s。非河道セルは負の番兵 = 上書きなし)を本
  !   モジュールが init で構築し、鉛直モデル・側方カーネルが
  !   `allocated(s%kbed)` ガードで参照する(s%frofac と同型 = 無効時は
  !   配列未確保・分岐なし・ビット一致)。静的係数なので毎ステップの更新も
  !   私有の save/restore もない(契約5の私有ファイルは不要)。
  !
  ! 【入力】&list_gwflow_bed(fn_gwflow 内)
  !   gwbed_k_mmh : 河道セル一律の交換能 (mm/h)。0 を許す(= 不透。
  !                 0 に意味があるため既定を置かない。§64.1)
  !   fn_gwbed_k  : セル別マップ (mm/h)。指定で一律値より優先。河道セルの
  !                 値だけを使う(非河道セルの値は無視)。負値は停止
  !   どちらも未指定なら停止(与件)。fn_rw(河道マスク)が必須。
  !   鉛直モデルか側方モデルのどちらかが有効であること(どちらも無効なら
  !   作用点がない = 設定の齟齬として停止)
  ! =====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_fileio, only : fileio_read_matrix
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_scatter_cell, par_allreduce_sumi
  use m_util, only : itoa, rtoa
  implicit none
  private
  public :: gwflow_bed_init
  public :: gwflow_bed_dispose
  public :: t_gwbed

  ! モデル私有の設定(実体は切替器 m_gwflow の t_gwflow が持つ)
  type t_gwbed
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 河床交換能の初期化(固有グループを自分で読み、s%kbed を構築する)
!----------------------------------------------------------------------
subroutine gwflow_bed_init(gwb, p, g, s)
  type(t_gwbed), intent(inout) :: gwb
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: un, ios, i, j
  integer :: ncnt(2)
  real :: gwbed_k_mmh
  character(len=1024) :: fn_gwbed_k
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  namelist /list_gwflow_bed/ gwbed_k_mmh, fn_gwbed_k

  gwbed_k_mmh = -1.0        ! 負 = 未指定(0 は有効な指定 = 不透)
  fn_gwbed_k = ""

  call par_info("reading list_gwflow_bed in " // trim(p%fn_gwflow))
  open(newunit=un, file=trim(p%fn_gwflow), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_bed: cannot open " // trim(p%fn_gwflow))
  read(un, nml=list_gwflow_bed, iostat=ios)
  if (ios /= 0) call par_stop("list_gwflow_bed: cannot read namelist")
  close(un)

  ! 河道マスクが必須(init 時の g%rw は全域形。判定は全ランク同一)
  if (.not. any(g%rw(:,:) > 0)) then
    call par_stop("list_gwflow: f_gwbed=1 requires channel cells (fn_rw in list_geoinfo)")
  end if
  if (len_trim(fn_gwbed_k) == 0 .and. gwbed_k_mmh < 0.0) then
    call par_stop("list_gwflow_bed: set gwbed_k_mmh >= 0 (0 = impervious bed) or fn_gwbed_k")
  end if

  ! 帯+ハロの係数場。非河道セルは負の番兵(鉛直モデルは上書きしない)
  allocate(s%kbed(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = -1.0)
  if (len_trim(fn_gwbed_k) > 0) then
    ! rank0 が全域マップを読み par_scatter_cell で帯+ハロへ配布する(方式2)
    fname = trim(p%dir_data) // "/" // trim(fn_gwbed_k)
    call par_info(" reading " // fname)
    if (is_root) then
      allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
      call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
      call par_scatter_cell(wk, s%kbed)
    else
      call par_scatter_cell(dum, s%kbed)
    end if
    ! 河道セルだけを有効化(mm/h -> m/s)。非河道セルは番兵へ戻す。
    ! 負値はデータ不良として停止(判定は配布後の帯で。全ランク同一の結論)
    do j = dcp%jsh, dcp%jeh
      do i = dcp%ish, dcp%ieh
        if (g%x(i,j) > 0 .and. g%rw(i,j) > 0) then
          if (s%kbed(i,j) < 0.0 .and. j >= dcp%js .and. j <= dcp%je) then
            write(msg,'(a,2i7,es12.4)') "gwflow_bed: negative gwbed_k at", i, j, s%kbed(i,j)
            call par_stop(trim(msg))
          end if
          s%kbed(i,j) = max(s%kbed(i,j), 0.0) / 1000.0 / 3600.0
        else
          s%kbed(i,j) = -1.0
        end if
      end do
    end do
  else
    do j = dcp%jsh, dcp%jeh
      do i = dcp%ish, dcp%ieh
        if (g%x(i,j) > 0 .and. g%rw(i,j) > 0) s%kbed(i,j) = gwbed_k_mmh / 1000.0 / 3600.0
      end do
    end do
    call par_info("gwflow_bed: gwbed_k = " // rtoa(gwbed_k_mmh) // " mm/h on all channel cells")
  end if

  ! 件数の表示(河道セル数と不透(k=0)セル数。帯のみを数えて総和)
  ncnt(:) = 0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (s%kbed(i,j) < 0.0) cycle
      ncnt(1) = ncnt(1) + 1
      if (s%kbed(i,j) <= 0.0) ncnt(2) = ncnt(2) + 1
    end do
  end do
  call par_allreduce_sumi(ncnt)
  call par_info("gwflow_bed: bed exchange limit on " // itoa(ncnt(1)) // " channel cells (" &
                // itoa(ncnt(2)) // " impervious)")

  gwb%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 破棄(s%kbed の解放は m_state_dispose が行う。私有状態なし)
!----------------------------------------------------------------------
subroutine gwflow_bed_dispose(gwb)
  type(t_gwbed), intent(inout) :: gwb
  gwb%initialized = .false.
end subroutine

end module
