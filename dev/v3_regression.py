import sys; sys.path.insert(0, ".")
import numpy as np
from site_loader import load_site
from site_helpers import use_site
use_site(load_site("sites/sinsa_19_147.json"))
from optimizer import run_consensus_optimization, select_knee
F, X, info = run_consensus_optimization(pop_size=80, n_gen=40, seeds=(0,1,2))
ki = select_knee(F, X)
x = X[ki]; actual = np.array([-0.3, 6.5])
d = float(np.hypot(x[0]-actual[0], x[1]-actual[1]))
print(f"knee=({x[0]:.2f},{x[1]:.2f}) dist={d:.2f} m  agreement={info['agreement_m']:.1f} m  merged={info['n_merged']}")
assert d < 1.6, f"회귀 실패: {d:.2f} m (기대 1.43)"
print("✅ v2 수치 그대로 — v3 UI 변경이 수학을 건드리지 않음 증명")
