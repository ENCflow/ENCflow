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
| `test_bmi.f90` | 検証ドライバ。ケースを BMI 経由で完走させる(Log.txt が既存 reference とビット一致することを回帰テストに使う) |

## ビルドと検証

```sh
cd bmi
make                # ../src が未ビルドなら先にビルドされる
cd ../test/wave
ln -sf ../../bmi/test_encflow_bmi .
./test_encflow_bmi param.txt        # BMI 経由でケースを完走
SKIPCOLS=4 ULP=0 ../Scripts/Compare_ref.sh Log.txt   # reference とビット一致
```

## 公開変数(段2)

| CSDMS Standard Name | 内部 | 単位 |
| --- | --- | --- |
| `surface_water__depth` | s%h | m |
| `land_surface__elevation` | s%z | m |
| `atmosphere_water__precipitation_leq-volume_flux` | s%pre | m s-1 |

配列は BMI 仕様どおり flatten した 1 次元(index = i + (j-1)*nx)。
格子は grid 0 = uniform_rectilinear、shape は [ny, nx] 順。
