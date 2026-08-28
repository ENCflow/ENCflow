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


def make_param(tag, add_rain):
    """雛形の dir_result を差し替え(+A は降雨 namelist を追記)。"""
    text = Path(BASE_PARAM).read_text()
    assert "dir_result = 'result'" in text
    text = text.replace("dir_result = 'result'",
                        f"dir_result = 'result_seteq{tag}'")
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


def main():
    if len(sys.argv) > 1:
        {"A": run_phase_a, "B": run_phase_b}[sys.argv[1]]()
        return

    me = str(Path(__file__).resolve())
    for phase in ("A", "B"):
        r = subprocess.run([sys.executable, me, phase])
        if r.returncode != 0:
            sys.exit(f"test_set_value: phase {phase} FAILED")

    log_a = Path("result_seteqA/Log.txt").read_text().splitlines()
    log_b = Path("result_seteqB/Log.txt").read_text().splitlines()
    if log_a == log_b:
        print(f"test_set_value: PASS "
              f"(Log identical, {len(log_a)} lines; file-forced rain == "
              f"BMI set_value rain)")
    else:
        n = sum(1 for a, b in zip(log_a, log_b) if a != b)
        print(f"test_set_value: FAIL ({n} differing lines)")
        for a, b in zip(log_a, log_b):
            if a != b:
                print(f"  A: {a}\n  B: {b}")
                break
        sys.exit(1)


if __name__ == "__main__":
    main()
