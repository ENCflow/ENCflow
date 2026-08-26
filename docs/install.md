# インストールガイド

ENCflow のインストールは「Fortran コンパイラを用意して `make install`」
だけです。外部ライブラリは一切不要で、管理者権限(sudo)も要りません。
生成物はリポジトリ内の `bin/` に置かれるだけなので、消したくなったら
ディレクトリごと削除すれば元通りです。

- Windows の方・Unix がはじめての方 → [Windows での使い方](windows.md)
- まず動かしたい → [1. 5分で動かす](#1-5分で動かす)
- チュートリアルの図化に → [2. 可視化ツールの準備](#2-可視化ツールの準備gnuplotparaview)
- 複数コアで速く → 何もしなくても並列です([3.3](#33-openmp-並列は最初から有効))
- クラスタ・スパコンで → [4. MPI ハイブリッド版](#4-mpi-ハイブリッド版のビルド)
- gfortran 以外で → [5. コンパイラの切り替え](#5-コンパイラの切り替え)
- エラーが出た → [7. トラブルシューティング](#7-トラブルシューティング)

## 1. 5分で動かす

> **Unix / Linux がはじめての方・Windows の方は、まず
> [Windows での使い方](windows.md) へ。** WSL(Windows 標準の
> Linux 環境)の導入から、ターミナルの基本、ファイルのやりとり
> まで、迷わない順路で案内しています。本章は、ターミナル(WSL の
> Ubuntu を含む)が使える状態からの手順です。

必要なのは git と gfortran だけです。

**Ubuntu / Debian / WSL**:

```bash
sudo apt install -y git gfortran make
```

**macOS**(Homebrew):

```bash
brew install gcc    # gfortran は gcc に同梱されています
```

続いて共通です。`git clone` は、GitHub で公開されているリポジトリ
(ソースコード・例題・文書を含むプロジェクト一式)を手元の PC に
クローン(コピー)するコマンドです:

```bash
git clone https://github.com/ENCflow/ENCflow.git   # リポジトリ一式を手元にコピー
cd ENCflow/src                                     # ソースコードのディレクトリへ移動
make install                                       # ビルド → ../bin/encflow ができます
```

動作確認(最初の例題を実行して検証済みの結果と自動比較します):

```bash
cd ../test/wave    # 最初の例題のディレクトリへ移動
./Run.sh           # 実行して検証済みの結果と自動比較
```

最後に `=== regression test PASS ===` と表示されれば、あなたの環境の
ENCflow は開発環境と同じ答えを出しています。これでインストールは
完了です。次は[チュートリアル](../tutorials/wave/README.md)へ
(チュートリアルは結果の図化に gnuplot を使うので、先に
[2章](#2-可視化ツールの準備gnuplotparaview)で入れておくとスムーズです)。

## 2. 可視化ツールの準備(gnuplot・ParaView)

ENCflow 本体は可視化ツールに依存しません(結果は行列テキストや
GeoTIFF なので、GIS・Python・Excel など何でも読めます)。ただし
チュートリアルと同梱のプロットスクリプト(`Plot_*.plt`)は
**gnuplot**(5.2 以降)を使うので、チュートリアルを進める場合は
インストールしておいてください。

**以下からお使いの環境に合ったコマンドを1つだけ選んで**実行して
ください(複数行をまとめてコピペするとエラーになります)。

Ubuntu / Debian(WSL を含む):

```bash
sudo apt install -y gnuplot
```

macOS(Homebrew):

```bash
brew install gnuplot
```

Fedora / RHEL 系:

```bash
sudo dnf install -y gnuplot
```

`gnuplot --version` でインストールとバージョンを確認できます。

3D 可視化・アニメーション(チュートリアル chichibu の Step 7)には
**ParaView** を使います。[公式サイト](https://www.paraview.org/download/)
のバイナリ(Windows / macOS / Linux)をインストールするのが確実です。
パッケージマネージャでも入ります(こちらも環境に合った1つだけ):

Ubuntu / Debian:

```bash
sudo apt install -y paraview
```

macOS(Homebrew):

```bash
brew install --cask paraview
```

WSL で計算している場合は、ParaView は **Windows 側にインストール**し、
結果ファイルをエクスプローラのパス `\\wsl$\...`(または
`/mnt/c/...` に置いた結果)から開くのが手軽です(WSLg が有効なら
WSL 内の ParaView も動きます)。日本語版 Windows ではバックスラッシュ
`\` は円記号 `¥` として表示・入力されます(同じ文字です。
[Windows での使い方](windows.md))。

## 3. インストールの仕組み

### 3.1 どこに何ができるか

- `src/` で `make install` すると、実行ファイル **`encflow`** が
  ビルドされ、リポジトリ直下の **`bin/`** にコピーされます。
  システムディレクトリには何も書き込みません。
- 各例題ディレクトリ(`test/wave` など)で `make` すると、`bin/` の
  実行ファイルへのシンボリックリンクが張られます(テストの
  Run スクリプトは必要なら自動で張ります)。実行は常に
  `./encflow パラメータファイル` の形です。
- リポジトリ直下で `make install` すると、本体に加えて `utils/` の
  前処理・後処理ユーティリティ群もまとめてビルドされます
  (最初は不要です)。

### 3.2 ビルド設定は make.inc 1枚

コンパイラ・最適化・並列モードなどのビルド設定は、リポジトリ直下の
**`make.inc`** に集約されています(コメントの付け外しで切り替える
方式)。既定は「gfortran・最適化あり・逐次(OpenMP)版」で、
そのまま使い始められます。`make.inc` を編集すると次回の make で
全体が自動的に作り直されるので、手動の `make clean` は原則不要です
(例外は [7章](#7-トラブルシューティング))。

### 3.3 OpenMP 並列は最初から有効

`encflow` は既定で OpenMP スレッド並列が有効で、何も設定しなくても
マシンの全コアを使います。スレッド数を制御したいときだけ環境変数を
設定してください:

```bash
export OMP_NUM_THREADS=4    # 4スレッドに制限する例
```

### 3.4 自分の計算はどこで実行してもよい

自分の計算を始めるのに、追加のインストール作業はありません。
**計算を実行したいディレクトリに `bin/` の `encflow`(MPI 版は
`encflow_mpi`)へのシンボリックリンクを張る(またはコピーする)だけ**
です。リポジトリの外でもかまいません。

```bash
mkdir ~/mycase && cd ~/mycase
ln -s ~/ENCflow/bin/encflow .     # リンクを張る(推奨)
./encflow param.txt
```

- 入出力はすべて実行したディレクトリが基準です(結果は `result/` に
  できます)。PATH を通したりシステムにインストールしたりする必要は
  ありません。例題ディレクトリの `make` も、このリンク張りを自動化
  しているだけです。
- **リンク(推奨)**: 再ビルド(`make install`)すると自動的に新しい
  実行ファイルが使われます。
- **コピー**: 計算に使った実行ファイルをその時点の版で固定したいとき
  (長期プロジェクトでの再現性の凍結)にはコピーが向きます。
- 大規模な格子の計算では、シェルのスタック上限を先に外しておくことを
  勧めます(`ulimit -s unlimited`。既定上限のままだと無言の
  Segmentation fault で止まることがあります —
  [7章](#7-トラブルシューティング))。

パラメータファイルの書き方は[チュートリアル](../tutorials/wave/README.md)
と[ユーザーガイド](users_guide.md)へ。

## 4. MPI ハイブリッド版のビルド

ワークステーションやスパコンでノードをまたいで計算する場合は、
MPI 版 **`encflow_mpi`** をビルドします。MPI ライブラリ(OpenMPI か
MPICH)が必要です:

```bash
sudo apt install -y openmpi-bin libopenmpi-dev    # Ubuntu の例
```

ビルドと実行:

```bash
cd ENCflow/src
make MODE=mpi install       # → ../bin/encflow_mpi
cd ../test/wave
./Run_MPI.sh 2              # 2ランクで実行して検証結果と自動比較
```

手動で実行する場合は `mpirun -np ランク数 ./encflow_mpi param.txt`。
ノード内は OpenMP スレッド、ノード間は MPI という**ハイブリッド並列**
なので、ランク数×スレッド数=総コア数が基本です。

**Open MPI の落とし穴 — スレッドが1コアに押し込められる**:
Open MPI の mpirun は既定で各ランクを特定のコアに固定(bind)します。
そのまま実行すると、**各ランクの OpenMP スレッド全部が1つのコアに
乗り**、エラーは出ないのに並列が効きません(症状: ランクあたりの
CPU 使用率が 100% 前後に張り付き、スレッド数を増やしても速く
ならない)。`--bind-to none` でバインドを解除してください:

```bash
export OMP_NUM_THREADS=6
mpirun -np 4 --bind-to none ./encflow_mpi param.txt
```

テストスクリプト(Run_MPI.sh)には設定済みです。性能を詰める場合は
バインド解除の代わりに `--map-by l3cache:pe=$OMP_NUM_THREADS
--bind-to core` のような明示配置も有効です(NUMA 環境で有利)。
なお MPICH の mpiexec は既定ではバインドしないため、この問題は
起きません。ジョブスクリプトの流儀はお使いのシステムの資料に
従ってください。

補足:

- `bin/` には `encflow` と `encflow_mpi` が**共存できます**。逐次版と
  MPI 版を行き来しても、ビルドし直すのは切り替えた側だけです
  (中間ファイルの混在はビルドシステムが自動検出して作り直します)。
- ENCflow は**ランク数をいくつにしても結果がビット単位で一致**する
  よう設計されています。`./Run_MPI.sh 4` でも同じ PASS が出ます。
- 恒久的に MPI 版を既定にするなら `make.inc` の `MODE = serial` を
  `MODE = mpi` に書き換えてもかまいません。
- Ubuntu 24.04 の apt 版 MPICH には、同梱 mpiexec でも全プロセスが
  ランク0になる既知の不具合があります(Debian Bug #1066735)。
  Ubuntu では OpenMPI を使うのが無難です。誤った起動は ENCflow 側でも
  検出して停止します([7章](#7-トラブルシューティング))。

## 5. コンパイラの切り替え

`make.inc` のコンパイラブロックのコメントを切り替えるだけです。
以下で動作確認しています:

| コンパイラ | make.inc の FC | 備考 |
|---|---|---|
| GNU gfortran | `gfortran` | 既定。無償 |
| Intel oneAPI | `ifx` | 無償配布あり |
| NVIDIA HPC SDK | `nvfortran` | 無償配布あり |
| AMD AOCC | `flang` | 無償配布あり |
| LLVM Flang | `flang-22` | 無償 |
| NEC SDK | `nfort` | SX-Aurora TSUBASA(ベクトル機)向け |

各ブロックには推奨最適化フラグとデバッグ用フラグが用意済みです。
**serial モードのままコンパイラ本体を切り替えたときだけ**、切り替え後に
`src/` で `make clean` を実行してください(それ以外の切り替え —
最適化フラグ・MODE・精度 — は自動検出されます)。

## 6. 設定リファレンス(make.inc)

| 設定 | 既定 | 説明 |
|---|---|---|
| `MODE` | `serial` | `serial`(OpenMP 版 encflow)/ `mpi`(ハイブリッド版 encflow_mpi)。コマンドラインの `make MODE=mpi` でも上書き可 |
| `PREC` | `double` | 実数精度。`single` にするとメモリ半減(結果は double と一致しません) |
| `FC` / `FC_MPI` | gfortran / mpifort | コンパイラ本体と MPI ラッパー |
| `FFLAGS` | 最適化あり | コメント切替でデバッグビルド(実行時検査つき)に変更可 |

開発に参加する場合のビルドシステムの詳細(モード切替の安全装置、
LTO とアーカイバの対応関係など)は [developer.md](developer.md) の
§1〜§3 を参照してください。

## 7. トラブルシューティング

**`gfortran: command not found`**
コンパイラが未インストールです。[1章](#1-5分で動かす)のコマンドで
インストールしてください。

**`ERROR: ../../bin/encflow not found; run 'make MODE=serial install' in src first`**
実行ファイルが未ビルドです。メッセージに表示されるコマンドを
`src/` で実行してください(MPI 版なら `make MODE=mpi install`)。

**`ERROR: the src build does not match the current environment` / `may not have been installed`**
`src/` のビルド状態が実行しようとしているモードや環境と食い違って
います。表示される対処コマンド(`make MODE=... install`)をそのまま
実行すれば解消します。スパコンで module を切り替えた後にも出ることが
あります(ビルド時と同じ module 環境に揃えてください)。

**大きな計算が `Segmentation fault` と一言だけ出て止まる**
シェルのスタックサイズ上限が原因である可能性が高いです。Fortran
コンパイラは作業配列や式の一時配列をスタックに置くことがあり、
既定の上限(WSL や多くの Linux で 8192 KB)では大規模な格子の
読み込み・計算の途中で上限を超え、何のメッセージもなく停止します。
実行前に

```bash
ulimit -s unlimited
```

を実行すると解消します。毎回打つ代わりに、**`~/.bashrc` に
書いておくことを推奨**します(以後の新しいシェルから常に有効):

```bash
echo 'ulimit -s unlimited' >> ~/.bashrc
```

- macOS は unlimited を指定できないので `ulimit -s hard`(引き上げ
  られる上限まで拡大)を使ってください。
- OpenMP のスレッド並列で同じ症状が残る場合は、スレッド側の
  スタック上限 `export OMP_STACKSIZE=512m` も併せて設定して
  ください。
- スパコンのバッチ実行では `~/.bashrc` が読まれないことがあるため、
  ジョブスクリプト内に書いてください。

**MPI 版でスレッド数を増やしても速くならない(CPU 使用率が
ランクあたり 100% 前後に張り付く)**
Open MPI の既定バインドで全スレッドが1コアに押し込められています。
`mpirun --bind-to none` を付けてください
([4章](#4-mpi-ハイブリッド版のビルド))。

**MPI 実行が「ランク数不一致」で即座に停止する**
mpirun と MPI ライブラリの組み合わせが不整合で、全プロセスが独立に
起動しています(テストスクリプト経由では ENCflow が自動検出して
停止します)。ビルドに使った MPI と同じ実装の mpirun を使って
ください。Ubuntu 24.04 の apt 版 MPICH 自体の不具合の場合は
OpenMPI に切り替えてください([4章](#4-mpi-ハイブリッド版のビルド))。

**コンパイラを替えたら大量のエラーが出る**
serial モードでのコンパイラ本体切替だけは自動検出されません。
`src/` で `make clean` してから `make install` してください。

**回帰テストが PASS しない**
コンパイラやマシンが違っても、各テスト既定の許容誤差(表示最終桁
1つ分)内で PASS するはずです。FAIL する場合はビルド設定(特に
`PREC=single` になっていないか、`make.inc` の変更)を確認して
ください。解決しない場合は環境情報(OS・コンパイラとバージョン・
`make.inc` の変更点)を添えて Issue でお知らせください。

## アンインストール

リポジトリのディレクトリを削除するだけです。ENCflow はシステムに
何もインストールしません。
