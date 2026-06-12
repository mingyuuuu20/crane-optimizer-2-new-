import numpy as np
from site_loader import load_site
from site_helpers import use_site
use_site(load_site("sites/sinsa_19_147.json"))
from optimizer import run_optimization, select_knee

actual = np.array([-0.3, 6.5])
rows = []
for s in [0,1,2,3,4,5,42]:
    res, _ = run_optimization(pop_size=80, n_gen=40, seed=s, verbose=False, per_model=True)
    if res.F is None or len(res.F)==0:
        print(f"seed {s}: infeasible"); continue
    ki = select_knee(res.F, res.X)
    x = res.X[ki]
    d = float(np.hypot(x[0]-actual[0], x[1]-actual[1]))
    rows.append((s, x[0], x[1], int(x[2]), x[3], d, len(res.F)))
    print(f"seed {s:>2}: knee=({x[0]:6.2f},{x[1]:6.2f}) model={int(x[2])} jib={x[3]:4.1f}  dist={d:5.2f} m  (Pareto {len(res.F)})")
ds = np.array([r[5] for r in rows])
print(f"\ndist: mean={ds.mean():.2f}  median={np.median(ds):.2f}  std={ds.std():.2f}  range=[{ds.min():.2f},{ds.max():.2f}]")
np.save("/tmp/sweep_dists.npy", ds)
