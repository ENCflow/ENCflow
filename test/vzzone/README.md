# test/vzzone — VZ の区画・共有柱・出口の検定(fn_vz)

[English](en/README.md)

鉛直不飽和浸透(VZ)流出([ユーザーガイドの章](../../docs/users_guide/vz.md)、
developer.md §87)の区画・柱の共有・出口への受け渡し・雨の扱い・再開・基底流の検定です。
`Check_vzzone.py` で解析的に決まる量を確かめ、`param.txt` の結果は reference の
Log.txt とも比較します(ULP=0。CSV を比較に入れない理由は
[test/vzcol](../vzcol/README.md) と同じ)。

## 構成

7 × 8 セル(Δx = Δy = 10 m)。列 1〜5 が VZ セルで、行 1〜3 が区画 1、
行 4〜5 が区画 2、行 6〜8 が区画 3。列 6 は領域外、列 7 は行 1・3・5 だけが
領域内の孤立した受水セル O_a・O_b・O_c(周囲を領域外で囲み、地表水が動かない)。

| 区画 | 参照する柱 | 出口 |
|---|---|---|
| 1 | 柱 1(Ks = 100 mm/h、σ = 1.5) | O_a へ 0.6、O_b へ 0.4 |
| 2 | 柱 2(Ks = 50 mm/h、σ = 1.0) | O_a へ 1.0(区画 1 と同じ受水セル) |
| 3 | 柱 1(区画 1 と共有) | 系外流出 |

O_c は雨だけを受ける対照です。小杉パラメータは検定用の例示値です。降雨は
test/vzcol と同じ(0〜60 分 1 mm/h、61〜180 分 50 mm/h、以後 0)を全セル一様に
与えます。dt = 5 s、dt_vz = 60 s、12 h。

| 構成 | ファイル | 内容 |
|---|---|---|
| 基本 | `param.txt` | 上記 |
| 柱の複製 | `param_dup.txt` | 区画 3 が柱 1 の複製(柱 3)を参照 |
| 雨の分布 | `param_avg.txt` | 雨を分布(`prmap.txt`、mm/day × 時系列倍率)で与え、f_vz_rain = 1(柱内の面積平均) |
| 厳密モードの停止 | `param_strictfail.txt` | 同じ雨で f_vz_rain = 0 → 柱内の雨量の不一致で停止するはず |
| 保存と再開 | `param_save.txt` / `param_restart.txt` | 6 h で保存(同期時刻)し、再開して 12 h まで |
| 基底流 | `param_bflow.txt`(区画 3 の系列は `data_vzzone/base3.txt`) | 区画 1 に namelist の基底流(30.5 分まで 0、90 分で 2 → 4 mm/h の段差、300.25 分に 1 mm/h、以後保持)、区画 3 にファイルの基底流(10 分まで 0.5、360 分に 1.5 mm/h、以後保持)。Run.sh が tt・dir_result・f_state_save・f_state_restore を sed で書き換えて保存 → 再開と、時刻が減る系列での停止も確かめる |

## 検定(Check_vzzone.py)

- **受水セルの水深**(プローブ): R を地上雨量の積算、V1・V2 を区画 1・2 の
  地表への移送量として O_a = R + (0.6 V1 + V2)/A、O_b = R + 0.4 V1/A、O_c = R。
- **地表水の総量**(Log の S_surf × セル数 × A)= 受水セル 3 つへの雨 + V1 + V2
  (同じ受水セルに 2 区画から渡る量が一度だけ加わる)。
- **全体の収支**: Log の S_total の変化 = 雨 − 系外流出(区画 3)/全面積。
- **区画の収支残差**が非線形残差の予算内。
- **柱の共有と複製**: 区画 3 が柱 1 を共有しても複製(柱 3)を参照しても、区画の
  応答と Log がビット一致(共有柱は計算量を減らすだけで結果を変えない)。
- **雨の分布と面積平均**: 各区画の入力 = 区画面積 × 柱内の平均雨量(柱 1 は
  区画 1 と 3 のセルの平均)、S_total の収支。同じ雨で厳密モードは停止。
- **再開**: 6 h で保存 → 再開した結果(vz_zone.csv・vz_column.csv・Log)が
  連続計算の後半とビット一致。
- **基底流**(`param.txt` の結果と比べる): 累積の基底流 vbase = 区分線形の時系列
  (範囲外は端の値)の厳密な積分(Python の分数で計算)× 区画面積、VZ 側の値
  (vin・vstore・vdrain・vcorr・residual と vz_column.csv)は基底流なしと文字列で一致、
  出口の量(vsurface・vexternal)= 排水 + 基底流。受水セルの水深・地表水の総量・
  S_total の収支も基本と同じ検定で確かめる(区画 1 の基底流は系への入力、区画 3 の
  基底流は系外から系外へ)。保存 → 再開は連続計算とビット一致、時刻が減る系列は停止。

## 実行

```bash
make
./Run.sh          # 逐次 + reference 比較 + 全検定
./Run_MPI.sh 4    # MPI(np ≤ 4)。Log は逐次 reference と ULP=0、CSV は np = 1 と一致、面積平均・停止・再開も MPI で
```

## 検証記録(2026-10-26。gfortran 13.3 / Open MPI 4.1、Ubuntu 24.04)

受水セルの水深はプローブの表示 5 桁で配分どおり、地表水の総量は 3e-14(相対)、
S_total の収支は 2e-11 m、区画の残差は予算の 3e-4 倍。柱の共有と複製は区画の
応答と Log が完全一致。面積平均の入力は 3e-14、厳密モードは
「rainfall differs within column」で停止(MPI でも全ランクで停止)。保存 → 再開は
連続計算と完全一致(逐次・MPI)。`-Og -fcheck=all` で逐次と np = 2・4 の全出力
ファイル(プローブ含む)が一致、release で np = 1・2・4 が逐次 reference に
ULP=0。

reference の確定(2026-10-29。利用者の指示): 暫定で置いていた reference を確定した。
更新は `ULP=0 RTOL=0 FILES="Log.txt vz_zone.csv vz_column.csv" ./Run.sh -u`(逐次
release)。Log.txt と param.txt は従来の reference とビット一致で、CSV だけが最終桁
(相対 1e-15 以下。収支残差の列は丸め雑音の 1e-13 m³ 規模)で変わった。理由は
test/vzcol と同じ(作業ホストの CPU の違いによる `-march=native` の差。コードの変更では
ない)。新しい reference に対して MPI np = 2・4 が CSV を含めて一致。

基底流(2026-10-27): 累積の基底流は解析積分と相対 2e-14、出口の量 = 排水 + 基底流は
相対 2e-14、VZ 側の値と vz_column.csv は基底流なしと一致、S_total の収支は 2e-11 m。
保存 → 再開は連続計算と完全一致、時刻が減る系列は「baseflow times of zone 1 must not
decrease」で停止(MPI でも全ランク)。`-Og -fcheck=all` で実行時検査に掛からず、
release で np = 1・2・4 が合格し、np = 1 と 4 の全出力ファイル(プローブ含む)が一致。
基底流を与えない既存の構成は Log.txt・vz_zone.csv・vz_column.csv とも reference と
バイト一致。
