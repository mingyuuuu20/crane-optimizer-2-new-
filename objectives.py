"""
================================================================================
objectives.py
================================================================================
타워크레인 배치 다목적 최적화 — 목적함수 F1·F2 (작업 4)
--------------------------------------------------------------------------------
F1: 제3자 안전 지수 최소화 (Third-Party Safety Risk Index)
F2: 양중 사이클 타임 최소화 (Lifting Cycle Time)

수학적 정식화 출처:
  - F1 구조 (Risk = Likelihood × Consequence): ISO 31000:2018
  - F1 취약성 가중치 카테고리: KOSHA KRAS 위험성평가 + CIRIA C703
  - F2 시간 계산: 제조사 카탈로그 운동 속도 사양

설계 원칙:
  - 두 함수 모두 "낮을수록 좋음" (minimization)
  - 결정변수: (crane_x, crane_y, model_id, jib_length, mast_height)
  - 알고리즘은 두 값을 동시 최소화하려 함 → trade-off → Pareto front
"""

import math
from typing import Tuple, Dict
from shapely.geometry import Point

# --- 활성 부지 관리 ---------------------------------------------------------
import site_model as _default_site

SITE                        = _default_site.SITE
ADJACENT_BUILDINGS          = _default_site.ADJACENT_BUILDINGS
ROADS                       = _default_site.ROADS
PLANNED_BUILDING            = _default_site.PLANNED_BUILDING
PLANNED_BUILDING_HEIGHT_M   = _default_site.PLANNED_BUILDING_HEIGHT_M
LIFT_POINTS                 = _default_site.LIFT_POINTS
MATERIAL_YARD               = _default_site.MATERIAL_YARD
BUILDING_GRID_POINTS        = _default_site.BUILDING_GRID_POINTS
LIFT_POINT_MATERIAL_PROFILE = _default_site.LIFT_POINT_MATERIAL_PROFILE
MATERIAL_WEIGHTS            = _default_site.MATERIAL_WEIGHTS
MATERIAL_HANDLING_TIME      = _default_site.MATERIAL_HANDLING_TIME


def set_active_site(site):
    """모듈 전역 부지 변수를 SiteData 로 교체 (constraints.set_active_site와 짝)."""
    global SITE, ADJACENT_BUILDINGS, ROADS, PLANNED_BUILDING
    global PLANNED_BUILDING_HEIGHT_M, LIFT_POINTS, MATERIAL_YARD
    global BUILDING_GRID_POINTS, LIFT_POINT_MATERIAL_PROFILE
    global MATERIAL_WEIGHTS, MATERIAL_HANDLING_TIME
    SITE                        = site.SITE
    ADJACENT_BUILDINGS          = site.ADJACENT_BUILDINGS
    ROADS                       = site.ROADS
    PLANNED_BUILDING            = site.PLANNED_BUILDING
    PLANNED_BUILDING_HEIGHT_M   = site.PLANNED_BUILDING_HEIGHT_M
    LIFT_POINTS                 = site.LIFT_POINTS
    MATERIAL_YARD               = site.MATERIAL_YARD
    BUILDING_GRID_POINTS        = site.BUILDING_GRID_POINTS
    LIFT_POINT_MATERIAL_PROFILE = site.LIFT_POINT_MATERIAL_PROFILE
    MATERIAL_WEIGHTS            = site.MATERIAL_WEIGHTS
    MATERIAL_HANDLING_TIME      = site.MATERIAL_HANDLING_TIME
    _invalidate_raster()


from crane_models import CRANES


# =============================================================================
# F1 관련 — 취약성 가중치 (Vulnerability Weights)
# =============================================================================
# (KOSHA 통계 출처 등은 동일, 위에 정의)

VULNERABILITY_WEIGHTS = {
    "own_site":              0.5,
    "planned_building":      0.5,
    "adjacent_residential":  3.0,
    "road":                  5.0,
    "empty":                 0.5,
}


# =============================================================================
# F2 관련 — 시공 시나리오 (자재별 + 위치별)
# =============================================================================
# 양중점·자재별 cycle 수 = LIFT_POINT_MATERIAL_PROFILE 에서 가져옴
# 자재별 중량 = MATERIAL_WEIGHTS
# 자재별 결박·해제 시간 = MATERIAL_HANDLING_TIME

HOOK_OPERATING_HEIGHT_M = PLANNED_BUILDING_HEIGHT_M + 7   # 39m
LIFT_POINT_DELIVERY_HEIGHT_M = 27                          # 9층 바닥

# 사고 확률 (per cycle) — 자재 무게에 비례 조정
# 출처 정당화는 위 docstring 동일
INCIDENT_PROBABILITY_PER_CYCLE = 1e-4   # baseline (갱폼 3톤 기준)

# 자재 무게별 사고 확률 가중치 (heavier → higher risk)
MATERIAL_RISK_FACTOR = {
    "gangform":  1.00,
    "rebar":     0.50,    # 가벼움
    "concrete":  0.70,
    "pc_part":   1.30,    # 무겁고 부피 큼
    "finishing": 0.20,    # 매우 가벼움
}

UTILIZATION_FACTOR = 0.62


# =============================================================================
# F1 모드 전환 — "static"(정적 선회면적, 논문 기준) / "operational"(운영가중 노출)
# =============================================================================
# [배경] 정적 F1은 선회원판 전체를 균일 노출로 가정한다. 그러나 실제 낙하물
# 위험은 "하중이 매달려 지나가는 경로" 아래에 집중된다는 것이 안전규정의
# 공통 원칙이다 (HSE 'loads should not be suspended over occupied areas',
# OSHA 1910.179(n)(3)(vi) 'avoid carrying loads over people').
# [모델] 운영 모드는 야적장→양중점 사이클의 적재(loaded) 구간이 각 방위각에
# 머무는 시간 비중 w(θ)를 계산해, 취약구역 면적 V(θ)를 가중 적분한다:
#     F1_op = (위험가중 사이클수 × P_base) × Σ_θ w(θ)·V(θ)·B
# w(θ)가 균일하면(B=빈 수) 정적 모드의 가중면적과 일치 → 정적은 특수해.
# 논문 수치 재현은 항상 "static" 모드 기준.

F1_MODE = "static"          # 실행 직전 app/스크립트에서 설정
_DWELL_BINS = 72            # 5° 간격
_RADIAL_SAMPLES = 10        # 등면적 환형 반경 샘플
_raster_cache = {"key": None, "grid": None, "x0": 0, "y0": 0, "res": 1.0}


def set_F1_mode(mode: str):
    global F1_MODE
    assert mode in ("static", "operational"), mode
    F1_MODE = mode


def _invalidate_raster():
    _raster_cache["key"] = None


def _build_vulnerability_raster(res: float = 1.0):
    """취약성 가중치 격자 (1m 해상도). 부지 전환 시 1회만 생성."""
    import numpy as _np
    import shapely

    zone_polys = ([("road", r["polygon"], VULNERABILITY_WEIGHTS["road"])
                    for r in ROADS.values()] +
                   [("adj", b["footprint"], VULNERABILITY_WEIGHTS["adjacent_residential"])
                    for b in ADJACENT_BUILDINGS.values()])
    all_geoms = [SITE] + [p for _, p, _ in zone_polys]
    minx = min(g.bounds[0] for g in all_geoms) - 40
    miny = min(g.bounds[1] for g in all_geoms) - 40
    maxx = max(g.bounds[2] for g in all_geoms) + 40
    maxy = max(g.bounds[3] for g in all_geoms) + 40
    nx = min(int((maxx - minx) / res) + 1, 800)
    ny = min(int((maxy - miny) / res) + 1, 800)
    xs = minx + _np.arange(nx) * res
    ys = miny + _np.arange(ny) * res
    XX, YY = _np.meshgrid(xs, ys, indexing="ij")
    grid = _np.full((nx, ny), VULNERABILITY_WEIGHTS["empty"], dtype=float)
    # own_site/planned 도 0.5 라 별도 칠 필요 없음. 도로·인접만 덮어씀
    # (인접 먼저, 도로가 우선)
    flat_x, flat_y = XX.ravel(), YY.ravel()
    for kind in ("adj", "road"):
        for k, poly, w in zone_polys:
            if k != kind:
                continue
            mask = shapely.contains_xy(poly, flat_x, flat_y).reshape(nx, ny)
            grid[mask] = w
    _raster_cache.update({"key": id(SITE), "grid": grid,
                           "x0": minx, "y0": miny, "res": res})


def _raster_lookup(px, py):
    """벡터화 격자 조회. 격자 밖 = empty 가중치."""
    import numpy as _np
    rc = _raster_cache
    g = rc["grid"]
    ix = ((px - rc["x0"]) / rc["res"]).astype(int)
    iy = ((py - rc["y0"]) / rc["res"]).astype(int)
    out = _np.full(px.shape, VULNERABILITY_WEIGHTS["empty"], dtype=float)
    ok = (ix >= 0) & (ix < g.shape[0]) & (iy >= 0) & (iy < g.shape[1])
    out[ok] = g[ix[ok], iy[ok]]
    return out


def compute_F1_operational(crane_xy, model_id, jib_length_m) -> Dict:
    """운영가중 노출 F1: 적재 후크 경로의 방위각 체류분포 w(θ)로 가중."""
    import numpy as _np
    if _raster_cache["key"] != id(SITE):
        _build_vulnerability_raster()

    spec = CRANES[model_id]
    cx, cy = crane_xy
    B = _DWELL_BINS
    omega = spec["slewing_speed_rpm"] * 2 * math.pi / 60  # rad/s
    if spec["type"] == "hammerhead":
        v_radial = spec["trolley_speed_mpm"] / 60
    else:
        v_radial = spec.get("luffing_speed_mpm", 40) / 60

    yard = MATERIAL_YARD
    th_yard = math.atan2(yard[1] - cy, yard[0] - cx)
    r_yard = math.hypot(yard[0] - cx, yard[1] - cy)

    dwell = _np.zeros(B)
    weighted_cycles = 0.0
    raw_cycles = 0
    for idx, profile in LIFT_POINT_MATERIAL_PROFILE.items():
        p = BUILDING_GRID_POINTS[idx]
        th_p = math.atan2(p[1] - cy, p[0] - cx)
        r_p = math.hypot(p[0] - cx, p[1] - cy)
        d_th = th_p - th_yard
        while d_th > math.pi:
            d_th -= 2 * math.pi
        while d_th < -math.pi:
            d_th += 2 * math.pi
        t_slew = abs(d_th) / omega if omega > 0 else 0.0
        t_radial = abs(r_p - r_yard) / v_radial if v_radial > 0 else 0.0
        t_horiz = max(t_slew, t_radial)
        for material, n in profile.items():
            if n == 0:
                continue
            rf = MATERIAL_RISK_FACTOR.get(material, 1.0)
            w_cyc = n * rf
            weighted_cycles += w_cyc
            raw_cycles += n
            mw = MATERIAL_WEIGHTS.get(material, 3000)
            wr = mw / spec["max_load_kgf"]
            v_loaded = (spec["hoist_speed_at_full_mpm"] +
                         (spec["hoist_speed_max_mpm"] - spec["hoist_speed_at_full_mpm"])
                         * (1 - wr)) / 60
            t_up = HOOK_OPERATING_HEIGHT_M / v_loaded                       # 야적장 위
            t_down = (HOOK_OPERATING_HEIGHT_M - LIFT_POINT_DELIVERY_HEIGHT_M) / v_loaded  # 양중점 위
            # 끝점 체류 (수직 이동 중 하중이 그 방위각 위에 정지)
            dwell[int(((th_yard % (2*math.pi)) / (2*math.pi)) * B) % B] += w_cyc * t_up
            dwell[int(((th_p % (2*math.pi)) / (2*math.pi)) * B) % B] += w_cyc * t_down
            # 호 구간 (수평 이동시간을 호를 따라 균등 분배)
            n_arc = max(1, int(abs(d_th) / (2*math.pi/B)) + 1)
            step = d_th / n_arc
            share = w_cyc * t_horiz / n_arc
            for k in range(n_arc):
                th_k = th_yard + step * (k + 0.5)
                dwell[int(((th_k % (2*math.pi)) / (2*math.pi)) * B) % B] += share

    if dwell.sum() <= 0:
        dwell[:] = 1.0
    w_theta = dwell / dwell.sum()

    # V(θ): 빈별 얇은 부채꼴의 취약가중 면적 (등면적 환형 반경 샘플)
    K = _RADIAL_SAMPLES
    th_bins = (_np.arange(B) + 0.5) * (2*math.pi/B)
    rr = jib_length_m * _np.sqrt((_np.arange(K) + 0.5) / K)
    TH, RR = _np.meshgrid(th_bins, rr, indexing="ij")
    PX = cx + RR * _np.cos(TH)
    PY = cy + RR * _np.sin(TH)
    cell_area = math.pi * jib_length_m**2 / (B * K)
    Vmap = _raster_lookup(PX, PY) * cell_area      # (B, K)
    V_theta = Vmap.sum(axis=1)                      # 빈별 가중면적

    exposure = float((w_theta * V_theta).sum() * B)   # w 균일 시 = Σ V_theta (정적과 동일 스케일)
    static_equiv = float(V_theta.sum())
    F1_value = weighted_cycles * INCIDENT_PROBABILITY_PER_CYCLE * exposure

    return {
        "F1": F1_value,
        "mode": "operational",
        "weighted_area_sum": exposure,
        "static_equiv_area": static_equiv,
        "concentration_ratio": exposure / static_equiv if static_equiv > 0 else 1.0,
        "raw_cycles": raw_cycles,
        "weighted_cycles": weighted_cycles,
        "dwell_theta": w_theta,
        "V_theta": V_theta,
    }


def compute_F1_active(crane_xy, model_id, jib_length_m) -> Dict:
    """현재 F1_MODE 에 따라 정적/운영 F1 디스패치 (optimizer 가 사용)."""
    if F1_MODE == "operational":
        return compute_F1_operational(crane_xy, model_id, jib_length_m)
    return compute_F1(crane_xy, model_id, jib_length_m)


# =============================================================================
# F1: 제3자 안전 지수 (자재별 가중)
# =============================================================================

def compute_F1(crane_xy: Tuple[float, float],
               model_id: str,
               jib_length_m: float,
               total_cycles: int = None) -> Dict:
    """
    제3자 안전 지수 F1 계산 (자재별 risk factor 반영).

    수식:
        F1 = Σ_material (N_material × P_base × R_material) × Σ V_z × A_overlap

    Args:
        crane_xy: 크레인 위치 (x, y) in meters
        model_id: 크레인 모델 ID
        jib_length_m: 지브 길이 (작업 반경)
        total_cycles: deprecated, 자동 계산

    Returns:
        dict with breakdown by zone + total F1
    """
    # 자재별 가중 cycles 합산
    weighted_cycles = 0
    raw_cycles = 0
    for idx, profile in LIFT_POINT_MATERIAL_PROFILE.items():
        for material, n in profile.items():
            risk_factor = MATERIAL_RISK_FACTOR.get(material, 1.0)
            weighted_cycles += n * risk_factor
            raw_cycles += n

    swept = Point(crane_xy).buffer(jib_length_m)

    # 카운터지브 영역 (T형은 별도 swept area)
    spec = CRANES[model_id]
    if spec["type"] == "hammerhead":
        counter_swept = Point(crane_xy).buffer(spec["counter_jib_length_m"])
        total_swept = swept.union(counter_swept)
    else:
        total_swept = swept

    breakdown = {}

    # 자기 부지
    overlap_site = total_swept.intersection(SITE).area
    breakdown["own_site"] = {
        "vulnerability": VULNERABILITY_WEIGHTS["own_site"],
        "area_m2": overlap_site,
        "risk_contribution": VULNERABILITY_WEIGHTS["own_site"] * overlap_site,
    }

    # 도로 (보행자·차량)
    road_total = 0
    for road_key, road in ROADS.items():
        overlap = total_swept.intersection(road["polygon"]).area
        road_total += overlap
    breakdown["road"] = {
        "vulnerability": VULNERABILITY_WEIGHTS["road"],
        "area_m2": road_total,
        "risk_contribution": VULNERABILITY_WEIGHTS["road"] * road_total,
    }

    # 인접 건물
    adj_total = 0
    for direction, bldg in ADJACENT_BUILDINGS.items():
        overlap = total_swept.intersection(bldg["footprint"]).area
        adj_total += overlap
    breakdown["adjacent_residential"] = {
        "vulnerability": VULNERABILITY_WEIGHTS["adjacent_residential"],
        "area_m2": adj_total,
        "risk_contribution": VULNERABILITY_WEIGHTS["adjacent_residential"] * adj_total,
    }

    # 그 외 (빈 영역) — 가중치 낮음
    total_swept_area = total_swept.area
    covered_area = overlap_site + road_total + adj_total
    empty_area = max(0, total_swept_area - covered_area)
    breakdown["empty"] = {
        "vulnerability": VULNERABILITY_WEIGHTS["empty"],
        "area_m2": empty_area,
        "risk_contribution": VULNERABILITY_WEIGHTS["empty"] * empty_area,
    }

    weighted_area_sum = sum(b["risk_contribution"] for b in breakdown.values())
    F1_value = weighted_cycles * INCIDENT_PROBABILITY_PER_CYCLE * weighted_area_sum

    return {
        "F1": F1_value,
        "weighted_area_sum": weighted_area_sum,
        "raw_cycles": raw_cycles,
        "weighted_cycles": weighted_cycles,
        "breakdown": breakdown,
    }


# =============================================================================
# F2: 양중 사이클 타임
# =============================================================================

def _angle_diff_rad(p1: Tuple[float, float], p2: Tuple[float, float],
                     center: Tuple[float, float]) -> float:
    """두 점이 중심에서 이루는 각도 차 (radian)."""
    a1 = math.atan2(p1[1] - center[1], p1[0] - center[0])
    a2 = math.atan2(p2[1] - center[1], p2[0] - center[0])
    d = abs(a1 - a2)
    return min(d, 2*math.pi - d)


def _radial_change(p1: Tuple[float, float], p2: Tuple[float, float],
                    center: Tuple[float, float]) -> float:
    """두 점의 반경 차이 (m)."""
    r1 = math.hypot(p1[0] - center[0], p1[1] - center[1])
    r2 = math.hypot(p2[0] - center[0], p2[1] - center[1])
    return abs(r2 - r1)


def compute_single_cycle_time(crane_xy: Tuple[float, float],
                                lift_point: Tuple[float, float],
                                model_id: str,
                                material: str = "gangform") -> Dict:
    """
    야적장 → 양중점 → 야적장 한 사이클의 총 시간 (초).
    자재 종류에 따라 결박·해제 시간, 호이스트 속도 영향 받음.
    """
    spec = CRANES[model_id]
    yard = MATERIAL_YARD

    # 각도·반경 변화 (크레인 기준)
    delta_theta_rad = _angle_diff_rad(yard, lift_point, crane_xy)
    delta_r = _radial_change(yard, lift_point, crane_xy)

    # 자재 중량에 따른 호이스트 속도 보정
    # 무거우면 full speed, 가벼우면 max speed
    material_weight = MATERIAL_WEIGHTS.get(material, 3000)
    weight_ratio = material_weight / spec["max_load_kgf"]
    # 보정 속도: weight_ratio가 1에 가까우면 full speed, 0에 가까우면 max speed
    v_hoist_loaded = (spec["hoist_speed_at_full_mpm"] +
                      (spec["hoist_speed_max_mpm"] - spec["hoist_speed_at_full_mpm"])
                      * (1 - weight_ratio)) / 60  # m/s
    v_hoist_empty = spec["hoist_speed_max_mpm"] / 60       # m/s

    # 선회·반경 속도
    omega_slew = spec["slewing_speed_rpm"] * 2 * math.pi / 60  # rad/s
    if spec["type"] == "hammerhead":
        v_radial = spec["trolley_speed_mpm"] / 60
    else:
        v_radial = spec.get("luffing_speed_mpm", 40) / 60

    # 자재별 결박·해제 시간
    handling = MATERIAL_HANDLING_TIME.get(material,
                                            {"attach": 30, "release": 20})
    t_attach = handling["attach"]
    t_release = handling["release"]

    # 호이스트 + 수평 이동
    t_hoist_up_loaded = HOOK_OPERATING_HEIGHT_M / v_hoist_loaded
    t_hoist_down_loaded = (HOOK_OPERATING_HEIGHT_M - LIFT_POINT_DELIVERY_HEIGHT_M) / v_hoist_loaded
    t_hoist_up_empty = (HOOK_OPERATING_HEIGHT_M - LIFT_POINT_DELIVERY_HEIGHT_M) / v_hoist_empty
    t_hoist_down_empty = HOOK_OPERATING_HEIGHT_M / v_hoist_empty

    t_slew = delta_theta_rad / omega_slew if omega_slew > 0 else 0
    t_radial = delta_r / v_radial if v_radial > 0 else 0
    t_horizontal_loaded = max(t_slew, t_radial)
    t_horizontal_empty = t_horizontal_loaded * 0.75

    t_one_cycle = (
        t_attach +
        t_hoist_up_loaded +
        t_horizontal_loaded +
        t_hoist_down_loaded +
        t_release +
        t_hoist_up_empty +
        t_horizontal_empty +
        t_hoist_down_empty
    )

    return {
        "total_sec": t_one_cycle,
        "material": material,
        "delta_theta_deg": math.degrees(delta_theta_rad),
        "delta_r_m": delta_r,
    }


def compute_F2(crane_xy: Tuple[float, float], model_id: str) -> Dict:
    """
    F2: 모든 양중점 × 자재에 대한 총 사이클 타임 (초).

    수식:
        F2_nominal = Σ_(point, material) N(point, material) × T_cycle(point, material)
        F2_calendar = F2_nominal / UTILIZATION_FACTOR

    자재별·위치별 cycle 수를 LIFT_POINT_MATERIAL_PROFILE 에서 가져와 합산.
    """
    total_time = 0.0
    per_point = {}
    per_material = {m: 0.0 for m in MATERIAL_WEIGHTS}

    for idx, profile in LIFT_POINT_MATERIAL_PROFILE.items():
        p = BUILDING_GRID_POINTS[idx]
        point_contribution = 0.0
        point_cycles = 0
        for material, n in profile.items():
            if n == 0:
                continue
            cycle_info = compute_single_cycle_time(crane_xy, p, model_id, material)
            contribution = n * cycle_info["total_sec"]
            point_contribution += contribution
            point_cycles += n
            per_material[material] += contribution
        total_time += point_contribution
        per_point[f"P{idx+1}"] = {
            "cycles": point_cycles,
            "total_sec": point_contribution,
            "position": p,
        }

    # 가동률 적용
    calendar_time = total_time / UTILIZATION_FACTOR

    return {
        "F2_sec": total_time,
        "F2_hours": total_time / 3600,
        "F2_days_at_8h": total_time / 3600 / 8,
        "F2_calendar_sec": calendar_time,
        "F2_calendar_hours": calendar_time / 3600,
        "F2_calendar_days_at_8h": calendar_time / 3600 / 8,
        "utilization_factor": UTILIZATION_FACTOR,
        "per_point": per_point,
        "per_material_hours": {m: t/3600 for m, t in per_material.items()},
    }


# =============================================================================
# 통합 평가
# =============================================================================

def evaluate_objectives(crane_xy: Tuple[float, float],
                          model_id: str,
                          jib_length_m: float) -> Dict:
    """주어진 배치에 대한 F1·F2 동시 계산."""
    f1 = compute_F1(crane_xy, model_id, jib_length_m)
    f2 = compute_F2(crane_xy, model_id)
    return {"F1": f1, "F2": f2}


# =============================================================================
# 자체 테스트
# =============================================================================

if __name__ == "__main__":
    print("=" * 78)
    print("F1 / F2 목적함수 자체 테스트")
    print("=" * 78)

    test_cases = [
        ("부지 중앙 + MR 160C + 짧은 지브",   (0, 0),    "Potain_MR_160C",    25),
        ("부지 중앙 + MR 160C + 긴 지브",     (0, 0),    "Potain_MR_160C",    50),
        ("부지 동남 + MR 160C",               (8, -5),   "Potain_MR_160C",    25),
        ("부지 북서 + MR 160C",               (-8, 5),   "Potain_MR_160C",    25),
        ("부지 중앙 + MDT 178 (T형)",         (0, 0),    "Potain_MDT_178",    25),
        ("부지 중앙 + 280 HC-L (대형)",       (0, 0),    "Liebherr_280_HC_L", 25),
    ]

    print(f"\n{'케이스':<40} {'F1':>10} {'F2(hours)':>12} {'F2(days@8h)':>12}")
    print("-" * 78)
    for name, xy, mid, jib in test_cases:
        r = evaluate_objectives(xy, mid, jib)
        F1 = r["F1"]["F1"]
        F2_h = r["F2"]["F2_hours"]
        F2_d = r["F2"]["F2_days_at_8h"]
        print(f"{name:<40} {F1:>10.3f} {F2_h:>12.1f} {F2_d:>12.1f}")

    # 상세 breakdown 한 케이스
    print("\n" + "=" * 78)
    print("상세 분석 — 부지 중앙 + MR 160C + 25m 지브")
    print("=" * 78)
    r = evaluate_objectives((0, 0), "Potain_MR_160C", 25)

    print("\n[F1 영역별 기여도]")
    for zone, b in r["F1"]["breakdown"].items():
        print(f"  {zone:<25} V={b['vulnerability']:>4.1f}  "
              f"Area={b['area_m2']:>7.1f}m²  "
              f"Risk={b['risk_contribution']:>8.2f}")
    print(f"  {'─'*60}")
    print(f"  Weighted area sum: {r['F1']['weighted_area_sum']:.2f}")
    print(f"  Total cycles: {r['F1']['total_cycles']}")
    print(f"  F1 = {r['F1']['F1']:.4f}")

    print("\n[F2 양중점별 기여도]")
    for pid, p in r["F2"]["per_point"].items():
        print(f"  {pid}: {p['cycles']}cycles × {p['single_cycle_sec']:.1f}s "
              f"= {p['total_sec']/3600:.1f}h")
    print(f"  {'─'*60}")
    print(f"  F2 = {r['F2']['F2_hours']:.1f}h = {r['F2']['F2_days_at_8h']:.1f} working days @8h/day")
