# test/gvchange — 空隙率変更手続き m_state_set_gv の単体検定

セル空隙率 gv(瓦礫・建物などが水柱を占めることで減る「水の入れる割合」。
developer.md §63.1 の A1・A2)を変更する手続き `m_state_set_gv` の単体
検定です。計算本体(時間ループ)は回さず、`libencflow.a` の手続きを
3 × 3 の小さな帯状態に直接適用します([test/gtif](../gtif/) と同じ様式)。
図はありません。

## 構成

| 検定 | 内容 |
|---|---|
| (1) 体積保存 | 柱状量 × gv が、全ての台帳(h, hs, hrs, hd, cq, hss)で変更前後に機械精度(相対 1e-14)で一致する |
| (2) 導出量 | lm = gv + (1 − gv)·cm、e = z + h、af が gv の因子だけ比例して更新される |
| (3) 無変更 | 変更しないセルは不変、gv_new == gv_old の呼び出しは no-op(ビット不変) |
| (4) 任意台帳 | 未確保の任意台帳(wd, hbd 等)があっても落ちない(allocated 判定) |

| ファイル | 内容 |
|---|---|
| `test_setgv.f90` | 検定プログラム(セル (2,2) を gv 0.95 に、(1,3) を 1.0 に変更) |
| `Makefile` | `../../make.inc` のコンパイラ設定で `libencflow.a` をリンク |
| `Run.sh` | ビルドして実行。最終行が `== gvchange 検定: PASS ==` |

## 実行

```bash
./Run.sh      # make → ./test_setgv(1 秒)
```

MODE=mpi でビルドされていても collective を呼ばないので、mpirun なしの
シングルトンで動きます。

## 所見

```
(3) no-op          : PASS
(1) volume balance : 0 failure(s) so far (0 = PASS)
(2) derived fields : 0 failure(s) so far (0 = PASS)
== gvchange 検定: PASS ==
```

- gv の変更は「柱状量を保存して水深を読み替える」操作で、
  h_new = h_old × gv_old / gv_new です。全台帳に同じ因子を掛けるので
  水・土砂・流木・水質・塩水のいずれも体積が保存されます。
- 公開インターフェース(`m_state_set_gv(p, s, i, j, gv_new)`)を変える
  ときは、この検定と utils/ の追随をトップレベルの `make` で確認して
  ください(§10)。
- 空隙率を使う物理モジュール: 建物瓦礫 [test/bldgdebris](../bldgdebris/)
  (§63)。

## 関連文書

- developer.md §63.1(空隙率の状態化: s%gv / s%lm、A1・A2)
