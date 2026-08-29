# bmi/ — CSDMS Basic Model Interface (BMI 2.0) アダプタ

ENCflow 全体をひとつの BMI component として外部(Python・結合
フレームワーク等)から操作するための **optional アダプタ**。
`src/` の既定ビルド(encflow / encflow_mpi / libencflow.a)は本
ディレクトリに一切依存しない(developer.md §0 方針10 追記)。

- 全体像・設計の正本: **docs/bmi_plan.md**(段階計画は §6)
- ライフサイクル API(m_main)の設計記録: developer.md §53
- 現段階(段2): 逐次専用。出力変数(get_value)のみ。

## 構成

| ファイル | 役割 |
| --- | --- |
| `vendor/bmi.f90` | BMI 2.0 仕様(bmif_2_0 モジュール)。CSDMS bmi-fortran 由来の同梱(MIT。`vendor/LICENSE`・NOTICE 参照) |
| `bmi_encflow.f90` | アダプタ本体。`type(encflow_bmi)` が bmif_2_0 を実装し、m_main の公開手続きへ翻訳する |
| `bmi_encflow_c.f90` | bind(c) の C 相互運用層(Python 等から呼ぶための C 互換シンボル。iso_c_binding のみ・外部依存なし) |
| `test_bmi.f90` | 検証ドライバ。ケースを BMI 経由で完走させる(Log.txt が既存 reference とビット一致することを回帰テストに使う) |
| `python/encflow.py` | ctypes 最小ラッパー(サンプル)。`ENCflow` クラスと numpy での状態量取得 |
| `python/live_view.py` | 計算しながら水深分布とハイドログラフを順次表示するサンプル |

## ビルドと検証

```sh
cd bmi
make                # test_encflow_bmi と libencflow_bmi.so を生成
                    # (../src が未ビルドなら先にビルドされる)
cd ../test/wave
ln -sf ../../bmi/test_encflow_bmi .
./test_encflow_bmi param.txt        # BMI 経由でケースを完走
SKIPCOLS=4 ULP=0 ../Scripts/Compare_ref.sh Log.txt   # reference とビット一致
```

## Python から使う(逐次)

必要なのは Python3 + numpy(+ 表示するなら matplotlib)だけ。

```python
import sys; sys.path.insert(0, "path/to/ENCflow/bmi/python")
from encflow import ENCflow, VAR_DEPTH

with ENCflow("param.txt") as model:
    while model.time < model.end_time:
        model.update_until(model.time + 600.0)   # 10 分ずつ進める
        h = model.get2d(VAR_DEPTH)               # (ny, nx) numpy 配列
        print(model.time, h.max())
```

計算しながら分布を順次表示するサンプル(表示間隔は `--interval`。
省略時は param の dt_file を読んでファイル出力と同期):

```sh
cd test/chichibu
python3 ../../bmi/python/live_view.py param.txt --probe 479 36
python3 ../../bmi/python/live_view.py param.txt --save frames   # PNG 連番(ヘッドレス)
```

注意: 共有ライブラリ経由はコンパイルフラグ(-fPIC)の異なる別
バイナリになる(gfortran の LTO がリンク時に再コード生成する)。
物理量の出力は一致するが、比較除外列(適応 RK 発動率)がまれに
±0.1% 変わり得る(developer.md §55)。get/get2d の行順は標準形
(行0=南)。

## 公開変数

| CSDMS Standard Name | 内部 | 単位 | set の受理条件と意味論 |
| --- | --- | --- | --- |
| `surface_water__depth` | s%h | m | 常時受理。**状態の置換**(データ同化型。加算ではない。運動量は非更新) |
| `land_surface__elevation` | s%z | m | **z 更新プロセス(geomorph 等)無効時のみ**。地形の置換(h 保存・e 回復。海セル除外) |
| `atmosphere_water__precipitation_leq-volume_flux` | s%pre | m s-1 | **降水未設定(prtype=0)のみ**。持続強制(次の set まで有効) |

3変数とも get/set 可。set は次の update 冒頭で適用される(受理規則の
正本は developer.md §56(降水)・§57(z, h)。共通原則は「生産者は
変数ごとに一人」)。Python では `model.set(名前, arr)`(1 次元標準形か
(ny, nx) の 2 次元)。受け入れ試験は `bmi/python/test_set_value.py`
(test/wave で実行 — 降水はファイル強制と set_value 強制の Log 全行
一致、h・z は「同値 set の不変性」= 無介入ランと Log 全行一致)。

**交換間隔の指針**: get/set は場のコピーであり、毎ステップの交換は
コピー方式のモデル連携一般に共通のオーバーヘッドを生む。結合間隔は
**交換する量の時間スケール**で選ぶこと(降雨なら分オーダー。数値 dt
より細かい交換に物理的な意味はない)。粗すぎる間隔は結合の時間分割
誤差になる。詳細は docs/bmi_plan.md §8.0。

配列は BMI 仕様どおり flatten した 1 次元。行順は **BMI 標準形に
正規化**して受け渡す: 要素 0 = 南西隅、行は南→北(origin = 左下・
spacing 正と整合。内部の j=1=北 とは逆順で、変換は BMI 層が行う。
bmi_plan.md §7-5 案A)。Landlab の RasterModelGrid ノード配列とは
無変換で 1:1 対応する。格子は grid 0 = uniform_rectilinear、
shape は [ny, nx] 順。
