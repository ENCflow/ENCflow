# bmi/ — CSDMS Basic Model Interface (BMI 2.0) アダプタ

[English README](README.en.md)

ENCflow を **Python や他モデルから操作するための標準インターフェース**
です。ENCflow 全体がひとつの BMI component となり、
initialize / update / get_value / set_value という共通の操作で、
計算を任意の時点で止めて状態を取り出したり、外部から強制を与えたり
できます。CSDMS 公式の適合性テスト(bmi-tester)に合格しています。

BMI はオプション機能です。通常のビルド(encflow / encflow_mpi)は
本ディレクトリに依存せず、従来どおり外部ライブラリなしで動きます。
BMI を使う場合も、必要な追加ソフトは Python 側の numpy だけです
(BMI 仕様ファイルは同梱しており、CMake 等のツールは不要です)。

## クイックスタート(Python から使う)

```sh
cd bmi && make        # libencflow_bmi.so を生成(初回は ../src もビルド)
```

```python
import sys; sys.path.insert(0, "path/to/ENCflow/bmi/python")
from encflow import ENCflow, VAR_DEPTH

with ENCflow("param.txt") as model:          # 通常のケースをそのまま使える
    while model.time < model.end_time:
        model.update_until(model.time + 600.0)   # 10 分ずつ進める
        h = model.get2d(VAR_DEPTH)               # 水深 (ny, nx) の numpy 配列
        print(model.time, h.max())
```

パラメータファイル・入力データ・結果出力はスタンドアロン実行と
まったく同じです(BMI は操作口が増えるだけで、dt_file のファイル出力や
Log.txt もこれまでどおり書かれます)。

計算しながら水深分布とハイドログラフを順次表示するサンプル:

```sh
cd test/chichibu
python3 ../../bmi/python/live_view.py param.txt --probe 479 36
python3 ../../bmi/python/live_view.py param.txt --save frames   # PNG 連番(画面なし環境)
```

表示間隔は `--interval` 秒で指定できます。省略時は param の dt_file を
読んで、ファイル出力と同じタイミングで表示します。

## 公開変数(get / set)

| CSDMS Standard Name | 内容 | 単位 | set(外部からの設定) |
| --- | --- | --- | --- |
| `surface_water__depth` | 水深 | m | 可(**置換**。加算ではない。流速は変更されない) |
| `land_surface__elevation` | 標高 | m | 地形変化系の機能(geomorph 等)が**無効のケースのみ**可。水深は保存され水位が追随。海セルには適用されない |
| `atmosphere_water__precipitation_leq-volume_flux` | 降水強度 | m/s | 降水を**パラメータで設定していないケースのみ**可。次に set するまで持続する強制 |

3変数とも get できます。set した値は次の update の冒頭で適用されます。
set の「〜のみ可」は、**同じ量の与え方は一つ**(ファイル強制と外部
供給を併用しない)という原則によるもので、条件を満たさない set は
エラー(BMI_FAILURE)になります。Python では
`model.set(名前, 配列)`(下記の 1 次元標準形か、(ny, nx) の 2 次元)。

**交換間隔の目安**: get/set は場のコピーなので、交換はモデルの
時間刻みごとではなく、**交換する量の時間スケール**で行ってください
(降雨なら分オーダー)。細かすぎる交換は無駄なだけですが、粗すぎる
交換は結合誤差になります。

## 配列と格子の規約

- 配列は BMI 仕様どおり flatten した 1 次元で、**要素 0 = 南西隅、
  行は南→北**(格子の origin = 左下隅・spacing 正と整合)。
  Landlab の RasterModelGrid ノード配列とは無変換で 1:1 対応します。
- Python の `get2d()` は (ny, nx) を返します(行 0 = 南。matplotlib
  では `origin='lower'` で地図の向きどおりに表示されます)。
- 格子は grid 0 = uniform_rectilinear、shape は [ny, nx] 順。
  georef(hdr)を使うケースでは origin に実座標が入ります。
- 参照渡し(get_value_ptr)と非構造格子系の問い合わせは非対応です
  (BMI 仕様が認める BMI_FAILURE / NotImplementedError を返します)。

## MPI で使う

```sh
cd bmi && make clean && make MODE=mpi      # → 検証ドライバ test_encflow_bmi_mpi
mpirun -np 4 ./test_encflow_bmi_mpi param.txt
```

- update / update_until / get / set は**全ランクが揃って呼びます**。
  get で得られる全域配列と、set に与える配列は **rank 0 のみ有効**です
  (他ランクの配列は参照されません)。
- MPI が呼び出し側(mpi4py 等)で初期化済みの場合、ENCflow は
  MPI を横取り・終了しません。
- Python 用の共有ライブラリは現在は逐次版のみです。MPI で使えるのは
  Fortran からの呼び出し(上記ドライバが例)です。

## 検証ツール

| ツール | 内容 |
| --- | --- |
| `test_encflow_bmi [param] [set]` | ケースを BMI 経由で完走させる検証ドライバ(結果はスタンドアロン実行と一致する。`set` を付けると同値 set の無害性も検査) |
| `python/test_set_value.py` | set_value の等価性テスト(ファイル強制と外部供給で結果が一致すること等。test/wave で実行) |
| `python/check_bmi.sh` | CSDMS 公式適合性テスト bmi-tester の実行スクリプト |

適合性テストの再現手順:

```sh
pip install bmi-tester bmipy 'pytest<8' 'gimli.units==0.3.*'
cd test/wave
../../bmi/python/check_bmi.sh param.txt
```

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `vendor/bmi.f90` | BMI 2.0 仕様(CSDMS bmi-fortran 由来の同梱。MIT。`vendor/LICENSE`・NOTICE 参照) |
| `bmi_encflow.f90` | アダプタ本体(Fortran から BMI で使う場合はこれを use する) |
| `bmi_encflow_c.f90` | C 互換シンボル層(共有ライブラリの口) |
| `python/encflow.py` | Python ラッパー。`ENCflow` クラス(日常利用はこちら) |
| `python/encflow_bmi.py` | bmipy 準拠クラス `EncflowBmi`(bmi-tester・pymt 系ツール用) |
| `python/live_view.py` | ライブ表示サンプル |

## 制約・注意

- 1 プロセスにつき 1 モデルです(同時に2つの ENCflow を持てません。
  finalize 後の再 initialize は逐次では可能です)。
- 共有ライブラリ(.so)経由の実行は、コンパイル条件の違いにより
  スタンドアロン実行とビットまでは一致しないことがあります(物理量の
  出力は表示桁で一致します)。厳密なビット再現が必要な検証には
  静的な `test_encflow_bmi` を使ってください。

## 開発者向け

設計の経緯・全体計画は [docs/bmi_plan.md](../docs/bmi_plan.md)、
決定事項と検証記録の正本は
[docs/developer.md](../docs/developer.md) の §53〜§59 にあります。
