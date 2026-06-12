"""대표 그림 3종을 실제 코드 경로로 렌더 → PNG (시각 검수용)"""
import sys; sys.path.insert(0, ".")
from plot_style import apply_style, NAVY, GOLD, RED
apply_style()
import numpy as np, json
import matplotlib.pyplot as plt

# 활성 부지: 지도 E2E로 만든 합성 현장
from site_loader import load_site
from site_helpers import use_site
use_site(load_site("/tmp/custom_site_maptest.json"))

# (a) 부지 미리보기 — map_input._preview_local 실제 호출 (st.pyplot 패치)
import map_input
_saved = {}
map_input.st.pyplot = lambda fig, **k: _saved.setdefault("fig", fig)
obj = json.load(open("/tmp/custom_site_maptest.json"))
map_input._preview_local(obj)
_saved["fig"].savefig("/tmp/insp_preview.png")

# (b) Pareto front — tab3 스타일 재현 (합성 front)
rng = np.random.default_rng(2)
f1 = np.sort(rng.uniform(180, 420, 28)); f2 = 260 - 0.45*f1 + rng.normal(0, 6, 28)
fig, ax = plt.subplots(figsize=(6.4, 4.6))
ax.scatter(f1, f2, s=42, c=NAVY, alpha=0.8, label="Pareto 해 (합의 통합)")
ki = 11
ax.scatter([f1[ki]], [f2[ki]], s=240, marker="*", c=GOLD, ec="k", lw=0.8,
           zorder=5, label="추천 (Robust knee)")
ax.annotate("추천안", (f1[ki], f2[ki]), textcoords="offset points",
            xytext=(10, 8), fontweight="bold", color="#1B2A4A")
ax.set_xlabel("F1 — 제3자 안전위험 지수"); ax.set_ylabel("F2 — 총 양중 사이클 시간 (h)")
ax.set_title("Pareto Front — 안전 vs 효율 균형해 탐색")
ax.legend()
fig.savefig("/tmp/insp_pareto.png"); plt.close(fig)

# (c) w(θ) 장미도 — 앱 expander와 동일 코드
import objectives as O
op = O.compute_F1_operational((-8.0, 2.0), "Potain_MR_160C", 22.0)
B = len(op["dwell_theta"]); th = np.arange(B)*2*np.pi/B
figr = plt.figure(figsize=(5.2, 5.2))
axr = figr.add_subplot(111, projection="polar")
axr.bar(th, op["dwell_theta"], width=2*np.pi/B, color=NAVY, alpha=0.85,
        label=r"w($\theta$) 적재 체류비중")
V = op["V_theta"]; Vn = V/(V.max()+1e-9)*(op["dwell_theta"].max()+1e-9)
axr.plot(np.append(th, th[0]), np.append(Vn, Vn[0]), color=RED, lw=1.6,
         label=r"V($\theta$) 취약면적 (정규화)")
axr.set_theta_zero_location("E"); axr.set_theta_direction(1)
axr.set_yticklabels([])
axr.set_title(f"적재 경로 체류분포 — 집중비 ×{op['concentration_ratio']:.2f}", pad=16)
import numpy as _np
pk = int(_np.argmax(op["dwell_theta"]))
axr.annotate("야적장 방향\n(적재 권상 체류)", xy=(th[pk], op["dwell_theta"][pk]),
             xytext=(18, 14), textcoords="offset points", fontsize=8.5,
             fontweight="bold", color="#1B2A4A",
             bbox=dict(fc="white", ec="none", alpha=0.78, pad=1.5),
             arrowprops=dict(arrowstyle="->", lw=1.1, color="#1B2A4A"))
axr.legend(loc="upper center", fontsize=8.5, ncol=2, bbox_to_anchor=(0.5, -0.06))
figr.savefig("/tmp/insp_rose.png"); plt.close(figr)
print("3 figs saved")
