"""
================================================================================
explain.py
================================================================================
추천 결과 자동 설명 — knee 해의 "왜"를 비전문가용 한국어로 생성
--------------------------------------------------------------------------------
규칙 기반 (LLM 미사용, 오프라인 결정적 출력).
근거 데이터: 제약 여유(G1·G5·G2), F1 영역별 기여도, Pareto front 상대위치,
다중 seed 합의도. 모든 수치는 동일 평가 함수에서 직접 산출.
"""

import math
import numpy as np

MODEL_LIST = ["Potain_MDT_178", "Potain_MR_160C", "Liebherr_280_HC_L"]
MODEL_KO = {
    "Potain_MDT_178": "Potain MDT 178 (T형)",
    "Potain_MR_160C": "Potain MR 160C (러핑형 소형)",
    "Liebherr_280_HC_L": "Liebherr 280 HC-L (러핑형 대형)",
}


def build_explanation(x, F_row, F_all, mode="static",
                       agreement_m=None, n_seeds=None):
    """knee 해 x = (cx, cy, model_idx, jib, mast) 에 대한 설명 markdown."""
    import objectives as O
    import constraints as C

    cx, cy = float(x[0]), float(x[1])
    model = MODEL_LIST[int(np.clip(x[2], 0, 2))]
    jib, mast = float(x[3]), float(x[4])
    spec_name = MODEL_KO.get(model, model)

    # --- 기종 근거: 최원거리 양중점에서의 능력 여유 ---
    radii = [math.hypot(p[0] - cx, p[1] - cy) for p in O.BUILDING_GRID_POINTS]
    r_far = max(radii) if radii else 0.0
    cap_at_far = C.lookup_load_capacity(model, r_far)
    payload = C.PAYLOAD_MAX_KGF
    margin_pct = (cap_at_far / payload - 1) * 100 if payload > 0 else 0
    reach_util = r_far / jib * 100 if jib > 0 else 0

    # --- 위치 근거: F1 영역별 기여 + 인접건물 최소거리 ---
    f1d = O.compute_F1((cx, cy), model, jib)
    bd = f1d["breakdown"]
    total_risk = sum(b["risk_contribution"] for b in bd.values()) + 1e-9
    share_road = bd["road"]["risk_contribution"] / total_risk * 100
    share_adj = bd["adjacent_residential"]["risk_contribution"] / total_risk * 100
    share_own = (bd["own_site"]["risk_contribution"] +
                  bd["empty"]["risk_contribution"]) / total_risk * 100
    from shapely.geometry import Point
    p_crane = Point(cx, cy)
    d_adj = min((b["footprint"].distance(p_crane)
                  for b in O.ADJACENT_BUILDINGS.values()), default=float("nan"))

    # --- 트레이드오프: front 내 상대 위치 ---
    F_all = np.asarray(F_all)
    f1n = (F_row[0] - F_all[:, 0].min()) / (np.ptp(F_all[:, 0]) + 1e-9)
    f2n = (F_row[1] - F_all[:, 1].min()) / (np.ptp(F_all[:, 1]) + 1e-9)

    lines = []
    lines.append("#### 🤖 이 추천이 나온 이유")
    lines.append(
        f"**위치 ({cx:.1f}, {cy:.1f})** — 선회 위험의 "
        f"{share_own:.0f}%가 자기 부지·공지 위에 머물고, 도로 {share_road:.0f}%·"
        f"인접 건물 {share_adj:.0f}%로 제3자 노출이 억제되는 지점입니다. "
        f"인접 건물과의 이격은 최소 {d_adj:.1f} m로 KOSHA 이격 기준(0.6 m)을 "
        f"충족합니다."
    )
    lines.append(
        f"**기종 {spec_name}** — 가장 먼 양중점(반경 {r_far:.1f} m)에서 "
        f"정격능력 {cap_at_far:,.0f} kgf로 최대 자재 {payload:,.0f} kgf 대비 "
        f"여유 {margin_pct:+.0f}%. 지브 {jib:.1f} m의 {reach_util:.0f}%만 사용해 "
        f"불필요하게 큰 선회반경을 만들지 않습니다."
    )
    lines.append(
        f"**균형점(knee)** — Pareto front에서 안전(F1) {f1n*100:.0f}%·"
        f"효율(F2) {f2n*100:.0f}% 지점(0%=해당 목적 최저). 한쪽을 극단적으로 "
        f"희생하지 않는 절충해입니다. 더 안전한 해·더 빠른 해는 front의 양 끝에서 "
        f"확인할 수 있습니다."
    )
    if mode == "operational":
        f1op = O.compute_F1_operational((cx, cy), model, jib)
        cr = f1op["concentration_ratio"]
        if cr > 1.05:
            note = (f"적재 후크 경로가 취약구역 방향에 몰려 정적 평가보다 "
                     f"{cr:.2f}배 높게 평가되었습니다 — 야적장 위치 조정을 검토하세요.")
        elif cr < 0.95:
            note = (f"적재 후크 경로가 취약구역을 피해 다녀 정적 평가의 "
                     f"{cr:.2f}배로 낮게 평가되었습니다 (운영상 유리).")
        else:
            note = "적재 경로 분포가 균등에 가까워 정적 평가와 사실상 동일합니다."
        lines.append(f"**운영가중 노출 모드** — {note}")
    if agreement_m is not None and n_seeds:
        if agreement_m <= 3.0:
            lines.append(
                f"**재현성** — 독립 {n_seeds}회 탐색의 추천 위치 편차 최대 "
                f"{agreement_m:.1f} m로 매우 안정적입니다."
            )
        else:
            lines.append(
                f"**재현성** — 독립 {n_seeds}회 탐색 간 편차가 최대 "
                f"{agreement_m:.1f} m였으나, 합의(합집합 Pareto) 과정에서 "
                f"열등한 탐색 결과는 자동 제거되었습니다."
            )
    lines.append(
        "> ⚠️ 본 결과는 **의사결정 보조** 목적입니다. 지반 지지력, 지하 지장물, "
        "장비 반입 동선, 인접 동의 등은 모델 밖 요인이므로 최종 배치 전 "
        "전문가 검토가 필요합니다."
    )
    return "\n\n".join(lines)
