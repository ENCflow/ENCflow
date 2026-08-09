submodule(m_swflow_enc) m_swflow_enc_channel
  ! 河道水理モデル(堤防・開口補正・サブグリッド河道幅)の構築・適用層
  ! (m_swflow_enc_adv / _bc と同じ「親の私有状態へのホスト結合を活かした
  !  コード分割」の submodule)。
  !   - build_channel_frw : エッジ別通過幅係数 frw(開口補正+幅キャップ)と
  !                         セル方向別通水率 cwx/cwy の構築(init で1回)
  !   - build_wfrac       : セルの河道平面積率 wfrac の構築(init で1回)
  !   - bank_wall         : 堤防(仮想壁面)エッジの uve1/mne1 上書き
  !                         (calc_kth_momentum から毎エッジ呼ばれるホット
  !                          コール。submodule 境界のインライン化は
  !                          nvfortran だけ効かない点は adv_edge と同じ。§3)
  ! 設計の正本は developer.md §17(堤防)、§18(開口補正・河道幅)。
  ! bc と違い、状態(frw/wfrac/cwx/cwy と有効フラグ)は親モジュールに置く:
  ! ホスト結合は submodule→親の一方向で、これらを読むのは親カーネルの
  ! ホットパスだから(§18)。本 submodule はその構築者にすぎない。
  ! 親の重みシェア(lpx/lpy/ldx/ldy, l8x/l8y, w8dr)・方位定数(din/dje 等)は
  ! ホスト結合で参照する。dcp・zbank_min 等の use 経由の名前は nvfortran
  ! バグ回避のため submodule 側で直接 use する(§13)。
  ! 補助手続きは contained にせず引数渡しの submodule レベル手続きにする(§13)
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo, zbank_min
  use m_state, only : t_state
  use m_parallel, only : dcp, par_stop, par_allreduce_maxi
  use m_util, only : itoa
  use list_channel, only : t_list_channel, nbrsmax, nbrvmax
  ! 時系列補間は m_boundary の公開手続きを共用する(以前あった同一実装の
  ! 複製は削除: nvfortran は submodule のホスト結合で祖先の use を
  ! only 制限なしに見せるため、複製の再宣言が 1254 エラーになる。§13)
  use m_boundary, only : interp_series
  implicit none

  ! エッジ格納スロットの k 成分(親の continuous と同じ写像)
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]

  ! ---- 破堤の私有状態(developer.md §18。breach_init が構築)----
  ! サイト=セル対 (ic,jc)-(il,jl) で一意に決まるエッジ。実効天端は
  !   zeff(t) = zgnd0 + f(t)·(zcrest0 − zgnd0)   (f: 1=天端高, 0=堤内地盤高)
  ! で毎ステップ更新する(f は時系列の線形補間・範囲外は端値保持。
  ! f>=1 は zcrest0、f<=0 は zgnd0 に厳密固定=無破堤とのビット一致条件)。
  ! 履歴状態なし(t の純関数)のため save/restore 対象外。
  ! 基準地盤 zgnd0 は init 時の堤内地セルの s%z で静的(侵食に追従しない)。
  ! 型 t_breach の定義は親モジュール(AOCC flang の LTO が submodule 内
  ! 定義型の型記述子を解決できないため。§13)
  integer :: nbr = 0                          ! サイト数
  type(t_breach), allocatable :: br(:)        ! サイトリスト(全ランク同一)
  ! 行バケット: 行 jc にあるサイトの並び ibrs(ibr0(jc):ibr1(jc))。
  ! bank_wall のゲート(サイトのない行は整数比較1回で素通り)
  integer, allocatable :: ibr0(:), ibr1(:)    ! (jsh:jeh)
  integer, allocatable :: ibrs(:)             ! 行順に整列したサイト番号

contains

!----------------------------------------------------------------------
! エッジ別通過幅係数テーブル frw の構築(developer.md §18)
!
! [開口補正(have_bopen)]
!   河道—河道の法線エッジ(成分4: x横断、成分2: y横断)について、
!   同じ横断方向の斜め開口のうち堤防壁で恒久的に塞がれた本数
!   (エッジ両側セルの平均)のシェアを法線エッジへ振り替える:
!     成分4: frw = (lpy + nb·ldy) / lpy    (nb = 塞がり本数の平均 0〜2)
!     成分2: frw = (lpx + nb·ldx) / lpx
!   斜めエッジ(成分1, 3)と壁エッジ(越流の敷幅)は 1 のまま。
!   「塞がれた」= その側の河道セルが天端を持ち(zbank 有効)、斜め先が
!   堤内地(x>0, sw=0, rw<=0)。bank_wall の発動条件と同一に保つこと。
!   領域外(x<=0)は従来どおり無フラックスのままで振り替え対象にしない。
!
! [幅キャップ(have_width)]
!   河道—河道の全成分エッジについて、両セルの河道幅の最小値 W_e
!   (正の値のみ。両方幅情報なしなら対象外)から
!     q = min(W_e / 面長, 1)   面長: 成分4=dy, 成分2=dx,
!                              成分1,3=√(dx·dy)(dx=dy で横断合計が厳密)
!   を frw に重畳する。直線河道では法線エッジが幅 W_e を担い、蛇行の
!   屈曲では法線+斜めショートカットへ横断合計 W_e が按分される。
!   W_e ≥ 面長では q = 1 で解像河道の表現と厳密一致(退化性)。
!
! MPI: 入力(rw/sw/x は全域、zbank / wrw は帯+ハロ)から各ランクが
!   自分のエッジ行 jsh..jeh-1 を決定的演算で冗長構築する(通信不要。
!   §11「冗長計算=配布機構」)。行 jsh-1, jeh は参照されないため 1 のまま
!----------------------------------------------------------------------
module subroutine build_channel_frw(g)
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, jlo, jhi
  real :: nb, capd

  allocate(frw(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 1.0)

  jlo = max(dcp%jsh, 1)
  jhi = min(dcp%jeh, g%ny)
  capd = sqrt(g%dx * g%dy)

  ! x法線エッジ(成分4): セル (i,j)-(i+1,j) の間
  do j = jlo, jhi
    do i = 1, g%nx - 1
      if (.not. is_channel(g, i, j) .or. .not. is_channel(g, i+1, j)) cycle
      if (have_bopen) then
        nb = (real(nblk(g, i, j, i+1)) + real(nblk(g, i+1, j, i))) / 2
        if (nb > 0) frw(4,i,j) = (lpy + nb * ldy) / lpy
      end if
    end do
  end do

  ! y法線エッジ(成分2): セル (i,j)-(i,j+1) の間
  !   両セルの zbank / wrw(帯確保 jsh:jeh)を読むため上限は jeh-1
  !   (時間ループが参照するエッジ行は je+1 = jeh-1 まで。§11)
  do j = jlo, min(dcp%jeh - 1, g%ny - 1)
    do i = 1, g%nx
      if (.not. is_channel(g, i, j) .or. .not. is_channel(g, i, j+1)) cycle
      if (have_bopen) then
        nb = (real(nblk_y(g, i, j, j+1)) + real(nblk_y(g, i, j+1, j))) / 2
        if (nb > 0) frw(2,i,j) = (lpx + nb * ldx) / lpx
      end if
    end do
  end do

  if (have_width) then
    ! セルの方向別通水率 cwx/cwy(u,v 正規化係数)を、幅キャップを
    ! frw に乗せる「前」に構築する: 分子=キャップ後の開口和、
    ! 分母=キャップ前(振り替えのみ)の開口和。比の形にすることで
    ! W ≥ 面長のセルでは分子=分母となり厳密に 1.0(退化性)。
    ! 対象は自帯セル js..je のみ(ハロ行の u,v は交換で得るため不要)。
    ! 壁エッジ(zbank 有効な河道セル↔堤内地)は u,v に寄与しないため
    ! 和から除外する(含めると比が 1 に希釈され正規化が失われる)
    call build_cw(g, capd)

    ! σ 有効時はキャップ前の frw を保存する(cw_cell の h 依存再評価が
    ! build_cw と同じ分母・分子を再構成するため。§26)
    if (have_sect) then
      allocate(frw0, source = frw)
    end if

    ! 幅キャップ q を全成分の河道—河道エッジへ重畳する
    ! (q の計算は build_cw と同じ wcap = 決定的に同値)
    do j = jlo, jhi
      do i = 1, g%nx - 1
        if (.not. is_channel(g, i, j) .or. .not. is_channel(g, i+1, j)) cycle
        frw(4,i,j) = frw(4,i,j) * wcap(g, i, j, i+1, j, g%dy)
      end do
    end do
    do j = jlo, min(dcp%jeh - 1, g%ny - 1)
      do i = 1, g%nx
        if (.not. is_channel(g, i, j) .or. .not. is_channel(g, i, j+1)) cycle
        frw(2,i,j) = frw(2,i,j) * wcap(g, i, j, i, j+1, g%dx)
      end do
    end do
    ! 斜めエッジ: 成分1 は添字 (a,b) でセル (a,b)-(a+1,b+1) を、
    !   成分3 はセル (a,b+1)-(a+1,b) を繋ぐ(die/dje の正準)。
    !   幅キャップのみ(開口補正は法線へ振り替える設計のため対象外)
    do j = jlo, min(dcp%jeh - 1, g%ny - 1)
      do i = 1, g%nx - 1
        if (is_channel(g, i, j) .and. is_channel(g, i+1, j+1)) then
          frw(1,i,j) = frw(1,i,j) * wcap(g, i, j, i+1, j+1, capd)
        end if
        if (is_channel(g, i, j+1) .and. is_channel(g, i+1, j)) then
          frw(3,i,j) = frw(3,i,j) * wcap(g, i, j+1, i+1, j, capd)
        end if
      end do
    end do
  end if
end subroutine


!----------------------------------------------------------------------
! セルの河道平面積率 wfrac の構築(developer.md §18)
!   wfrac = min(W · L_ch / (dx·dy), 1)。
!   L_ch は河道長のセル内通過長の近似で、河道隣接8近傍(x>0, sw=0,
!   rw>0)への半距離 w8dr(k)/2 の総和(直線 x 河道で dx、屈曲・合流・
!   異方格子が1つの定義で閉じる)。河道隣接ゼロの孤立河道セルは
!   L_ch = min(dx, dy) とみなす。下限は g%min_gv(gv と同じ理由の
!   数値ガード)。非河道セル・幅情報なし(W<=0)セルは 1。
!   蛇行によるセル内河道長の延長(蛇行係数)は表現しない(§18)。
!   MPI: 各ランクが帯 jsh..jeh を冗長構築(rw/sw/x 全域、wrw 帯+ハロ)
!----------------------------------------------------------------------
module subroutine build_wfrac(g)
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, k, in, jn
  real :: w, lch

  allocate(wfrac(1:g%nx, dcp%jsh:dcp%jeh), source = 1.0)

  do j = max(dcp%jsh, 1), min(dcp%jeh, g%ny)
    do i = 1, g%nx
      if (g%x(i,j) <= 0 .or. g%sw(i,j) /= 0 .or. g%rw(i,j) <= 0) cycle
      w = g%wrw(i,j)
      if (w <= 0.0) cycle                     ! 幅情報なし: 解像扱い
      lch = 0.0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle            ! x 番兵が領域外を弾く
        if (g%sw(in,jn) /= 0 .or. g%rw(in,jn) <= 0) cycle
        lch = lch + w8dr(k) / 2
      end do
      if (lch <= 0.0) lch = min(g%dx, g%dy)   ! 孤立河道セル
      wfrac(i,j) = min(w * lch / (g%dx * g%dy), 1.0)
      wfrac(i,j) = max(wfrac(i,j), g%min_gv)
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 堤防(仮想壁面)エッジの処理(developer.md §17)
!   河道セル(rw>0)と堤内地セル(rw=0 の陸)の間の全エッジ(対角含む)に
!   セル天端標高 g%zbank(河道セル持ち)の仮想壁を立て、f_bank_mode に
!   応じて計算済みの uve1, mne1 を上書きする。天端は絶対標高
!   (静的。geomorph による z の変化には追従しない)。
!   海(sw)が絡むエッジは rivermouth_drop の管轄なので対象外。
!   calc_kth_momentum から対象エッジ判定込みで毎エッジ呼ばれる
!----------------------------------------------------------------------
module subroutine bank_wall(p, g, s, i, j, in, jn, uve1, mne1)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j     ! 中心セルのインデックス
  integer, intent(in) :: in, jn   ! 近傍セルのインデックス
  real, intent(inout) :: uve1, mne1  ! エッジの流速・流量(中心→近傍が正)
  integer :: ic, jc               ! 河道側セルのインデックス
  integer :: il, jl               ! 堤内地側セルのインデックス
  real :: sgn                     ! 堤内地→河道向きの符号(中心→近傍が正)
  real :: zc                      ! 天端標高
  real :: wsr, wsl                ! 河道側・堤内地側の水位
  real :: h, u

  ! 対象エッジの判定
  if (g%sw(i,j) > 0 .or. g%sw(in,jn) > 0) return
  if (g%rw(i,j) > 0 .and. g%rw(in,jn) <= 0) then
    ic = i;  jc = j;  il = in; jl = jn
    sgn = -1.0
  else if (g%rw(in,jn) > 0 .and. g%rw(i,j) <= 0) then
    ic = in; jc = jn; il = i;  jl = j
    sgn = 1.0
  else
    return
  end if
  zc = g%zbank(ic,jc)
  if (zc <= zbank_min) return     ! この河道セルは堤防なし(通常計算のまま)

  ! 破堤サイトのエッジなら実効天端に差し替える(行バケットで
  ! サイトのない行は整数比較1回で素通り。§18)
  if (have_breach) zc = breach_crest(ic, jc, il, jl, zc)

  wsr = s%z(ic,jc) + max(s%h(ic,jc), 0.0)
  wsl = s%z(il,jl) + max(s%h(il,jl), 0.0)

  select case (f_bank_mode)
  case (e_bank_pump)
    ! 強制排水: 天端以下では河道水位によらず堤内地の全水深で段落ち
    ! (rivermouth_drop と同式)。どちらかの水位が天端を超えたら
    ! 単純堤防と同じ双方向の堰越流に切り替わる(ポンプの理想化は
    ! 堤防が機能している水位域でのみ意味を持つため)
    if (max(wsr, wsl) > zc) then
      call bank_weir_flux(p%gg, wsr, wsl, zc, sgn, uve1, mne1)
    else
      h = max(s%h(il,jl), 0.0)
      u = ((2. / 3.)**(3. / 2)) * sqrt(p%gg * h)
      uve1 = sgn * u
      mne1 = sgn * u * h
    end if
  case (e_bank_oneway)
    ! 樋門(逆止弁): 堤内水位が高い間は壁なしの通常計算のまま通す
    ! (逆向き成分は 0 にクリップ)。河道水位が高いときは天端まで
    ! 不透過、天端を超えたら河道→堤内の堰越流
    if (wsl >= wsr) then
      if (sgn * uve1 < 0) then
        uve1 = 0
        mne1 = 0
      end if
    else if (wsr > zc) then
      call bank_weir_flux(p%gg, wsr, wsl, zc, sgn, uve1, mne1)
    else
      uve1 = 0
      mne1 = 0
    end if
  case default    ! e_bank_weir
    ! 越流のみ(単純堤防): 双方向とも天端までは不透過、超えたら堰越流
    if (max(wsr, wsl) > zc) then
      call bank_weir_flux(p%gg, wsr, wsl, zc, sgn, uve1, mne1)
    else
      uve1 = 0
      mne1 = 0
    end if
  end select
end subroutine


!----------------------------------------------------------------------
! 破堤サイトの解釈・検証・行バケット構築(developer.md §18)
!   検証は全ランク冗長(隣接性・マスクは全域データ)。zbank の有効性と
!   zcrest0/zgnd0 の取得は帯を持つランクのみが行い、エラーは
!   par_allreduce_maxi で全ランク共有してから collective に par_stop(§11)。
!   セル対を帯内(jsh..jeh)に持たないランクの zcrest0/zgnd0 は 0 の
!   ままだが、そのランクの bank_wall は当該エッジに触れないため無害
!----------------------------------------------------------------------
module subroutine breach_init(p, g, s, ch)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_list_channel), intent(in) :: ch
  integer :: isite, k, n, ierr
  integer :: ic, jc, il, jl
  integer, allocatable :: nrow(:)
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  have_breach = .false.
  if (.not. ch%present_breach) return

  ! サイト数(br_cell の第1成分が埋まっている数。先頭からの連続充填を要求)
  nbr = 0
  do isite = 1, nbrsmax
    if (ch%br_cell(1,isite) == -9999) exit
    nbr = nbr + 1
  end do
  if (nbr <= 0) then
    call par_stop("list_channel_breach: br_cell が指定されていません")
  end if
  if (.not. have_bank) then
    call par_stop("list_channel_breach: 破堤には堤防(fn_bank / bank0 / fn_width)が必要です")
  end if

  allocate(br(nbr))
  do isite = 1, nbr
    ic = ch%br_cell(1,isite)
    jc = ch%br_cell(2,isite)
    il = ch%br_cell(3,isite)
    jl = ch%br_cell(4,isite)
    ! --- 全域データによる検証(全ランク冗長・同一判定 = par_stop 安全)---
    if (min(ic, il) < 1 .or. max(ic, il) > g%nx .or. &
        min(jc, jl) < 1 .or. max(jc, jl) > g%ny) then
      call par_stop("list_channel_breach: サイト"//itoa(isite)//" のセル座標が領域外です")
    end if
    if (max(abs(ic - il), abs(jc - jl)) /= 1) then
      call par_stop("list_channel_breach: サイト"//itoa(isite)// &
                    " のセル対が8近傍で隣接していません")
    end if
    if (.not. (g%x(ic,jc) > 0 .and. g%sw(ic,jc) == 0 .and. g%rw(ic,jc) > 0)) then
      call par_stop("list_channel_breach: サイト"//itoa(isite)// &
                    " の (ic,jc) が河道セルではありません")
    end if
    if (.not. (g%x(il,jl) > 0 .and. g%sw(il,jl) == 0 .and. g%rw(il,jl) <= 0)) then
      call par_stop("list_channel_breach: サイト"//itoa(isite)// &
                    " の (il,jl) が堤内地セルではありません")
    end if
    br(isite)%ic = ic
    br(isite)%jc = jc
    br(isite)%il = il
    br(isite)%jl = jl
    ! --- 時系列(分→秒、単調増加、割合 0〜1)---
    n = 0
    do k = 1, nbrvmax
      if (ch%br_series(1,k,isite) <= -9998.0) exit
      n = n + 1
    end do
    if (n <= 0) then
      call par_stop("list_channel_breach: サイト"//itoa(isite)//" の br_series がありません")
    end if
    br(isite)%nval = n
    allocate(br(isite)%val(1:2, 1:n))
    do k = 1, n
      br(isite)%val(1,k) = ch%br_series(1,k,isite) * 60   ! 分を秒に換算
      br(isite)%val(2,k) = ch%br_series(2,k,isite)
      if (br(isite)%val(2,k) < 0.0 .or. br(isite)%val(2,k) > 1.0) then
        call par_stop("list_channel_breach: サイト"//itoa(isite)// &
                      " の割合は 0〜1 で指定してください")
      end if
      if (k >= 2) then
        if (br(isite)%val(1,k) <= br(isite)%val(1,k-1)) then
          call par_stop("list_channel_breach: サイト"//itoa(isite)// &
                        " の時系列の時刻が単調増加ではありません")
        end if
      end if
    end do
  end do

  ! --- zbank の有効性検査と基準値の取得(帯を持つランクのみ)---
  ierr = 0
  do isite = 1, nbr
    ic = br(isite)%ic
    jc = br(isite)%jc
    if (jc >= dcp%jsh .and. jc <= dcp%jeh) then
      if (g%zbank(ic,jc) <= zbank_min) ierr = max(ierr, isite)
    end if
    if (jc >= dcp%jsh .and. jc <= dcp%jeh .and. &
        br(isite)%jl >= dcp%jsh .and. br(isite)%jl <= dcp%jeh) then
      br(isite)%zcrest0 = g%zbank(ic,jc)
      br(isite)%zgnd0 = s%z(br(isite)%il, br(isite)%jl)
      br(isite)%zeff = br(isite)%zcrest0
    end if
  end do
  call par_allreduce_maxi(ierr)
  if (ierr > 0) then
    call par_stop("list_channel_breach: サイト"//itoa(ierr)// &
                  " の河道セルに堤防天端がありません(zbank 無効)")
  end if

  ! --- 行バケットの構築(行 jc 順の安定整列。§18)---
  allocate(nrow(dcp%jsh:dcp%jeh), source = 0)
  allocate(ibr0(dcp%jsh:dcp%jeh), source = 1)
  allocate(ibr1(dcp%jsh:dcp%jeh), source = 0)
  allocate(ibrs(1:nbr), source = 0)
  do isite = 1, nbr
    jc = br(isite)%jc
    if (jc >= dcp%jsh .and. jc <= dcp%jeh) nrow(jc) = nrow(jc) + 1
  end do
  n = 0
  do jc = dcp%jsh, dcp%jeh
    ibr0(jc) = n + 1
    ibr1(jc) = n + nrow(jc)
    n = n + nrow(jc)
  end do
  nrow(:) = 0
  do isite = 1, nbr
    jc = br(isite)%jc
    if (jc >= dcp%jsh .and. jc <= dcp%jeh) then
      ibrs(ibr0(jc) + nrow(jc)) = isite
      nrow(jc) = nrow(jc) + 1
    end if
  end do
  deallocate(nrow)

  have_breach = .true.
end subroutine


!----------------------------------------------------------------------
! 破堤サイトの現時刻の実効天端 zeff の更新(毎ステップ。t の純関数で
! 全ランクが同値を冗長計算。f>=1 / f<=0 は端値に厳密固定=無破堤・
! 全破堤とのビット一致条件)
!----------------------------------------------------------------------
module subroutine breach_update(t)
  real, intent(in) :: t
  integer :: isite
  real :: f
  do isite = 1, nbr
    f = interp_series(br(isite)%val, br(isite)%nval, t)
    if (f >= 1.0) then
      br(isite)%zeff = br(isite)%zcrest0
    else if (f <= 0.0) then
      br(isite)%zeff = br(isite)%zgnd0
    else
      br(isite)%zeff = br(isite)%zgnd0 + f * (br(isite)%zcrest0 - br(isite)%zgnd0)
    end if
  end do
end subroutine


!----------------------------------------------------------------------
!----------------------------------------------------------------------
module subroutine breach_dispose()
  integer :: isite
  if (allocated(br)) then
    do isite = 1, nbr
      if (allocated(br(isite)%val)) deallocate(br(isite)%val)
    end do
    deallocate(br)
  end if
  if (allocated(ibr0)) deallocate(ibr0)
  if (allocated(ibr1)) deallocate(ibr1)
  if (allocated(ibrs)) deallocate(ibrs)
  nbr = 0
  have_breach = .false.
end subroutine


!======================================================================
!============= SUBMODULE 内の補助手続き(引数渡し。§13)==============
!======================================================================

!----------------------------------------------------------------------
! エッジ (ic,jc)-(il,jl) が破堤サイトなら実効天端を返す(それ以外は zc)
!----------------------------------------------------------------------
function breach_crest(ic, jc, il, jl, zc) result(z)
  integer, intent(in) :: ic, jc, il, jl
  real, intent(in) :: zc
  real :: z
  integer :: n, isite
  z = zc
  if (jc < lbound(ibr0,1) .or. jc > ubound(ibr0,1)) return
  do n = ibr0(jc), ibr1(jc)         ! この行のサイトだけ照合
    isite = ibrs(n)
    if (br(isite)%ic == ic .and. br(isite)%il == il .and. br(isite)%jl == jl) then
      z = br(isite)%zeff
      return
    end if
  end do
end function


!----------------------------------------------------------------------
! 堤防天端の堰越流流束(本間公式。自由/潜りを自動切替)
!   水位の高い側を上流として流向を決める。h2/h1 = 2/3 で両式は連続
!----------------------------------------------------------------------
subroutine bank_weir_flux(gg, wsr, wsl, zc, sgn, uve1, mne1)
  real, intent(in) :: gg          ! 重力加速度
  real, intent(in) :: wsr, wsl    ! 河道側・堤内地側の水位
  real, intent(in) :: zc          ! 天端標高
  real, intent(in) :: sgn         ! 堤内地→河道向きの符号(中心→近傍が正)
  real, intent(out) :: uve1, mne1
  real :: h1, h2                  ! 天端上の上流側・下流側の越流水深
  real :: dir                     ! 流向の符号(中心→近傍が正)
  real :: u

  if (wsl >= wsr) then            ! 堤内地→河道の越流
    h1 = max(wsl - zc, 0.0)
    h2 = max(wsr - zc, 0.0)
    dir = sgn
  else                            ! 河道→堤内地の越流
    h1 = max(wsr - zc, 0.0)
    h2 = max(wsl - zc, 0.0)
    dir = -sgn
  end if
  if (h1 <= 0) then
    uve1 = 0
    mne1 = 0
    return
  end if
  if (h2 < h1 * (2. / 3.)) then   ! 自由越流
    u = 0.35 * sqrt(2 * gg * h1)
    uve1 = dir * u
    mne1 = dir * u * h1
  else                            ! 潜り越流
    u = 0.91 * sqrt(2 * gg * (h1 - h2))
    uve1 = dir * u
    mne1 = dir * u * h2
  end if
end subroutine


!----------------------------------------------------------------------
! セルの方向別通水率 cwx/cwy の構築(自帯セル js..je)。
! 呼び出し時点の frw は振り替えのみ(幅キャップ前)であること
!----------------------------------------------------------------------
subroutine build_cw(g, capd)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: capd        ! 斜めエッジの幅キャップの分母 √(dx·dy)
  integer :: ic, jc, k, in, jn
  real :: f0, q, sx_, sy_
  real :: numx, denx, numy, deny
  real :: cap8(1:8)

  ! k 方位ごとの幅キャップの分母(成分4系=dy, 成分2系=dx, 斜め=√(dx·dy))
  cap8(1:8) = [ capd, g%dx, capd, g%dy, g%dy, capd, g%dx, capd ]

  allocate(cwx(1:g%nx, dcp%js:dcp%je), source = 1.0)
  allocate(cwy(1:g%nx, dcp%js:dcp%je), source = 1.0)

  do jc = dcp%js, dcp%je
    do ic = 1, g%nx
      if (.not. is_channel(g, ic, jc)) cycle
      if (g%wrw(ic,jc) <= 0.0) cycle        ! 幅情報なし: 正規化しない
      numx = 0.0
      denx = 0.0
      numy = 0.0
      deny = 0.0
      do k = 1, 8
        in = ic + din(k)
        jn = jc + djn(k)
        if (g%x(in,jn) <= 0) cycle          ! 領域外・無効(x 番兵)
        ! 壁エッジ(自セルが天端を持ち、相手が堤内地)は除外
        if (g%zbank(ic,jc) > zbank_min .and. g%sw(in,jn) == 0 .and. &
            g%rw(in,jn) <= 0) cycle
        f0 = frw(ke(k), ic+die(k), jc+dje(k))
        if (is_channel(g, in, jn)) then
          q = wcap(g, ic, jc, in, jn, cap8(k))
        else
          q = 1.0                           ! 河道—河道以外はキャップなし
        end if
        sx_ = l8y(k) / 2
        sy_ = l8x(k) / 2
        numx = numx + sx_ * f0 * q
        denx = denx + sx_ * f0
        numy = numy + sy_ * f0 * q
        deny = deny + sy_ * f0
      end do
      if (denx > 0.0) cwx(ic,jc) = numx / denx
      if (deny > 0.0) cwy(ic,jc) = numy / deny
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 幅キャップ係数 q = min(W_e / cap, 1)。W_e は両セルの正の幅の最小値。
! 両セルとも幅情報なし(W<=0)なら 1(解像扱い)
!----------------------------------------------------------------------
function wcap(g, i1, j1, i2, j2, cap) result(q)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i1, j1, i2, j2
  real, intent(in) :: cap
  real :: q, w1, w2, we
  q = 1.0
  w1 = g%wrw(i1,j1)
  w2 = g%wrw(i2,j2)
  if (w1 > 0.0 .and. w2 > 0.0) then
    we = min(w1, w2)
  else if (w1 > 0.0) then
    we = w1
  else if (w2 > 0.0) then
    we = w2
  else
    return
  end if
  q = min(we / cap, 1.0)
end function


!----------------------------------------------------------------------
! スケール付き幅キャップ q = min(W_e·sig / cap, 1)(§26)。
! sig=1 のとき we*1.0 はビット恒等のため wcap と厳密同値
!----------------------------------------------------------------------
function wcap_s(g, i1, j1, i2, j2, cap, sig) result(q)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i1, j1, i2, j2
  real, intent(in) :: cap, sig
  real :: q, w1, w2, we
  q = 1.0
  w1 = g%wrw(i1,j1)
  w2 = g%wrw(i2,j2)
  if (w1 > 0.0 .and. w2 > 0.0) then
    we = min(w1, w2)
  else if (w1 > 0.0) then
    we = w1
  else if (w2 > 0.0) then
    we = w2
  else
    return
  end if
  q = min(we * sig / cap, 1.0)
end function


!----------------------------------------------------------------------
! セル方向別通水率をスケール sig 付きで計算する(§26)。
! build_cw の1セル分と同一の式・同一の巡回順で、frw はキャップ前の
! 保存値 frw0 を使う(sig=1 で静的 cwx/cwy と厳密同値)。
! 親の continuous / restore_uvmn から σ(h) 付きで呼ばれる
!----------------------------------------------------------------------
module subroutine cw_cell(g, i, j, sig, cx, cy)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real, intent(in) :: sig
  real, intent(out) :: cx, cy
  integer :: k, in, jn
  real :: f0, q, sx_, sy_
  real :: numx, denx, numy, deny
  real :: cap8(1:8), capd

  cx = 1.0
  cy = 1.0
  if (.not. is_channel(g, i, j)) return
  if (g%wrw(i,j) <= 0.0) return
  capd = sqrt(g%dx * g%dy)
  cap8(1:8) = [ capd, g%dx, capd, g%dy, g%dy, capd, g%dx, capd ]
  numx = 0.0
  denx = 0.0
  numy = 0.0
  deny = 0.0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (g%x(in,jn) <= 0) cycle
    if (g%zbank(i,j) > zbank_min .and. g%sw(in,jn) == 0 .and. &
        g%rw(in,jn) <= 0) cycle
    f0 = frw0(ke(k), i+die(k), j+dje(k))
    if (is_channel(g, in, jn)) then
      q = wcap_s(g, i, j, in, jn, cap8(k), sig)
    else
      q = 1.0
    end if
    sx_ = l8y(k) / 2
    sy_ = l8x(k) / 2
    numx = numx + sx_ * f0 * q
    denx = denx + sx_ * f0
    numy = numy + sy_ * f0 * q
    deny = deny + sy_ * f0
  end do
  if (denx > 0.0) cx = numx / denx
  if (deny > 0.0) cy = numy / deny

end subroutine


!----------------------------------------------------------------------
! 河道セル(陸)か
!----------------------------------------------------------------------
function is_channel(g, ic, jc) result(res)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: ic, jc
  logical :: res
  res = g%x(ic,jc) > 0 .and. g%sw(ic,jc) == 0 .and. g%rw(ic,jc) > 0
end function


!----------------------------------------------------------------------
! 河道セル (ic,jc) の x横断側(斜め先の列 id)の塞がり本数(0〜2)
!----------------------------------------------------------------------
function nblk(g, ic, jc, id) result(n)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: ic, jc, id
  integer :: n, jd
  n = 0
  if (g%zbank(ic,jc) <= zbank_min) return   ! 天端なし: 壁もなし
  do jd = jc - 1, jc + 1, 2
    if (blocked(g, id, jd)) n = n + 1
  end do
end function


!----------------------------------------------------------------------
! 河道セル (ic,jc) の y横断側(斜め先の行 jd)の塞がり本数(0〜2)
!----------------------------------------------------------------------
function nblk_y(g, ic, jc, jd) result(n)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: ic, jc, jd
  integer :: n, id
  n = 0
  if (g%zbank(ic,jc) <= zbank_min) return   ! 天端なし: 壁もなし
  do id = ic - 1, ic + 1, 2
    if (blocked(g, id, jd)) n = n + 1
  end do
end function


!----------------------------------------------------------------------
! 斜め先セルが堤防壁の相手(堤内地)か。x 番兵が領域外を弾くため
! sw/rw の添字は番兵通過後のみ触る
!----------------------------------------------------------------------
function blocked(g, id, jd) result(res)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: id, jd
  logical :: res
  res = .false.
  if (g%x(id,jd) <= 0) return               ! 領域外・無効: 元々無フラックス
  res = g%sw(id,jd) == 0 .and. g%rw(id,jd) <= 0
end function

end submodule
