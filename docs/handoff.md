# ENCflow 作業引き継ぎメモ(チャット移行用)

設計・規約・実バグの記録の正本は開発記録(目次 developer.md、本文は docs/developer/NNN.md)。
基本方針は policy.md、全体の案内図は architecture.md。このメモは「現在進行中・未完了の項目」だけを書く。
完了したら消してよい(他の文書から参照されている完了済みの調査記録だけは
末尾の節に残す)。2026-10-30 に全体を整理し、完了した経過は developer.md の
各 § に任せて、残りの項目だけにした。

本書は目次で、項目の本文は 1 項目 1 ファイルで docs/handoff/<番号>.md に置く(00y なら
[handoff/00y.md](handoff/00y.md))。公開準備と中期の道標も docs/handoff/ の別のファイルにある。
全体を通して読まず、下の一覧から、いまの作業に関わる項目だけを開く。

## 書き方

- **項目番号は識別子**。ほかの文書から「handoff 00y」の形で引用される。番号は付け直さず、使い終わった番号を
  別の項目に使わない(過去の記録の「handoff 00y」の指す先が変わるため)。
- **新しい項目**: 使っていない番号で docs/handoff/<番号>.md を起こす。1 行目は「<番号>. **題名** — 本文」の形。
  下の一覧の該当する節に同じ題名で 1 行足す(150 字を超える題名は、先頭を残して「…」で縮めてよい)。本書に
  項目の本文を書かない。
- **完了したら**: その項目のファイルと一覧の行を消し、経過は開発記録の該当する節に書く。他の文書から参照されて
  いる調査の記録だけは残し、一覧の行を「完了した調査の記録」へ移す。
- **大きさ**: 1 つのファイルが 200 KB を超えそうなら項目を分ける(Markdown は 400 KB まで。CI)。
- **検査**: tools/devdocs/check.py の handoff が、一覧とファイル・1 行目の番号・題名の一致を照合する。
- **分割前の履歴**: 本書は 2026-11-22 まで 1 ファイル(約 340 KB)だった。分割前の最後の版はコミット 0bad327 の
  docs/handoff.md で、`git log 0bad327 -- docs/handoff.md` でたどる(分割の記録は developer.md §116.7)。

## 現在の到達点(要約。2026-10-30)

- MPI 化は完了・検証済み: 帯分割+ハロ交換(案A)、確保縮小(第二段)、
  静的データの帯化(方式a・2点縮小)、m_record の点集約、決定的リダクション、
  領域マスクの窓への確保の縮小(§79〜§83)。
  検証の柱 =「np=1,2,4 が逐次 reference に ULP=0」+「-fcheck np>=2 を先に回す」
  (-Ofast では逐次↔MPI ビルド間の最終桁差が出るため、厳密なビット検証は
  -O2 厳密数学で行う。§28.3・§63.6)。毎 push の CI(ci.yml)と夜間の Nightly
  (nightly.yml。逐次・np=1,2,4・-Og -fcheck=all の np=2・BMI)が回る(§10)。
- 動的状態化: s%z(計算標高。g%z = 入力地形。帯で持つ §81)に加え、
  空隙率 s%gv / 有効慣性係数 s%lm(§63.1。変更は m_state_set_gv 経由で
  体積保存)。
- 物理プロセスモジュール: 浅水流(ENC/STG。1 層非静水圧 §69)、河道・堤防・
  構造物族(ポンプ・カルバート・分水・ダム/湖沼)、降雨・遮断・蒸発散・気象、
  2 層地下水+管路連続体+井戸+凍土+鉛直不飽和浸透 VZ(§87)+貯留関数法の区画流出(§106)、
  淡塩 2 層、水質、
  積雪・融雪、氷河、土砂・地形変化(creep/fluvial/suspend/wash/splash/debris/
  bedslide/rockfall、蛇行・河岸侵食・定着 §84、溶食 §86、岩盤下刻 §89)、波浪
  (沿岸漂砂 fn_wave §84.15、沿岸の波浪場 §90)、規定底面運動(断層津波 §70)、
  溶岩流、流木、家屋破壊・瓦礫、土壌雨量指数、多段ネスティング(§71〜§75)と
  BMI(§73・§76・§77)。有効化は fn_* の有無、無効時はメモリ・CPU ゼロ追加。
- 「まず動かしてみる」既定値方針: geomorph(§62)・流木(§50.6)・家屋破壊・
  瓦礫(§63.9)・地下水(§64。sd0 の既定 1 m を含む)・積雪と氷河(§65)・
  遮断・蒸発散・溶岩流(§66)は物性・校正値に既定を持ち、採用値を
  "(default)" 付きで表示。型別の推奨値は各ガイド章の「パターン別の推奨値」。
  wq は物質依存のため既定を置かず「物質別の代表値」表(§66)。与件
  (強制場・境界・構造物諸元・分布ファイル・噴火口・井戸)には既定を置かず、
  それらの章(浅水流・河道・境界・潮位・初期条件・地理情報の粗度・淡塩・
  SWI・構造物・計測・降雨)には「とりあえず動かしてみる」最小入力と
  型別の目安表を置いた(2026-10-01。日英)。潮位は titype 未指定 = 固定
  潮位 0 m の既定(§67)で空の &list_tide が最小入力。
- 河道水理(fn_channel。§17・§18・§26・§68.9〜§68.33): 堤防(壁は天端が
  両側地盤より高いエッジだけ、堰越流に追い越し禁止上限)、開口補正、
  サブグリッド幅(壁なし=自然河岸は動的開口+動的通水率 cwxd)、σ 断面
  (天端固定 D(t)、濃度 hs/vh)、幅河道終端の出口規則。等流ベンチマーク
  test/bendloss(軸・対角・折れ線 × W × 矩形・σ)が Manning 解析値に一致、
  リスタート往復ビット一致、np=1,2,4 ULP=0。測線計測は ENC でエッジ流量
  方式(§24.2。観測者規律 §24.1 の最初の適用)。
- 利用者向け文書: ユーザーガイド(章と解説ページ。日英ミラー)+全パラメータ索引+
  注釈付き namelist 見本(List_samples 日英)+チュートリアル(wave・chichibu・bmi)+
  例題。日英の更新漏れ・索引と namelist の突合・設定例と宣言の一致は CI(i18n.yml)が
  検査する(§34.2・§35.1)。理論解のある挙動は test/<case>/Check_*.py で検定する
  (方針 13)。
- 移流項(developer.md §68・docs/advection_design.md): 既定は運動量保存形+
  MUSCL(f_advection_scheme = 3。2026-10-13 昇格)。斜め副格子モードは側方面の
  反対偶奇リンク結合で減衰(§68.36)、片側しか無い面はその 1 本が面と同程度の
  深さ(1/2〜2 倍)のときだけ使う(§68.37 の壁面扱いは壁沿いの行で発散 →
  §68.39 で水深の切り分けに改定、2026-10-18)。スカラー輸送もリンクごとの MUSCL が既定
  (§78)。設計の解説と論文化メモは advection_design.md(図は docs/figs/guide)。
  tutorials/wave の表・本文・図は 2026-10-18 に、chichibu は §68.42 の修正後の 2026-11-01 に現行スキームで再生成済み。
- 公開: v3.0.0(2026-10-25。Zenodo の版 DOI)。CSDMS モデルリポジトリへ提出済み
  (2026-10-29)。

## 未完了・検証待ち

- [00x](handoff/00x.md) 河道の平坦区間(窪地処理の跡)の解消: 標準のデータと教材の作り直し・新しい utils・新しい例題 (2026-11-17。利用者の提案。developer.md §111)
- [00z](handoff/00z.md) 既定の切り替え: `f_advection_donor` 3 → 4・`f_advection_bend` 1 → 2・`f_advection_lateral` 1 → 2・`f_dry_head_cap` 3 → 4(2026-11-21 に切り替えた。developer.md §114)の残り
- [00y](handoff/00y.md) 移流項の設計のやり直し: 深くて遅い隣のセルの扱い(2026-11-18〜19。developer.md §111.14・§111.15・§112・§113。4 つの値は 2026-11-21 に既定になった = §114)の残り
- [00aa](handoff/00aa.md) 非静水圧 + MUSCL(`f_nonhydrostatic = 1`・`f_advection_scheme = 3`)で、壁ぎわの行に短い波が育つ(2026-11-20 発見。developer.md §113.9 (6)。未調査。4 つの値・既定の切り替えとは別の件 = 利用者の決定)
- [00ab](handoff/00ab.md) 波浪場(`f_wf_current = 1`)の準定常の反復が、逆流の上で発散する(2026-11-20 発見。developer.md §113.9 (8)。未調査。今の既定でも起きる)
- [00ac](handoff/00ac.md) 開発記録の分割の残り(2026-11-22。developer.md §116)
- [00ad](handoff/00ad.md) 結果のディレクトリ(dir_result)の長いパスで、プローブ・測線・集計のファイル名が 80 字で切れる(2026-11-23 発見。未修正)
- [00ai](handoff/00ai.md) 田んぼダムの評価機能 fn_paddy(2026-11-24 合意。docs/paddy_plan.md、developer.md §127)の残り
- [00w](handoff/00w.md) 移流項: 屈曲直後の辺の風上値(f_advection_bend)、濡れた谷壁の辺による側方面の減速と合流の損失(f_advection_lateral)、…
- [00v](handoff/00v.md) 秩父の河道マスクを標高の落水線に載せ直した(2026-11-13。利用者の指摘と決定「河道マスクは、全ての解像度で 落水線ベースで。ただし、元のファイルは保存しておく」。developer.md §109)の残り
- [00s](handoff/00s.md) 流木の集積(構造物での捕捉・集積と流れへの作用。2026-11-12 合意・第 1 段と第 2 段を実装。 developer.md §50.7・§50.8、docs/woodjam_plan.md)の残り
- [00u](handoff/00u.md) 濡れた河岸に接する河道の 2 つの性質(2026-11-12 に例題 bridge_wood_jam の準備で切り分けた。developer.md §50.9。…
- [00t](handoff/00t.md) ENC の家屋の抗力項の次元の誤り(2026-11-12 調査・修正。developer.md §107)の残り
- [00q](handoff/00q.md) examples/source_area(2026-11-10 作成。2026-11-11 に出口を移し、同日に基本の側方の透水係数を 36000 mm/h に変えた。山地流域の流出寄与域の発達と縮小)の残り
- [00p](handoff/00p.md) 浅水方程式の入門ページと `f_govequation = 1` の呼称(2026-11-11。developer.md §105)の残り
- [00o](handoff/00o.md) examples の監査(2026-11-08。chichibu を除く README のある 31 例題)の残り
- [00n](handoff/00n.md) 運動量保存形移流の風上供給元 f_advection_donor(developer.md §102。2026-11-09 に既定を 0 から 3 に変更。2026-11-07 に 3 を追加して 1・2 を廃止、同日 3 に側方面の乾湿判定の連続化を追加。…
- [00m](handoff/00m.md) 拡散型プロセスの 4 近傍の異方性(developer.md §96、landslide_tsunami_plan.md §11.1。2026-11-05 合意)の残り
- [00l](handoff/00l.md) 急勾配の摩擦と水平流速・斜面方向の流速の扱い(2026-11-04 に解説 docs/steep_slope_design.md を作成し、2026-11-05 にユーザーガイド users_guide/steep_slope.md へ移した。…
- [00f](handoff/00f.md) BMI チュートリアル tutorials/bmi(2026-10-24 新設)の残り
- [00g](handoff/00g.md) examples の英語ラベル図(2026-10-25。tutorials/test と同じ方式)
- [00r](handoff/00r.md) 貯留関数法の区画流出 fn_sfm(2026-11-11。developer.md §106)の残り
- [00h](handoff/00h.md) 鉛直不飽和浸透(VZ)流出モデル fn_vz(2026-10-26。docs/vz_plan.md、§87)の残り
- [00c](handoff/00c.md) 方針 13(説明責任。policy.md。2026-10-24 制定)の既存部分への遡及
- [00d](handoff/00d.md) 河口デルタ形成の試行(2026-10-20〜21。docs/delta_plan.md)の残り
- [00e](handoff/00e.md) 波浪による沿岸漂砂 fn_wave(2026-10-22。docs/wave_plan.md、§84.15)の残り
- [00](handoff/00.md) 移流項の改良(developer.md §68。設計の正本 docs/advection_design.md)の未追跡事項
- [0](handoff/0.md) 家屋破壊・瓦礫モデル(developer.md §63。2026-10-01 実装・文献照合・ 既定値まで完了)
- [0c](handoff/0c.md) コンパイラ・精度の確認(2026-10-30 に各項目から集約)
- [1d](handoff/1d.md) 河道関係の残課題(整理 2026-10-04)
- [1e](handoff/1e.md) 構造物族(&list_struct_*。§15・§22)の残検証
- [1g](handoff/1g.md) 潮位境界 m_tide(2026-08-08 実装。仕様は developer.md §23)の残検証
- [1h](handoff/1h.md) 計測(実座標指定 §36・フラックス測線 §24)の残項目
- [4](handoff/4.md) 降雨遮断モジュール(m_intercept)の残検証
- [1j](handoff/1j.md) 土石流・地滑りモデル(f_debris/f_release/f_slide。2026-08-09 実装。 developer.md §28、docs/debris_plan.md)の残作業
- [1k](handoff/1k.md) 流木モジュール(fn_driftwood。2026-08-21 実装。developer.md §50、 docs/driftwood_plan.md)の残作業
- [1i](handoff/1i.md) ダム・湖沼(&list_struct_dam。族の第四号。§22「ダム・湖沼への一般化」、 lake_plan.md)の残検証・第2弾
- [1r](handoff/1r.md) 土壌雨量指数 m_swi(fn_swi。2026-08-20 実装済み。developer.md §49。旧番号 1k)の残項目
- [1s](handoff/1s.md) 蒸発散(§27。2026-08-09 実装。旧番号 1k)の残項目
- [1l](handoff/1l.md) 水質(負荷流出)m_wq(§30。2026-08-09 実装)の残項目
- [1n2](handoff/1n2.md) 石灰岩の溶食 f_dissol(§86。2026-10-21 実装。docs/karst_plan.md)の残項目
- [1n](handoff/1n.md) 長期地形変動(§32。2026-08-10 実装)の残項目
- [1o](handoff/1o.md) 海岸堤防(仮想壁面の海岸応用。§17.1。2026-08-10 実装)
- [1p](handoff/1p.md) ParaView 可視化 utils/out2vtk(§43。2026-08-16 実装)の残項目
- [1q](handoff/1q.md) 氷河 m_glacier(§45。2026-08-16 実装)の残項目

## 公開準備(方針の正本は developer.md §34)

- [公開準備](handoff/publication.md)

## 中期の道標(着手順は実測次第)

- [中期の道標](handoff/roadmap.md)

## 完了した調査の記録(他の文書から参照されるため残す)

test/tracer の README(日英)と設定ファイル(param*.txt・reference/param.txt)のコメント、docs/advection_design.md §7、
developer.md §68.36・§68.40 が下の 00a を、developer.md §78 が 00b を参照している。どちらも作業は完了済み。

- [00a](handoff/00a.md) examples/levee_breach(解像堤防の破堤。2026-10-13 新設)で見つかった要確認事項
- [00b](handoff/00b.md) スカラー輸送(advect_scalar)の数値拡散の計測と MUSCL 化(2026-10-13 完了。 developer.md §78、test/tracer)
