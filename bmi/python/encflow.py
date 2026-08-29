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

1 プロセス 1 モデル(モデル状態は Fortran 側の単一インスタンス)。
"""

import ctypes
import os
from pathlib import Path

import numpy as np

_BMI_SUCCESS = 0

# 公開変数名(bmi/README.md の表と同じ)
VAR_DEPTH = "surface_water__depth"
VAR_ELEVATION = "land_surface__elevation"
VAR_PRECIP = "atmosphere_water__precipitation_leq-volume_flux"
VAR_WSE = "surface_water__elevation"                        # 水位 (m)。get のみ
VAR_SPEED = "surface_water_flow__speed"                     # 速さ (m/s)。get のみ
VAR_UNIT_DISCHARGE = "surface_water_flow__unit_width_volume_flow_rate"  # 比流量 (m2/s)。get のみ
VAR_VELOCITY_X = "surface_water__x_component_of_velocity"   # 流速 x=東成分 (m/s)。get のみ
VAR_VELOCITY_Y = "surface_water__y_component_of_velocity"   # 流速 y=北成分 (m/s)。get のみ


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
        ny, nx = ctypes.c_int(), ctypes.c_int()
        self._check(
            self._lib.encflow_bmi_get_grid_shape(
                ctypes.byref(ny), ctypes.byref(nx)
            ),
            "get_grid_shape",
        )
        self.ny, self.nx = ny.value, nx.value

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
        for f in ("get_current_time", "get_start_time", "get_end_time",
                  "get_time_step"):
            getattr(lib, f"encflow_bmi_{f}").argtypes = [pd]
        lib.encflow_bmi_get_grid_shape.argtypes = [pi, pi]
        lib.encflow_bmi_get_grid_spacing.argtypes = [pd, pd]
        lib.encflow_bmi_get_grid_origin.argtypes = [pd, pd]
        lib.encflow_bmi_get_grid_size.argtypes = [pi]
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

    # ---- ライフサイクル ----

    def update(self):
        """1 タイムステップ進める。"""
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
    def grid_shape(self):
        """(ny, nx)"""
        return (self.ny, self.nx)

    @property
    def grid_spacing(self):
        """(dy, dx)(m)"""
        dy, dx = ctypes.c_double(), ctypes.c_double()
        self._check(
            self._lib.encflow_bmi_get_grid_spacing(
                ctypes.byref(dy), ctypes.byref(dx)
            ),
            "get_grid_spacing",
        )
        return (dy.value, dx.value)

    @property
    def grid_origin(self):
        """(y0, x0) = 左下隅の外縁座標(georef 未管理なら (0, 0))"""
        y0, x0 = ctypes.c_double(), ctypes.c_double()
        self._check(
            self._lib.encflow_bmi_get_grid_origin(
                ctypes.byref(y0), ctypes.byref(x0)
            ),
            "get_grid_origin",
        )
        return (y0.value, x0.value)

    @property
    def output_var_names(self):
        n = ctypes.c_int()
        self._check(self._lib.encflow_bmi_get_output_item_count(ctypes.byref(n)),
                    "get_output_item_count")
        names = []
        for i in range(1, n.value + 1):
            buf = ctypes.create_string_buffer(2048)
            self._check(
                self._lib.encflow_bmi_get_output_var_name(i, buf, len(buf)),
                "get_output_var_name",
            )
            names.append(buf.value.decode())
        return names

    # ---- 状態量 ----

    def get(self, name):
        """状態量の flatten 1 次元コピー(float64、長さ nx*ny)。

        BMI 標準形(要素 0 = 南西隅、行は南→北、x は西→東)。
        origin(左下)+ spacing と整合しており、Landlab の
        RasterModelGrid ノード配列とは無変換で 1:1 対応する。
        """
        n = self.nx * self.ny
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
        """強制場・状態を設定する(VAR_PRECIP / VAR_ELEVATION / VAR_DEPTH)。

        values は長さ nx*ny の 1 次元(BMI 標準形 = 要素 0 が南西)か、
        (ny, nx) の 2 次元(行 0 = 南。get2d と同じ向き)。いずれも
        次の update の冒頭で適用される。変数ごとの意味論:
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
        arr = np.ascontiguousarray(values, dtype=np.float64).ravel()
        n = self.nx * self.ny
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
        """状態量の (ny, nx) 2 次元コピー。

        行 0 が南(BMI 標準形)。matplotlib では origin='lower' で
        地図の向きどおりに表示できる。ENCflow 内部のセル (i, j)
        (j=1 が北)は arr[ny - j, i - 1] に対応する。
        """
        return self.get(name).reshape(self.ny, self.nx)
