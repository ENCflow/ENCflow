# ENCflow チュートリアル

ENCflow の使い方を、実行できる例題つきで段階的に学ぶための道案内です。
各チュートリアルは [tutorials/](../tutorials/) 以下のディレクトリで
完結しており、その中の README を読みながら実際にコマンドを打って
進めます。事前準備は [インストールガイド](install.md) を参照して
ください(計算に必要なのは Fortran コンパイラ1つだけです。結果の
可視化には gnuplot を、chichibu の 3D 可視化には ParaView を使い
ます — インストールは同ガイドの 2 章)。

## チュートリアル一覧

| # | ケース | 学べること |
|---|---|---|
| 1 | [wave — 静水に広がる波](../tutorials/wave/README.md) | 最初の実行と出力の読み方 / パラメータファイルの構造 / 時間刻みと精度・適応的ルンゲクッタ法 / 境界条件 / ENC 格子の壁の性質 |
| 2 | [chichibu — 実地形の流域に降る雨](../tutorials/chichibu/README.md) | 実地形データ(DEM・マスク)と窪地除去 / GeoTIFF 入出力 / 河道マスクと粗度 / 計測(プローブ・測線) / 数値設定の調整 / 降雨遮断・地下浸透と水収支 / 流域出口の境界条件 / 実地形データに由来する流量振動の理解 / ParaView での 3D 可視化(アニメーション) |

以降のチュートリアル(河道の精緻化、長期計算と再開など)は順次
追加していきます。そのほかは [examples/](../examples/) の
設定サンプル集と [test/](../test/) の検証済み例題が参考になります。

## 学習の道筋(段階別)

簡単な例から順に進む道筋です。各段階の教材は、前の段階の内容を前提に
しています。ユーザーガイドの章ページは「概要 → とりあえず動かしてみる
(最小入力)→ パターン別の推奨値 → 詳細 → 検証・例題」の順に書いて
あるので、**先頭の 2 節だけ読めば動かせます**。解説ページ(「…の解説」)は
式と根拠をまとめた上級者向けで、後回しで構いません。

| 段階 | 読む・動かすもの | 学べること |
|---|---|---|
| 入門 1 | [tutorials/wave](../tutorials/wave/README.md) Step 1〜3 | 最初の実行、パラメータファイルの構造、時間刻み、境界条件 |
| 入門 2 | [ユーザーガイド 第I部](users_guide.md)(骨格・fn_\* の原則・パラメータファイルの読み方) | 機能の有効化の仕組み、1 枚のファイルに何を書くか |
| 入門 3 | [test/wave](../test/wave/)、[test/dambreak](../test/dambreak/)、[examples/benchmark](../examples/benchmark/) | 解析解との比較の読み方(段波・降雨流出)。`./Run.sh` と `Check_*.py` の使い方 |
| 中級 1 | [tutorials/chichibu](../tutorials/chichibu/README.md) | 実地形データ、河道マスク、計測、降雨遮断・浸透、水収支 |
| 中級 2 | [地理情報](users_guide/geoinfo.md)・[初期条件](users_guide/initial.md)・[境界条件](users_guide/boundary.md)・[降雨・気象](users_guide/forcing.md)の「とりあえず動かしてみる」 | 自分のケースを組み立てる最小の入力 |
| 中級 3 | [test/tide](../test/tide/)、[test/pump](../test/pump/)、[test/culvert](../test/culvert/)、[examples/sewer_hybrid](../examples/sewer_hybrid/)、[examples/qanat](../examples/qanat/) | 潮位・構造物・地下水・管路の最小例(各 1 機能) |
| 上級 1 | [ENC 格子と時間積分の解説](users_guide/encgrid.md) → [移流項](users_guide/advection.md) → [拡散項](users_guide/diffusion.md) → [非静水圧補正](users_guide/nonhydrostatic.md) | 浅水計算の式・スキーム・既定値の根拠 |
| 上級 2 | [examples/nest_reflect](../examples/nest_reflect/)、[examples/landslide_tsunami](../examples/landslide_tsunami/)、[examples/tsunami_fault](../examples/tsunami_fault/)、[examples/tsunami_coast](../examples/tsunami_coast/) | ネスティング、非静水圧、動く底層・規定底面運動の組合せ |
| 上級 3 | [examples/tsunami_town](../examples/tsunami_town/)、[examples/timberyard](../examples/timberyard/)、[examples/ashfall_lahar](../examples/ashfall_lahar/)、[examples/badland](../examples/badland/) | 複数プロセスの連鎖(家屋破壊・流木・土石流・地形発達)と 2 ケース比較の組み方 |
| 開発 | [developer.md](developer.md) §0(基本方針)→ [architecture.md](architecture.md) | 設計思想と、新しいプロセスを足すときの契約 |

## ディレクトリの役割

紛らわしい3つのディレクトリは、次のように使い分けられています。

- **tutorials/** — 学習用。解説文書(README)を読みながら手を
  動かすチュートリアル。
- **examples/** — 設定ファイルのサンプル集。機能ごとの namelist の
  書き方の見本(`examples/List_samples/`)と実データの例題。
- **test/** — 開発用の回帰テスト。基準値(reference)との自動比較が
  ついており、学習向けの解説はありません。

## 次に読むもの

- [ユーザーガイド](users_guide.md) — 設定と実行のリファレンス
  (第I部 全体像、第II部 横断機能、第III部 機能別リファレンスと解説ページ)
- [他モデルとの比較](comparison.md) — ENCflow の位置付け
- [developer.md](developer.md) — 設計思想と開発規約(開発に参加する方へ)
