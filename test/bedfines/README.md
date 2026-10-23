# bedfines — 河床の細粒分の帳簿(f_bedfines)の検定

[English](en/README.md)

developer.md §84.10、docs/meander_plan.md §3.6c。掃流砂(fluv_d50)と浮遊砂
(susp_d50)を重ねる計算で、浮遊砂の巻き上げを河床に在庫する細粒分 sf
(0 ≤ sf ≤ sd。出力 Sf)に限り、細粒分は掃流砂・側岸侵食・崩落と一緒に動く
(等移動度)、という 2 成分の帳簿を検定する。

## 構成

| 構成 | 設定 | 検定 |
|---|---|---|
| off | 浮遊砂のみ、f_bedfines = 0(test/suspend と同じ閉領域ダムブレイク) | all との比較基準。Sf 出力がない |
| all | 細粒 100 %(fines_frac0 = 1、L_a = 0.01 m) | state.dat が off とビット一致、sf = sd |
| mix | 掃流砂+浮遊砂、細粒 50 %(L_a = 0.05 m) | 0 ≤ sf ≤ sd、固体総量 Σhs + (1−λ)Σ(z − z0) と細粒分 Σhs + (1−λ)Σ(sf − sf0) が 1e-9 未満、細粒分が浮遊砂に出ている(Σ(sf − sf0) < 0) |
| coarse | 掃流砂+浮遊砂、粗粒のみ(fines_frac0 = 0) | hs・sf が厳密に 0 のまま河床は動く |
| feed | 粗粒だけの直線水路(幅 10 セル、勾配 0.002)に区間流入から細粒分を濃度 0.002 で給砂(浮遊砂のみ) | z − z0 ≥ 0(河床は削られない)、sf = z − z0(在庫 = 堆積)、堆積がある |
| bfeed | 細粒 50 % の河床(L_a = 10 m で流出の細粒分 ff = 0.5)、掃流砂だけが動く(巻き上げなし)、上流端まで可動にして容量給砂 | 入口列の \|z − z0\| と \|sf − sf0\| < 1e-9(給砂は流入セルと同じ組成)、0 ≤ sf ≤ sd、在庫が掃流砂に同伴して動く |
| rt1 → rt2 | mix を 4 s で分割 | state.dat と geomorph_fines.dat が mix とビット一致 |

## 実行

```
make
./Run.sh            # 逐次。Check_bedfines.py + cmp
./Run_MPI.sh 2      # MPI(np=2)。逐次の save とのビット一致も確認
```

入力 zinit.txt / hinit.txt / sdinit.txt / sdfeed.txt は make_init.py が生成する(追跡外)。
