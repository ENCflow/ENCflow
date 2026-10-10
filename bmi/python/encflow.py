"""ENCflow の BMI を Python から使う最小 ctypes ラッパー。

共有ライブラリ ../libencflow_bmi.so(`make` で生成)をロードし、
BMI のライフサイクル(initialize / update / update_until / finalize)と
格子・時間・状態量の問い合わせを Python らしい形で提供する。

これは「サンプル」の位置づけ(test/ の検証スクリプトと同じ扱い。
developer.md §0 方針10 追記)。正式な Python パッケージ化(pymt 化)は
babelizer ルートを使う(docs/bmi_plan.md §4.3)。

使い方:
    from encflow import ENCflow

    with ENCflow("param.txt") as model:
        model.update_until(model.time + 60.0)
        h = model.get2d("surface_water__depth")   # (ny, nx) の numpy 配列

ネスト系(ルートの param に fn_nest)は全体が 1 つのモデルで、格子は
grid id で区別する(0 = ルート、k = 一覧の k+1 行目)。非ルート格子の変数は
var_on_grid(名前, k) で組み立てる(object 部に ~grid<k>。例:
surface_water~grid1__depth)。model.grids が格子 id の一覧、
model.shape_of(k) 等が格子ごとの情報、get / get2d / set は名前から格子を
判別する。update はルートの 1 歩(子はその中でサブステップ)。

1 プロセス 1 モデル(モデル状態は Fortran 側の単一 component)。
"""

import ctypes
import os
from pathlib import Path

import numpy as np

_BMI_SUCCESS = 0

# 公開変数名(bmi/README.md の表と同じ。ルート格子の名前)
VAR_DEPTH = "surface_water__depth"
VAR_ELEVATION = "land_surface__elevation"
VAR_PRECIP = "atmosphere_water__precipitation_leq-volume_flux"
VAR_WSE = "surface_water__elevation"                        # 水位 (m)。get のみ
VAR_SPEED = "surface_water_flow__speed"                     # 速さ (m/s)。get のみ
VAR_UNIT_DISCHARGE = "surface_water_flow__unit_width_volume_flow_rate"  # 比流量 (m2/s)。get のみ
VAR_VELOCITY_X = "surface_water__x_component_of_velocity"   # 流速 x=東成分 (m/s)。get のみ
VAR_VELOCITY_Y = "surface_water__y_component_of_velocity"   # 流速 y=北成分 (m/s)。get のみ


def var_on_grid(name, grid):
    """格子 grid 上の変数名。grid 0(ルート)はそのまま、k >= 1 は object 部の
    末尾に ~grid<k> を付ける(Fortran 側 encflow_var_on_grid と同じ規則。
    CSDMS Standard Names の文法 object~adjective__quantity の範囲内)。

        var_on_grid("surface_water__depth", 2) -> "surface_water~grid2__depth"
    """
    if grid <= 0:
        return name
    obj, sep, qty = name.partition("__")
    if not sep:
        raise ValueError(f"not a standard name (no '__'): {name}")
    return f"{obj}~grid{grid}__{qty}"


def _find_library(explicit=None):
    """libencflow_bmi.so を探す(引数 > 環境変数 > このファイルの親)。"""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("ENCFLOW_BMI_LIB")
    if env:
        candidates.append(Path(env))
    candidates.append(Path(__file__).resolve().parent.parent / "libencflow_bmi.so")
    for p in candidates:
        if p.is_file():
            return str(p)
    raise FileNotFoundError(
        "libencflow_bmi.so not found. Build it with `make` in bmi/ "
        "(or set ENCFLOW_BMI_LIB)."
    )


class BmiError(RuntimeError):
    """BMI 呼び出しが BMI_FAILURE を返した。"""


class ENCflow:
    """ENCflow の BMI ハンドル(1 プロセス 1 インスタンス)。"""

    def __init__(self, param_file, lib=None):
        self._lib = ctypes.CDLL(_find_library(lib))
        self._declare()
        self._finalized = False
        self._check(
            self._lib.encflow_bmi_initialize(str(param_file).encode()),
            f"initialize({param_file})",
        )
        # 格子の一覧(出力変数の grid id から集める)と各格子の形
        self._shapes = {}
        for name in self.output_var_names:
            gid = self.var_grid(name)
            if gid not in self._shapes:
                self._shapes[gid] = self.shape_of(gid)
        self.ny, self.nx = self._shapes[0]

    # ---- 内部 ----

    def _declare(self):
        lib = self._lib
        c_int, c_double, c_char_p = ctypes.c_int, ctypes.c_double, ctypes.c_char_p
        pd = ctypes.POINTER(c_double)
        pi = ctypes.POINTER(c_int)
        lib.encflow_bmi_initialize.argtypes = [c_char_p]
        lib.encflow_bmi_update.argtypes = []
        lib.encflow_bmi_update_until.argtypes = [c_double]
        lib.encflow_bmi_finalize.argtypes = []
        lib.encflow_bmi_get_component_name.argtypes = [c_char_p, c_int]
        lib.encflow_bmi_get_output_item_count.argtypes = [pi]
        lib.encflow_bmi_get_output_var_name.argtypes = [c_int, c_char_p, c_int]
        lib.encflow_bmi_get_input_item_count.argtypes = [pi]
        lib.encflow_bmi_get_input_var_name.argtypes = [c_int, c_char_p, c_int]
        for f in ("get_current_time", "get_start_time", "get_end_time",
                  "get_time_step"):
            getattr(lib, f"encflow_bmi_{f}").argtypes = [pd]
        lib.encflow_bmi_get_var_grid.argtypes = [c_char_p, pi]
        lib.encflow_bmi_get_grid_shape.argtypes = [c_int, pi, pi]
        lib.encflow_bmi_get_grid_spacing.argtypes = [c_int, pd, pd]
        lib.encflow_bmi_get_grid_origin.argtypes = [c_int, pd, pd]
        lib.encflow_bmi_get_grid_size.argtypes = [c_int, pi]
        lib.encflow_bmi_get_value_double.argtypes = [c_char_p, pd, c_int]
        lib.encflow_bmi_set_value_double.argtypes = [c_char_p, pd, c_int]

    @staticmethod
    def _check(status, what):
        if status != _BMI_SUCCESS:
            raise BmiError(f"BMI {what} failed (status={status})")

    def _get_double(self, fname):
        v = ctypes.c_double()
        self._check(getattr(self._lib, fname)(ctypes.byref(v)), fname)
        return v.value

    def _names(self, count_fn, name_fn):
        n = ctypes.c_int()
        self._check(getattr(self._lib, count_fn)(ctypes.byref(n)), count_fn)
        names = []
        for i in range(1, n.value + 1):
            buf = ctypes.create_string_buffer(2048)
            self._check(getattr(self._lib, name_fn)(i, buf, len(buf)), name_fn)
            names.append(buf.value.decode())
        return names

    # ---- ライフサイクル ----

    def update(self):
        """1 タイムステップ進める(ネスト系ではルートの 1 歩)。"""
        self._check(self._lib.encflow_bmi_update(), "update")

    def update_until(self, t):
        """時刻 t(秒)まで進める(dt の整数倍・終了時刻以内)。"""
        self._check(self._lib.encflow_bmi_update_until(float(t)),
                    f"update_until({t})")

    def finalize(self):
        """終了処理(最終出力・破棄)。二重呼び出しは無視する。"""
        if not self._finalized:
            self._finalized = True
            self._check(self._lib.encflow_bmi_finalize(), "finalize")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.finalize()
        return False

    # ---- 情報 ----

    @property
    def name(self):
        buf = ctypes.create_string_buffer(2048)
        self._check(
            self._lib.encflow_bmi_get_component_name(buf, len(buf)),
            "get_component_name",
        )
        return buf.value.decode()

    @property
    def time(self):
        return self._get_double("encflow_bmi_get_current_time")

    @property
    def start_time(self):
        return self._get_double("encflow_bmi_get_start_time")

    @property
    def end_time(self):
        return self._get_double("encflow_bmi_get_end_time")

    @property
    def time_step(self):
        return self._get_double("encflow_bmi_get_time_step")

    @property
    def grids(self):
        """格子 id の一覧(昇順。ネストなしは [0])。"""
        return sorted(self._shapes)

    @property
    def grid_shape(self):
        """ルート格子の (ny, nx)。格子ごとには shape_of(grid)。"""
        return (self.ny, self.nx)

    @property
    def grid_spacing(self):
        """ルート格子の (dy, dx)(m)。格子ごとには spacing_of(grid)。"""
        return self.spacing_of(0)

    @property
    def grid_origin(self):
        """ルート格子の (y0, x0) = 左下隅の外縁座標。格子ごとには origin_of(grid)。"""
        return self.origin_of(0)

    def shape_of(self, grid):
        """格子 grid の (ny, nx)。"""
        ny, nx = ctypes.c_int(), ctypes.c_int()
        self._check(
            self._lib.encflow_bmi_get_grid_shape(int(grid), ctypes.byref(ny), ctypes.byref(nx)),
            f"get_grid_shape({grid})",
        )
        return (ny.value, nx.value)

    def spacing_of(self, grid):
        """格子 grid の (dy, dx)(m)。"""
        dy, dx = ctypes.c_double(), ctypes.c_double()
        self._check(
            self._lib.encflow_bmi_get_grid_spacing(int(grid), ctypes.byref(dy), ctypes.byref(dx)),
            f"get_grid_spacing({grid})",
        )
        return (dy.value, dx.value)

    def origin_of(self, grid):
        """格子 grid の (y0, x0) = 左下隅の外縁座標。

        georef(hdr)を使うケースではその実座標。ネストの子で georef が
        なければ親の原点と整列位置から導かれ、全格子がルートの座標系
        (ルートに georef がなければ (0, 0) 原点)で表される。
        """
        y0, x0 = ctypes.c_double(), ctypes.c_double()
        self._check(
            self._lib.encflow_bmi_get_grid_origin(int(grid), ctypes.byref(y0), ctypes.byref(x0)),
            f"get_grid_origin({grid})",
        )
        return (y0.value, x0.value)

    def size_of(self, grid):
        """格子 grid のセル数(= nx*ny)。"""
        n = ctypes.c_int()
        self._check(self._lib.encflow_bmi_get_grid_size(int(grid), ctypes.byref(n)),
                    f"get_grid_size({grid})")
        return n.value

    def var_grid(self, name):
        """変数 name が載る格子 id。"""
        g = ctypes.c_int()
        self._check(self._lib.encflow_bmi_get_var_grid(name.encode(), ctypes.byref(g)),
                    f"get_var_grid({name})")
        return g.value

    @property
    def output_var_names(self):
        return self._names("encflow_bmi_get_output_item_count",
                           "encflow_bmi_get_output_var_name")

    @property
    def input_var_names(self):
        return self._names("encflow_bmi_get_input_item_count",
                           "encflow_bmi_get_input_var_name")

    # ---- 状態量 ----

    def get(self, name):
        """状態量の flatten 1 次元コピー(float64、長さ nx*ny。格子は名前から)。

        BMI 標準形(要素 0 = 南西隅、行は南→北、x は西→東)。
        origin(左下)+ spacing と整合しており、Landlab の
        RasterModelGrid ノード配列とは無変換で 1:1 対応する。
        """
        ny, nx = self._shapes[self.var_grid(name)]
        n = nx * ny
        dest = np.empty(n, dtype=np.float64)
        self._check(
            self._lib.encflow_bmi_get_value_double(
                name.encode(),
                dest.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                n,
            ),
            f"get_value({name})",
        )
        return dest

    def set(self, name, values):
        """強制場・状態を設定する(VAR_PRECIP / VAR_ELEVATION / VAR_DEPTH と
        その格子版 var_on_grid(…, k))。

        values は長さ nx*ny の 1 次元(BMI 標準形 = 要素 0 が南西)か、
        (ny, nx) の 2 次元(行 0 = 南。get2d と同じ向き)。いずれも
        その格子の次の 1 歩の冒頭で適用される。変数ごとの意味論:
        - VAR_PRECIP (m/s): 持続強制(次の set まで有効)。降水が
          パラメータファイル駆動(prtype != 0)のケースでは BmiError
          (生産者は一人の規則)。
        - VAR_ELEVATION (m): 地形の置換(一回適用。h は保存され水位
          e = z + h が回復される)。geomorph 等の地形更新プロセスが
          有効なケースでは BmiError。海セルには適用されない。
        - VAR_DEPTH (m): 水深の置換(一回適用。データ同化型の状態
          上書き。加算ではない — 水を足すなら VAR_PRECIP を使う)。
          運動量(u, v)は変更されない。負値は BmiError。
        """
        ny, nx = self._shapes[self.var_grid(name)]
        arr = np.ascontiguousarray(values, dtype=np.float64).ravel()
        n = nx * ny
        if arr.size != n:
            raise ValueError(
                f"set({name}): size {arr.size} != nx*ny = {n}")
        self._check(
            self._lib.encflow_bmi_set_value_double(
                name.encode(),
                arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                n,
            ),
            f"set_value({name})",
        )

    def get2d(self, name):
        """状態量の (ny, nx) 2 次元コピー(格子は名前から)。

        行 0 が南(BMI 標準形)。matplotlib では origin='lower' で
        地図の向きどおりに表示できる。ENCflow 内部のセル (i, j)
        (j=1 が北)は arr[ny - j, i - 1] に対応する。
        """
        ny, nx = self._shapes[self.var_grid(name)]
        return self.get(name).reshape(ny, nx)
