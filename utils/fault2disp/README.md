# fault2disp — 断層パラメータ → 地盤変位のスナップショット表

[fn_bedmotion](../../docs/users_guide/bedmotion.md)(規定底面運動)の入力を
断層パラメータから作る前処理ユーティリティ(docs/bedmotion_plan.md §6)。
計算本体には依存しない(Fortran、外部ライブラリなし)。

```
make && make check          # ビルドと Okada (1985) Table 2 の検算
./fault2disp fault2disp.txt # 設定ファイルを読んで dir_out/ に出力
```

変位は Okada (1985) の半無限弾性体(Poisson 比 0.25)における矩形断層の
地表変位(式 (25)〜(30))。複数セグメントの重ね合わせ、セグメントごとの
破壊開始時刻と立ち上がり時間(線形 / 半正弦)、オプションで水平変位の
寄与 u_h·∇z(Tanioka & Satake 1996。fn_z を与えたとき)。

## 設定(&list_fault2disp)

| 項目 | 意味 |
|---|---|
| nx, ny, dx, dy | ENCflow の格子(セル数とセル寸法 m) |
| x_ll, y_ll | 左下隅セルの外縁座標 (m。既定 0)。x は東、y は北に増える。経緯度→投影座標の変換は利用者側 |
| dir_out | 出力先ディレクトリ(既定 bm) |
| prefix_list | 表に書くファイル名の前置き(既定 'bm/'。ENCflow の dir_data からの相対になるように) |
| nout | 出力時刻の分割数(スナップショットは nout + 1 枚。既定 20) |
| t_start, t_end | 出力時刻の範囲 (s)。負なら自動(破壊開始の最小 〜 破壊終了の最大) |
| fn_z | 地盤高ファイル(与えると u_h·∇z を加える) |
| f_window | 1: \|u_z\| > d_min の外接矩形(全セグメントの和集合)だけを書き、表に窓 `i1 j1 ni nj` を付ける(既定 0 = 全域。広域の計算向け) |
| d_min | 窓の閾値 (m。既定 1e-3) |
| nseg | セグメント数(≤ 50) |
| x_top(k), y_top(k) | 上端の中心 (m) |
| d_top(k) | 上端の深さ (m。≥ 0) |
| strike(k) | 走向(北から時計回り、度)。断層は走向の右側に下がる |
| dip(k) | 傾斜(度。0 < dip ≤ 90) |
| rake(k) | すべり角(度。断層面上で走向方向から反時計回り。90 = 逆断層、0 = 左横ずれ) |
| flength(k), fwidth(k) | 長さ(走向方向)・幅(傾斜方向) (m) |
| slip(k) | すべり量 (m) |
| t_r(k), t_rise(k) | 破壊開始時刻・立ち上がり時間 (s。0 = 瞬時) |
| f_rise(k) | 立ち上がり関数 1: 線形、2: 半正弦 (1 − cos)/2(既定) |

出力は dir_out/disp_NNNN.txt(累積変位。ENCflow のテキスト行列形式、行順は
北 → 南。f_window=1 なら窓の部分だけ)と dir_out/bmlist.txt(「時刻 ファイル名
[i1 j1 ni nj]」)。ENCflow の &list_bedmotion に `fn_bmlist = 'bm/bmlist.txt'`
と書く。

使用例は examples/tsunami_fault。
