# test/dbslope — 混合体流動の抵抗則を斜面に沿って評価する(f_gravity_correction = 2)等流の検定

[English](en/README.md)

急勾配の重力補正 `f_gravity_correction = 2`(`&list_enc`。既定)が、土石流モデル(`f_debris`)の混合体流動の
抵抗則を斜面に沿う速さ $`|\mathbf V_s|`$ と地盤に直角な厚さ $`h\cos\theta`$ で評価すること(developer.md §101、
docs/users_guide/steep_slope.md §2.3)の検証ケースです。抵抗の応力 $`\tau`$ を斜面に沿って与えると、水平の
流速の減速度は $`\tau/(\rho_m h\cos\theta\,|\mathbf V_s|)\,\mathbf V`$ になり、水平の形(1)に対して

- 降伏(クーロン・Voellmy の $`\mu`$・一定の停止応力)は $`1/(r\cos\theta)`$ 倍(最急勾配の向きの流れでは 1)、
- 速度の 2 乗の抵抗(Voellmy の乱流項・江頭の層流則・高橋・中川の石礫型)は $`r/\cos^3\theta`$ 倍
  (最急勾配の向きでは $`1/\cos^4\theta`$)、高橋・中川の掃流状集合流動は $`r/\cos^2\theta`$ 倍

になります($`r = |\mathbf V_s|/|\mathbf V|`$)。たとえば 2 の Voellmy の等流は、斜面に沿う式
$`V_s^2 = \xi\,h\cos\theta\,(\sin\theta - \mu\cos\theta)`$(RAMMS と同じ)になります。4 つの抵抗則の等流の深さを、
2 と 1 のそれぞれの解析解と比べます。reference 比較ではなく `Check_dbslope.py` の自己検定で合否を決めます
(test/slopefric・test/volcano と同じ型)。

## 構成

| 項目 | 値 |
|---|---|
| 地形 | 勾配 tan30° の一様な斜面の帯 150 m × 8 m(Δx = 1 m)。x 軸の向きに下る。周囲は壁(`make_init.py` が `d_slope/z.txt` を書く) |
| 格子 | 4 近傍(`p_diagratio = 0`。斜めの辺の「勾配の低下 × 降伏」の非線形を除く。test/volcano と同じ。developer.md §28.8) |
| 流れ | 西辺の 8 セルから水 4 m³/s と土砂を一定に流入(土砂の交換なし `f_dbed = 0` で、濃度は流入の値のまま)。dt = 0.02 s、90 s |
| ケース | 抵抗則 4 つ × `f_gravity_correction` 1・2 の 8 ケース(名前は `stony_g2` = 石礫型・2) |

| 抵抗則 | 設定 | 濃度 C | 単位幅の混合体流量 q |
|---|---|---:|---:|
| voellmy | `f_dbres = 4`、μ = 0.1、ξ = 200 m/s² | 0.444 | 0.9 m²/s |
| egashira | `f_dbres = 2`、φ = 35°、d = 0.05 m、e = 0.85 | 0.444 | 0.9 m²/s |
| stony | `f_dbres = 3`、d = 0.05 m(C > 0.4 C* の石礫型) | 0.444 | 0.9 m²/s |
| collective | `f_dbres = 3`、d = 0.05 m(C ≤ 0.4 C* の掃流状集合流動) | 0.200 | 0.625 m²/s |

| ファイル | 内容 |
|---|---|
| `make_init.py` | 地形 `d_slope/z.txt` と設定 `p_<case>.txt` を書く(引数 `list` でケース名を出す)。定数は Check と対 |
| `Check_dbslope.py` | 最後の出力(H・Hs)から下の (1)・(2) を判定する(引数 `table` で値の表も出す) |

判定:

1. 帯の中ほど(x = 60〜100 m)の混合体の鉛直の深さ $`h_t = h + h_s`$ の平均が、解析解と 0.5 % 以内、窓の変動係数が
   0.02 未満、濃度が流入の値と 1e-3 以内。解析解は、水平の流速・鉛直の深さで書いた釣り合い
   $`g_e\tan\theta = a_y + f_v\,R(|\mathbf V|, h_t)`$($`g_e = g\cos^2\theta`$、$`a_y`$ は降伏、$`R`$ は速度の 2 乗の
   抵抗、$`f_v`$ は 2 で $`1/\cos^4\theta`$(掃流状は $`1/\cos^3\theta`$)、1 で 1)と $`q = h_t|\mathbf V|`$ の閉じた解
   (Voellmy は $`h_t^3`$、江頭・石礫型は $`h_t^5`$、掃流状は $`h_t^4`$ について解ける)
2. 検出力: 2 と 1 の解析解の比が 1 から 5 % 以上離れる(2 つの形を区別できる)

水深は小数 4 桁(0.1 mm)で印字されるので、濃度は丸めで 1e-4 程度ずれます。

## 実行

```bash
make            # 実行ファイルへのリンク
./Run.sh        # 8 ケースを実行して判定(1 スレッドで約 30 秒)
./Run_MPI.sh 2  # MPI(先に Run.sh を実行しておくと、逐次の save と state.dat をバイト比較する)
```

## 結果(2026-11-06)

| ケース | 抵抗則 | 値 | $`\langle h_t\rangle`$ (m) | 解析解 (m) | 誤差 | 変動係数 | 濃度 |
|---|---|---:|---:|---:|---:|---:|---:|
| voellmy_g1 | Voellmy | 1 | 0.2039 | 0.2040 | −0.01 % | 0.0002 | 0.4444 |
| voellmy_g2 | Voellmy | 2 | 0.2471 | 0.2471 | +0.00 % | 0.0001 | 0.4444 |
| egashira_g1 | 江頭 | 1 | 0.2185 | 0.2185 | −0.00 % | 0.0003 | 0.4444 |
| egashira_g2 | 江頭 | 2 | 0.2452 | 0.2452 | +0.03 % | 0.0033 | 0.4444 |
| stony_g1 | 石礫型 | 1 | 0.2858 | 0.2858 | −0.01 % | 0.0026 | 0.4444 |
| stony_g2 | 石礫型 | 2 | 0.3206 | 0.3206 | −0.01 % | 0.0002 | 0.4445 |
| collective_g1 | 掃流状集合流動 | 1 | 0.3285 | 0.3285 | −0.00 % | 0.0000 | 0.2000 |
| collective_g2 | 掃流状集合流動 | 2 | 0.3659 | 0.3659 | −0.01 % | 0.0000 | 0.2001 |

2 と 1 の解析解の比(同じ流量の深さ): Voellmy 1.211($`\cos^{-4/3}30°`$)、江頭・石礫型 1.122($`\cos^{-4/5}30°`$)、
掃流状集合流動 1.114($`\cos^{-3/4}30°`$)。

## 所見

- 4 つの抵抗則とも、2 は斜面に沿う式の、1 は水平の式の等流に印字の桁で合います。30° の斜面では、2 の等流は 1 より
  11〜21 % 深く、流速はその分だけ遅くなります(同じ深さで比べると、Voellmy の斜面に沿う速さは $`\cos^2\theta`$ = 0.75 倍)。
- 最急勾配の向きの流れでは降伏の倍率が 1 なので、降伏だけで決まる止まり方(test/dbonset の剛体の滑り)は 2 と
  1 で同じです。

## できないこと・限界

- 格子の軸に沿う一様な斜面の、最急勾配の向きの等流だけの検定です。斜面を斜めに流れるときの $`r`$ の効き方
  (降伏が最大 $`1/\cos\theta`$ 倍)は、マニングの摩擦の倍率と同じ式の組み立てで、test/slopefric の向きの検定に
  頼っています。
- 8 近傍では、斜めの辺の「勾配の低下 × 降伏」の非線形で、降伏のある抵抗則の等流が 1 次元の解析解からずれます
  (test/volcano の注意、developer.md §28.8)。
- 一定の停止応力(`f_dbres = 5`)は、降伏の倍率が最急勾配の向きで 1、マニングの項は §93 の倍率なので、この検定には
  含めていません。土砂の交換(侵食・堆積)と曲率項は扱いません。
- 慣性のない底層(`f_bedslide`)の Voellmy は水平の形のままです(developer.md §101 の「適用しないもの」)。

## 関連文書

- docs/users_guide/steep_slope.md §2.3・§6.2、docs/users_guide/massflow.md(抵抗則)、developer.md §93・§101
- [test/slopefric](../slopefric/)(水の流れの摩擦と流砂のせん断)、[test/volcano](../volcano/)(Voellmy の等流と
  τ_y のランアウト)、[test/dbonset](../dbonset/)(斜面の剛体の滑り)

## 参考文献

- Voellmy, A. (1955): Über die Zerstörungskraft von Lawinen. *Schweizerische Bauzeitung*, 73, 159–165, 212–217,
  246–249, 280–285.
- Christen, M., Kowalski, J. and Bartelt, P. (2010): RAMMS: Numerical simulation of dense snow avalanches in
  three-dimensional terrain. *Cold Reg. Sci. Technol.*, 63, 1–14.
- 江頭進治 (1993): 土石流の停止・堆積のメカニズム(2). 新砂防, 46(2).(江頭ら(1989)の構成則と降伏応力の原式)
- 高橋保・中川一 (1991): 石礫型土石流の予測法. 新砂防, 44(3), 12–19.
