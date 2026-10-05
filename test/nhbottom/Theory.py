#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nhbottom の線形理論(docs/nonhydrostatic_plan.md §16.1)。1 次元・平坦床 H・微小振幅。
#   底面 z_b(x,t) = ζ0 s(x) r(t)、s = 1 (|x − xc| < b)、r = (1 − cos(πt/tc))/2 (t < tc)。
#   水面の Fourier 成分 η̂_k は  η̈ + ω_k² η̂ = F_k ẑ̈_k  に従う:
#     hydro : ω² = gHΛ,            F = 1
#     nh0   : ω² = gHΛ/(1 + βΛ),   F = 1                  (NH、加速度項なし)
#     nh1   : ω² = gHΛ/(1 + βΛ),   F = 1/(1 + βΛ)²        (NH、加速度項あり。源項を
#                                   同じ Helmholtz 作用素で平滑化した −(h/4)(z̈ + z̈_s)。
#                                   素朴な −(h/2) z̈ なら (1 − βΛ)/(1 + βΛ) = "nh1raw")
#     exact : ω² = gk tanh kH,     F = 1/cosh kH           (ポテンシャル流)
#   β = H²/4。Λ は ENC の 1 次元半離散シンボル 2(1 − cos kΔx)/Δx²(連続では k²)。
#   Duhamel 積分 η̂_k(t) = F ζ0 ŝ_k ∫₀^min(t,tc) sin(ω(t−τ))/ω · r̈(τ) dτ を τ の台形則で評価。
#   使い方: import して surface(model, times) / probe(model, x, times)、または
#           python3 Theory.py で数表(プローブ x = xc + 200 m の最大水位)
import math, sys
import numpy as np
if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz

G = 9.80665
H = 10.0
XC, B, ZETA0, TC = 500.0, 20.0, 0.2, 1.0
LX = 1000.0
DX_ENC = 1.25            # ENC の Δx(Λ のシンボル用)
N = 8192                 # 理論の周期格子(Δx = 0.122 m)
MODELS = ("hydro", "nh0", "nh1raw", "nh1", "exact")
LABEL = {"hydro": "静水圧", "nh0": "NH(加速度項なし)", "nh1raw": "NH(素朴な源項 −(h/2)z̈)",
         "nh1": "NH(加速度項あり)", "exact": "厳密(線形ポテンシャル流)"}

def _ramp_dd(tau):
    return 0.5 * (math.pi / TC) ** 2 * np.cos(math.pi * tau / TC)

def _omega_F(model, k, enc=True):
    beta = H * H / 4
    lam = 2.0 * (1 - np.cos(k * DX_ENC)) / DX_ENC ** 2 if enc else k * k
    if model == "hydro":
        return np.sqrt(G * H * lam), np.ones_like(k)
    if model == "nh0":
        return np.sqrt(G * H * lam / (1 + beta * lam)), np.ones_like(k)
    if model == "nh1":
        return np.sqrt(G * H * lam / (1 + beta * lam)), 1.0 / (1 + beta * lam) ** 2
    if model == "nh1raw":
        return np.sqrt(G * H * lam / (1 + beta * lam)), (1 - beta * lam) / (1 + beta * lam)
    if model == "exact":
        kk = np.abs(k)
        return np.sqrt(G * kk * np.tanh(kk * H)), 1.0 / np.cosh(kk * H)
    raise ValueError(model)

class Theory:
    def __init__(self, model, enc=True):
        self.model = model
        self.x = (np.arange(N) + 0.5) * LX / N
        self.k = 2 * np.pi * np.fft.fftfreq(N, d=LX / N)
        s = np.where(np.abs(self.x - XC) < B, 1.0, 0.0)
        self.sk = np.fft.fft(s)
        self.w, self.F = _omega_F(model, self.k, enc)
        # t ≥ tc 用: C = ∫cos(ωτ) r̈ dτ, S = ∫sin(ωτ) r̈ dτ(台形則)
        tau = np.linspace(0, TC, 801)
        rdd = _ramp_dd(tau)
        wt = np.outer(self.w, tau)
        self.C = np.trapezoid(np.cos(wt) * rdd, tau, axis=1)
        self.S = np.trapezoid(np.sin(wt) * rdd, tau, axis=1)

    def _eta_k(self, t):
        w = self.w
        if t >= TC:
            with np.errstate(divide="ignore", invalid="ignore"):
                I = (np.sin(w * t) * self.C - np.cos(w * t) * self.S) / w
            I[w == 0] = 1.0          # k=0: ∫(t−τ) r̈ dτ = r(tc) − r(0) = 1
        else:
            tau = np.linspace(0, t, 401)
            rdd = _ramp_dd(tau)
            with np.errstate(divide="ignore", invalid="ignore"):
                ker = np.sin(np.outer(w, t - tau)) / w[:, None]
            ker[w == 0, :] = (t - tau)[None, :]
            I = np.trapezoid(ker * rdd, tau, axis=1)
        return ZETA0 * self.F * self.sk * I

    def surface(self, t):
        """時刻 t の水面変位 η(x)(self.x 上)"""
        return np.real(np.fft.ifft(self._eta_k(t)))

    def probe(self, xp, times):
        """位置 xp の時系列(Fourier 和を直接評価)"""
        ph = np.exp(1j * self.k * xp) / N
        return np.array([np.real(np.sum(self._eta_k(t) * ph)) for t in times])

if __name__ == "__main__":
    times = np.arange(0, 40.0001, 0.05)
    xp = XC + 200.0
    print("| model | η_max at x = xc+200 (m) | t of η_max (s) | η at x = xc, t = tc (m) |")
    print("|---|---:|---:|---:|")
    for m in MODELS:
        th = Theory(m)
        e = th.probe(xp, times)
        i = int(np.argmax(e))
        e0 = th.surface(TC)
        j = int(np.argmin(np.abs(th.x - XC)))
        print("| %s | %.4f | %.2f | %.4f |" % (LABEL[m], e[i], times[i], e0[j]))
