import numpy as np
from site_loader import load_site
from site_helpers import use_site
use_site(load_site("sites/sinsa_19_147.json"))
import objectives as O
from optimizer import run_consensus_optimization, select_knee

actual = np.array([-0.3, 6.5])
for mode in ("static", "operational"):
    O.set_F1_mode(mode)
    F, X, info = run_consensus_optimization(pop_size=80, n_gen=40, seeds=(0,1,2))
    ki = select_knee(F, X)
    x = X[ki]
    d = np.hypot(x[0]-actual[0], x[1]-actual[1])
    print(f"[{mode:>11}] merged={info['n_merged']:>3}  agreement={info['agreement_m']:.1f} m  "
          f"knee=({x[0]:6.2f},{x[1]:6.2f}) model={int(x[2])} jib={x[3]:4.1f}  dist={d:.2f} m")
O.set_F1_mode("static")
