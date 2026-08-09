submodule (m_boundary) m_boundary_structure
  ! 内部水理構造物族(§22)の実装分離。
  !   - 共通骨格: 2つのセル集合(取水 cin → 吐口 cout または域外)+
  !     水理則 Q(基準値の純関数)+ 質量保存的な転送
  !   - 状態(t_structure)と公開経路(interface)は親 m_boundary が持つ
  !     (makebdc からの呼び出しと boundary_h の適用が親の型を読むため)
  !   - 本サブモジュール: namelist(fn_structure)の解釈・検証・格納
  !     (init_structure)と、毎ステップの水理則評価(structure_makebdc)
  !   - 適用(転送)は m_swflow_enc_bc の boundary_h の構造物節
  !   - 水理則は手続きポインタ成分 law で切り替える(排他切替の様式)。
  !     現在状態の純関数=履歴状態なし(save/restore 対象外)。内部状態を
  !     持つ種別(ダム貯留・ゲート開度・ヒステリシス)は save 対応と併せて
  !     第2弾(handoff)
  ! 親の private 手続き(interp_series, read_cell_file2)はホスト結合で使う
  ! (手続き本体レベルの単段参照は nvfortran でも解決できる。§13)。
  ! dcp 等の use 経由の名前は nvfortran バグ回避のため submodule 側で
  ! 直接 use する(§13)。補助手続きは contained にしない(§13)
  use, intrinsic :: iso_fortran_env, only : r64 => real64
  use m_parallel, only : par_stop, par_info, is_root, dcp, &
                         par_allreduce_sumr, par_allreduce_maxi, par_sum_rows
  use m_util, only : itoa
  use m_sysdep_util, only : sysdep_mkdir
  use list_structure, only : t_list_structure, list_structure_read, &
                             nstmax, nstccmax
  implicit none

contains

!----------------------------------------------------------------------
! 内部水理構造物族の初期化(初期化ゾーン2: 全域マスク前提)。
! 有効化は fn_structure の指定の有無。型別グループごとに解釈し、
! b%struct に通し番号で格納する
!----------------------------------------------------------------------
module subroutine init_structure(b, p, g)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_structure) :: list
  integer :: npump, nculv, ndiv, ndam

  if (len_trim(p%fn_structure) <= 0) return

  call list_structure_read(p, list)

  !--- 型別に数えてから一括確保し、通し番号で格納する ---
  npump = count_pump(list)
  nculv = count_culvert(list)
  ndiv = count_diversion(list)
  ndam = count_dam(list)
  b%nstruct = npump + nculv + ndiv + ndam
  if (b%nstruct <= 0) return
  allocate(b%struct(1:b%nstruct))

  !--- 排水ポンプ(&list_struct_pump): 1..npump ---
  call init_pump(b, p, g, list, npump)

  !--- カルバート(&list_struct_culvert): npump+1..npump+nculv ---
  call init_culvert(b, p, g, list, npump, nculv)

  !--- 分水(&list_struct_diversion): npump+nculv+1.. ---
  call init_diversion(b, p, g, list, npump + nculv, ndiv)

  !--- ダム(&list_struct_dam): npump+nculv+ndiv+1.. ---
  call init_dam(b, p, g, list, npump + nculv + ndiv, ndam)

end subroutine


!----------------------------------------------------------------------
! 有効なダム数を数える(番号の連続性も検証)
!----------------------------------------------------------------------
function count_dam(list) result(ndam)
  type(t_list_structure), intent(in) :: list
  integer :: ndam
  logical :: active(1:nstmax)
  integer :: id

  ndam = 0
  if (.not. list%present_dam) return
  do id = 1, nstmax
    active(id) = (list%dam_in_cell(1,1,id) > -9999) &
                 .or. (list%dam_hv(1,1,id) > -9998.0) &
                 .or. (len_trim(list%fn_dam_in_cell(id)) > 0)
  end do
  ndam = count(active)
  if (ndam <= 0) return
  if (.not. all(active(1:ndam))) then
    call par_stop("list_struct_dam: ダム番号は 1 から連続で指定してください")
  end if

end function


!----------------------------------------------------------------------
! 有効なポンプ数を数える(番号の連続性も検証)
!----------------------------------------------------------------------
function count_pump(list) result(npump)
  type(t_list_structure), intent(in) :: list
  integer :: npump
  logical :: active(1:nstmax)
  integer :: ip

  npump = 0
  if (.not. list%present_pump) return
  do ip = 1, nstmax
    active(ip) = (list%pump_in_cell(1,1,ip) > -9999) &
                 .or. (list%pump_q0(ip) > -9998.0) &
                 .or. (list%pump_rule(1,1,ip) > -9999) &
                 .or. (len_trim(list%fn_pump_in_cell(ip)) > 0)
  end do
  npump = count(active)
  if (npump <= 0) return
  if (.not. all(active(1:npump))) then
    call par_stop("list_struct_pump: ポンプ番号は 1 から連続で指定してください")
  end if

end function


!----------------------------------------------------------------------
! 有効なカルバート数を数える(番号の連続性も検証)
!----------------------------------------------------------------------
function count_culvert(list) result(nculv)
  type(t_list_structure), intent(in) :: list
  integer :: nculv
  logical :: active(1:nstmax)
  integer :: ic

  nculv = 0
  if (.not. list%present_culvert) return
  do ic = 1, nstmax
    active(ic) = (list%culv_in_cell(1,1,ic) > -9999) &
                 .or. (list%culv_width(ic) > -9998.0) &
                 .or. (len_trim(list%fn_culv_in_cell(ic)) > 0)
  end do
  nculv = count(active)
  if (nculv <= 0) return
  if (.not. all(active(1:nculv))) then
    call par_stop("list_struct_culvert: カルバート番号は 1 から連続で指定してください")
  end if

end function


!----------------------------------------------------------------------
! 有効な分水数を数える(番号の連続性も検証)
!----------------------------------------------------------------------
function count_diversion(list) result(ndiv)
  type(t_list_structure), intent(in) :: list
  integer :: ndiv
  logical :: active(1:nstmax)
  integer :: id

  ndiv = 0
  if (.not. list%present_diversion) return
  do id = 1, nstmax
    active(id) = (list%div_in_cell(1,1,id) > -9999) &
                 .or. (list%div_q0(id) > -9998.0) &
                 .or. (list%div_rule(1,1,id) > -9999) &
                 .or. (len_trim(list%fn_div_in_cell(id)) > 0)
  end do
  ndiv = count(active)
  if (ndiv <= 0) return
  if (.not. all(active(1:ndiv))) then
    call par_stop("list_struct_diversion: 分水番号は 1 から連続で指定してください")
  end if

end function


!----------------------------------------------------------------------
! 各内部水理構造物の現時刻の目標流量を水理則から決める(毎ステップ、
! makebdc から呼ばれる)。
!   基準値(代表セル=各セル群の先頭)は所有ランクだけが読めるため、
!   「所有ランクのみ非ゼロ+総和 allreduce」で全ランクに共有する(§11。
!   collective は nstruct が namelist 由来で全ランク同一のため安全)。
!   評価はステップ開始時点の状態(s%h)による(他族の時系列と同じ時相)
!----------------------------------------------------------------------
module subroutine structure_makebdc(b, p, g, s)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: refs(:)
  real :: deta, qcap
  integer :: ist, i, j

  ! refs(2*ist-1) = 取水(上流)側代表セル、refs(2*ist) = 吐口(下流)側
  ! 代表セルの基準値。値の意味は種別ごと(ポンプ: f_ref に従う片側のみ、
  ! カルバート: 両側の水位η)
  allocate(refs(1:2*b%nstruct), source = 0.0)
  do ist = 1, b%nstruct
    i = b%struct(ist)%cin(1,1)
    j = b%struct(ist)%cin(2,1)
    if (j >= dcp%js .and. j <= dcp%je) then
      select case (b%struct(ist)%kind)
        case (e_struct_pump)
          if (b%struct(ist)%f_ref == 1) then
            ! 水深基準: 代表セルがため池(rscap>0)なら貯留水深 hrs を読む
            ! (前池水深トリガー。地表 h は池が満杯になるまで 0 のため)
            if (g%rscap(i,j) > 0.0) then
              refs(2*ist-1) = max(s%hrs(i,j), 0.0)
            else
              refs(2*ist-1) = max(s%h(i,j), 0.0)
            end if
          else
            refs(2*ist-1) = s%z(i,j) + max(s%h(i,j), 0.0)
          end if
        case (e_struct_culvert, e_struct_diversion)
          refs(2*ist-1) = s%z(i,j) + max(s%h(i,j), 0.0)
      end select
    end if
    ! 下流(送水先)側の基準値: カルバートは常に、分水は送水先ありのみ
    ! (域外分水は refd 不要=0 のまま)
    if (b%struct(ist)%kind == e_struct_culvert &
        .or. (b%struct(ist)%kind == e_struct_diversion .and. b%struct(ist)%ncout > 0)) then
      i = b%struct(ist)%cout(1,1)
      j = b%struct(ist)%cout(2,1)
      if (j >= dcp%js .and. j <= dcp%je) then
        refs(2*ist) = s%z(i,j) + max(s%h(i,j), 0.0)
      end if
    end if
  end do
  call par_allreduce_sumr(refs)
  do ist = 1, b%nstruct
    ! ダムは law 経路を使わない(評価は boundary_h のダム節 → dam_operate。
    ! q は 0 のままで汎用転送節も素通りする)
    if (b%struct(ist)%kind == e_struct_dam) cycle
    b%struct(ist)%q = b%struct(ist)%law(b%struct(ist)%rule, b%struct(ist)%nrule, &
                                        b%struct(ist)%geom, refs(2*ist-1), refs(2*ist))
    ! 双方向種別の均衡上限(§22): 1ステップの転送量を、代表水位差の
    ! 半分を埋める体積までに制限する(dt に依らず単調に平衡へ向かい、
    ! 粗い dt での往復振動を防ぐ)。geom(7) = 有効平面積の調和平均
    ! (代表水位と gv のみの近似。§22 の既知の妥協)
    if (b%struct(ist)%kind == e_struct_culvert) then
      deta = refs(2*ist-1) - refs(2*ist)
      qcap = 0.5 * b%struct(ist)%geom(7) * abs(deta) / p%dt
      b%struct(ist)%q = sign(min(abs(b%struct(ist)%q), qcap), b%struct(ist)%q)
    end if
  end do
  deallocate(refs)

end subroutine


!----------------------------------------------------------------------
! カルバートの水理則: 対称双方向(水位の高い側を上流として評価し
! 符号を付ける)。3レジーム:
!   無流       : 上流水深 h1 <= 0、または上流水位が下流側敷高以下
!                (登り勾配の管は出口敷高を越えないと通せない)
!   自由水面   : 本間公式(幅 B。堤防越流 §17 と同系)。下流水深比
!                h2/h1 = 2/3 で自由/潜り切替
!   管路(満管): オリフィス式 Qp = cp√Δη'。Δη' の下流側は
!                max(下流水位, 出口管頂) — 出口非水没なら管頂基準。
!                Q = min(堰, 管路) で連続に接続(浅水では堰支配、
!                深い水没では管路容量が上限)
! 係数(cw_free/cw_sub/cp)は init_culvert が gg・形状・損失から前計算
! して geom に畳み込み済み(law の引数に p を持たないため)。
! 樋管・樋門のゲート(§22):
!   開度ルール(geom(10)=1): 基準側(geom(9): 0=in/1=out)代表水位の
!   折れ線 rule = (η, 開度0-1) を線形補間した乗率を掛ける(開度は
!   流量の線形乗率の妥協=オリフィス面積の非線形は非表現)。
!   ゲート無しは乗算自体をスキップ(ゲート無しカルバートとビット同一)。
!   フラップ(geom(8)=1): 逆流(q<0 = out→in)を遮断(無動力の
!   逆流防止弁)。評価順: 3レジーム流量 → ×開度 → フラップ
!----------------------------------------------------------------------
function law_culvert(rule, nrule, geom, refu, refd) result(q)
  real, intent(in) :: rule(:,:)
  integer, intent(in) :: nrule
  real, intent(in) :: geom(:)
  real, intent(in) :: refu, refd
  real :: q, c

  if (refu >= refd) then
    q = culv_q1(geom(1), geom(2), geom(3), geom(4), geom(5), geom(6), refu, refd)
  else
    q = -culv_q1(geom(2), geom(1), geom(3), geom(4), geom(5), geom(6), refd, refu)
  end if
  if (geom(10) > 0.5) then
    if (geom(9) > 0.5) then
      c = interp_series(rule, nrule, refd)
    else
      c = interp_series(rule, nrule, refu)
    end if
    q = q * c
  end if
  if (geom(8) > 0.5 .and. q < 0.0) q = 0.0

end function


!----------------------------------------------------------------------
! カルバートの片方向流量(上流水位 eh >= 下流水位 el を仮定)
!   zh/zl: 流入側/流出側の敷高、d: 断面高、
!   cwf/cws: 本間公式の自由/潜り係数(×B×√2g 済)、cp: 管路係数
!----------------------------------------------------------------------
function culv_q1(zh, zl, d, cwf, cws, cp, eh, el) result(q)
  real, intent(in) :: zh, zl, d, cwf, cws, cp, eh, el
  real :: q
  real :: h1, h2, detap, qw

  q = 0.0
  h1 = eh - zh
  if (h1 <= 0.0) return
  if (eh <= zl) return             ! 出口敷高以下の水位は通せない(登り勾配)
  h2 = max(el - zh, 0.0)           ! 流入側敷高基準の下流水深
  if (h2 < h1 * (2.0 / 3.0)) then
    qw = cwf * h1 * sqrt(h1)                   ! 自由越流
  else
    qw = cws * h2 * sqrt(h1 - h2)              ! 潜り越流
  end if
  detap = eh - max(el, zl + d)
  if (detap > 0.0) then
    q = min(qw, cp * sqrt(detap))              ! 満管容量が上限
  else
    q = qw                                     ! 満管に届かない=堰支配
  end if

end function


!----------------------------------------------------------------------
! 排水ポンプの水理則: 取水側基準値の折れ線(線形補間・範囲外端値)。
! 常に非負(一方向。吐口→取水の逆流はない)
!----------------------------------------------------------------------
function law_pump(rule, nrule, geom, refu, refd) result(q)
  real, intent(in) :: rule(:,:)
  integer, intent(in) :: nrule
  real, intent(in) :: geom(:)
  real, intent(in) :: refu, refd
  real :: q
  if (size(geom) < 0 .or. refd > huge(refd)) continue  ! 引数未使用の警告を抑制

  q = max(interp_series(rule, nrule, refu), 0.0)

end function


!----------------------------------------------------------------------
! 排水ポンプの解釈・検証・格納(内部水理構造物族の第一号。§22)
!   取水セル群から吐口セル群(未指定なら域外)への強制転送。
!   運転ルールは「一定流量 pump_q0」か「基準水位—流量の折れ線
!   pump_rule」のどちらか一方(排他)。一定流量は1点折れ線に退化させ、
!   実行時は単一経路にする(stage の固定値と同じ流儀)。
!   折れ線は現在状態の純関数(線形補間・範囲外端値)で履歴状態なし。
!   起動/停止ヒステリシスは表現しない(必要なら急なランプで近似)。
!   位置の検証は全域マスク(ゾーン2)で全ランク冗長に行う
!----------------------------------------------------------------------
subroutine init_pump(b, p, g, list, npump)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_structure), intent(in) :: list
  integer, intent(in) :: npump          ! count_pump の結果(通し番号 1..npump)
  logical :: has_q0, has_rule
  integer :: ip, n, k, i, j

  if (npump <= 0) return

  do ip = 1, npump

    b%struct(ip)%kind = e_struct_pump
    b%struct(ip)%law => law_pump

    !--- 取水セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_pump_in_cell(ip)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_pump_in_cell(ip)), &
                           b%struct(ip)%ncin, b%struct(ip)%cin)
    else
      n = 0
      do k = 1, nstccmax
        if (list%pump_in_cell(1,k,ip) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ip)%cin(1:2,1:max(n,1)))
      b%struct(ip)%cin(1:2,1:n) = list%pump_in_cell(1:2,1:n,ip)
      b%struct(ip)%ncin = n
    end if

    !--- 吐口セル集合(任意。なければ域外排水) ---
    if (len_trim(list%fn_pump_out_cell(ip)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_pump_out_cell(ip)), &
                           b%struct(ip)%ncout, b%struct(ip)%cout)
    else
      n = 0
      do k = 1, nstccmax
        if (list%pump_out_cell(1,k,ip) <= -9999) exit  ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ip)%cout(1:2,1:max(n,1)))
      b%struct(ip)%cout(1:2,1:n) = list%pump_out_cell(1:2,1:n,ip)
      b%struct(ip)%ncout = n
    end if

    !--- 運転ルール(pump_q0 と pump_rule は排他) ---
    has_q0 = list%pump_q0(ip) > -9998.0
    has_rule = list%pump_rule(1,1,ip) > -9999
    if (has_q0 .and. has_rule) then
      call par_stop("list_struct_pump: ポンプ "//itoa(ip) &
                    //" は pump_q0 と pump_rule を同時に指定できません")
    end if
    if (.not. (has_q0 .or. has_rule)) then
      call par_stop("list_struct_pump: ポンプ "//itoa(ip) &
                    //" に運転ルール(pump_q0 か pump_rule)がありません")
    end if
    if (has_q0) then
      if (list%pump_q0(ip) < 0.0) then
        call par_stop("list_struct_pump: ポンプ "//itoa(ip)//" の pump_q0 は非負のみです")
      end if
      ! 一定流量は1点折れ線に退化(補間は常に固定値を返す)
      allocate(b%struct(ip)%rule(1:2,1:1))
      b%struct(ip)%rule(1,1) = 0.0
      b%struct(ip)%rule(2,1) = list%pump_q0(ip)
      b%struct(ip)%nrule = 1
    else
      n = 0
      do k = 1, size(list%pump_rule, 2)
        if (list%pump_rule(1,k,ip) <= -9999) exit      ! 番兵で終端
        n = n + 1
      end do
      ! 第1列は基準水位 (m)。時系列と違い分→秒換算はしない
      allocate(b%struct(ip)%rule(1:2,1:max(n,1)))
      b%struct(ip)%rule(1:2,1:n) = list%pump_rule(1:2,1:n,ip)
      b%struct(ip)%nrule = n
      do k = 1, n
        if (b%struct(ip)%rule(2,k) < 0.0) then
          call par_stop("list_struct_pump: ポンプ "//itoa(ip)//" の流量は非負のみです")
        end if
        if (k >= 2) then
          if (b%struct(ip)%rule(1,k) <= b%struct(ip)%rule(1,k-1)) then
            call par_stop("list_struct_pump: ポンプ "//itoa(ip) &
                          //" のルールの基準水位が単調増加ではありません")
          end if
        end if
      end do
    end if
    if (list%f_pump_ref(ip) < 0 .or. list%f_pump_ref(ip) > 1) then
      call par_stop("list_struct_pump: f_pump_ref は 0(水位η), 1(水深h) のいずれか: " &
                    //itoa(list%f_pump_ref(ip)))
    end if
    b%struct(ip)%f_ref = list%f_pump_ref(ip)

    !--- 検証(セルは有効な陸セルのみ) ---
    if (b%struct(ip)%ncin <= 0) then
      call par_stop("list_struct_pump: ポンプ "//itoa(ip)//" に取水セルがありません")
    end if
    do k = 1, b%struct(ip)%ncin + b%struct(ip)%ncout
      if (k <= b%struct(ip)%ncin) then
        i = b%struct(ip)%cin(1,k)
        j = b%struct(ip)%cin(2,k)
      else
        i = b%struct(ip)%cout(1,k-b%struct(ip)%ncin)
        j = b%struct(ip)%cout(2,k-b%struct(ip)%ncin)
      end if
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_struct_pump: ポンプ "//itoa(ip)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_struct_pump: ポンプ "//itoa(ip)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
      if (g%sw(i,j) /= 0) then
        call par_stop("list_struct_pump: ポンプ "//itoa(ip)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が海セルです")
      end if
    end do

  end do

  ! 代表セルがため池(rscap>0)のポンプは水位基準(η)を使えない
  ! (ため池水面の標高は未定義。取水は s%hrs から行われる)。
  ! rscap は帯配布済み(方式2)のため所有ランクが判定し、エラー番号を
  ! allreduce で共有してから collective に停止する(§11)
  n = 0
  do ip = 1, npump
    if (b%struct(ip)%f_ref /= 0) cycle
    i = b%struct(ip)%cin(1,1)
    j = b%struct(ip)%cin(2,1)
    if (j >= dcp%js .and. j <= dcp%je) then
      if (g%rscap(i,j) > 0.0) n = max(n, ip)
    end if
  end do
  call par_allreduce_maxi(n)
  if (n > 0) then
    call par_stop("list_struct_pump: ポンプ "//itoa(n)//" の代表セルはため池(rscap>0)です。" &
                  //"水位基準(f_pump_ref=0)は使えません。f_pump_ref=1(水深=ため池水深)を指定してください")
  end if

end subroutine


!----------------------------------------------------------------------
! カルバートの解釈・検証・格納(§22。2026-08-07)
!   上流側セル群と下流側セル群(両方必須)を結ぶ矩形断面 B×D の管。
!   水理則は law_culvert(対称双方向・3レジーム)。gg・形状・損失係数は
!   ここで係数に前計算して geom に畳み込む:
!     geom(1)=zin, (2)=zout, (3)=D,
!     (4)=cw_free = 0.35 B √(2g)         (本間・自由)
!     (5)=cw_sub  = 0.91 B √(2g)         (本間・潜り)
!     (6)=cp = BD √(2g / (1+ce+2g n²L/R^(4/3)))  (管路。R=BD/(2(B+D)))
!     (7)=Ah = 有効平面積(Σgv·dx·dy)の調和平均(均衡上限用。§22)
!     (8)=フラップ (0/1)、(9)=ゲート基準側 (0:in/1:out)、
!     (10)=ゲート有無 (0/1。1 なら rule = 開度折れ線)
!   樋管・樋門はゲート付きカルバートとして表す(§22): フラップ
!   (culv_flap=1)は逆流 out→in の遮断、開度ルール(culv_gate_rule)は
!   基準側代表水位の折れ線 (η, 開度0-1) による流量乗率。
!   ため池(rscap>0)セルは不許可(転送則が hrs と絡むため。実務は
!   ポンプを使う)。域外(下流側なし)も不許可(逆流の定義がないため。
!   域外排水はポンプの一定流量で代替)
!----------------------------------------------------------------------
subroutine init_culvert(b, p, g, list, ofs, nculv)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_structure), intent(in) :: list
  integer, intent(in) :: ofs            ! 通し番号のオフセット(=ポンプ数)
  integer, intent(in) :: nculv          ! count_culvert の結果
  real :: bw, d, a, r, fric, area(1:2)
  integer :: ic, ist, n, k, i, j

  if (nculv <= 0) return

  do ic = 1, nculv
    ist = ofs + ic

    b%struct(ist)%kind = e_struct_culvert
    b%struct(ist)%law => law_culvert
    b%struct(ist)%f_ref = 0

    !--- ゲート(樋管・樋門): フラップと開度ルール ---
    if (list%culv_flap(ic) < 0 .or. list%culv_flap(ic) > 1) then
      call par_stop("list_struct_culvert: culv_flap は 0(なし), 1(逆流遮断) のいずれか: " &
                    //itoa(list%culv_flap(ic)))
    end if
    if (list%culv_gate_ref(ic) < 0 .or. list%culv_gate_ref(ic) > 1) then
      call par_stop("list_struct_culvert: culv_gate_ref は 0(in側), 1(out側) のいずれか: " &
                    //itoa(list%culv_gate_ref(ic)))
    end if
    b%struct(ist)%geom(8) = real(list%culv_flap(ic))
    n = 0
    do k = 1, size(list%culv_gate_rule, 2)
      if (list%culv_gate_rule(1,k,ic) <= -9999) exit   ! 番兵で終端
      n = n + 1
    end do
    if (n > 0) then
      ! 開度折れ線 (基準水位η m, 開度0-1)。第1列は水位(分→秒換算なし)
      allocate(b%struct(ist)%rule(1:2,1:n))
      b%struct(ist)%rule(1:2,1:n) = list%culv_gate_rule(1:2,1:n,ic)
      b%struct(ist)%nrule = n
      do k = 1, n
        if (b%struct(ist)%rule(2,k) < 0.0 .or. b%struct(ist)%rule(2,k) > 1.0) then
          call par_stop("list_struct_culvert: カルバート "//itoa(ic) &
                        //" のゲート開度は 0〜1 のみです")
        end if
        if (k >= 2) then
          if (b%struct(ist)%rule(1,k) <= b%struct(ist)%rule(1,k-1)) then
            call par_stop("list_struct_culvert: カルバート "//itoa(ic) &
                          //" のゲートルールの基準水位が単調増加ではありません")
          end if
        end if
      end do
      b%struct(ist)%geom(9) = real(list%culv_gate_ref(ic))
      b%struct(ist)%geom(10) = 1.0
    else
      ! ゲート無し: 折れ線は law へ渡す実引数のための1点ダミー
      allocate(b%struct(ist)%rule(1:2,1:1), source = 0.0)
      b%struct(ist)%nrule = 1
      b%struct(ist)%geom(9) = 0.0
      b%struct(ist)%geom(10) = 0.0
    end if

    !--- 上流側セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_culv_in_cell(ic)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_culv_in_cell(ic)), &
                           b%struct(ist)%ncin, b%struct(ist)%cin)
    else
      n = 0
      do k = 1, nstccmax
        if (list%culv_in_cell(1,k,ic) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ist)%cin(1:2,1:max(n,1)))
      b%struct(ist)%cin(1:2,1:n) = list%culv_in_cell(1:2,1:n,ic)
      b%struct(ist)%ncin = n
    end if

    !--- 下流側セル集合(必須) ---
    if (len_trim(list%fn_culv_out_cell(ic)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_culv_out_cell(ic)), &
                           b%struct(ist)%ncout, b%struct(ist)%cout)
    else
      n = 0
      do k = 1, nstccmax
        if (list%culv_out_cell(1,k,ic) <= -9999) exit  ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ist)%cout(1:2,1:max(n,1)))
      b%struct(ist)%cout(1:2,1:n) = list%culv_out_cell(1:2,1:n,ic)
      b%struct(ist)%ncout = n
    end if

    if (b%struct(ist)%ncin <= 0) then
      call par_stop("list_struct_culvert: カルバート "//itoa(ic)//" に上流側セルがありません")
    end if
    if (b%struct(ist)%ncout <= 0) then
      call par_stop("list_struct_culvert: カルバート "//itoa(ic)//" に下流側セルがありません" &
                    //"(双方向のため両側必須。域外排水はポンプ pump_q0 を使ってください)")
    end if

    !--- 形状・損失の検証と係数の前計算 ---
    bw = list%culv_width(ic)
    d = list%culv_height(ic)
    if (bw <= 0.0 .or. d <= 0.0) then
      call par_stop("list_struct_culvert: カルバート "//itoa(ic) &
                    //" の断面(culv_width, culv_height)は正の値で必須です")
    end if
    if (list%culv_zin(ic) < -9998.0 .or. list%culv_zout(ic) < -9998.0) then
      call par_stop("list_struct_culvert: カルバート "//itoa(ic) &
                    //" の敷高(culv_zin, culv_zout)は必須です")
    end if
    if (list%culv_length(ic) < 0.0 .or. list%culv_manning(ic) < 0.0 &
        .or. list%culv_ce(ic) < 0.0) then
      call par_stop("list_struct_culvert: カルバート "//itoa(ic) &
                    //" の culv_length / culv_manning / culv_ce は非負のみです")
    end if
    a = bw * d
    r = a / (2.0 * (bw + d))
    fric = 2.0 * p%gg * list%culv_manning(ic)**2 * list%culv_length(ic) / r**(4.0/3.0)
    b%struct(ist)%geom(1) = list%culv_zin(ic)
    b%struct(ist)%geom(2) = list%culv_zout(ic)
    b%struct(ist)%geom(3) = d
    b%struct(ist)%geom(4) = 0.35 * bw * sqrt(2.0 * p%gg)
    b%struct(ist)%geom(5) = 0.91 * bw * sqrt(2.0 * p%gg)
    b%struct(ist)%geom(6) = a * sqrt(2.0 * p%gg / (1.0 + list%culv_ce(ic) + fric))

    !--- 位置の検証(全域マスク。ゾーン2で全ランク冗長) ---
    do k = 1, b%struct(ist)%ncin + b%struct(ist)%ncout
      if (k <= b%struct(ist)%ncin) then
        i = b%struct(ist)%cin(1,k)
        j = b%struct(ist)%cin(2,k)
      else
        i = b%struct(ist)%cout(1,k-b%struct(ist)%ncin)
        j = b%struct(ist)%cout(2,k-b%struct(ist)%ncin)
      end if
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_struct_culvert: カルバート "//itoa(ic)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_struct_culvert: カルバート "//itoa(ic)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
      if (g%sw(i,j) /= 0) then
        call par_stop("list_struct_culvert: カルバート "//itoa(ic)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が海セルです")
      end if
    end do

    !--- 均衡上限用の有効平面積(調和平均)---
    !   gv は帯配布済み(方式2)のため所有ランクの部分和を allreduce で
    !   合算する(§11。collective は全ランク同数実行)。wfrac(河道幅)は
    !   m_swflow_enc の私有状態のため含めない近似(§22 の既知の妥協)
    area = 0.0
    do k = 1, b%struct(ist)%ncin
      i = b%struct(ist)%cin(1,k)
      j = b%struct(ist)%cin(2,k)
      if (j >= dcp%js .and. j <= dcp%je) area(1) = area(1) + g%gv(i,j) * g%dx * g%dy
    end do
    do k = 1, b%struct(ist)%ncout
      i = b%struct(ist)%cout(1,k)
      j = b%struct(ist)%cout(2,k)
      if (j >= dcp%js .and. j <= dcp%je) area(2) = area(2) + g%gv(i,j) * g%dx * g%dy
    end do
    call par_allreduce_sumr(area)
    if (area(1) <= 0.0 .or. area(2) <= 0.0) then
      call par_stop("list_struct_culvert: カルバート "//itoa(ic) &
                    //" のセル群の有効平面積(gv)がゼロです")
    end if
    b%struct(ist)%geom(7) = area(1) * area(2) / (area(1) + area(2))

  end do

  ! ため池(rscap>0)セルは不許可(所有ランク判定+allreduce → collective 停止)
  n = 0
  do ic = 1, nculv
    ist = ofs + ic
    do k = 1, b%struct(ist)%ncin + b%struct(ist)%ncout
      if (k <= b%struct(ist)%ncin) then
        i = b%struct(ist)%cin(1,k)
        j = b%struct(ist)%cin(2,k)
      else
        i = b%struct(ist)%cout(1,k-b%struct(ist)%ncin)
        j = b%struct(ist)%cout(2,k-b%struct(ist)%ncin)
      end if
      if (j >= dcp%js .and. j <= dcp%je) then
        if (g%rscap(i,j) > 0.0) n = max(n, ic)
      end if
    end do
  end do
  call par_allreduce_maxi(n)
  if (n > 0) then
    call par_stop("list_struct_culvert: カルバート "//itoa(n)//" のセルにため池(rscap>0)が" &
                  //"含まれています。カルバートはため池セルに接続できません(ポンプを使ってください)")
  end if

end subroutine


!----------------------------------------------------------------------
! 分水の水理則: 取水側代表水位ηの rating 折れ線(線形補間・範囲外端値。
! 非負=一方向)。受動性ガード: 送水先あり(geom(1)=1)で下流側代表 η が
! 上流側以上なら 0(重力では登れない)。0/1 の粗い遮断で、背水が上流
! 水位に迫る状態の漸減は非表現(§22)。域外分水はガードなし
!----------------------------------------------------------------------
function law_diversion(rule, nrule, geom, refu, refd) result(q)
  real, intent(in) :: rule(:,:)
  integer, intent(in) :: nrule
  real, intent(in) :: geom(:)
  real, intent(in) :: refu, refd
  real :: q

  q = max(interp_series(rule, nrule, refu), 0.0)
  if (geom(1) > 0.5 .and. refd >= refu) q = 0.0

end function


!----------------------------------------------------------------------
! 分水の解釈・検証・格納(族の第三号。§22。2026-08-08)
!   取水セル群から域外(流域外分水=主用途)または送水先セル群への
!   一方向・受動的な取水。ルールは「一定流量 div_q0」か「取水代表セルの
!   水位η—流量の rating 折れ線 div_rule」のどちらか一方(排他。ポンプと
!   同じ流儀で一定流量は1点折れ線に退化)。基準は η のみ(f_ref なし。
!   受動性ガードとの基準統一のため)。ため池セルは不許可(η未定義。
!   ポンプで代替)。geom(1) = 送水先の有無(受動性ガード用)
!----------------------------------------------------------------------
subroutine init_diversion(b, p, g, list, ofs, ndiv)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_structure), intent(in) :: list
  integer, intent(in) :: ofs            ! 通し番号のオフセット(=ポンプ数+カルバート数)
  integer, intent(in) :: ndiv           ! count_diversion の結果
  logical :: has_q0, has_rule
  integer :: id, ist, n, k, i, j

  if (ndiv <= 0) return

  do id = 1, ndiv
    ist = ofs + id

    b%struct(ist)%kind = e_struct_diversion
    b%struct(ist)%law => law_diversion
    b%struct(ist)%f_ref = 0

    !--- 取水セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_div_in_cell(id)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_div_in_cell(id)), &
                           b%struct(ist)%ncin, b%struct(ist)%cin)
    else
      n = 0
      do k = 1, nstccmax
        if (list%div_in_cell(1,k,id) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ist)%cin(1:2,1:max(n,1)))
      b%struct(ist)%cin(1:2,1:n) = list%div_in_cell(1:2,1:n,id)
      b%struct(ist)%ncin = n
    end if

    !--- 送水先セル集合(任意。なければ域外分水) ---
    if (len_trim(list%fn_div_out_cell(id)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_div_out_cell(id)), &
                           b%struct(ist)%ncout, b%struct(ist)%cout)
    else
      n = 0
      do k = 1, nstccmax
        if (list%div_out_cell(1,k,id) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ist)%cout(1:2,1:max(n,1)))
      b%struct(ist)%cout(1:2,1:n) = list%div_out_cell(1:2,1:n,id)
      b%struct(ist)%ncout = n
    end if

    b%struct(ist)%geom(1) = merge(1.0, 0.0, b%struct(ist)%ncout > 0)

    !--- ルール(div_q0 と div_rule は排他) ---
    has_q0 = list%div_q0(id) > -9998.0
    has_rule = list%div_rule(1,1,id) > -9999
    if (has_q0 .and. has_rule) then
      call par_stop("list_struct_diversion: 分水 "//itoa(id) &
                    //" は div_q0 と div_rule を同時に指定できません")
    end if
    if (.not. (has_q0 .or. has_rule)) then
      call par_stop("list_struct_diversion: 分水 "//itoa(id) &
                    //" にルール(div_q0 か div_rule)がありません")
    end if
    if (has_q0) then
      if (list%div_q0(id) < 0.0) then
        call par_stop("list_struct_diversion: 分水 "//itoa(id)//" の div_q0 は非負のみです")
      end if
      ! 一定流量は1点折れ線に退化(補間は常に固定値を返す)
      allocate(b%struct(ist)%rule(1:2,1:1))
      b%struct(ist)%rule(1,1) = 0.0
      b%struct(ist)%rule(2,1) = list%div_q0(id)
      b%struct(ist)%nrule = 1
    else
      n = 0
      do k = 1, size(list%div_rule, 2)
        if (list%div_rule(1,k,id) <= -9999) exit       ! 番兵で終端
        n = n + 1
      end do
      ! 第1列は基準水位 (m)。時系列と違い分→秒換算はしない
      allocate(b%struct(ist)%rule(1:2,1:max(n,1)))
      b%struct(ist)%rule(1:2,1:n) = list%div_rule(1:2,1:n,id)
      b%struct(ist)%nrule = n
      do k = 1, n
        if (b%struct(ist)%rule(2,k) < 0.0) then
          call par_stop("list_struct_diversion: 分水 "//itoa(id)//" の流量は非負のみです")
        end if
        if (k >= 2) then
          if (b%struct(ist)%rule(1,k) <= b%struct(ist)%rule(1,k-1)) then
            call par_stop("list_struct_diversion: 分水 "//itoa(id) &
                          //" のルールの基準水位が単調増加ではありません")
          end if
        end if
      end do
    end if

    !--- 検証(セルは有効な陸セルのみ) ---
    if (b%struct(ist)%ncin <= 0) then
      call par_stop("list_struct_diversion: 分水 "//itoa(id)//" に取水セルがありません")
    end if
    do k = 1, b%struct(ist)%ncin + b%struct(ist)%ncout
      if (k <= b%struct(ist)%ncin) then
        i = b%struct(ist)%cin(1,k)
        j = b%struct(ist)%cin(2,k)
      else
        i = b%struct(ist)%cout(1,k-b%struct(ist)%ncin)
        j = b%struct(ist)%cout(2,k-b%struct(ist)%ncin)
      end if
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_struct_diversion: 分水 "//itoa(id)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_struct_diversion: 分水 "//itoa(id)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
      if (g%sw(i,j) /= 0) then
        call par_stop("list_struct_diversion: 分水 "//itoa(id)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が海セルです")
      end if
    end do

  end do

  ! ため池(rscap>0)セルは不許可(η未定義。所有ランク判定+allreduce →
  ! collective 停止)
  n = 0
  do id = 1, ndiv
    ist = ofs + id
    do k = 1, b%struct(ist)%ncin + b%struct(ist)%ncout
      if (k <= b%struct(ist)%ncin) then
        i = b%struct(ist)%cin(1,k)
        j = b%struct(ist)%cin(2,k)
      else
        i = b%struct(ist)%cout(1,k-b%struct(ist)%ncin)
        j = b%struct(ist)%cout(2,k-b%struct(ist)%ncin)
      end if
      if (j >= dcp%js .and. j <= dcp%je) then
        if (g%rscap(i,j) > 0.0) n = max(n, id)
      end if
    end do
  end do
  call par_allreduce_maxi(n)
  if (n > 0) then
    call par_stop("list_struct_diversion: 分水 "//itoa(n)//" のセルにため池(rscap>0)が" &
                  //"含まれています。分水はため池セルに接続できません(ポンプを使ってください)")
  end if

end subroutine


!----------------------------------------------------------------------
! ダムの解釈・検証・格納(族の第四号。§22。2026-08-08)
!   捕捉帯(堤体直上流を横断するセル群)が到達水を毎ステップ全量吸収して
!   s%hrs に貯留し(=バケツ。湛水面は解かない)、運転ルールで放流セル群
!   へ放流する。状態は s%hrs のみ(save/restore は既存機構で閉じる)。
!   運転ルール(f_dam_mode):
!     1: 一定量放流 dam_q0(+但し書き)
!     2: 一定率カット dam_rate(吸収スプリッタ: その歩の吸収×r を放流。
!        遅れゼロ・履歴状態ゼロ)(+但し書き)
!     3: 自然調節 = 水位—放流の rating。指定は3段階(優先順):
!        (a) dam_hq_rule 折れ線 / (b) オリフィス諸元 →係数前計算 /
!        (c) dam_qmax(計画最大放流量)1点アンカーの √則
!   但し書き(モード1,2): V が開始水位相当を超えたら放流を流入へ漸増
!   (r_eff→1 ランプ)。サーチャージ超過分は強制スピル(自動)。
!   geom の割当: (1)=Vmin, (2)=Vmax, (3)=V_tadashigaki, (4)=q0,
!   (5)=rate, (6)=√則係数, (7)=√則敷高, (8)=V_init
!   制約: 捕捉帯・放流セルとも ため池(rscap>0)・河道幅指定(wrw>0)
!   セルは不許可(hrs・体積換算の機構が競合するため)
!----------------------------------------------------------------------
subroutine init_dam(b, p, g, list, ofs, ndam)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_structure), intent(in) :: list
  integer, intent(in) :: ofs            ! 通し番号のオフセット
  integer, intent(in) :: ndam           ! count_dam の結果
  real :: hmin, hsur, htad, hini, ce, zb, bw, d
  integer :: id, ist, n, k, i, j, un
  character(len=80) :: fn
  character(len=4) :: cun

  if (ndam <= 0) return

  do id = 1, ndam
    ist = ofs + id

    b%struct(ist)%kind = e_struct_dam
    b%struct(ist)%law => null()
    b%struct(ist)%f_ref = 0

    !--- セル群(両方必須。ファイル指定が優先) ---
    if (len_trim(list%fn_dam_in_cell(id)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_dam_in_cell(id)), &
                           b%struct(ist)%ncin, b%struct(ist)%cin)
    else
      n = 0
      do k = 1, nstccmax
        if (list%dam_in_cell(1,k,id) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ist)%cin(1:2,1:max(n,1)))
      b%struct(ist)%cin(1:2,1:n) = list%dam_in_cell(1:2,1:n,id)
      b%struct(ist)%ncin = n
    end if
    if (len_trim(list%fn_dam_out_cell(id)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_dam_out_cell(id)), &
                           b%struct(ist)%ncout, b%struct(ist)%cout)
    else
      n = 0
      do k = 1, nstccmax
        if (list%dam_out_cell(1,k,id) <= -9999) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(b%struct(ist)%cout(1:2,1:max(n,1)))
      b%struct(ist)%cout(1:2,1:n) = list%dam_out_cell(1:2,1:n,id)
      b%struct(ist)%ncout = n
    end if
    if (b%struct(ist)%ncin <= 0) then
      call par_stop("list_struct_dam: ダム "//itoa(id)//" に貯水池セル(捕捉帯)がありません")
    end if
    if (b%struct(ist)%ncout <= 0) then
      call par_stop("list_struct_dam: ダム "//itoa(id)//" に放流セルがありません")
    end if

    !--- HV 曲線(必須。水位・貯水量とも単調増加) ---
    n = 0
    do k = 1, size(list%dam_hv, 2)
      if (list%dam_hv(1,k,id) <= -9998.0) exit         ! 番兵で終端
      n = n + 1
    end do
    if (n < 2) then
      call par_stop("list_struct_dam: ダム "//itoa(id)//" の HV 曲線(dam_hv)は最低2点" &
                    //"(最低水位・サーチャージ)必要です")
    end if
    allocate(b%struct(ist)%hv(1:2,1:n))
    b%struct(ist)%hv(1:2,1:n) = list%dam_hv(1:2,1:n,id)
    b%struct(ist)%nhv = n
    do k = 2, n
      if (b%struct(ist)%hv(1,k) <= b%struct(ist)%hv(1,k-1) &
          .or. b%struct(ist)%hv(2,k) <= b%struct(ist)%hv(2,k-1)) then
        call par_stop("list_struct_dam: ダム "//itoa(id)//" の HV 曲線は水位・貯水量とも" &
                      //"単調増加で指定してください")
      end if
    end do
    if (b%struct(ist)%hv(2,1) < 0.0) then
      call par_stop("list_struct_dam: ダム "//itoa(id)//" の最低水位の貯水量は非負のみです")
    end if
    hmin = b%struct(ist)%hv(1,1)
    hsur = b%struct(ist)%hv(1,n)
    b%struct(ist)%geom(1) = b%struct(ist)%hv(2,1)    ! Vmin
    b%struct(ist)%geom(2) = b%struct(ist)%hv(2,n)    ! Vmax

    !--- 運転モード ---
    b%struct(ist)%dmode = list%f_dam_mode(id)
    select case (list%f_dam_mode(id))
      case (1)      ! 一定量放流
        if (list%dam_q0(id) < 0.0) then
          call par_stop("list_struct_dam: ダム "//itoa(id) &
                        //"(モード1)には dam_q0 >= 0 が必要です")
        end if
        b%struct(ist)%geom(4) = list%dam_q0(id)
      case (2)      ! 一定率カット
        if (list%dam_rate(id) < 0.0 .or. list%dam_rate(id) > 1.0) then
          call par_stop("list_struct_dam: ダム "//itoa(id) &
                        //"(モード2)には dam_rate(放流率 0〜1)が必要です")
        end if
        b%struct(ist)%geom(5) = list%dam_rate(id)
      case (3)      ! 自然調節(rating の3段階指定)
        n = 0
        do k = 1, size(list%dam_hq_rule, 2)
          if (list%dam_hq_rule(1,k,id) <= -9998.0) exit
          n = n + 1
        end do
        if (n >= 2) then
          ! (a) H-Q 折れ線
          allocate(b%struct(ist)%rule(1:2,1:n))
          b%struct(ist)%rule(1:2,1:n) = list%dam_hq_rule(1:2,1:n,id)
          b%struct(ist)%nrule = n
          do k = 1, n
            if (b%struct(ist)%rule(2,k) < 0.0) then
              call par_stop("list_struct_dam: ダム "//itoa(id)//" の dam_hq_rule の流量は非負のみです")
            end if
            if (k >= 2) then
              if (b%struct(ist)%rule(1,k) <= b%struct(ist)%rule(1,k-1)) then
                call par_stop("list_struct_dam: ダム "//itoa(id) &
                              //" の dam_hq_rule の水位が単調増加ではありません")
              end if
            end if
          end do
        else if (list%dam_ori_width(id) > -9998.0 .or. list%dam_ori_height(id) > -9998.0) then
          ! (b) オリフィス諸元 → 満管オリフィス √則の係数に前計算
          bw = list%dam_ori_width(id)
          d = list%dam_ori_height(id)
          zb = list%dam_ori_zbase(id)
          ce = merge(0.5, list%dam_ori_ce(id), list%dam_ori_ce(id) < -9998.0)
          if (bw <= 0.0 .or. d <= 0.0 .or. zb < -9998.0 .or. ce < 0.0) then
            call par_stop("list_struct_dam: ダム "//itoa(id)//" のオリフィス諸元" &
                          //"(dam_ori_width/height/zbase, 任意 ce)が不正です")
          end if
          b%struct(ist)%geom(6) = bw * d * sqrt(2.0 * p%gg / (1.0 + ce))
          b%struct(ist)%geom(7) = zb
        else if (list%dam_qmax(id) > 0.0) then
          ! (c) 計画最大放流量アンカーの √則: Q(H) = Qmax·√((H−zb)/(Hsur−zb))
          zb = merge(hmin, list%dam_zbase(id), list%dam_zbase(id) < -9998.0)
          if (zb >= hsur) then
            call par_stop("list_struct_dam: ダム "//itoa(id)//" の √則敷高(dam_zbase)は" &
                          //"サーチャージ水位より低い必要があります")
          end if
          b%struct(ist)%geom(6) = list%dam_qmax(id) / sqrt(hsur - zb)
          b%struct(ist)%geom(7) = zb
        else
          call par_stop("list_struct_dam: ダム "//itoa(id)//"(モード3=自然調節)には " &
                        //"dam_hq_rule / オリフィス諸元 / dam_qmax のいずれかが必要です")
        end if
      case default
        call par_stop("list_struct_dam: ダム "//itoa(id)//" の f_dam_mode は " &
                      //"1(一定量), 2(一定率カット), 3(自然調節) のいずれか: " &
                      //itoa(list%f_dam_mode(id)))
    end select

    ! 折れ線未確保の種別も law 実引数の形を保つ(ダムは law 不使用だが統一)
    if (.not. allocated(b%struct(ist)%rule)) then
      allocate(b%struct(ist)%rule(1:2,1:1), source = 0.0)
      b%struct(ist)%nrule = merge(b%struct(ist)%nrule, 1, b%struct(ist)%nrule > 0)
    end if

    !--- 但し書き開始水位(モード1,2。省略時=最低+0.9×(サーチャージ−最低)) ---
    if (list%dam_tadashigaki(id) > -9998.0) then
      htad = list%dam_tadashigaki(id)
    else
      htad = hmin + 0.9 * (hsur - hmin)
    end if
    if (htad <= hmin .or. htad >= hsur) then
      call par_stop("list_struct_dam: ダム "//itoa(id)//" の但し書き開始水位は" &
                    //"最低水位とサーチャージ水位の間(両端を除く)で指定してください")
    end if
    b%struct(ist)%geom(3) = dam_v_of_h(b%struct(ist)%hv, b%struct(ist)%nhv, htad)

    !--- 初期水位(省略時=最低水位=空虚) ---
    if (list%dam_h_init(id) > -9998.0) then
      hini = list%dam_h_init(id)
    else
      hini = hmin
    end if
    if (hini < hmin .or. hini > hsur) then
      call par_stop("list_struct_dam: ダム "//itoa(id)//" の初期水位は" &
                    //"最低水位とサーチャージ水位の間で指定してください")
    end if
    b%struct(ist)%geom(8) = dam_v_of_h(b%struct(ist)%hv, b%struct(ist)%nhv, hini)

    !--- 湛水面積(蒸発散用オプション。§27。未指定は 0 = 捕捉帯セル面積で評価) ---
    if (list%dam_area(id) > -9998.0) then
      if (list%dam_area(id) <= 0.0) then
        call par_stop("list_struct_dam: ダム "//itoa(id)//" の dam_area は正のみです")
      end if
      b%struct(ist)%geom(9) = list%dam_area(id)
    end if

    !--- 位置の検証(全域マスク。ゾーン2で全ランク冗長) ---
    do k = 1, b%struct(ist)%ncin + b%struct(ist)%ncout
      if (k <= b%struct(ist)%ncin) then
        i = b%struct(ist)%cin(1,k)
        j = b%struct(ist)%cin(2,k)
      else
        i = b%struct(ist)%cout(1,k-b%struct(ist)%ncin)
        j = b%struct(ist)%cout(2,k-b%struct(ist)%ncin)
      end if
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_struct_dam: ダム "//itoa(id)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が領域外です")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_struct_dam: ダム "//itoa(id)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が無効セル(x=0)です")
      end if
      if (g%sw(i,j) /= 0) then
        call par_stop("list_struct_dam: ダム "//itoa(id)//" のセル (" &
                      //itoa(i)//","//itoa(j)//") が海セルです")
      end if
    end do

  end do

  ! ため池(rscap>0)・河道幅(wrw>0)セルの不許可(hrs・体積換算の機構が
  ! 競合するため)。帯配布データの判定は所有ランク+allreduce → collective 停止
  n = 0
  do id = 1, ndam
    ist = ofs + id
    do k = 1, b%struct(ist)%ncin + b%struct(ist)%ncout
      if (k <= b%struct(ist)%ncin) then
        i = b%struct(ist)%cin(1,k)
        j = b%struct(ist)%cin(2,k)
      else
        i = b%struct(ist)%cout(1,k-b%struct(ist)%ncin)
        j = b%struct(ist)%cout(2,k-b%struct(ist)%ncin)
      end if
      if (j >= dcp%js .and. j <= dcp%je) then
        if (g%rscap(i,j) > 0.0) n = max(n, id)
        if (g%width_active) then
          if (g%wrw(i,j) > 0.0) n = max(n, id)
        end if
      end if
    end do
  end do
  call par_allreduce_maxi(n)
  if (n > 0) then
    call par_stop("list_struct_dam: ダム "//itoa(n)//" のセルにため池(rscap>0)または" &
                  //"河道幅指定(wrw>0)が含まれています。ダムのセル群とは併用できません")
  end if

  !--- ダム CSV の初期化(rank0 のみ) ---
  if (.not. is_root) return
  call sysdep_mkdir(trim(p%dir_result)//"/dams")
  do id = 1, ndam
    ist = ofs + id
    write(cun, '(i4.4)') id
    fn = trim(p%dir_result)//"/dams/"//"dam"//cun//trim(p%outfn_suffix)//".csv"
    open(newunit=un, file=trim(fn), status='replace')
    write(un, '("# dam number =,",i3)') id
    write(un, '("# mode =,",i3)') b%struct(ist)%dmode
    write(un, '("# Vmin(m3) =,",es14.6,", Vmax(m3) =,",es14.6)') &
          b%struct(ist)%geom(1), b%struct(ist)%geom(2)
    write(un, '("# t(hour), t(min), H(m), V(m3), Qin(m3/s), Qout(m3/s), Qspill(m3/s)")')
    b%struct(ist)%un = un
  end do

end subroutine


!----------------------------------------------------------------------
! HV 曲線の補間: 水位 → 貯水量(範囲外は端値。単調増加を init で検証済み)
!----------------------------------------------------------------------
function dam_v_of_h(hv, nhv, h) result(v)
  real, intent(in) :: hv(:,:)
  integer, intent(in) :: nhv
  real, intent(in) :: h
  real :: v
  v = interp_series(hv, nhv, h)
end function


!----------------------------------------------------------------------
! HV 曲線の逆補間: 貯水量 → 水位(範囲外は端値)
!----------------------------------------------------------------------
function dam_h_of_v(hv, nhv, v) result(h)
  real, intent(in) :: hv(:,:)
  integer, intent(in) :: nhv
  real, intent(in) :: v
  real :: h
  integer :: k

  if (v <= hv(2,1)) then
    h = hv(1,1)
  else if (v > hv(2,nhv)) then
    h = hv(1,nhv)
  else
    h = hv(1,nhv)
    do k = 2, nhv
      if (v < hv(2,k)) then
        h = hv(1,k-1) + (v - hv(2,k-1)) / (hv(2,k) - hv(2,k-1)) &
                        * (hv(1,k) - hv(1,k-1))
        exit
      end if
    end do
  end if

end function


!----------------------------------------------------------------------
! ダムの初期貯留を s%hrs に投入する(フレッシュラン時のみ。
! restore 時は復元された hrs をそのまま使う=状態は hrs で完結)。
! 初期貯水量 V_init を捕捉帯セルへ体積等分し、水深換算(/gv)で置く
!----------------------------------------------------------------------
module subroutine m_boundary_dam_seed(b, p, g, s)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real(r64) :: vrow(dcp%js:dcp%je), v8
  real :: vshare
  integer :: ist, k, i, j

  do ist = 1, b%nstruct
    if (b%struct(ist)%kind /= e_struct_dam) cycle

    !--- 初期貯留の投入(フレッシュランのみ。restore は復元 hrs を使う) ---
    if (p%f_state_restore <= 0 .and. b%struct(ist)%geom(8) > 0.0) then
      vshare = b%struct(ist)%geom(8) / b%struct(ist)%ncin
      do k = 1, b%struct(ist)%ncin
        i = b%struct(ist)%cin(1,k)
        j = b%struct(ist)%cin(2,k)
        if (j < dcp%js .or. j > dcp%je) cycle
        s%hrs(i,j) = vshare / (g%gv(i,j) * g%dx * g%dy)
      end do
    end if

    !--- 初期診断(V, H)を hrs から算定(CSV の初期行用。フレッシュ・
    !    restore とも。決定的総和=全ランク同値。§22)---
    vrow = 0.0_r64
    do k = 1, b%struct(ist)%ncin
      i = b%struct(ist)%cin(1,k)
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      vrow(j) = vrow(j) + real(s%hrs(i,j) * g%gv(i,j) * g%dx * g%dy, r64)
    end do
    call par_sum_rows(vrow, v8)
    b%struct(ist)%dv = real(v8)
    b%struct(ist)%dh = dam_h_of_v(b%struct(ist)%hv, b%struct(ist)%nhv, b%struct(ist)%dv)
  end do

end subroutine


!----------------------------------------------------------------------
! ダムの毎ステップ運転(boundary_h のダム節から呼ばれる。§22)
!   呼び出し側が構築した行部分和(vabs_row = この歩の吸収体積、
!   vrow = 吸収後の hrs 総体積)を決定的総和(par_sum_rows。np に依らず
!   ビット同一)し、運転ルールで引き落とし体積を決めて、担当帯の hrs を
!   比例縮小する(比率は全ランク同値 → 決定的)。
!   吸収スプリッタ(モード2): その歩の吸収 A に対し r_eff·A を放流。
!   遅れゼロ・履歴状態ゼロ(r_eff は V の純関数)。
!   但し書き(モード1,2): V_tad→Vmax の間で放流を流入へ線形漸増。
!   サーチャージ超過は強制スピル。引き落とし下限は Vmin(死水)
!----------------------------------------------------------------------
module subroutine dam_operate(b, ist, p, g, s, vabs_row, vrow, vdraw)
  type(t_boundary), intent(inout) :: b
  integer, intent(in) :: ist
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real(r64), intent(in) :: vabs_row(dcp%js:)
  real(r64), intent(in) :: vrow(dcp%js:)
  real, intent(out) :: vdraw
  real(r64) :: vnow8, a8
  real :: vnow, a, vmin, vmax, vtad, ramp, reff, vt, vrel, vspill, ratio, hh
  integer :: k, i, j
  if (g%initialized) continue  ! 引数未使用の警告を抑制

  call par_sum_rows(vabs_row, a8)
  call par_sum_rows(vrow, vnow8)
  a = real(a8)
  vnow = real(vnow8)

  vmin = b%struct(ist)%geom(1)
  vmax = b%struct(ist)%geom(2)
  vtad = b%struct(ist)%geom(3)

  ! 但し書きランプ(V_tad → Vmax で 0 → 1)
  ramp = min(max((vnow - vtad) / (vmax - vtad), 0.0), 1.0)

  select case (b%struct(ist)%dmode)
    case (1)      ! 一定量放流(+但し書き: 放流を流入へ漸増)
      vt = b%struct(ist)%geom(4) * p%dt
      vt = vt + ramp * max(a - vt, 0.0)
    case (2)      ! 一定率カット(吸収スプリッタ+但し書き)
      reff = b%struct(ist)%geom(5) + (1.0 - b%struct(ist)%geom(5)) * ramp
      vt = reff * a
    case default  ! 3: 自然調節 = rating(H(V))
      hh = dam_h_of_v(b%struct(ist)%hv, b%struct(ist)%nhv, vnow)
      if (b%struct(ist)%nrule >= 2) then
        vt = interp_series(b%struct(ist)%rule, b%struct(ist)%nrule, hh) * p%dt
      else
        vt = b%struct(ist)%geom(6) * sqrt(max(hh - b%struct(ist)%geom(7), 0.0)) * p%dt
      end if
  end select

  ! 引き落とし下限(死水)とサーチャージ超過の強制スピル
  vrel = min(vt, max(vnow - vmin, 0.0))
  vspill = max(vnow - vrel - vmax, 0.0)
  vdraw = vrel + vspill

  ! 担当帯の捕捉帯セル hrs を比例縮小(比率は全ランク同値 → 決定的。
  ! vdraw <= vnow が上の式で保証される)
  if (vdraw > 0.0 .and. vnow > 0.0) then
    ratio = 1.0 - vdraw / vnow
    do k = 1, b%struct(ist)%ncin
      i = b%struct(ist)%cin(1,k)
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      s%hrs(i,j) = s%hrs(i,j) * ratio
    end do
  else
    vdraw = 0.0
  end if

  ! 診断量(CSV 用。全ランク同値)
  b%struct(ist)%dv = vnow - vdraw
  b%struct(ist)%dh = dam_h_of_v(b%struct(ist)%hv, b%struct(ist)%nhv, b%struct(ist)%dv)
  b%struct(ist)%dqin = a / p%dt
  b%struct(ist)%dqout = vrel / p%dt
  b%struct(ist)%dqsp = vspill / p%dt

end subroutine


!----------------------------------------------------------------------
! ダム CSV の1行出力(記録間隔で m_main から呼ばれる。rank0 のみ。
! 値は dam_operate が決定的総和で全ランク同値に更新済み)
!----------------------------------------------------------------------
module subroutine m_boundary_dam_record(b, p, s)
  type(t_boundary), intent(in) :: b
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: ist, un
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (.not. is_root) return
  do ist = 1, b%nstruct
    if (b%struct(ist)%kind /= e_struct_dam) cycle
    un = b%struct(ist)%un
    if (un == 0) cycle           ! 0 = 未開設(newunit は負値を返す)
    write(un, '(f13.4,",",f13.4,",",f13.4,",",es15.7,3(",",f13.4))') &
          s%t / 3600, s%t / 60, b%struct(ist)%dh, b%struct(ist)%dv, &
          b%struct(ist)%dqin, b%struct(ist)%dqout, b%struct(ist)%dqsp
  end do

end subroutine

end submodule
