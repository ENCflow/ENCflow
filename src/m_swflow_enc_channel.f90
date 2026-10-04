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

  ! 破堤の状態(t_breach 型・br/行バケット)は親モジュールに置く
  ! (frw/wfrac/cwx と同じ「状態は親、構築は本 submodule」の様式。
  ! submodule 内に置けない理由は §13 の classic flang 系不具合2件:
  ! submodule 内定義型は AOCC の LTO が型記述子を解決できず、親の
  ! private 型は submodule の宣言部から見えない)

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
!   斜めエッジ(成分1,3)には対称に、両端セルが共有する側方 2 セルの塞がれた
!   軸開口シェア(d̂ 投影)を振り替える(diag_reassign。§68.11)。
!
! [幅キャップ(have_width)]
!   河道—河道の全成分エッジについて、両セルの河道幅の最小値 W_e
!   (正の値のみ。両方幅情報なしなら対象外)から
!     q = min(W_e / 面長, 1)   面長: 成分4=dy, 成分2=dx,
!                              成分1,3=dx·dy/dr(斜めの自然幅。§68.11)
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
  integer :: i, j, jlo, jhi, k, in, jn, ie, je
  real :: nb, capd, qb

  allocate(frw(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 1.0)

  jlo = max(dcp%jsh, 1)
  jhi = min(dcp%jeh, g%ny)
  ! 斜めエッジの幅キャップの分母 = 斜めの自然幅 dx·dy/dr(セル面積/対角
  ! 路長。dx=dy で 0.707·dx)。旧 √(dx·dy) から変更(§68.11): 対角 1 セル
  ! 河道で W = 自然幅のとき係数がちょうど 1 になり、貯留 wfrac = 1・流速
  ! 正規化 1 と整合する。W がこれを超える対角河道は「解像」扱い(自然幅で
  ! 頭打ち。より広い河道は 2 セル厚の階段で表す)
  capd = g%dx * g%dy / sqrt(g%dx**2 + g%dy**2)

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

  ! 斜めエッジ(成分1: (i,j)-(i+1,j+1)、成分3: (i,j+1)-(i+1,j))への対称な
  ! 振り替え(developer.md §68.11)。両端セルが共有する 2 つの側方セル
  ! (成分1 なら (i+1,j) と (i,j+1))が堤防壁で塞がれた分を斜めエッジへ
  ! 振り替え、2 つとも塞がれた直線の対角 1 セル河道で通過幅が斜めの自然幅
  ! dx·dy/dr(dx=dy で 0.707·dx。4.14 → 7.07)になるようにする。軸の規則が
  ! 直線の軸 1 セル河道で lpy·dy → dy(自然幅)にするのと対称。塞がり判定は
  ! 両端セルから見た平均(軸の規則と同形)。屈曲部では開いた軸エッジと
  ! 斜めエッジの両方が増強されるため横断合計が自然幅を超える
  ! (channel_model.md §3)
  if (have_bopen) then
    do j = jlo, min(dcp%jeh - 1, g%ny - 1)
      do i = 1, g%nx - 1
        if (is_channel(g, i, j) .and. is_channel(g, i+1, j+1)) then
          frw(1,i,j) = 1.0 + diag_reassign(g, i, j, i+1, j+1) / l8(1)
        end if
        if (is_channel(g, i, j+1) .and. is_channel(g, i+1, j)) then
          frw(3,i,j) = 1.0 + diag_reassign(g, i, j+1, i+1, j) / l8(3)
        end if
      end do
    end do
  end if

  if (have_width) then
    ! セルの方向別通水率 cwx/cwy(u,v 正規化係数)を、幅キャップを
    ! frw に乗せる「前」に構築する: 分子=キャップ後の開口和、
    ! 分母=キャップ前(振り替えのみ)の開口和。比の形にすることで
    ! W ≥ 面長のセルでは分子=分母となり厳密に 1.0(退化性)。
    ! 対象は自帯セル js..je のみ(ハロ行の u,v は交換で得るため不要)。
    ! 壁エッジ(zbank 有効な河道セル↔堤内地)は u,v に寄与しないため
    ! 和から除外する(含めると比が 1 に希釈され正規化が失われる)
    call build_cw(g, capd)

    ! σ 有効時と動的通水率(壁なし幅モード。§68.32)はキャップ前の frw を
    ! 保存する(cw_cell / build_cwd が build_cw と同じ分母・分子を再構成する
    ! ため。§26)
    if (have_sect .or. have_cwd) then
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
    ! 開いた辺境界の面(developer.md §68.26): 幅情報を持つ河道セルの
    ! 枠外近傍への面は「同じ幅の河道が外側へ続く」として、内部の
    ! 河道—河道エッジと同じ幅キャップ q = min(W/面長, 1) を与える。
    ! 係数なし(=1)のままだと、連続式の流出が自然幅あたりになって狭い
    ! 河道の貯留を抜き切るうえ、セル流速の再構成(Σ uve·w·frw / cwx)で
    ! 境界面の流速だけが 1/cwx 倍に増幅される正帰還になり発散する
    ! (対角 W=4 の東辺終端で毎ステップ ×1.26)。build_cw / cw_cell も
    ! 同じ面を同じ q で開口和に含める(境界セルの cwx が内部と同じ比に
    ! なる条件)。閉じた辺(壁)は無フラックスで対象外。区間流入の法線面
    ! (bc_inflow_face)は係数 1 のまま: 規定流量は面幅で按分した mn1 を
    ! 連続式がそのまま取り込む(質量厳密)。build_cw も同じ面を q=1 で
    ! 数えるので整合する
    if (have_open_bc) then
      do j = max(dcp%jsh, 1), min(dcp%jeh, g%ny)
        do i = 1, g%nx
          if (i /= 1 .and. i /= g%nx .and. j /= 1 .and. j /= g%ny) cycle
          if (.not. is_channel(g, i, j)) cycle
          if (g%wrw(i,j) <= 0.0) cycle
          ! 開面に共通の係数 q_b(流向への投影幅で正規化。合計流出 = W·u·h。
          ! 2026-10-04 に面ごとの min(W/面長, 1) から変更: 軸終端で 1.24 W、
          ! 対角終端で 0.88 W になり終端セルの水深が下がる/盛り上がった)
          qb = qb_bound(g, i, j)
          do k = 1, 8
            in = i + din(k)
            jn = j + djn(k)
            if (in >= 1 .and. in <= g%nx .and. jn >= 1 .and. jn <= g%ny) cycle
            if (.not. bc_open_face(in, jn)) cycle
            if (bc_inflow_face(in, jn)) cycle
            ie = i + die(k)
            je = j + dje(k)
            if (je < dcp%jsh - 1 .or. je > dcp%jeh) cycle
            frw(ke(k), ie, je) = qb
          end do
        end do
      end do
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! 境界セルの開面に共通の幅係数 q_b = min(W / Wn, 1)(§68.26)
!   Wn = Σ_open l8_k·max(n̂_k·d̂, 0) は開面(流入面を除く)の河道流向 d̂ への
!   投影幅(軸河道の終端で dx、対角河道で dx·dy/dr = 斜めの自然幅)。d̂ は
!   河道マスク上の河道近傍セルから自セルへ向かうベクトルの和(終端セルでは
!   上流側近傍 1 つ = 流下方向)。河道近傍がない孤立セルは辺の外向き法線。
!   開面すべてに同じ q_b を与えると、流向 d̂ の流れに対する合計流出が
!   ちょうど W·u·h になる(ENC の配分 Σ l8·n̂ が自然幅になる性質)。
!   静的(マスク幾何のみ)なので cwx との整合が保てる。build_cw / cw_cell
!   も同じ値を使う
!----------------------------------------------------------------------
!----------------------------------------------------------------------
! 境界河道セルの流向 d̂(河道マスク上の河道近傍から自セルへのベクトル和の
! 向き。終端セルでは上流側近傍 = 流下方向)。近傍なし・対称なら辺の
! 外向き法線(角は合成)。それも無ければ偽。qb_bound と put_bc_faces
! (幅河道の終端セルの出口流束。§68.30)が同じ d̂ を使う
!----------------------------------------------------------------------
module function chan_dir(g, i, j, ux, uy) result(ok)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real, intent(out) :: ux, uy
  logical :: ok
  integer :: k, in, jn
  real :: vn
  ok = .true.
  ux = 0.0
  uy = 0.0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (in < 1 .or. in > g%nx .or. jn < 1 .or. jn > g%ny) cycle
    if (is_channel(g, in, jn)) then
      ux = ux - real(din(k)) * g%dx
      uy = uy - real(djn(k)) * g%dy
    end if
  end do
  vn = sqrt(ux**2 + uy**2)
  if (vn > 0.0) then
    ux = ux / vn
    uy = uy / vn
  else
    ! 河道近傍なし(孤立セル)または対称: 辺の外向き法線(角は合成)
    ux = 0.0
    uy = 0.0
    if (i == 1) ux = -1.0
    if (i == g%nx) ux = 1.0
    if (j == 1) uy = -1.0
    if (j == g%ny) uy = 1.0
    vn = sqrt(ux**2 + uy**2)
    if (vn <= 0.0) then
      ok = .false.
      return
    end if
    ux = ux / vn
    uy = uy / vn
  end if
end function


function qb_bound(g, i, j) result(q)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real :: q
  integer :: k, in, jn
  real :: ux, uy, wn
  q = 1.0
  if (.not. chan_dir(g, i, j, ux, uy)) return
  wn = 0.0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (in >= 1 .and. in <= g%nx .and. jn >= 1 .and. jn <= g%ny) cycle
    if (.not. bc_open_face(in, jn)) cycle
    if (bc_inflow_face(in, jn)) cycle
    wn = wn + l8(k) * max(n8x(k) * ux + n8y(k) * uy, 0.0)
  end do
  if (wn > 0.0) q = min(g%wrw(i,j) / wn, 1.0)
end function


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
      lch = lch_cell(g, i, j)
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
module subroutine seawall_wall(p, g, s, i, j, in, jn, uve1, mne1)
  ! 海岸堤防(仮想壁面の海岸応用。§17.1・handoff 1o 改訂設計)。
  ! 「天端を持つ陸側セル」と「海側セル(ssw = fn_seaside ∪ sw)」の間の
  ! 全エッジ(対角含む)に仮想壁を立てる。天端は陸側(保護側)セルの
  ! g%zswall。sw を使わない津波ケース(境界入射の伝搬計算)でも
  ! fn_seaside の向き付けで機能し、海側水位には伝搬してきた波の動的
  ! 水位がそのまま効く。河道セルには setup が天端を置かないため河口は
  ! 開口。水理モード f_swall_mode は f_bank_mode と同義(0:越流のみ,
  ! 1:フラップ=陸閘・水門相当(陸→海の排水のみ通し海→陸は天端まで
  ! 遮断), 2:強制排水=排水機場相当)。越流は本間公式(bank_weir_flux
  ! を共用)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j     ! 中心セルのインデックス
  integer, intent(in) :: in, jn   ! 近傍セルのインデックス
  real, intent(inout) :: uve1, mne1  ! エッジの流速・流量(中心→近傍が正)
  integer :: ic, jc               ! 海側セルのインデックス
  integer :: il, jl               ! 陸側セルのインデックス
  real :: sgn                     ! 陸→海向きの符号(中心→近傍が正)
  real :: zc                      ! 天端標高
  real :: wsr, wsl                ! 海側・陸側の水位
  real :: h, u

  ! 対象エッジの判定(片側が海側マスク・他側が陸)
  if (g%ssw(i,j) > 0 .and. g%ssw(in,jn) <= 0) then
    ic = i;  jc = j;  il = in; jl = jn
    sgn = -1.0
  else if (g%ssw(in,jn) > 0 .and. g%ssw(i,j) <= 0) then
    ic = in; jc = jn; il = i;  jl = j
    sgn = 1.0
  else
    return
  end if
  zc = g%zswall(il,jl)
  if (zc <= zbank_min) return     ! この陸側セルは堤防なし(通常計算のまま)

  wsr = s%z(ic,jc) + max(s%h(ic,jc), 0.0)
  wsl = s%z(il,jl) + max(s%h(il,jl), 0.0)

  select case (f_swall_mode)
  case (e_bank_pump)
    ! 強制排水(排水機場): 天端以下では海側水位によらず陸側の全水深で
    ! 段落ち排水。どちらかの水位が天端を超えたら双方向の堰越流に切替
    if (max(wsr, wsl) > zc) then
      call bank_weir_flux(p%gg, wsr, wsl, zc, sgn, uve1, mne1)
    else
      h = max(s%h(il,jl), 0.0)
      u = ((2. / 3.)**(3. / 2)) * sqrt(p%gg * h)
      uve1 = sgn * u
      mne1 = sgn * u * h
    end if
  case (e_bank_oneway)
    ! フラップ(陸閘・水門): 陸側水位が高い間は壁なしの通常計算のまま
    ! 通す(海→陸成分は 0 にクリップ)。海側水位が高いときは天端まで
    ! 不透過、天端を超えたら海→陸の堰越流
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
! エッジ (i,j)-(in,jn) が堤防壁エッジか(bank_wall が流速・流量を上書き
! するエッジ。bank_wall の対象判定と同一に保つこと)
!----------------------------------------------------------------------
module function bank_edge(g, s, i, j, in, jn) result(res)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j, in, jn
  logical :: res
  res = .false.
  if (g%sw(i,j) > 0 .or. g%sw(in,jn) > 0) return
  if (g%rw(i,j) > 0 .and. g%rw(in,jn) <= 0) then
    res = is_wall(g%zbank(i,j), s%z(i,j), s%z(in,jn))
  else if (g%rw(in,jn) > 0 .and. g%rw(i,j) <= 0) then
    res = is_wall(g%zbank(in,jn), s%z(in,jn), s%z(i,j))
  end if
end function


!----------------------------------------------------------------------
! セルごとの堤防壁エッジ本数 nwall(帯+ハロ)。bank_wall が参照するのは
! 自帯セルとその近傍(js-1..je+1)で、その 8 近傍は jsh..jeh に収まる
! (ハロ 2)。壁判定は静的(g%z)。§68.29 (C')
!----------------------------------------------------------------------
module subroutine bank_init(g)
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, k, in, jn, jlo, jhi
  if (allocated(nwall)) deallocate(nwall)
  allocate(nwall(1:g%nx, dcp%jsh:dcp%jeh), source = 0)
  jlo = max(dcp%jsh, 1)
  jhi = min(dcp%jeh, g%ny)
  do j = jlo, jhi
    do i = 1, g%nx
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) cycle
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (in < 1 .or. in > g%nx .or. jn < jlo .or. jn > jhi) cycle
        if (g%x(in,jn) <= 0 .or. g%sw(in,jn) > 0) cycle
        if (g%rw(i,j) > 0 .and. g%rw(in,jn) <= 0) then
          if (is_wall(g%zbank(i,j), g%z(i,j), g%z(in,jn))) nwall(i,j) = nwall(i,j) + 1
        else if (g%rw(in,jn) > 0 .and. g%rw(i,j) <= 0) then
          if (is_wall(g%zbank(in,jn), g%z(in,jn), g%z(i,j))) nwall(i,j) = nwall(i,j) + 1
        end if
      end do
    end do
  end do
end subroutine

module subroutine bank_wall(p, g, s, i, j, k, in, jn, uve1, mne1)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j     ! 中心セルのインデックス
  integer, intent(in) :: k        ! 近傍方向(mn2dh の添字)
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
  ! 天端が両側地盤より高いエッジだけが壁(§68.29 (B)。天端なし、または
  ! 天端が河床・堤内地地盤以下のエッジは通常計算のまま = 地盤が段差)
  if (.not. is_wall(zc, s%z(ic,jc), s%z(il,jl))) return

  ! 破堤サイトのエッジなら実効天端に差し替える(行バケットで
  ! サイトのない行は整数比較1回で素通り。§18)
  if (have_breach) zc = breach_crest(ic, jc, il, jl, zc)

  ! エッジごとの実効天端: 天端は堤内地側の地盤と河道側の河床を下回れない
  ! (セル 1 値の天端が堤内地地盤を下回るエッジでは、越流水深 h1 に地盤差が
  ! 乗って斜面側の水量を超える落差流が立つ。§68.12 の発散機構。河床を
  ! 下回る天端も同様に河道側で落差が乗るため河床で下限する。天端が両地盤
  ! 以上のエッジでは恒等。§68.25)
  zc = max(zc, s%z(il,jl), s%z(ic,jc))

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
      call cap_overshoot
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
      call cap_overshoot
    else
      uve1 = 0
      mne1 = 0
    end if
  case default    ! e_bank_weir
    ! 越流のみ(単純堤防): 双方向とも天端までは不透過、超えたら堰越流
    if (max(wsr, wsl) > zc) then
      call bank_weir_flux(p%gg, wsr, wsl, zc, sgn, uve1, mne1)
      call cap_overshoot
    else
      uve1 = 0
      mne1 = 0
    end if
  end select

contains
  !--------------------------------------------------------------------
  ! 堰流量の追い越し禁止(§68.29 (C')): 堰公式は慣性のない代数則で、潜り
  ! 越流の流量が天端上水深 h2 に比例するため、天端が水面より十分下
  ! (深い湛水)では 1 ステップで移る水量が水位差を追い越して 2Δt 振動に
  ! なる(追い越し条件 Δws < 0.01·h2²)。両セルの水位差の半分までしか
  ! 1 ステップで縮めないよう流量に上限を掛ける。セルの壁エッジ本数 nwall
  ! で按分する(全壁エッジが同時に同じ上限まで流しても追い越さない)。
  ! 水位の応答は実効平面積率 af(gv·wfrac·σ 比)で換算する。上限が効くのは
  ! 追い越し域だけで、天端近くの本来の堰流れでは恒等
  !--------------------------------------------------------------------
  subroutine cap_overshoot
    real :: qcap, cor
    qcap = 0.5 * abs(wsr - wsl) / (mn2dh(k) * (real(nwall(ic,jc)) / s%af(ic,jc) &
                                              + real(nwall(il,jl)) / s%af(il,jl)))
    if (abs(mne1) > qcap) then
      cor = qcap / abs(mne1)
      mne1 = mne1 * cor
      uve1 = uve1 * cor
    end if
  end subroutine
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
    call par_stop("list_channel_breach: br_cell is not specified")
  end if
  if (.not. have_bank) then
    call par_stop("list_channel_breach: breach requires a levee (fn_bank / bank0 / fn_width)")
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
      call par_stop("list_channel_breach: cell coordinates of site "//itoa(isite)// &
                    " are outside the domain")
    end if
    if (max(abs(ic - il), abs(jc - jl)) /= 1) then
      call par_stop("list_channel_breach: cell pair of site "//itoa(isite)// &
                    " is not adjacent within the 8 neighbors")
    end if
    if (.not. (g%x(ic,jc) > 0 .and. g%sw(ic,jc) == 0 .and. g%rw(ic,jc) > 0)) then
      call par_stop("list_channel_breach: (ic,jc) of site "//itoa(isite)// &
                    " is not a channel cell")
    end if
    if (.not. (g%x(il,jl) > 0 .and. g%sw(il,jl) == 0 .and. g%rw(il,jl) <= 0)) then
      call par_stop("list_channel_breach: (il,jl) of site "//itoa(isite)// &
                    " is not a landside (non-channel) cell")
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
      call par_stop("list_channel_breach: br_series of site "//itoa(isite)//" is missing")
    end if
    br(isite)%nval = n
    allocate(br(isite)%val(1:2, 1:n))
    do k = 1, n
      br(isite)%val(1,k) = ch%br_series(1,k,isite) * 60   ! 分を秒に換算
      br(isite)%val(2,k) = ch%br_series(2,k,isite)
      if (br(isite)%val(2,k) < 0.0 .or. br(isite)%val(2,k) > 1.0) then
        call par_stop("list_channel_breach: breach fraction of site "//itoa(isite)// &
                      " must be in [0, 1]")
      end if
      if (k >= 2) then
        if (br(isite)%val(1,k) <= br(isite)%val(1,k-1)) then
          call par_stop("list_channel_breach: br_series times of site "//itoa(isite)// &
                        " must be strictly increasing")
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
    call par_stop("list_channel_breach: channel cell of site "//itoa(ierr)// &
                  " has no levee crest (zbank is invalid there)")
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

  ! 流速正規化のキャップ分母はセルの自然幅 dx·dy/L_ch(軸 1 セル河道で
  ! dy = 通過幅キャップの面長と同値、対角 1 セル河道で dx²/dr)。セル平均
  ! 流量 (m, n) は自然幅に塗り広げた量なので、河道内流速 = (|q|/h)/(W/自然幅)。
  ! 通過幅キャップ(frw)の分母 面長(成分別 cap8)とは別物(§68.11)。
  ! 河道の端のセル(河道隣接 1 つ)は L_ch = dx/2 で自然幅が 2 倍になるため
  ! L_ch の下限を min(dx,dy) にする(直線軸河道の全セルで dy に一致)
  if (capd > 0.0) continue                  ! 引数未使用の警告を抑制(互換のため残す)

  allocate(cwx(1:g%nx, dcp%js:dcp%je), source = 1.0)
  allocate(cwy(1:g%nx, dcp%js:dcp%je), source = 1.0)

  do jc = dcp%js, dcp%je
    do ic = 1, g%nx
      if (.not. is_channel(g, ic, jc)) cycle
      if (g%wrw(ic,jc) <= 0.0) cycle        ! 幅情報なし: 正規化しない
      cap8(1:8) = g%dx * g%dy / max(lch_cell(g, ic, jc), min(g%dx, g%dy))
      numx = 0.0
      denx = 0.0
      numy = 0.0
      deny = 0.0
      do k = 1, 8
        in = ic + din(k)
        jn = jc + djn(k)
        if (in < 1 .or. in > g%nx .or. jn < 1 .or. jn > g%ny) then
          ! 枠外近傍: 開いた辺境界の面は「同じ幅の河道の続き」として
          ! 内部の河道—河道エッジと同じ q で開口和に含める(§68.26)。
          ! 閉じた辺は無フラックス
          if (.not. have_open_bc) cycle
          if (.not. bc_open_face(in, jn)) cycle
          f0 = 1.0
          if (bc_inflow_face(in, jn)) then
            q = 1.0                         ! 流入面は係数なし(frw も 1)
          else
            q = qb_bound(g, ic, jc)         ! 境界面の frw と同じ係数
          end if
        else
          if (g%x(in,jn) <= 0) cycle        ! 無効セル(x 番兵)
          ! 壁エッジ(自セルが天端を持ち、相手が堤内地)は除外
          ! (zbank は堤防有効時だけ確保される。壁なし幅モードでは壁エッジなし)
          if (g%bank_active) then
            if (g%sw(in,jn) == 0 .and. g%rw(in,jn) <= 0 .and. &
                is_wall(g%zbank(ic,jc), g%z(ic,jc), g%z(in,jn))) cycle
          end if
          f0 = frw(ke(k), ic+die(k), jc+dje(k))
          if (is_channel(g, in, jn)) then
            q = wcap(g, ic, jc, in, jn, cap8(k))
          else
            q = 1.0                         ! 河道—河道以外はキャップなし
          end if
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
! 動的な通水率 cwxd/cwyd(§68.32。壁なし幅モード = 幅 + 動的開口)。
!   build_cw と同じ巡回・同じ式で、非河道の近傍エッジに塞がり率 s(sblk。
!   fwd と同じ定義)の重み (1 − s) を掛けて開口和に入れる。壁エッジは除外
!   (build_cw と同じ)。重みが 1 のエッジ(河道—河道、開いた辺境界)と
!   除外エッジだけのセルでは静的 cwx とビット同値(1.0 の乗算と 0 の加算)。
!   ステップ頭(h, z はハロ交換済み)に自帯セルについて構築する
!----------------------------------------------------------------------
module subroutine build_cwd(g, s)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: ic, jc, k, in, jn
  real :: f0, q, wgt, sx_, sy_
  real :: numx, denx, numy, deny
  real :: cap8(1:8)

  !$omp parallel do schedule(dynamic) private(ic, jc, k, in, jn, f0, q, wgt, sx_, sy_, numx, denx, numy, deny, cap8)
  do jc = dcp%js, dcp%je
    do ic = 1, g%nx
      if (.not. is_channel(g, ic, jc)) cycle
      if (g%wrw(ic,jc) <= 0.0) cycle
      cap8(1:8) = g%dx * g%dy / max(lch_cell(g, ic, jc), min(g%dx, g%dy))
      numx = 0.0
      denx = 0.0
      numy = 0.0
      deny = 0.0
      do k = 1, 8
        in = ic + din(k)
        jn = jc + djn(k)
        wgt = 1.0
        if (in < 1 .or. in > g%nx .or. jn < 1 .or. jn > g%ny) then
          if (.not. have_open_bc) cycle
          if (.not. bc_open_face(in, jn)) cycle
          f0 = 1.0
          if (bc_inflow_face(in, jn)) then
            q = 1.0
          else
            q = qb_bound(g, ic, jc)
          end if
        else
          if (g%x(in,jn) <= 0) cycle
          if (g%bank_active) then
            if (g%sw(in,jn) == 0 .and. g%rw(in,jn) <= 0 .and. &
                is_wall(g%zbank(ic,jc), g%z(ic,jc), g%z(in,jn))) cycle
          end if
          f0 = frw0(ke(k), ic+die(k), jc+dje(k))   ! キャップ前(build_cw と同じ)
          if (is_channel(g, in, jn)) then
            q = wcap(g, ic, jc, in, jn, cap8(k))
          else
            q = 1.0
            wgt = 1.0 - sblk(g, s, ic, jc, in, jn)   ! 乾いて高い側方 = 0、開いた氾濫原 = 1
          end if
        end if
        sx_ = l8y(k) / 2
        sy_ = l8x(k) / 2
        numx = numx + sx_ * f0 * q * wgt
        denx = denx + sx_ * f0 * wgt
        numy = numy + sy_ * f0 * q * wgt
        deny = deny + sy_ * f0 * wgt
      end do
      cwxd(ic,jc) = 1.0
      cwyd(ic,jc) = 1.0
      if (denx > 0.0) cwxd(ic,jc) = numx / denx
      if (deny > 0.0) cwyd(ic,jc) = numy / deny
    end do
  end do
  !$omp end parallel do
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
  ! 2026-10-04(§68.28): 面流束を断面積ベース u·vh に統一したため、エッジ
  ! 流速はそのまま河道内流速であり、通水率の σ 縮尺(q = W·σ/面長)は
  ! 行わない(sig は互換のため受け取るが無視。静的 cwx/cwy と厳密同値)
  if (sig > 0.0) continue
  if (.not. is_channel(g, i, j)) return
  if (g%wrw(i,j) <= 0.0) return
  capd = g%dx * g%dy / max(lch_cell(g, i, j), min(g%dx, g%dy))   ! 自然幅(build_cw と同じ)
  cap8(1:8) = capd
  numx = 0.0
  denx = 0.0
  numy = 0.0
  deny = 0.0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (in < 1 .or. in > g%nx .or. jn < 1 .or. jn > g%ny) then
      ! 枠外近傍: build_cw と同じ扱い(開いた辺境界の面は同じ幅の続き。
      ! sig=1 で build_cw とビット同値)
      if (.not. have_open_bc) cycle
      if (.not. bc_open_face(in, jn)) cycle
      f0 = 1.0
      if (bc_inflow_face(in, jn)) then
        q = 1.0
      else
        q = qb_bound(g, i, j)               ! 境界面の frw と同じ係数
      end if
    else
      if (g%x(in,jn) <= 0) cycle
      if (g%bank_active) then
        if (g%sw(in,jn) == 0 .and. g%rw(in,jn) <= 0 .and. &
            is_wall(g%zbank(i,j), g%z(i,j), g%z(in,jn))) cycle
      end if
      f0 = frw0(ke(k), i+die(k), j+dje(k))
      if (is_channel(g, in, jn)) then
        q = wcap(g, i, j, in, jn, cap8(k))
      else
        q = 1.0
      end if
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
!----------------------------------------------------------------------
! 斜めエッジ A(ia,ja)–B(ib,jb) へ振り替える塞がりシェアの合計(通過幅 m)
!   側方セルは S1=(ib,ja)、S2=(ia,jb)。A から S1 は x 法線(ib = ia±1)、
!   A から S2 は y 法線、B からはその逆。塞がり判定は各端セルの天端の
!   有無を要する(nblk と同じ)。両端からの平均
!----------------------------------------------------------------------
function diag_reassign(g, ia, ja, ib, jb) result(sh)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: ia, ja, ib, jb
  real :: sh, s1, ld
  ! 側方 2 セルとも塞がれたとき通過幅が斜めの自然幅 dx·dy/dr(セル面積/
  ! 対角路長)になるよう、塞がり 1 件あたり (dx·dy/dr − l8_d)/2 を振り替える
  ! (dx=dy: 4.14 → 7.07 = 0.707·dx。軸の規則が lpy·dy → dy にするのと同じ
  ! 「自然幅まで」の目標。W = 自然幅 ⇔ wfrac = 1 ⇔ 流速正規化 1 と整合)
  ld = l8(1)
  s1 = (g%dx * g%dy / sqrt(g%dx**2 + g%dy**2) - ld) / 2
  sh = 0.0
  if (blocked(g, ia, ja, ib, ja)) sh = sh + s1
  if (blocked(g, ia, ja, ia, jb)) sh = sh + s1
  if (blocked(g, ib, jb, ib, ja)) sh = sh + s1
  if (blocked(g, ib, jb, ia, jb)) sh = sh + s1
  sh = sh / 2                         ! 両端セルから見た塞がりの平均
end function

!----------------------------------------------------------------------
! 河道セルのセル内河道長 L_ch(河道隣接 8 近傍への半距離 w8dr/2 の総和。
!   直線 x 河道で dx、対角 1 セル河道で dr、孤立セルは min(dx,dy))。
!   wfrac = W·L_ch/(dx·dy) の L_ch であり、dx·dy/L_ch はセルの「自然幅」
!   (セル面積/路長。軸 1 セル河道で dy、対角で dx²/dr)。§18・§68.11
!----------------------------------------------------------------------
function lch_cell(g, i, j) result(lch)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real :: lch
  integer :: k, in, jn
  lch = 0.0
  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (g%x(in,jn) <= 0) cycle            ! x 番兵が領域外を弾く
    if (g%sw(in,jn) /= 0 .or. g%rw(in,jn) <= 0) cycle
    lch = lch + w8dr(k) / 2
  end do
  if (lch <= 0.0) lch = min(g%dx, g%dy)   ! 孤立河道セル
end function

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
  do jd = jc - 1, jc + 1, 2
    if (blocked(g, ic, jc, id, jd)) n = n + 1
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
  do id = ic - 1, ic + 1, 2
    if (blocked(g, ic, jc, id, jd)) n = n + 1
  end do
end function


!----------------------------------------------------------------------
! 河道セル (ic,jc) から見た斜め先セル (id,jd) が堤防壁で塞がれているか
! (相手が堤内地で、天端が両側地盤より高い。is_wall = bank_wall と同じ
! 述語。静的表なので g%z)。x 番兵が領域外を弾くため sw/rw の添字は
! 番兵通過後のみ触る
!----------------------------------------------------------------------
function blocked(g, ic, jc, id, jd) result(res)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: ic, jc, id, jd
  logical :: res
  res = .false.
  if (g%x(id,jd) <= 0) return               ! 領域外・無効: 元々無フラックス
  if (g%sw(id,jd) /= 0 .or. g%rw(id,jd) > 0) return
  res = is_wall(g%zbank(ic,jc), g%z(ic,jc), g%z(id,jd))
end function

end submodule
