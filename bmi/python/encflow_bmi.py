"""ENCflow の bmipy 準拠クラス(bmi-tester 用アダプタ)。

CSDMS の適合性テスト bmi-tester は「Python の BMI クラス(bmipy.Bmi
準拠)」を検査するため、ctypes ラッパー(encflow.py)の上に BMI の
標準シグネチャそのままの薄いクラスを被せる。日常利用には encflow.py の
ENCflow クラスの方が便利で、本クラスは適合性確認と pymt 系ツール向け。

実行例(test/wave で):
    pip install bmi-tester
    export PYTHONPATH=../../bmi/python
    bmi-test encflow_bmi:EncflowBmi --config-file=param.txt --root-dir=. -vvv

制約(実装どおり):
- 1 プロセス 1 インスタンス(モデル状態は Fortran 側の singleton)。
  initialize → finalize → initialize の再初期化は逐次で可(bmi-tester が
  この使い方をする)。
- get_value_ptr / at_indices / 非構造格子系は NotImplementedError。
- 型は倍精度接口(float64)に統一(PREC=single ビルドでも交換は倍精度)。
"""

import ctypes

import numpy as np
from bmipy import Bmi

from encflow import _find_library

_OK = 0


def _err(what):
    raise RuntimeError(f"BMI {what} failed")


class EncflowBmi(Bmi):
    """bmipy.Bmi 準拠の ENCflow ハンドル。"""

    def __init__(self, lib=None):
        self._lib = ctypes.CDLL(_find_library(lib))
        c_int, c_double, c_char_p = ctypes.c_int, ctypes.c_double, ctypes.c_char_p
        pd, pi = ctypes.POINTER(c_double), ctypes.POINTER(c_int)
        L = self._lib
        L.encflow_bmi_initialize.argtypes = [c_char_p]
        L.encflow_bmi_update_until.argtypes = [c_double]
        L.encflow_bmi_get_component_name.argtypes = [c_char_p, c_int]
        L.encflow_bmi_get_output_item_count.argtypes = [pi]
        L.encflow_bmi_get_input_item_count.argtypes = [pi]
        L.encflow_bmi_get_output_var_name.argtypes = [c_int, c_char_p, c_int]
        L.encflow_bmi_get_input_var_name.argtypes = [c_int, c_char_p, c_int]
        for f in ("get_current_time", "get_start_time", "get_end_time",
                  "get_time_step"):
            getattr(L, f"encflow_bmi_{f}").argtypes = [pd]
        L.encflow_bmi_get_time_units.argtypes = [c_char_p, c_int]
        L.encflow_bmi_get_grid_shape.argtypes = [pi, pi]
        L.encflow_bmi_get_grid_spacing.argtypes = [pd, pd]
        L.encflow_bmi_get_grid_origin.argtypes = [pd, pd]
        L.encflow_bmi_get_grid_size.argtypes = [pi]
        L.encflow_bmi_get_grid_rank.argtypes = [c_int, pi]
        L.encflow_bmi_get_grid_type.argtypes = [c_int, c_char_p, c_int]
        L.encflow_bmi_get_var_grid.argtypes = [c_char_p, pi]
        L.encflow_bmi_get_var_type.argtypes = [c_char_p, c_char_p, c_int]
        L.encflow_bmi_get_var_units.argtypes = [c_char_p, c_char_p, c_int]
        L.encflow_bmi_get_var_itemsize.argtypes = [c_char_p, pi]
        L.encflow_bmi_get_var_nbytes.argtypes = [c_char_p, pi]
        L.encflow_bmi_get_var_location.argtypes = [c_char_p, c_char_p, c_int]
        L.encflow_bmi_get_value_double.argtypes = [c_char_p, pd, c_int]
        L.encflow_bmi_set_value_double.argtypes = [c_char_p, pd, c_int]

    # ---- 内部ヘルパ ----

    def _str(self, fname, *args):
        buf = ctypes.create_string_buffer(2048)
        if getattr(self._lib, fname)(*args, buf, len(buf)) != _OK:
            _err(fname)
        return buf.value.decode()

    def _double(self, fname):
        v = ctypes.c_double()
        if getattr(self._lib, fname)(ctypes.byref(v)) != _OK:
            _err(fname)
        return v.value

    def _int_of_name(self, fname, name):
        v = ctypes.c_int()
        if getattr(self._lib, fname)(name.encode(), ctypes.byref(v)) != _OK:
            _err(f"{fname}({name})")
        return v.value

    # ---- Initialize, run, finalize ----

    def initialize(self, config_file):
        if self._lib.encflow_bmi_initialize(str(config_file).encode()) != _OK:
            _err(f"initialize({config_file})")

    def update(self):
        if self._lib.encflow_bmi_update() != _OK:
            _err("update")

    def update_until(self, time):
        if self._lib.encflow_bmi_update_until(float(time)) != _OK:
            _err(f"update_until({time})")

    def finalize(self):
        if self._lib.encflow_bmi_finalize() != _OK:
            _err("finalize")

    # ---- Model information ----

    def get_component_name(self):
        return self._str("encflow_bmi_get_component_name")

    def get_input_item_count(self):
        v = ctypes.c_int()
        if self._lib.encflow_bmi_get_input_item_count(ctypes.byref(v)) != _OK:
            _err("get_input_item_count")
        return v.value

    def get_output_item_count(self):
        v = ctypes.c_int()
        if self._lib.encflow_bmi_get_output_item_count(ctypes.byref(v)) != _OK:
            _err("get_output_item_count")
        return v.value

    # bmi-tester が hasattr で探す旧 API 互換の別名
    def get_input_var_name_count(self):
        return self.get_input_item_count()

    def get_output_var_name_count(self):
        return self.get_output_item_count()

    def get_input_var_names(self):
        return tuple(
            self._str("encflow_bmi_get_input_var_name", i + 1)
            for i in range(self.get_input_item_count()))

    def get_output_var_names(self):
        return tuple(
            self._str("encflow_bmi_get_output_var_name", i + 1)
            for i in range(self.get_output_item_count()))

    # ---- Variable information ----

    def get_var_grid(self, name):
        return self._int_of_name("encflow_bmi_get_var_grid", name)

    def get_var_type(self, name):
        t = self._str("encflow_bmi_get_var_type", name.encode())
        # Fortran 側の型名 → numpy 流(交換接口は常に倍精度)
        return {"double_precision": "float64", "real": "float64"}.get(t, t)

    def get_var_units(self, name):
        return self._str("encflow_bmi_get_var_units", name.encode())

    def get_var_itemsize(self, name):
        # 交換接口(get_value_double)は常に float64
        return np.dtype(self.get_var_type(name)).itemsize

    def get_var_nbytes(self, name):
        return self.get_var_itemsize(name) * self.get_grid_size(
            self.get_var_grid(name))

    def get_var_location(self, name):
        return self._str("encflow_bmi_get_var_location", name.encode())

    # ---- Time information ----

    def get_current_time(self):
        return self._double("encflow_bmi_get_current_time")

    def get_start_time(self):
        return self._double("encflow_bmi_get_start_time")

    def get_end_time(self):
        return self._double("encflow_bmi_get_end_time")

    def get_time_units(self):
        return self._str("encflow_bmi_get_time_units")

    def get_time_step(self):
        return self._double("encflow_bmi_get_time_step")

    # ---- Getters / setters ----

    def get_value(self, name, dest):
        arr = np.ascontiguousarray(dest, dtype=np.float64)
        n = arr.size
        if self._lib.encflow_bmi_get_value_double(
                name.encode(),
                arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), n) != _OK:
            _err(f"get_value({name})")
        if arr is not dest:
            dest[:] = arr
        return dest

    def get_value_ptr(self, name):
        raise NotImplementedError("get_value_ptr")

    def get_value_at_indices(self, name, dest, inds):
        raise NotImplementedError("get_value_at_indices")

    def set_value(self, name, src):
        arr = np.ascontiguousarray(src, dtype=np.float64).ravel()
        if self._lib.encflow_bmi_set_value_double(
                name.encode(),
                arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                arr.size) != _OK:
            _err(f"set_value({name})")

    def set_value_at_indices(self, name, inds, src):
        raise NotImplementedError("set_value_at_indices")

    # ---- Grid information ----

    def get_grid_rank(self, grid):
        v = ctypes.c_int()
        if self._lib.encflow_bmi_get_grid_rank(grid, ctypes.byref(v)) != _OK:
            _err("get_grid_rank")
        return v.value

    def get_grid_size(self, grid):
        if grid != 0:
            _err("get_grid_size")
        v = ctypes.c_int()
        if self._lib.encflow_bmi_get_grid_size(ctypes.byref(v)) != _OK:
            _err("get_grid_size")
        return v.value

    def get_grid_type(self, grid):
        return self._str("encflow_bmi_get_grid_type", grid)

    def get_grid_shape(self, grid, shape):
        if grid != 0:
            _err("get_grid_shape")
        ny, nx = ctypes.c_int(), ctypes.c_int()
        if self._lib.encflow_bmi_get_grid_shape(
                ctypes.byref(ny), ctypes.byref(nx)) != _OK:
            _err("get_grid_shape")
        shape[0], shape[1] = ny.value, nx.value
        return shape

    def get_grid_spacing(self, grid, spacing):
        if grid != 0:
            _err("get_grid_spacing")
        dy, dx = ctypes.c_double(), ctypes.c_double()
        if self._lib.encflow_bmi_get_grid_spacing(
                ctypes.byref(dy), ctypes.byref(dx)) != _OK:
            _err("get_grid_spacing")
        spacing[0], spacing[1] = dy.value, dx.value
        return spacing

    def get_grid_origin(self, grid, origin):
        if grid != 0:
            _err("get_grid_origin")
        y0, x0 = ctypes.c_double(), ctypes.c_double()
        if self._lib.encflow_bmi_get_grid_origin(
                ctypes.byref(y0), ctypes.byref(x0)) != _OK:
            _err("get_grid_origin")
        origin[0], origin[1] = y0.value, x0.value
        return origin

    def get_grid_x(self, grid, x):
        raise NotImplementedError("get_grid_x")

    def get_grid_y(self, grid, y):
        raise NotImplementedError("get_grid_y")

    def get_grid_z(self, grid, z):
        raise NotImplementedError("get_grid_z")

    def get_grid_node_count(self, grid):
        return self.get_grid_size(grid)

    def get_grid_edge_count(self, grid):
        raise NotImplementedError("get_grid_edge_count")

    def get_grid_face_count(self, grid):
        raise NotImplementedError("get_grid_face_count")

    def get_grid_edge_nodes(self, grid, edge_nodes):
        raise NotImplementedError("get_grid_edge_nodes")

    def get_grid_face_edges(self, grid, face_edges):
        raise NotImplementedError("get_grid_face_edges")

    def get_grid_face_nodes(self, grid, face_nodes):
        raise NotImplementedError("get_grid_face_nodes")

    def get_grid_nodes_per_face(self, grid, nodes_per_face):
        raise NotImplementedError("get_grid_nodes_per_face")
