# test/evapdry — 土の乾き具合による蒸発散の抑制(evap_hglim)

[English](en/README.md)

[蒸発散](../../docs/users_guide/forcing.md#蒸発散list_evap)の `evap_hglim` を与えると、
地下水から引く蒸発散を、地下の貯留 hg が evap_hglim より少ないときに
hg/evap_hglim の割合へ減らします(Ks = min(1, hg/evap_hglim)。FAO-56 の水分ストレス
係数と同じ線形の低減。[解説](../../docs/users_guide/forcing_models.md) §3、
developer.md §27.2)。ステップの中では dhg/dt = −E·min(1, hg/evap_hglim) を厳密に
解くので、雨の後の hg は解析解(evap_hglim を上回る間は速さ E で線形、下回ると
時定数 evap_hglim/E の指数減衰)に丸めの範囲で一致するはずです。その検定です。

- **param.txt(回帰の reference と比較)**: 平らな閉領域(10 × 10 セル、dx = 10 m、
  地盤高一様)。バケツ型の浸透(浸透能 200 mm/h、容量 0.1 m)で 1 時間の一様降雨
  50 mm/h をすべてしみ込ませ、可能蒸発散 PET 一定 48 mm/day(2 mm/h)で地下の貯留
  から蒸発させる。地表の流れも地下の流れもないので、雨の後は蒸発散だけが hg を
  減らす。evap_hglim = 0.02 m(雨の後の 0.048 m より小さい = 線形 → 指数減衰)。
  雨には濃度 1 mg/L のトレーサを持たせる(水質の台帳から雨の総量を得る)。
- **param_b.txt**: evap_hglim = 0.1 m(雨の後の貯留より大きい = はじめから指数減衰。
  時定数 50 時間)。
- **param_c.txt**: evap_hglim を指定しない対照(抑制なし = 従来の「あるだけ引く」)。
  hg は速さ PET で線形に減り、25 時間ほどで尽きて 0 になる。

## 構成

| 項目 | param.txt | param_b.txt | param_c.txt |
|---|---|---|---|
| 地形 | 平らな閉領域(10 × 10 セル、dx = 10 m) | 同左 | 同左 |
| 水 | 雨 50 mm/h × 1 時間(1 mg/L) | 同左 | 同左 |
| 地下 | バケツ型(浸透能 200 mm/h、容量 0.1 m。側方流なし) | 同左 | 同左 |
| 蒸発散 | PET 一定 48 mm/day、evap_hglim = 0.02 m | PET 同左、evap_hglim = 0.1 m | PET 同左、evap_hglim なし |
| 時間 | dt = 10 s、30 時間 | 同左 | 同左 |

| ファイル | 内容 |
|---|---|
| `Run.sh` | param.txt の Log.txt・evap.csv を reference と比較(ULP = 0。Log の Runge 列は除外)→ `Check_evapdry.py` の検定 → param_b.txt・param_c.txt を実行して検定 |
| `Run_MPI.sh N` | N ランクで param.txt を実行し、逐次の reference と ULP = 0 で比較して検定 |
| `Check_evapdry.py decay\|evbal\|ledger` | 雨の後(1.5 時間以降)の地下の貯留(Log.txt の S_grnd)が解析解に一致(1.5 時間の値に対して 1e-9)/ 最終の総水量 + 蒸発散 = 雨の総量(相対 1e-6)/ 水質の台帳の閉合(蒸発では物質が残る) |

## 実行

```bash
make
./Run.sh
./Run_MPI.sh 4
```

## 所見

| 構成 | 1.5 時間の hg (m) | 30 時間の hg (m) | 解析解とのずれ(1.5 時間の値に対して) |
|---|---:|---:|---:|
| param.txt(evap_hglim 0.02 m) | 0.048097 | 0.004714 | 3e-13 |
| param_b.txt(evap_hglim 0.1 m) | 0.049697 | 0.028105 | 1e-13 |
| param_c.txt(抑制なし) | 0.047694 | 0 | 2e-13 |

- ずれは Log.txt の印字の桁(14 桁)の範囲です。ステップの中で厳密に解くので、
  時間刻みによらず解析解に一致します。
- 雨の間も蒸発散は働くので、1.5 時間の hg は雨の総量(0.0507 m)より少なく、
  構成ごとに違います(抑制の強い構成ほど多く残る)。検定は 1.5 時間の値から解析解を
  始めます。
- 抑制なし(param_c.txt)は従来の式のまま(抑制の分岐を通らない)です。
