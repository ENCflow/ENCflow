# チュートリアル 3: bmi — Python から ENCflow を操る

ENCflow を **Python のプログラムの中から**起動し、好きなところで止めて
水深を取り出し、雨を外から与える — その操作口が
**BMI(CSDMS Basic Model Interface)** です。モデルの種類を問わず共通の
数個の操作(initialize / update / get / set / finalize)でモデルを扱う
規格で、ENCflow 全体がひとつの BMI 部品になります。

このチュートリアルは、**Python に詳しくない人が「とりあえず試せる」**
ことを目標に、ごく短いスクリプトを 1 つずつ動かしながら進めます。
題材は chichibu チュートリアルと同じ秩父流域(200 m 格子、
200 mm/h × 30 分の雨)です。各ステップの計算は、4 コアの PC で
20〜30 秒ほどで終わります。

- **Step 0**: 準備 — ライブラリのビルドと Python 環境(uv ほか)
- **Step 1**: 起動して終了するだけ(initialize / finalize)
- **Step 2**: 時間を進める(update / update_until)
- **Step 3**: 状態を取り出す(get と配列の向き)
- **Step 4**: 取り出した水深を描く(Matplotlib で 1 枚)
- **Step 5**: 計算しながら描く(リアルタイム表示)
- **Step 6**: 外から与える(set: 雨)
- **Step 7**: パラメータを書き換える(set: 粗度係数)

[wave チュートリアル](../wave/README.md)を済ませていることを前提に
します(ENCflow の実行のしかたと画面表示の読み方)。
[chichibu チュートリアル](../chichibu/README.md)は先に済ませておくと
地形・雨・出口の設定が分かって読みやすくなりますが、必須ではありません
(入力データは chichibu のものを共有します)。以降の作業はすべて
このディレクトリ(`tutorials/bmi`)の中で行います。

> BMI の全体像(公開変数の一覧、ネスト系、MPI、適合性テスト)は
> [bmi/README.md](../../bmi/README.md) にあります。このチュートリアルは
> その入口です。

## Step 0: 準備

### ライブラリのビルド

BMI は ENCflow の**共有ライブラリ**(`libencflow_bmi.so`)を Python から
読み込んで使います。通常の `encflow` とは別に 1 度だけビルドします
(必要なら `src/` のビルドも自動で走ります。gfortran だけで済み、
追加のライブラリは要りません):

```bash
cd tutorials/bmi      # pwd で確認する癖を(wave チュートリアル参照)
make
```

`../../bmi/libencflow_bmi.so` ができれば準備完了です。Python 側の
ラッパー(`bmi/python/encflow.py`)がこの場所を自動で探します。

### Python 環境

スクリプトは **NumPy**(配列)と **Matplotlib**(描画。Step 4 以降)だけを
使います。Python のパッケージ管理にはいくつも流儀があるので、
**お使いの環境に合うものを 1 つ選んで**ください。迷ったら A です。

**A. uv(推奨。Python を入れていなくても使える)**

[uv](https://docs.astral.sh/uv/) は Python 本体と必要なパッケージを
自動でそろえてくれるツールです。1 行でインストールできます
(Linux・WSL・macOS):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

ターミナルを開き直して `uv --version` が表示されれば OK です。
あとは、各スクリプトを `uv run` で実行するだけです:

```bash
uv run step1_hello.py
```

初回は Python 本体と NumPy・Matplotlib のダウンロード(100 MB 程度)が
走ります。2 回目からは一瞬で起動します。スクリプトの先頭にある

```python
# /// script
# dependencies = ["numpy"]
# ///
```

というコメントは、uv が読む「このスクリプトに必要なパッケージ」の宣言
(PEP 723)です。uv を使わない場合は単なるコメントなので、消す必要は
ありません。

**B. venv + pip(標準の Python を使う)**

Python 3.9 以上が入っていれば、仮想環境を作ってパッケージを入れます:

```bash
python3 -m venv .venv                 # このディレクトリに仮想環境 .venv を作る
source .venv/bin/activate             # 有効化(以後、プロンプトに (.venv) が付く)
pip install -r requirements.txt       # numpy と matplotlib を入れる
python3 step1_hello.py
```

Ubuntu / WSL で `venv` が無いと言われたら `sudo apt install python3-venv`
を先に実行してください。別のターミナルで続きをするときは
`source .venv/bin/activate` を再度実行します。

**C. conda / mamba**

```bash
conda create -n encflow python numpy matplotlib
conda activate encflow
python3 step1_hello.py
```

**D. OS のパッケージ(Ubuntu / Debian / WSL)**

```bash
sudo apt install -y python3-numpy python3-matplotlib
python3 step1_hello.py
```

以下の各ステップの実行例は、A(uv)の `uv run step1_hello.py` と、
B〜D の `python3 step1_hello.py` を「または」で毎回併記します。
自分の環境に合う方の 1 行だけを実行してください。違いは起動の
しかただけで、スクリプトの中身と結果は同じです(B の venv は
`source .venv/bin/activate`、C の conda は `conda activate encflow` を
済ませたターミナルで実行します)。

> **Windows の方へ**: ENCflow 本体と同様、WSL(Ubuntu)の中で作業する
> 前提です([Windows での使い方](../../docs/windows.md))。WSL では
> Step 5 のリアルタイム表示のウィンドウも(WSLg により)そのまま
> 表示されます。画面が出ない環境では `--save` で PNG を保存できます。

### 題材のパラメータファイル

`param.txt` は chichibu チュートリアルの Step 2(GeoTIFF 入力、河道
マスクと粗度)に、Step 6 の流域出口の排水口(`&list_bound_stage`)だけを
足したものです。入力データは `dir_data = "../chichibu/data_chichibu"` で
chichibu のものを共有しています。BMI を使っても**入力ファイル・結果の
出力・画面表示はスタンドアロン実行とまったく同じ**です。試しに
通常の方法でも実行できます(`make` で `encflow` へのリンクを張る
代わりに `ln -s ../../bin/encflow .` として `./encflow param.txt`)。

## Step 1: 起動して終了するだけ

最初のスクリプト `step1_hello.py` は、ENCflow を起動(初期化)し、
いくつかの情報を表示して、時間を進めずに終了します。全文は
次のとおりです(先頭の uv 用コメントと説明文を除く):

```python
import sys
from pathlib import Path

# Python ラッパー(bmi/python/encflow.py)の場所を Python に教える
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow

model = ENCflow("param.txt")        # initialize: 入力を読んで計算の準備をする
print("component :", model.name)
print("grid      :", model.grid_shape, "(ny, nx)")
print("time      :", model.time, "->", model.end_time, "s   dt =", model.time_step, "s")
model.finalize()                    # finalize: 後始末をして計算を閉じる
print("finished without advancing time")
```

```bash
uv run step1_hello.py               # A(uv)の場合
# または
python3 step1_hello.py              # B〜D(venv / conda / OS パッケージ)の場合
```

```
reading list_sysparam in param.txt
reading list_geoinfo in param.txt
 ...
main: number of valid cells: 17885
time, progress, S(m), Runge, ex_flux, Cn_max, h_max(m), V_max(m/s)
  0:00:00.00   0.0%    0.0001   0.0%      0    0.1097    1.3650    0.0000
component : ENCflow
grid      : (150, 280) (ny, nx)
time      : 0.0 -> 21600.0 s   dt = 6.0 s
main: program terminated normally
finished without advancing time
```

- `ENCflow("param.txt")` が BMI の **initialize** です。パラメータ
  ファイルを読み、地形を読み、初期状態を作ります。画面に出る
  `reading ...` 以下の行は、スタンドアロン実行とまったく同じ ENCflow
  自身のメッセージです(入口が違うだけで、動いているのは同じ
  プログラムです)。
- `model.name`・`model.grid_shape`・`model.time` などは BMI の
  **問い合わせ**です。格子の形は `(ny, nx)` = (行数, 列数) の順です。
  終了時刻 21600 s = 6 時間、時間刻み 6 s は `param.txt` の `tt_c`・`dt`
  の値です。
- `model.finalize()` が **finalize** です。最終出力を書いて計算を
  閉じます。`result/` には `H0000.*`(初期水深)と `Log.txt` だけが
  できています(時間を進めていないので)。
- 先頭の `sys.path.insert(...)` は、ラッパー `encflow.py` の置き場所
  (リポジトリの `bmi/python/`)を Python に教える 1 行です。ラッパーは
  共有ライブラリを読み込み、BMI の関数を Python の普通のメソッドに
  見せてくれます。

これで「Python から ENCflow を起動して終了する」ができました。
残りのステップは、この骨格に 1 つずつ操作を足していくだけです。

## Step 2: 時間を進める

`step2_time.py` は、BMI の **update**(1 ステップ進める)と
**update_until**(指定時刻まで進める)を使います:

```python
with ENCflow("param.txt") as model:         # with を抜けるとき finalize が自動で呼ばれる
    dt = model.time_step

    model.update()                          # 1 ステップ(dt 秒)だけ進める
    print(f"after update():       t = {model.time:g} s")

    model.update_until(600.0)               # 指定した時刻まで進める(dt の整数倍の時刻)
    print(f"after update_until(): t = {model.time:g} s")

    interval = 1800.0                       # ここから 30 分ごとに進めて進捗を表示する
    while model.time < model.end_time:
        target = min(model.time + interval, model.end_time)
        model.update_until(target)
        print(f"t = {model.time:7.0f} s  ({model.time / model.end_time:5.1%})")

print("finished")
```

```bash
uv run step2_time.py                # A(uv)の場合
# または
python3 step2_time.py               # B〜D(venv / conda / OS パッケージ)の場合
```

```
  0:00:00.00   0.0%    0.0001   0.0%      0    0.1097    1.3650    0.0000
after update():       t = 6 s
after update_until(): t = 600 s
  0:30:00.00   8.3%    0.0488  97.6%      8    0.3493    2.0851    9.0955
t =    2400 s  (11.1%)
  1:00:00.00  16.7%    0.0999   0.9%      0    0.6065    8.3520   16.2870
t =    4200 s  (19.4%)
  ...
  6:00:00.00 100.0%    0.0274   0.3%     82    0.3577    4.2847    7.5987
t =   21600 s  (100.0%)
main: program terminated normally
finished
```

- `update()` を 1 回呼ぶと時刻が `dt` = 6 s 進みます。
  `update_until(600.0)` は 600 s まで(= 残り 99 ステップ)進めます。
  **目標時刻は現在時刻から `dt` の整数倍先で、終了時刻以内**である
  必要があります(それ以外はエラー)。ループの `min(..., end_time)` は
  最後の区間で終了時刻を超えないための定型です。
- 計算の進行は **Python が完全に握っています**。ENCflow は呼ばれた分
  だけ進み、戻ってきます。その間にスタンドアロン実行と同じ画面表示
  (`dt_disp_c` ごとの行)と結果ファイルの出力(`dt_file_c` ごと)が
  従来どおり行われるので、Python の表示と ENCflow の表示が交互に
  現れます(ENCflow の表示を減らしたければ `param.txt` の `dt_disp_c`
  を大きくします)。
- `with ENCflow(...) as model:` と書くと、ブロックを抜けるときに
  `finalize()` が自動で呼ばれます(途中でエラーが起きても)。以降は
  この形を使います。

実行後の `result/` には、スタンドアロン実行と同じ `H0000`〜`H0012` と
`Log.txt` ができています。

## Step 3: 状態を取り出す

`step3_state.py` は、30 分ごとに計算を止めて**水深の配列を取り出し**ます
(BMI の **get**)。あわせて格子の情報と、取り出せる変数の一覧も表示します:

```python
with ENCflow("param.txt") as model:
    ny, nx = model.grid_shape                 # 格子の形(行数 ny, 列数 nx)
    dy, dx = model.grid_spacing               # セルの大きさ (m)
    print("grid:", nx, "x", ny, "cells of", dx, "m")
    print("variables you can get:")
    for name in model.output_var_names:
        print("   ", name)

    z = model.get2d(VAR_ELEVATION)            # 標高 (ny, nx)。行 0 = 南端
    print(f"elevation: {np.nanmin(z[z > 0]):.0f} .. {z.max():.0f} m")

    # ENCflow 内部のセル番地 (i, j)(1 始まり、j = 1 が北)→ 配列の添字
    ip, jp = 147, 104                         # chichibu チュートリアル Step 3 のプローブ 3(本川中流)
    row, col = ny - jp, ip - 1
    print(f"probe cell (i={ip}, j={jp}) -> h[{row}, {col}],  z = {z[row, col]:.1f} m")

    print(" time(s)   h_probe(m)   h_max(m)   wet cells")
    while model.time < model.end_time:
        model.update_until(min(model.time + 1800.0, model.end_time))
        h = model.get2d(VAR_DEPTH)            # 水深のコピー (ny, nx)
        wet = int(np.count_nonzero(h > 0.01))
        print(f"{model.time:8.0f}   {h[row, col]:9.3f}   {h.max():8.3f}   {wet:9d}")
```

```bash
uv run step3_state.py               # A(uv)の場合
# または
python3 step3_state.py              # B〜D(venv / conda / OS パッケージ)の場合
```

```
grid: 280 x 150 cells of 200.0 m
variables you can get:
    surface_water__depth
    land_surface__elevation
    atmosphere_water__precipitation_leq-volume_flux
    surface_water__elevation
    surface_water_flow__speed
    surface_water_flow__unit_width_volume_flow_rate
    surface_water__x_component_of_velocity
    surface_water__y_component_of_velocity
    surface_water__time_max_of_depth
    surface_water_flow__time_max_of_speed
    surface_water_flow__time_max_of_unit_width_volume_flow_rate
    land_surface_water_flow__manning_n_parameter
elevation: 92 .. 2449 m
probe cell (i=147, j=104) -> h[46, 146],  z = 400.7 m
 time(s)   h_probe(m)   h_max(m)   wet cells
    1800       0.517      1.618       15861
    3600       1.403      8.352        8255
    5400       4.759      8.141        3373
    7200       4.048      7.966        2387
    9000       3.561      8.361        1943
   10800       2.210      8.883        1696
   12600       1.843      8.927        1527
   14400       1.596      8.305        1412
   16200       1.396      6.685        1328
   18000       1.224      4.956        1245
   19800       1.108      4.287        1182
   21600       1.017      3.809        1137
```
(ENCflow 自身の 30 分ごとの表示行は省略)

雨の間(〜3600 s)は濡れたセルが 15,861 個(流域のほぼ全セル)に
達し、雨が止むと急速に減って、水は河道(約 1,100 セル)に集まります。
本川中流のセルでは、雨が止んで 30 分後(5400 s)に水深が 4.8 m の
ピークに達し、以後ゆっくり減っていきます。

- `model.get2d(名前)` が水深などの**場のコピー**を NumPy の 2 次元配列
  `(ny, nx)` で返します。変数の名前は CSDMS 標準名
  (`surface_water__depth` など)で、`encflow.py` が `VAR_DEPTH` のような
  定数で用意しています。一覧は `model.output_var_names` で得られ、
  この 12 個はどのケースでも取り出せます(`get` だけでなく `set` も
  できる変数は `model.input_var_names`)。
- **配列の向き**: BMI の規約で、行 0 が**南端**(配列の先頭が南西隅)
  です。ENCflow 内部のセル番地 `(i, j)`(1 始まり、`j = 1` が北。
  chichibu の `pbxy` と同じ流儀)は、配列では `h[ny - j, i - 1]` に
  対応します。ここでは本川中流のセル `(147, 104)` を取り出しています。
- 取り出した配列は**コピー**です。配列を書き換えても ENCflow には
  伝わりません(伝えるには Step 6・7 の `set` を使います)。
- 流域外のセル(マスク外)は標高も水深も 0 で返ります。

## Step 4: 取り出した水深を描く

配列が手に入れば、あとは普通の Python です。`step4_plot.py` は
雨が止んで 1 時間後(t = 2 h)まで進め、水深の分布を地形の上に重ねて
1 枚の図にします:

```python
T_PLOT = 2.0 * 3600.0                         # 描く時刻 (s): 雨が止んで 1 時間後

with ENCflow("param.txt") as model:
    ny, nx = model.grid_shape
    dy, dx = model.grid_spacing
    z = model.get2d(VAR_ELEVATION)
    model.update_until(T_PLOT)
    h = model.get2d(VAR_DEPTH)

# ここからは普通の Matplotlib。配列の行 0 が南なので origin="lower" で北が上になる
extent = (0.0, nx * dx / 1000.0, 0.0, ny * dy / 1000.0)      # km
land = np.where(z > 0, z, np.nan)                            # 流域外(標高 0)は描かない
wet = np.where(h >= 0.01, h, np.nan)                         # 1 cm 未満は「水なし」

fig, ax = plt.subplots(figsize=(9, 5))
ax.imshow(land, cmap="Greys", origin="lower", extent=extent)
im = ax.imshow(wet, cmap="Blues", origin="lower", extent=extent, vmin=0.0, vmax=3.0)
fig.colorbar(im, ax=ax, shrink=0.8, label="water depth h (m)")
...
fig.savefig("figs/step4_depth.png", dpi=110)
plt.show()                                   # 画面がない環境では何も起きずに終わる
```

```bash
uv run step4_plot.py                # A(uv)の場合
# または
python3 step4_plot.py               # B〜D(venv / conda / OS パッケージ)の場合
```

![Step 4: t = 2 h の水深分布](figs/step4_depth.png)

- `imshow(..., origin="lower")` で、行 0(南)を図の下に置きます。
  これだけで北が上の地図になります(`extent` は軸の目盛りを km に
  するためのものです)。
- 流域外や水のないセルは `np.nan` にして透明にしています。
  chichibu の gnuplot 図と違って結果ファイルを読み直していないことに
  注意してください — 計算中のメモリの配列をそのまま描いています。
- 計算は t = 2 h で止めたままです。`with` を抜けるときに `finalize()`
  が呼ばれ、ENCflow は 2 h 時点の状態で正常終了します(Log.txt もそこ
  まで)。「途中で止めて終わる」ことも BMI では普通の操作です。

## Step 5: 計算しながら描く

Step 3 の「進めて取り出す」ループの中で Step 4 の描画を更新すれば、
**計算の進行をリアルタイムに眺める**ことができます。`step5_live.py` の
骨格は次のとおりです(図の枠を作る部分は省略):

```python
INTERVAL = 300.0                              # 表示間隔 (s)。dt(6 s)の整数倍にする
IP, JP = 147, 104                             # 時系列を描くセル(内部番地 i, j)
...
def draw():
    """いまの水深を取り出して、2 つの図を更新する。"""
    h = model.get2d(VAR_DEPTH)
    im.set_data(np.where(h >= 0.01, h, np.nan))
    ax_map.set_title(f"t = {model.time / 3600:4.2f} h   max h = {h.max():.2f} m")
    times.append(model.time / 3600.0)
    series.append(h[row, col])
    line.set_data(times, series)
    fig.canvas.draw_idle()
    plt.pause(0.01)                           # 画面を更新する(ここで絵が動く)

draw()                                        # 初期状態
while model.time < model.end_time:            # 計算 → 描画 → 計算 → 描画 …
    model.update_until(min(model.time + INTERVAL, model.end_time))
    draw()
model.finalize()
```

```bash
uv run step5_live.py                 # 画面に順次表示(終了後、ウィンドウを閉じると終わる)
uv run step5_live.py --save frames   # 画面がない環境: PNG 連番を frames/ に保存
# または(B〜D の場合)
python3 step5_live.py
python3 step5_live.py --save frames
```

![Step 5: リアルタイム表示の 1 コマ(t = 1.67 h)](figs/step5_frame.png)

左が水深分布、右が本川中流のセル `(147, 104)` の水深の時系列です。
5 分ごと(`INTERVAL`)に計算が止まり、絵が更新されます。雨の 30 分の
間に斜面が一斉に濡れ、雨が止むと斜面の水が引いて河道に集まり、
時系列はピーク(約 1.5 h)を過ぎて減衰していく様子が見えます。

- `plt.ion()`(対話モード)と `plt.pause()` が「描いてもスクリプトを
  止めない」ための Matplotlib の定型です。`--save` を付けると画面を
  使わない描画(`Agg`)に切り替え、1 コマずつ PNG に保存します
  (`ffmpeg -i frames/frame_%04d.png step5.mp4` などで動画にできます)。
- 表示間隔を細かくすれば動きは滑らかになりますが、描画の時間が
  計算より長くなります。計算だけなら 6 時間が 15 秒程度、5 分ごとの
  表示では 73 コマで 1 分程度です。
- 同じ考え方を、より多くのオプション(表示間隔の自動設定、カラー
  スケール、任意のセル)つきで実装したのが
  [bmi/python/live_view.py](../../bmi/python/live_view.py) です。
  `uv run --with numpy,matplotlib ../../bmi/python/live_view.py param.txt --probe 147 104`
  (B〜D では `python3 ../../bmi/python/live_view.py param.txt --probe 147 104`)
  のように、このディレクトリのケースにそのまま使えます。

## Step 6: 外から与える(雨)

ここまでは ENCflow から「取り出す」だけでした。BMI の **set** を使うと、
**Python で作った場を ENCflow に与える**ことができます。ENCflow では
降水強度・水深・標高・粗度係数などが set できます(一覧は
[bmi/README.md](../../bmi/README.md))。`step6_rain.py` は、雨を
Python から与えます:

```python
MMH = 1.0e-3 / 3600.0                       # mm/h → m/s


PRVAL = [(0.0, 0.0), (1800.0, 200.0), (3600.0, 0.0)]   # param.txt の prval(時刻は秒に換算)


def rain_rate(t):
    """時刻 t (s) の雨量強度 (mm/h)。ENCflow と同じく prval の点を直線でつなぐ。"""
    ...                                     # (線形補間。全文はスクリプト参照)


def run(param, pattern=None):
    """pattern が None なら雨はパラメータファイル任せ。
    配列なら、各ステップの前に rain_rate(t) × pattern を set する。"""
    with ENCflow(param) as model:
        if pattern is None:
            try:
                model.set(VAR_PRECIP, np.zeros(model.grid_shape))
            except BmiError as e:
                print("   set(VAR_PRECIP) refused as expected:", e)
        dt = model.time_step
        while model.time < model.end_time:
            t_next = model.time + dt                        # これから進む 1 歩の終端時刻
            if pattern is not None and round(t_next) % 60 == 0:
                # ENCflow の &list_precip は 1 分ごと(dt_prupdate)に、ステップ終端の
                # 時刻で雨量強度を評価する。同じ時刻・同じ値を set すれば結果は一致する
                rate = rain_rate(t_next) * MMH              # (m/s)
                field = np.full(model.grid_shape, rate) * pattern   # (ny, nx) の分布にする
                model.set(VAR_PRECIP, field)                # 次の update の冒頭で適用され、次の set まで持続
            model.update()
        return model.get2d(VAR_DEPTH)


print("run A: rain from param.txt")
h_a = run("param.txt")

print("run B: rain supplied from Python (uniform)")
h_b = run("param_norain.txt", pattern=1.0)
print(f"   max |h_B - h_A| = {np.abs(h_b - h_a).max():.3e} m")

print("run C: rain only on the western half")
ny, nx = h_a.shape
west = np.zeros((ny, nx))
west[:, : nx // 2] = 1.0
h_c = run("param_norain.txt", pattern=west)
print(f"   max h: A = {h_a.max():.2f} m,  C = {h_c.max():.2f} m")
```

```bash
uv run step6_rain.py                # A(uv)の場合
# または
python3 step6_rain.py               # B〜D(venv / conda / OS パッケージ)の場合
```

```
run A: rain from param.txt
   set(VAR_PRECIP) refused as expected: BMI set_value(atmosphere_water__precipitation_leq-volume_flux) failed (status=1)
run B: rain supplied from Python (uniform)
   max |h_B - h_A| = 5.329e-15 m
run C: rain only on the western half
   max h: A = 3.81 m,  C = 3.20 m
```

3 つのランを順に実行しています(ENCflow は 1 プロセスに 1 モデルなので、
`finalize` してから次を `initialize` します):

- **ラン A** は Step 2 と同じ(雨は `param.txt` の `&list_precip`)。
  このケースで降水を `set` しようとすると **エラー(`BmiError`)** に
  なります。ENCflow は「同じ量の与え方は一つ」(ファイルの強制と
  外部供給を併用しない)という規則で、取り違えを防いでいます。
- **ラン B** は `param_norain.txt`(`param.txt` から `fn_precip` と
  `&list_precip` を外し、出力先を `result_norain` にしたもの)に、
  同じ雨を Python から与えます。`set` した値は**次の `update` の冒頭で
  適用され、次に `set` するまで持続**します。ENCflow は `prval` の点を
  直線でつないだ雨量強度(0 → 200 mm/h → 0 の三角形。総雨量 100 mm)を
  1 分ごと(`dt_prupdate` の既定)に、そのステップの終端時刻で評価する
  ので、Python 側も同じ時刻に同じ値を `set` しています。終了時の水深の
  差は **5 × 10⁻¹⁵ m = 倍精度の丸めの桁**で、ラン A と実質的に一致
  します — 雨の与え方を変えても同じ計算になることの確認です(最終桁の
  差は Python と Fortran の浮動小数点演算の順序の違いによるもの。
  時刻や値の評価がずれると、差は cm〜m の桁になります。`get` で得た場を
  そのまま `set` し直すとビット単位で一致することは
  [bmi/python/test_set_value.py](../../bmi/python/test_set_value.py) が
  検証しています)。
- **ラン C** は BMI ならではの例で、流域の西半分だけに降る雨を
  与えています。`pattern` は `(ny, nx)` の配列なので、レーダー雨量や
  気象モデルの出力を補間した分布を、時刻ごとに差し替えて与えることが
  できます。最大水深は半分近くになります。

単位に注意してください。BMI の降水強度は **m/s**(CSDMS 標準名
`atmosphere_water__precipitation_leq-volume_flux`)なので、mm/h から
`MMH` を掛けて換算しています。`set` に渡す配列は `get2d` と同じ向き
(行 0 = 南)の `(ny, nx)` です。

## Step 7: パラメータを書き換える(粗度係数)

`set` できるのは状態や強制だけではありません。Manning の粗度係数 n は
**パラメータ**ですが、ENCflow は BMI で上書きを受け付けます
(キャリブレーションや、流量・地形変化に応じて粗度を変える規則を
利用側で組むため)。`step7_roughness.py` は、入力値の粗度を
1 倍・1.5 倍・2 倍にして、本川中流のセルの最大水深とピーク時刻を
比べます:

```python
def run(factor):
    with ENCflow("param.txt") as model:
        ny, nx = model.grid_shape
        row, col = ny - JP, IP - 1
        rn = model.get2d(VAR_MANNING_N)       # 入力値(rn0, rn0_rw を適用済み)
        model.set(VAR_MANNING_N, rn * factor)  # 全セル一括で書き換え。次の update から効く
        peak, t_peak = 0.0, 0.0
        while model.time < model.end_time:
            model.update_until(min(model.time + 60.0, model.end_time))
            h = model.get2d(VAR_DEPTH)[row, col]
            if h > peak:
                peak, t_peak = h, model.time
        return peak, t_peak
```

```bash
uv run step7_roughness.py           # A(uv)の場合
# または
python3 step7_roughness.py          # B〜D(venv / conda / OS パッケージ)の場合
```

```
probe cell (i=147, j=104)
 n factor   peak h (m)   time of peak
    1.0        4.791         86 min
    1.5        5.019         95 min
    2.0        5.275        106 min
```

- `get2d(VAR_MANNING_N)` は、いま効いている粗度の場(`rn0` と河道の
  `rn0_rw` を当てはめた後)を返します。「get → 加工 → set」が
  パラメータを扱う基本形です。ここでは一括で倍率を掛けていますが、
  配列なので河道だけ・特定の区間だけを変えることもできます。
- 粗度を大きくすると流れが遅くなり、同じ流量を流すのに深い水深が
  必要になる一方、ピークは遅れてなまります。表の数値はその両方を
  示しています(粗度 2 倍で水深のピークは高く・遅く)。
- 粗度を半分にすると流れが速くなり、`dt` = 6 s ではクーラン条件を
  破ります(`Courant number exceeds 1.0` で ENCflow が停止し、Python
  には `BmiError` が返ります)。BMI を使っても安定条件は何も変わり
  ません。そうした実験では `param.txt` の `dt` を小さくしてください。
- 粗度の `set` は保存ファイルには含まれません。再開(restart)した
  ランでは、必要なら再び `set` します。

## おわりに

7 つのスクリプトで、BMI の操作はひととおり使いました:

| 操作 | Python | 学んだステップ |
|---|---|---|
| initialize / finalize | `ENCflow("param.txt")` / `model.finalize()`(`with` 文) | 1, 2 |
| update / update_until | `model.update()` / `model.update_until(t)` | 2 |
| 問い合わせ | `model.time`, `end_time`, `time_step`, `grid_shape`, `grid_spacing`, `output_var_names` | 1, 3 |
| get | `model.get2d(VAR_DEPTH)` など(行 0 = 南) | 3, 4, 5 |
| set | `model.set(VAR_PRECIP, field)`, `model.set(VAR_MANNING_N, rn)` | 6, 7 |

ここから先は:

- **公開変数の全一覧と set の受理条件**(水深・標高・地下貯留・積雪の
  置換、機能依存の変数)、**ネスト系(多段格子)**、**MPI** での使い方は
  [bmi/README.md](../../bmi/README.md)。
- **BMI の規格そのもの**(他のモデルでも同じ操作)は CSDMS の
  [BMI ドキュメント](https://bmi.csdms.io/)。ENCflow は公式の適合性
  テスト(bmi-tester)に合格しており、BMI 対応の他モデル・
  フレームワーク(pymt、Landlab など)と同じ流儀で結合できます。
- 自分のケースで使うには、`param.txt` を差し替えるだけです
  (スクリプト中の `"param.txt"` を自分のファイル名に。`set` で雨を
  与えるケースは `&list_precip` を持たないこと)。

## 開発者向けメモ

- スクリプトは日英で共有し(コメントは日本語)、`param*.txt` は
  コメントのみ英訳した `en/` ミラーがあります。図のラベルは英語で、
  日英で同じファイルを参照します。
- 図の再生成: `uv run step4_plot.py`(`figs/step4_depth.png`)、
  `uv run step5_live.py --save frames` の `frames/frame_0020.png` を
  `figs/step5_frame.png` にコピー。
- 本チュートリアルの作成時に、共有ライブラリ経由で GeoTIFF 入力の
  ケースが initialize できない実バグ(ユニットの未クローズ)を検出・
  修正した(developer.md §55.2)。
