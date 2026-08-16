#!/usr/bin/env python3
# Step 7 の 3D 図(figs/step7_simple.png, figs/step7_3d.png)を再生成する。
#
#   前提: ./encflow param_step7.txt と ../../bin/out2vtk param_step7.txt を
#         実行済みで result/vtk/ が存在すること。
#   依存: VTK の Python パッケージ(pip install vtk)。ParaView と同じ
#         VTK ライブラリで描画するため、本文の ParaView 手順と同じ見え方になる。
#         ヘッドレス環境では OSMesa(libosmesa6 等)が必要。
#   構成: オフスクリーン GL 文脈は作り直しに弱い環境があるため、
#         1 図 = 1 サブプロセスで描画する。
#
#   使い方: python3 Fig_step7.py [出力ディレクトリ(既定 figs)]
import multiprocessing
import os
import sys

FLOOD = "result/vtk/flood_0060.vts"     # t = 2 時間
TERRAIN = "result/vtk/terrain.vts"
EXAG = 3.0                              # 図2の鉛直強調倍率


def load(vtklib, fname):
    r = vtklib.vtkXMLStructuredGridReader()
    r.SetFileName(fname)
    r.Update()
    return r.GetOutput()


def render(vtklib, ren, fname):
    rw = vtklib.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(1400, 900)
    rw.SetMultiSamples(8)
    rw.AddRenderer(ren)
    rw.Render()
    w2i = vtklib.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    p = vtklib.vtkPNGWriter()
    p.SetFileName(fname)
    p.SetInputConnection(w2i.GetOutputPort())
    p.Write()
    print("wrote:", fname)


# ---- 図1: 最小手順(flood.pvd 単体、H で色付け、NaN = 灰色)----
def fig_simple(outdir):
    import vtk

    fl = load(vtk, FLOOD)
    # vtkGeometryFilter は ghost セル(流域外)を描画から落とす
    gf = vtk.vtkGeometryFilter()
    gf.SetInputData(fl)
    nt = vtk.vtkPolyDataNormals()
    nt.SetInputConnection(gf.GetOutputPort())
    nt.SetFeatureAngle(80)
    nt.SplittingOff()

    lut = vtk.vtkColorTransferFunction()    # Cool to Warm 風
    lut.AddRGBPoint(0.0, 0.23, 0.30, 0.75)
    lut.AddRGBPoint(3.0, 0.87, 0.87, 0.87)
    lut.AddRGBPoint(6.0, 0.71, 0.02, 0.15)
    lut.SetNanColor(0.72, 0.72, 0.72)       # 乾燥セル(本文手順 3 の灰色)
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(nt.GetOutputPort())
    m.SetLookupTable(lut)
    m.SelectColorArray("H")
    m.SetScalarModeToUsePointFieldData()
    m.ScalarVisibilityOn()
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetAmbient(0.25)

    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.AddActor(a)
    cam = ren.GetActiveCamera()
    cam.SetViewUp(0, 0, 1)
    cam.SetFocalPoint(30000, 20000, 1000)
    cam.SetPosition(52000, -30000, 34000)
    ren.ResetCameraClippingRange()
    render(vtk, ren, os.path.join(outdir, "step7_simple.png"))


# ---- 図2: 地形+水面の2レイヤ、鉛直 EXAG 倍 ----
def fig_3d(outdir):
    import vtk

    tr = vtk.vtkTransform()
    tr.Scale(1, 1, EXAG)

    # 地形(標高で淡く色分け)
    gt = vtk.vtkGeometryFilter()
    gt.SetInputData(load(vtk, TERRAIN))
    tf1 = vtk.vtkTransformFilter()
    tf1.SetTransform(tr)
    tf1.SetInputConnection(gt.GetOutputPort())
    nt = vtk.vtkPolyDataNormals()
    nt.SetInputConnection(tf1.GetOutputPort())
    nt.SetFeatureAngle(80)
    nt.SplittingOff()
    lut_t = vtk.vtkColorTransferFunction()
    lut_t.AddRGBPoint(70, 0.52, 0.60, 0.44)
    lut_t.AddRGBPoint(700, 0.76, 0.70, 0.54)
    lut_t.AddRGBPoint(1700, 0.66, 0.58, 0.50)
    lut_t.AddRGBPoint(2600, 0.97, 0.97, 0.97)
    mt = vtk.vtkPolyDataMapper()
    mt.SetInputConnection(nt.GetOutputPort())
    mt.SetLookupTable(lut_t)
    mt.SelectColorArray("Z")
    mt.SetScalarModeToUsePointFieldData()
    mt.ScalarVisibilityOn()
    at = vtk.vtkActor()
    at.SetMapper(mt)

    # 水面は Threshold(H >= 0.01)。All Scalars を外して幅1セルの河道を残す
    th = vtk.vtkThreshold()
    th.SetInputData(load(vtk, FLOOD))
    th.SetInputArrayToProcess(0, 0, 0,
                              vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "H")
    th.SetUpperThreshold(0.01)
    th.SetThresholdFunction(vtk.vtkThreshold.THRESHOLD_UPPER)
    th.AllScalarsOff()
    gw = vtk.vtkGeometryFilter()
    gw.SetInputConnection(th.GetOutputPort())
    tf2 = vtk.vtkTransformFilter()
    tf2.SetTransform(tr)
    tf2.SetInputConnection(gw.GetOutputPort())
    lut_w = vtk.vtkColorTransferFunction()  # 水深で青の濃淡
    lut_w.AddRGBPoint(0.0, 0.45, 0.75, 1.0)
    lut_w.AddRGBPoint(1.5, 0.12, 0.40, 0.95)
    lut_w.AddRGBPoint(6.0, 0.02, 0.12, 0.65)
    lut_w.SetNanColor(0.5, 0.75, 1.0)
    if hasattr(lut_w, "SetNanOpacity"):
        lut_w.SetNanOpacity(0.0)            # 乾湿境界セルの NaN 縁を透明に
    mw = vtk.vtkPolyDataMapper()
    mw.SetInputConnection(tf2.GetOutputPort())
    mw.SetLookupTable(lut_w)
    mw.SelectColorArray("H")
    mw.SetScalarModeToUsePointFieldData()
    mw.ScalarVisibilityOn()
    aw = vtk.vtkActor()
    aw.SetMapper(mw)
    aw.GetProperty().SetAmbient(0.45)

    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.AddActor(at)
    ren.AddActor(aw)
    cam = ren.GetActiveCamera()
    cam.SetViewUp(0, 0, 1)
    cam.SetFocalPoint(34000, 22000, 3000)
    cam.SetPosition(50000, -14000, 21000)
    ren.ResetCameraClippingRange()
    render(vtk, ren, os.path.join(outdir, "step7_3d.png"))


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "figs"
    os.makedirs(outdir, exist_ok=True)
    ctx = multiprocessing.get_context("spawn")
    for f in (fig_simple, fig_3d):
        p = ctx.Process(target=f, args=(outdir,))
        p.start()
        p.join()
        if p.exitcode != 0:
            sys.exit(f"figure process failed: {f.__name__}")
