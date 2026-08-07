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
  use m_parallel, only : par_stop, dcp, par_allreduce_sumr, par_allreduce_maxi
  use m_util, only : itoa
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

  if (len_trim(p%fn_structure) <= 0) return

  call list_structure_read(p, list)

  !--- 排水ポンプ(&list_struct_pump) ---
  call init_pump(b, p, g, list)

end subroutine


!----------------------------------------------------------------------
! 各内部水理構造物の現時刻の目標流量を水理則から決める(毎ステップ、
! makebdc から呼ばれる)。
!   基準値(代表セル=各セル群の先頭)は所有ランクだけが読めるため、
!   「所有ランクのみ非ゼロ+総和 allreduce」で全ランクに共有する(§11。
!   collective は nstruct が namelist 由来で全ランク同一のため安全)。
!   評価はステップ開始時点の状態(s%h)による(他族の時系列と同じ時相)
!----------------------------------------------------------------------
module subroutine structure_makebdc(b, g, s)
  type(t_boundary), intent(inout) :: b
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: refp(:)
  integer :: ist, i, j

  allocate(refp(1:b%nstruct), source = 0.0)
  do ist = 1, b%nstruct
    i = b%struct(ist)%cin(1,1)
    j = b%struct(ist)%cin(2,1)
    if (j >= dcp%js .and. j <= dcp%je) then
      if (b%struct(ist)%f_ref == 1) then
        ! 水深基準: 代表セルがため池(rscap>0)なら貯留水深 hrs を読む
        ! (前池水深トリガー。地表 h は池が満杯になるまで 0 のため)
        if (g%rscap(i,j) > 0.0) then
          refp(ist) = max(s%hrs(i,j), 0.0)
        else
          refp(ist) = max(s%h(i,j), 0.0)
        end if
      else
        refp(ist) = s%z(i,j) + max(s%h(i,j), 0.0)
      end if
    end if
  end do
  call par_allreduce_sumr(refp)
  do ist = 1, b%nstruct
    b%struct(ist)%q = b%struct(ist)%law(b%struct(ist)%rule, b%struct(ist)%nrule, &
                                        b%struct(ist)%geom, refp(ist), 0.0)
  end do
  deallocate(refp)

end subroutine


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
subroutine init_pump(b, p, g, list)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_structure), intent(in) :: list
  logical :: active(1:nstmax)
  logical :: has_q0, has_rule
  integer :: npump, ip, n, k, i, j

  if (.not. list%present_pump) return

  !--- 有効なポンプ(取水セルかルールかファイル指定がある)を数える ---
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

  allocate(b%struct(1:npump))
  b%nstruct = npump

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

end submodule
