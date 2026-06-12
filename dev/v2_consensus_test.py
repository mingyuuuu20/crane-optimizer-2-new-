"""Test: union of K seed fronts -> non-dominated filter -> robust knee.
Question: does it neutralize bad-basin seeds (0, 42)?"""
import numpy as np
from site_loader import load_site
from site_helpers import use_site
use_site(load_site("sites/sinsa_19_147.json"))
from optimizer import run_optimization, select_knee
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

actual = np.array([-0.3, 6.5])

def consensus(seeds, pop, gen):
    allF, allX, per_seed_knees = [], [], []
    for s in seeds:
        res, _ = run_optimization(pop_size=pop, n_gen=gen, seed=s, verbose=False, per_model=True)
        if res.F is None or len(res.F) == 0: continue
        allF.append(res.F); allX.append(res.X)
        ki = select_knee(res.F, res.X)
        per_seed_knees.append(res.X[ki][:2])
    F = np.vstack(allF); X = np.vstack(allX)
    nd = NonDominatedSorting().do(F, only_non_dominated_front=True)
    F, X = F[nd], X[nd]
    ki = select_knee(F, X)
    return F, X, ki, np.array(per_seed_knees)

# deliberately INCLUDE the two bad seeds
for seeds in ([42, 0, 1], [42, 0, 1, 2, 3]):
    F, X, ki, ks = consensus(seeds, 80, 40)
    x = X[ki]
    d = np.hypot(x[0]-actual[0], x[1]-actual[1])
    spread = max(np.hypot(*(a-b)) for i,a in enumerate(ks) for b in ks[i+1:])
    print(f"seeds={seeds}: merged front={len(F)}, knee=({x[0]:.2f},{x[1]:.2f}) "
          f"dist={d:.2f} m | per-seed knee max-spread={spread:.1f} m")
