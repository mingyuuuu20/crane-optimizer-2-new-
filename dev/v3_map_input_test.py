"""v3 지도입력 검증: ① 좌표변환 왕복 오차 ② 위저드 상태→site JSON→로드→소형 최적화 E2E"""
import sys, json, math
sys.path.insert(0, "..") if False else sys.path.insert(0, ".")
import numpy as np
from map_input import m_per_deg, latlng_to_local, build_site_obj_from_wizard

# ① 변환 정확도: 진주 위도에서 동쪽 100m, 북쪽 80m 만큼 떨어진 위경도를 만들고 역변환
lat0, lng0 = 35.1800, 128.1076
m_lat, m_lng = m_per_deg(lat0)
print(f"m/deg @35.18N: lat={m_lat:.2f}  lng={m_lng:.2f}")
lat_t = lat0 + 80.0 / m_lat
lng_t = lng0 + 100.0 / m_lng
x, y = latlng_to_local(lat_t, lng_t, lat0, lng0)
print(f"round-trip: expected (100, 80) → got ({x:.4f}, {y:.4f})  err=({abs(x-100)*1000:.2f}, {abs(y-80)*1000:.2f}) mm")
assert abs(x-100) < 0.01 and abs(y-80) < 0.01

def ll(dx, dy):  # 로컬(m) → 위경도 (테스트 도형 생성용)
    return (lat0 + dy/m_lat, lng0 + dx/m_lng)

# ② 위저드 상태 합성: 40×30 대지, 24×17 신축, 인접 1, 도로 1, 야적장 서측
state = {
    "name": "지도테스트현장", "location": "진주시 어딘가",
    "lot":  [ll(-20,-15), ll(20,-15), ll(20,15), ll(-20,15)],
    "bld":  [ll(-12,-8),  ll(12,-8),  ll(12,9),  ll(-12,9)],
    "bld_h": 30.0, "bld_fl": 10,
    "adj":  [{"pts": [ll(-10,22), ll(10,22), ll(10,32), ll(-10,32)],
              "name": "북측건물", "height_m": 15.0, "floors": 5}],
    "roads":[{"pts": [ll(-26,-15), ll(-21,-15), ll(-21,15), ll(-26,15)],
              "name": "서측도로", "width_m": 6.0}],
    "yard": ll(-23.0, 0.0), "nx": 5, "ny": 5,
}
obj = build_site_obj_from_wizard(state)
print("area:", obj["metadata"]["official_area_m2"], "(기대 1200)")
print("bld box:", obj["planned_building"]["footprint_box"], "(기대 -12,-8,12,9)")
print("adj rect:", obj["adjacent_buildings"][0]["footprint"])
print("yard:", obj["lift_points"]["material_yard"], "(기대 -23, 0)")
assert abs(obj["metadata"]["official_area_m2"] - 1200) < 2
bb = obj["planned_building"]["footprint_box"]
assert all(abs(a-b) < 0.05 for a,b in zip(bb, [-12,-8,12,9]))
assert abs(obj["lift_points"]["material_yard"][0] + 23) < 0.2

# 로더 검증 + 활성화 + 소형 NSGA-II
p = "/tmp/custom_site_maptest.json"
json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False)
from site_loader import load_site
from site_helpers import use_site
use_site(load_site(p))
from optimizer import run_optimization, select_knee
res, _ = run_optimization(pop_size=30, n_gen=10, seed=1, verbose=False)
assert res.F is not None and len(res.F) > 0, "feasible 해 없음"
ki = select_knee(res.F, res.X)
print(f"E2E OK: Pareto {len(res.F)}개, knee=({res.X[ki][0]:.1f},{res.X[ki][1]:.1f})")

# ③ 불량 입력 거부 확인
bad = dict(state); bad["lot"] = [ll(-20,-15), ll(20,-15)]
try:
    build_site_obj_from_wizard(bad); print("FAIL: 불량 대지 통과됨"); sys.exit(1)
except ValueError as e:
    print("불량 입력 거부 OK:", str(e)[:30])
print("\n✅ map_input 전체 통과")
