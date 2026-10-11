#!/usr/bin/env python3
"""set_value(降水)の受け入れ試験: ファイル強制と BMI 供給の等価性。

bmi_plan.md §4.2 の受け入れ基準「同じ降雨を fn_* 駆動で与えた場合と
set_value で与えた場合の結果一致」を自動化する。test/wave で実行する:

    cd test/wave && python3 ../../bmi/python/test_set_value.py

手順(1プロセス1モデルの制約のため、ランは自プロセスの再帰起動):
  A: 雛形 param.txt に一様降雨(prtype=1、36 mm/h 定数)を追記した
     ケースをBMI で完走。1ステップ目の後に get した降水場を保存。
     ついでに誤用検査: 降水がファイル駆動のときの set は BmiError。
  B: 雛形のまま(prtype=0 = 降雨なし)initialize し、A で保存した場を
     set_value して完走。ついでに誤用検査: 負値の set は BmiError、
     set 後の get が設定値と厳密一致。
判定: A と B の result の Log.txt が全行一致(文字列一致 = ULP 0)。

加えて h・z の set(developer.md §57)の「同値 set の不変性」を検査:
  C1: 雛形のまま BMI で完走(基準ラン)。
  C2: 半分まで進めた時点で get した h・z をそのまま set して継続。
      ついでに誤用検査: 負の h の set は BmiError。
判定: C1 と C2 の Log.txt が全行一致(set が副作用ゼロで、
e = z + h の回復が元の状態を厳密に再現することの証明)。

加えて粗度 rn の set(developer.md §77。P 区分 = パラメータの外部上書き)を検査:
  D1: 半分まで進めた時点で get した rn をそのまま set して継続(同値 set の
      不変性 → C1 と Log 全行一致)。ついでに誤用検査: 負の rn の set は BmiError。
  D2: 半分の時点で rn を一様に +0.03 して set。次の 1 歩の後の get が設定値と
      厳密一致(有効セル)し、終了時の h が D1 と異なる(粗度が実際に効く)。
      wave は rn0 = 0(無摩擦)なので差は明確に出る。
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE_PARAM = "param.txt"
RAIN_NAMELIST = """
&list_precip
  prtype = 1                 ! 一様降雨時系列
  dt_prupdate = 9999         ! 再更新なし(初回適用のみ。min)
  prval(1:2,1) =    0, 36.0  ! 全期間 36 mm/h の定数
  prval(1:2,2) = 9999, 36.0
/
"""
PRE_NPY = "result_seteq_pre.npy"
H_D1_NPY = "result_seteq_hD1.npy"
RN_ADD = 0.03                      # D2 で加える粗度(wave の rn0 = 0 に対して)


def make_param(tag, add_rain):
    """雛形の dir_result を差し替え(+A は降雨 namelist を追記)。"""
    text = Path(BASE_PARAM).read_text()
    for q in ("'", '"'):
        old = f"dir_result = {q}result{q}"
        if old in text:
            text = text.replace(old, f"dir_result = {q}result_seteq{tag}{q}")
            break
    else:
        raise AssertionError("dir_result = 'result' not found in param")
    if add_rain:
        # &list_precip を読ませるには fn_precip の指定が要る
        # ("-" = システムパラメータファイル自身から読む)
        assert "fn_initial = '-'" in text
        text = text.replace("fn_initial = '-'",
                            "fn_initial = '-'\n  fn_precip = '-'")
        text += RAIN_NAMELIST
    fn = f"param_seteq{tag}.txt"
    Path(fn).write_text(text)
    return fn


def run_phase_a():
    import numpy as np
    from encflow import ENCflow, VAR_PRECIP, BmiError

    with ENCflow(make_param("A", add_rain=True)) as m:
        m.update()
        pre = m.get(VAR_PRECIP)
        assert pre.max() > 0, "phase A: rain field is empty"
        np.save(PRE_NPY, pre)
        try:                                    # 誤用: ファイル駆動中の set
            m.set(VAR_PRECIP, pre)
        except BmiError:
            pass
        else:
            raise AssertionError("phase A: set during file-driven rain "
                                 "should fail (ownership rule)")
        while m.time < m.end_time:
            m.update()
    print("phase A: done")


def run_phase_b():
    import numpy as np
    from encflow import ENCflow, VAR_PRECIP, BmiError

    pre = np.load(PRE_NPY)
    with ENCflow(make_param("B", add_rain=False)) as m:
        try:                                    # 誤用: 負の降水強度
            m.set(VAR_PRECIP, -pre - 1.0)
        except BmiError:
            pass
        else:
            raise AssertionError("phase B: negative set should fail")
        m.set(VAR_PRECIP, pre)                  # 本命: A と同一の場を供給
        m.update()
        back = m.get(VAR_PRECIP)
        assert (back == pre).all(), "phase B: get after set is not exact"
        while m.time < m.end_time:
            m.update()
    print("phase B: done")


def run_phase_c1():
    from encflow import ENCflow

    with ENCflow(make_param("C1", add_rain=False)) as m:
        while m.time < m.end_time:
            m.update()
    print("phase C1: done")


def run_phase_c2():
    import numpy as np
    from encflow import ENCflow, VAR_DEPTH, VAR_ELEVATION, BmiError

    with ENCflow(make_param("C2", add_rain=False)) as m:
        t0, tend, dt = m.start_time, m.end_time, m.time_step
        nhalf = round((tend - t0) / dt) // 2
        m.update_until(t0 + dt * nhalf)
        h = m.get(VAR_DEPTH)
        z = m.get(VAR_ELEVATION)
        try:                                    # 誤用: 負の水深
            m.set(VAR_DEPTH, h - (h.max() + 1.0))
        except BmiError:
            pass
        else:
            raise AssertionError("phase C2: negative h set should fail")
        m.set(VAR_ELEVATION, z)                 # 同値 set(不変のはず)
        m.set(VAR_DEPTH, h)
        while m.time < tend:
            m.update()
    print("phase C2: done")


def run_phase_d1():
    import numpy as np
    from encflow import ENCflow, VAR_DEPTH, VAR_MANNING_N, BmiError

    with ENCflow(make_param("D1", add_rain=False)) as m:
        if VAR_MANNING_N not in m.input_var_names:
            raise AssertionError("phase D1: rn missing from input names")
        rn = m.get(VAR_MANNING_N)
        if rn.size != m.nx * m.ny or np.any(rn < 0.0):
            raise AssertionError("phase D1: get(rn) is not a valid field")
        t0, tend, dt = m.start_time, m.end_time, m.time_step
        nhalf = round((tend - t0) / dt) // 2
        m.update_until(t0 + dt * nhalf)
        try:                                    # 誤用: 負の粗度
            m.set(VAR_MANNING_N, rn - 1.0)
        except BmiError:
            pass
        else:
            raise AssertionError("phase D1: negative rn set should fail")
        m.set(VAR_MANNING_N, rn)                # 同値 set(不変のはず)
        while m.time < tend:
            m.update()
        np.save(H_D1_NPY, m.get(VAR_DEPTH))
    print("phase D1: done")


def run_phase_d2():
    import numpy as np
    from encflow import ENCflow, VAR_DEPTH, VAR_MANNING_N

    with ENCflow(make_param("D2", add_rain=False)) as m:
        t0, tend, dt = m.start_time, m.end_time, m.time_step
        nhalf = round((tend - t0) / dt) // 2
        m.update_until(t0 + dt * nhalf)
        rn = m.get(VAR_MANNING_N)
        rn_new = rn + RN_ADD
        m.set(VAR_MANNING_N, rn_new.reshape(m.ny, m.nx))   # 2 次元形でも可
        m.update()                              # 次の 1 歩の冒頭で適用
        back = m.get(VAR_MANNING_N)
        # 有効セルは設定値と厳密一致、無効セル(x<=0)は 0 のまま
        if not np.all((back == rn_new) | (back == 0.0)) or not np.any(back == rn_new):
            raise AssertionError("phase D2: get after set is not exact")
        while m.time < tend:
            m.update()
        h_d1 = np.load(H_D1_NPY)
        h_d2 = m.get(VAR_DEPTH)
        if np.array_equal(h_d1, h_d2):
            raise AssertionError("phase D2: roughness change had no effect on h")
        print(f"phase D2: max |h(D2) - h(D1)| = {np.max(np.abs(h_d2 - h_d1)):.3e}")
    print("phase D2: done")


def compare_logs(fa, fb, what):
    log_a = Path(fa).read_text().splitlines()
    log_b = Path(fb).read_text().splitlines()
    if log_a == log_b:
        print(f"test_set_value: PASS ({what}: Log identical, "
              f"{len(log_a)} lines)")
        return True
    n = sum(1 for a, b in zip(log_a, log_b) if a != b)
    print(f"test_set_value: FAIL ({what}: {n} differing lines)")
    for a, b in zip(log_a, log_b):
        if a != b:
            print(f"  {fa}: {a}\n  {fb}: {b}")
            break
    return False


def main():
    phases = {"A": run_phase_a, "B": run_phase_b,
              "C1": run_phase_c1, "C2": run_phase_c2,
              "D1": run_phase_d1, "D2": run_phase_d2}
    if len(sys.argv) > 1:
        phases[sys.argv[1]]()
        return

    me = str(Path(__file__).resolve())
    for phase in phases:
        r = subprocess.run([sys.executable, me, phase])
        if r.returncode != 0:
            sys.exit(f"test_set_value: phase {phase} FAILED")

    ok = compare_logs("result_seteqA/Log.txt", "result_seteqB/Log.txt",
                      "pre: file-forced == set_value")
    ok = compare_logs("result_seteqC1/Log.txt", "result_seteqC2/Log.txt",
                      "h,z: same-value set is invariant") and ok
    ok = compare_logs("result_seteqC1/Log.txt", "result_seteqD1/Log.txt",
                      "rn: same-value set is invariant") and ok
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
