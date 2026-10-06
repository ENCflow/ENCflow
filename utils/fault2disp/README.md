# fault2disp — 断層パラメータから地盤変位の時刻歴を作る

[fn_bedmotion](../../docs/users_guide/bedmotion.md)(規定底面運動)の入力
(スナップショット表 + 累積変位ラスタ)を、断層パラメータから作る前処理
ユーティリティです。Okada (1985) の半無限弾性体(Poisson 比 0.25)における
矩形断層の地表変位を計算し、複数セグメントの重ね合わせ、セグメントごとの
破壊開始時刻と立ち上がり関数、水平変位の寄与(Tanioka & Satake 1996)、
経緯度入力、地理参照つきファイルからの格子の自動取得に対応します。
設計は docs/bedmotion_plan.md §6、実装記録は developer.md §70。

```
cd utils/fault2disp
make                        # ビルド(本体の libencflow.a をリンク。src が未ビルドなら先に作る)
make check                  # Okada (1985) Table 2 と横メルカトル投影の検算
./fault2disp fault2disp.txt # 設定ファイルを読んで dir_out/ に出力
```

出力は `dir_out/disp_NNNN.txt`(時刻ごとの累積変位。ENCflow の z と同じ
テキスト行列、行順は北 → 南)と `dir_out/bmlist.txt`(「時刻 ファイル名」の
表)。ENCflow 側は `&list_bedmotion` に `fn_bmlist = 'bm/bmlist.txt'` と書く
だけです。完全な例は [examples/tsunami_fault](../../examples/tsunami_fault/README.md)。

## 1. 最小の設定例

理想化実験(地理参照なし)。200 km × 150 km・1 km 格子に、逆断層 1 枚。

```
&list_fault2disp
  nx = 200                  ! 格子(ENCflow の list_geoinfo と同じ)
  ny = 150
  dx = 1000.0
  dy = 1000.0
  dir_out = 'bm'            ! 出力先。表のファイル名には prefix_list = 'bm/' が付く
  nout = 10                 ! 出力時刻の分割数(スナップショットは nout + 1 枚)
  nseg = 1
  x_top(1) = 120000.0       ! 上端中心の x(格子の左下隅から東へ 120 km)
  y_top(1) = 75000.0        ! 上端中心の y(左下隅から北へ 75 km)
  d_top(1) = 5000.0         ! 上端の深さ 5 km
  strike(1) = 0.0           ! 走向 N(北から時計回り)。断層は走向の右(東)へ下がる
  dip(1) = 15.0
  rake(1) = 90.0            ! 逆断層
  flength(1) = 60000.0      ! 長さ 60 km(走向方向)
  fwidth(1) = 30000.0       ! 幅 30 km(傾斜方向)
  slip(1) = 5.0             ! すべり 5 m
  t_r(1) = 0.0              ! 破壊開始 (s)
  t_rise(1) = 30.0          ! 立ち上がり 30 s(半正弦)
/
```

## 2. 断層パラメータの約束

セグメント k ごとに次を与えます(最大 50 セグメント。重ね合わせます)。

| 項目 | 意味 |
|---|---|
| x_top(k), y_top(k) | **上端の中心**の位置 (m)。座標の与え方は §3。f_lonlat=1 のときは代わりに lon_top(k), lat_top(k)(度) |
| d_top(k) | 上端の深さ (m。≥ 0。海底面・地表面からの深さ) |
| strike(k) | 走向(度。北から時計回り)。**断層面は走向の右手側に下がる**(北向きの走向なら東へ傾斜) |
| dip(k) | 傾斜(度。0 < dip ≤ 90) |
| rake(k) | すべり角(度。断層面上で走向方向から反時計回り)。90 = 逆断層(上盤が上がる)、−90 = 正断層、0 = 左横ずれ、180 = 右横ずれ |
| flength(k) | 長さ (m。走向方向) |
| fwidth(k) | 幅 (m。傾斜方向に沿って) |
| slip(k) | すべり量 (m) |
| t_r(k) | 破壊開始時刻 (s。計算開始からの相対) |
| t_rise(k) | 立ち上がり時間 (s)。0 で瞬時 |
| f_rise(k) | 立ち上がり関数。1: 線形、2: 半正弦 (1 − cos(πs))/2(既定) |

幾何の読み方: 上端中心から走向の右手側へ fwidth·cos(dip) 離れ、深さ
d_top + fwidth·sin(dip) に下端があります。逆断層では断層の投影の上
(浅い端の近く)が隆起し、下端の先(傾斜方向)が沈降します。長さ・幅・
位置はすべて同じ投影座標の m 単位で、投影面上の縮尺(k0〜1.0004)は
掛けません(0.04% 以下)。

## 3. 座標の与え方(3 つのパターン)

fault2disp の座標系は ENCflow の格子と同じで、x は東、y は北に増える
投影座標 (m) です。格子の左下隅セルの外縁座標 x_ll, y_ll(既定 0)を
基準に、セル (i, j) の中心が x = x_ll + (i − 1/2) dx、
y = y_ll + (ny − j + 1/2) dy(行 j = 1 が北端)になります。

### パターン A: 理想化実験(地理参照なし)

x_ll = y_ll = 0 のまま、x_top, y_top を**格子の左下隅からの距離**で
与えます(§1 の例)。nx, ny, dx, dy は必須です。

### パターン B: 投影座標系で地理参照がある解析

地盤高を bil+hdr または GeoTIFF(ENCflow の f_input_mode = 2 / 4)で
持っているなら、それを fn_z に与えるだけで格子(nx, ny, dx, dy)と原点
(x_ll, y_ll)がファイルから取られ、x_top, y_top は**その投影座標系の
絶対座標**で書けます。

```
&list_fault2disp
  fn_z = 'dem.tif'          ! 地理参照つきの地盤高(格子と原点はここから。u_h·∇z の項も加わる)
  f_input_mode = 4          ! 2: bil+hdr、4: GeoTIFF
  nseg = 1
  x_top(1) = 452300.0       ! その投影座標系の東距 (m)
  y_top(1) = 3987600.0      ! 同 北距 (m)
  ...(d_top 以下は §2)
/
```

日本の**平面直角座標系**(X が北距、Y が東距)で座標を持っているときは
`f_jpr = 1` を付けると、x_top(k) に X(北距)、y_top(k) に Y(東距)を
その順で書けます(x_ll, y_ll を手で書くときも同じ順)。

```
  f_jpr = 1
  x_top(1) = -35367.2       ! X(北距)
  y_top(1) = -5995.2        ! Y(東距)
```

地盤高がテキスト形式のときは地理参照を持たないので、x_ll, y_ll に
格子の左下隅の座標を手で書きます(その後は同じく絶対座標)。namelist に
nx, ny, dx, dy, x_ll, y_ll を書いた上で地理参照つきの fn_z も与えると、
値の一致を検査します(食い違えば停止)。

### パターン C: 経緯度で与える

`f_lonlat = 1` で断層の上端中心を lon_top(k), lat_top(k)(度)で与えると、
横メルカトル投影(Gauss–Krüger)で格子の投影座標に変換し、走向を子午線
収差で格子北基準に補正します。格子の投影を表すパラメータを与えます。

| 格子の投影 | proj_lon0 | proj_lat0 | proj_k0 | proj_fe | proj_fn |
|---|---|---|---|---|---|
| UTM(北半球)例: 54 帯 | 141.0(帯の中央子午線) | 0 | 0.9996 | 500000 | 0 |
| 平面直角座標系 例: IX 系 | 139.8333(139°50′) | 36.0 | 0.9999 | 0 | 0 |

```
&list_fault2disp
  fn_z = 'dem.tif'          ! 格子と原点はファイルから(または nx, ny, dx, dy と lon_ll, lat_ll)
  f_input_mode = 4
  f_lonlat = 1
  proj_lon0 = 141.0         ! UTM 54 帯
  proj_lat0 = 0.0
  proj_k0 = 0.9996
  proj_fe = 500000.0
  proj_fn = 0.0
  nseg = 1
  lon_top(1) = 142.80
  lat_top(1) = 38.10
  strike(1) = 195.0         ! 真北基準。子午線収差で格子北基準に補正される
  ...
/
```

格子の原点も経緯度で与えたいとき(地理参照のない格子)は lon_ll, lat_ll を
書くと x_ll, y_ll を同じ投影で求めます。楕円体は GRS80 が既定(WGS84 は
ell_rf = 298.257223563)。横メルカトル以外の投影(ランベルト等)の格子は、
利用者側で経緯度を投影座標に変換してパターン B で与えてください。

## 4. 時間と出力

- 出力時刻は t_start から t_end を nout 等分した nout + 1 個(t_start,
  t_end が負なら自動: 最も早い破壊開始 〜 最も遅い破壊終了)。各時刻の
  ファイルは**累積**変位(計算開始時の地形からの変位)で、ENCflow が
  スナップショット間を線形補間します。立ち上がりを滑らかに再現したい
  とき(特に非静水圧の f_nh_bottom)は nout を増やします。
- 瞬時変位(初期水位方式と同じ)は t_rise = 0 にするか、最後の
  スナップショットだけを表に書きます。
- `f_window = 1` で |u_z| > d_min の外接矩形(全セグメントの和集合)だけを
  書き、表に窓 `i1 j1 ni nj` を付けます(広域の計算でファイルを小さく
  する。切り捨てる変位は d_min 以下)。Okada の遠方場は mm 級で広く
  残るので、閾値は数 cm が実用的です。
- fn_z を与えると水平変位の寄与 u_h·∇z(Tanioka & Satake 1996)を鉛直
  変位に加えます(急な海底地形の上の断層で効く)。

## 5. パラメータ一覧

| 項目 | 既定 | 意味 |
|---|---|---|
| nx, ny, dx, dy | 0 | 格子(セル数、セル寸法 m)。地理参照つきの fn_z があれば省略可 |
| x_ll, y_ll | 0 | 格子左下隅の外縁座標 (m)。0 なら相対座標(パターン A) |
| fn_z | '' | 地盤高ファイル。与えると u_h·∇z を加え、地理参照の出所にもなる |
| f_input_mode | 1 | fn_z の形式(1: テキスト、2: bil+hdr、4: GeoTIFF。ENCflow と同じ) |
| f_georef | 1 | 1: fn_z が bil+hdr / GeoTIFF なら格子と原点をファイルから取る |
| f_jpr | 0 | 1: x_top/y_top と x_ll/y_ll を平面直角座標系の順 (X 北距, Y 東距) で与える |
| f_lonlat | 0 | 1: 断層位置を lon_top, lat_top(度)で与える(パターン C) |
| lon_top(k), lat_top(k) | 0 | 上端中心の経緯度(f_lonlat=1) |
| lon_ll, lat_ll | 未指定 | 格子左下隅の経緯度(与えると x_ll, y_ll を投影で求める) |
| proj_lon0, proj_lat0 | 0, 0 | 投影原点(度) |
| proj_k0 | 0.9996 | 中央子午線の縮尺係数 |
| proj_fe, proj_fn | 500000, 0 | 偽東距・偽北距 (m) |
| ell_a, ell_rf | 6378137, 298.257222101 | 楕円体の長半径・逆扁平率(GRS80) |
| f_strike_conv | 1 | 1: 走向を子午線収差で格子北基準に補正(f_lonlat=1 のとき) |
| dir_out | 'bm' | 出力先ディレクトリ |
| prefix_list | 'bm/' | 表に書くファイル名の前置き(ENCflow の dir_data からの相対になるように) |
| nout | 20 | 出力時刻の分割数 |
| t_start, t_end | −1 | 出力時刻の範囲 (s)。負なら自動 |
| f_window | 0 | 1: 変位がゼロでない外接矩形だけを書く |
| d_min | 0.001 | 窓の閾値 (m) |
| nseg | 0 | セグメント数(≤ 50) |
| x_top(k) 〜 f_rise(k) | — | 断層パラメータ(§2) |

## 6. 検算と例

`fault2disp -check` は Okada (1985) Table 2 の有限矩形断層(x=2, y=3, d=4,
dip 70°, L=3, W=2)の走向すべり・傾斜すべりの変位を 4 桁で再現し、横メルカトル
投影を UTM 54 帯と平面直角座標系 IX 系の点で Snyder (1987) の級数と 1 mm で
照合します。

examples/tsunami_fault に設定例があります: fault2disp.txt(パターン A)、
fault2disp_bil.txt / fault2disp_gtif.txt(パターン B。bil / GeoTIFF から
地理参照)、fault2disp_jpr.txt(平面直角座標系の並び)、fault2disp_ll.txt
(パターン C)。
