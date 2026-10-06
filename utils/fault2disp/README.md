# fault2disp — 断層パラメータ → 地盤変位のスナップショット表

[fn_bedmotion](../../docs/users_guide/bedmotion.md)(規定底面運動)の入力を
断層パラメータから作る前処理ユーティリティ(docs/bedmotion_plan.md §6)。
地理参照(bil の hdr / GeoTIFF)を本体と同じ部品で読むため libencflow.a を
リンクする(utils/rerecord と同じ型。Fortran、外部ライブラリなし)。

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
| nx, ny, dx, dy | ENCflow の格子(セル数とセル寸法 m)。地理参照つきの fn_z(下記)があれば省略できる |
| x_ll, y_ll | 左下隅セルの外縁座標 (m。既定 0 = 相対座標)。x は東、y は北に増える。地理参照された格子ではその投影座標系の原点を入れる(fn_z から自動取得できる)と、x_top, y_top はその系の絶対座標になる |
| f_input_mode | fn_z の形式(1: テキスト = 既定、2: bil+hdr、4: GeoTIFF。ENCflow と同じ) |
| f_georef | 1(既定): fn_z が bil+hdr / GeoTIFF のとき、nx, ny, dx, dy, x_ll, y_ll をファイルの地理参照から取る(namelist に書いた値は一致検査)。ENCflow と同じ m_georef / m_geotiff で読むので原点の解釈が本体と揃う |
| f_jpr | 1: x_top/y_top と x_ll/y_ll を日本の平面直角座標系の順「X(北距) Y(東距)」で与える(内部で東・北に入れ替える。既定 0) |
| dir_out | 出力先ディレクトリ(既定 bm) |
| prefix_list | 表に書くファイル名の前置き(既定 'bm/'。ENCflow の dir_data からの相対になるように) |
| nout | 出力時刻の分割数(スナップショットは nout + 1 枚。既定 20) |
| t_start, t_end | 出力時刻の範囲 (s)。負なら自動(破壊開始の最小 〜 破壊終了の最大) |
| fn_z | 地盤高ファイル(与えると u_h·∇z を加える。f_georef=1 なら格子の地理参照の出所にもなる) |
| f_window | 1: \|u_z\| > d_min の外接矩形(全セグメントの和集合)だけを書き、表に窓 `i1 j1 ni nj` を付ける(既定 0 = 全域。広域の計算向け) |
| d_min | 窓の閾値 (m。既定 1e-3)。窓の外に切り捨てる変位は d_min 以下なので、水位への影響も最大 d_min 程度 |
| f_lonlat | 1: 断層位置を経緯度 lon_top(k), lat_top(k)(度)で与え、横メルカトル投影で格子座標に変換する(既定 0 = x_top, y_top を投影座標で) |
| lon_ll, lat_ll | 格子左下隅の経緯度(与えると x_ll, y_ll を同じ投影で求める) |
| proj_lon0, proj_lat0 | 投影原点(度)。UTM は帯の中央子午線と 0、日本の平面直角座標系は系の原点 |
| proj_k0 | 中央子午線の縮尺係数(UTM 0.9996 = 既定、平面直角座標系 0.9999) |
| proj_fe, proj_fn | 偽東距・偽北距 (m)。UTM 北半球 500000, 0(既定)、平面直角座標系 0, 0 |
| ell_a, ell_rf | 楕円体の長半径と逆扁平率(既定 GRS80。WGS84 は 1/f = 298.257223563) |
| f_strike_conv | 1(既定): 走向(真北基準)を子午線収差 γ で格子北基準に補正する(strike − γ) |

経緯度入力の投影は横メルカトル(Gauss–Krüger。Krüger の級数、n の 6 次)で、
UTM と日本の平面直角座標系(X = 北距、Y = 東距。ENCflow の x_ll = Y、
y_ll = X)はその特殊形。`-check` が UTM 54 帯と平面直角座標系 IX 系の
点で Snyder (1987) の級数と 1 mm で一致することを示す。他の投影
(ランベルト等)は利用者側で変換する。投影面上の長さの縮尺(k0〜1.0004)は
断層の長さ・幅に掛けない(0.04% 以下)。
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

使用例は examples/tsunami_fault(fault2disp.txt: 投影座標、fault2disp_ll.txt:
経緯度、fault2disp_bil.txt: bil の hdr から地理参照、fault2disp_jpr.txt: 平面
直角座標系の並び)。
