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
| 3 | [bmi — Python から ENCflow を操る](../tutorials/bmi/README.md) | BMI(CSDMS Basic Model Interface)の入門。Python 環境の準備(uv ほか) / 起動と終了 / 時間を進める / 状態の取り出しと配列の向き / Matplotlib での描画とリアルタイム表示 / 雨の外部供給(set) / 粗度係数の上書き |

チュートリアル 3 は Python を使いますが、Python に詳しくなくても
試せるよう環境の準備から説明しています(計算本体は 1・2 と同じ
Fortran の ENCflow です)。以降のチュートリアル(河道の精緻化、長期計算と
再開など)は順次追加していきます。そのほかは [examples/](../examples/) の
設定サンプル集と [test/](../test/) の検証済み例題が参考になります。

## 学習の道筋

全員が全ての分野を理解する必要はありません。必須は次の 3 つだけで、
ここまでで原則(fn_\* による機能の有効化、パラメータファイルの書き方、
実行と出力の読み方)が身につきます。

1. [tutorials/wave](../tutorials/wave/README.md) Step 1〜3 — 最初の実行、パラメータファイル、時間刻み、境界条件
2. [tutorials/chichibu](../tutorials/chichibu/README.md) — 実地形データ、降雨、計測、水収支
3. [ユーザーガイド 第I部](users_guide.md) — 骨格、fn_\* の原則、パラメータファイルの読み方

wave の Step 1 に出てくるクーラン数(`Cn_max` 列)と時間刻み `dt` の
決め方に戸惑ったら、[クーラン数と時間刻みの決め方](users_guide/courant.md)
(流れの数値計算が初めての人向けの入門)を読んでください。

自分のケースを組むときは、[地理情報](users_guide/geoinfo.md)・
[初期条件](users_guide/initial.md)・[境界条件](users_guide/boundary.md)・
[降雨・気象](users_guide/forcing.md)の各章の「とりあえず動かしてみる
(最小入力)」の節から読んでください。

その先は、**興味のある分野の章だけ**読んでください。章ページは
「とりあえず(気軽に)動かすための説明」を優先して書いてあり、
「概要 → とりあえず動かしてみる → パターン別の推奨値 → 必要な節」の順に
読めば動かせます。さらに詳しく知りたい人は、その章の下にぶら下がる
**詳説ページ**(理論・式・既定値の根拠・詳細な設定)へ進んでください。

| 分野(章ページ) | 詳説ページ |
|---|---|
| [時刻の管理](users_guide/time.md) | [クーラン数と時間刻みの決め方](users_guide/courant.md)(入門)、[時間刻みの設計方針](users_guide/timestep_policy.md) |
| [浅水流計算](users_guide/swflow.md) | [ENC 格子と時間積分](users_guide/encgrid.md)、[移流項](users_guide/advection.md)、[拡散項](users_guide/diffusion.md)、[非静水圧補正](users_guide/nonhydrostatic.md) |
| [内部水理構造物](users_guide/structure.md)・[境界条件](users_guide/boundary.md)・[河道](users_guide/channel.md) | [構造物と境界の水理則](users_guide/hydraulics.md) |
| [地下水](users_guide/gwflow.md) | [地下水モデル](users_guide/gwflow_models.md) |
| [土砂・地形変化](users_guide/geomorph.md) | [土砂輸送と斜面・長期地形過程](users_guide/sediment.md)、[土石流・斜面崩壊・動く底層](users_guide/massflow.md) |
| [水質](users_guide/wq.md) | [水質モデル](users_guide/wq_models.md) |
| [降雨・気象](users_guide/forcing.md) | [降雨・気象のモデル](users_guide/forcing_models.md) |
| [河道](users_guide/channel.md) | [河道の解説](users_guide/channel_models.md) |
| [ネスティング](users_guide/nest.md) | [ネスティングの解説](users_guide/nest_models.md) |
| [規定底面運動](users_guide/bedmotion.md) | [規定底面運動の解説](users_guide/bedmotion_models.md) |
| [流木](users_guide/driftwood.md)・[家屋破壊・瓦礫](users_guide/bldgdebris.md) | [流木モデル](users_guide/driftwood_models.md)、[家屋破壊・瓦礫モデル](users_guide/bldgdebris_models.md) |

あなたが ENCflow を利用する理由は、**複数のプロセスを 1 つの計算の中で
連鎖させたい**からかもしれません(降雨 → 流出 → 土砂 → 河道、
津波 → 家屋破壊 → 瓦礫、噴火 → 溶岩原 → 二次的な洪水、など)。現象から必要な機能の組合せを引く
には[用途集](users_guide/usecases.md)を使い、関係する章を組み合わせて
ください。ネスティングや非静水圧補正のような専門的な機能は、必要になった
ときに読めば十分です。

[test/](../test/) と [examples/](../examples/) は初学者向けの教材では
ないので、章を読んだ後に必要に応じて見てください。test は各機能の検証の仕方
(解析解・保存則との比較)、examples は namelist の実例と、複数プロセスを
組み合わせた設定の見本です。

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
