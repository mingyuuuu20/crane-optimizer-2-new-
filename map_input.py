"""
================================================================================
map_input.py — 지도 기반 현장 입력 위저드 (v3)
================================================================================
위성사진/일반지도 위에 [대지 → 신축건물 → 인접건물 → 도로 → 야적장] 을
순서대로 그리면, 위경도(WGS84)를 부지중심 로컬 좌표(m, East+/North+)로
자동 변환해 기존 site JSON 스키마 그대로 만들어 준다.

- API 키 불필요: OpenStreetMap + Esri World Imagery 타일 (무료 공개 타일)
- 좌표 변환: 부지중심 위도 기준 국지 등장방형 근사
    1° 위도 ≈ 111,132.92 − 559.82·cos2φ + 1.175·cos4φ (m)
    1° 경도 ≈ 111,412.84·cosφ − 93.5·cos3φ (m)
  부지 규모(수백 m)에서 오차는 cm 단위 — 모델 해상도 대비 무시 가능.
- 절대좌표 정확도는 지도 영상 정합(±수 m)에 좌우되나, 모델이 쓰는 것은
  대지·건물·도로 사이의 '상대 기하'이므로 의사결정 보조 목적에 충분.
  측량 좌표가 있으면 '직접 입력(정밀)' 모드를 사용할 것.
"""

import math
import streamlit as st

# 진주시청 부근 — 초기 지도 중심 기본값
_DEFAULT_CENTER = (35.1800, 128.1076)
_DEFAULT_ZOOM = 16

_ESRI_URL = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
             "World_Imagery/MapServer/tile/{z}/{y}/{x}")

STEPS = ["위치 찾기", "① 대지", "② 신축 건물", "③ 인접 건물",
         "④ 도로", "⑤ 야적장", "확인·저장"]

_GUIDE = {
    0: "현장 위치로 지도를 이동·확대하세요. 카카오/네이버 지도에서 우클릭으로 "
       "위경도를 복사해 아래에 붙여넣고 이동할 수도 있습니다. "
       "건물 윤곽이 또렷이 보일 때까지(줌 18~19) 확대 후 [다음].",
    1: "왼쪽 도구(⬠ 또는 ▭)로 **대지 경계를 1개** 그리세요. 꼭짓점을 차례로 "
       "찍고 첫 점을 다시 클릭하면 닫힙니다. 다시 그리면 마지막 것이 사용됩니다.",
    2: "**신축 건물 외곽을 1개** 그리세요(▭ 권장). 다각형이면 외접 사각형으로 "
       "변환됩니다. 아래에 높이·층수를 입력하세요.",
    3: "**인접 건물들**을 그리세요(여러 개 가능, 없으면 바로 [다음]). 각 건물은 "
       "외접 사각형으로 변환되며, 아래 표에서 이름·높이·층수를 수정하세요.",
    4: "**주변 도로**를 그리세요(여러 개 가능, 도로 형상 그대로 사용). "
       "아래 표에서 폭(m)을 수정하세요.",
    5: "📍 도구로 **자재 야적장 위치를 1곳** 찍으세요. 운영가중 노출(F1) 계산의 "
       "적재 경로 출발점입니다.",
    6: "변환 결과를 확인하고 저장하세요. 수정하려면 [← 이전]으로 해당 단계로 "
       "돌아가 다시 그리면 됩니다.",
}


# =============================================================================
# 좌표 변환 (순수 함수 — 단위 테스트 대상)
# =============================================================================
def m_per_deg(lat_deg: float):
    """위도 lat에서 위도/경도 1도의 미터 환산값."""
    phi = math.radians(lat_deg)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lng = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return m_lat, m_lng


def latlng_to_local(lat, lng, lat0, lng0):
    """(lat,lng) → 원점(lat0,lng0) 기준 로컬 좌표 (x=East+, y=North+) [m]."""
    m_lat, m_lng = m_per_deg(lat0)
    return (lng - lng0) * m_lng, (lat - lat0) * m_lat


def _feature_latlng(feat):
    """GeoJSON feature → [(lat,lng), ...].  GeoJSON 좌표는 [lng,lat] 순서."""
    g = feat.get("geometry", {})
    t = g.get("type")
    if t == "Polygon":
        ring = g["coordinates"][0]
        pts = [(c[1], c[0]) for c in ring]
        # 닫힘점 중복 제거
        if len(pts) >= 2 and pts[0] == pts[-1]:
            pts = pts[:-1]
        return pts
    if t == "Point":
        c = g["coordinates"]
        return [(c[1], c[0])]
    return []


def _centroid_latlng(pts):
    """소규모 다각형 무게중심 (shapely, (lng,lat) 평면 근사)."""
    from shapely.geometry import Polygon as _P
    if len(pts) >= 3:
        c = _P([(p[1], p[0]) for p in pts]).centroid
        return c.y, c.x          # (lat, lng)
    la = sum(p[0] for p in pts) / len(pts)
    lo = sum(p[1] for p in pts) / len(pts)
    return la, lo


def _to_local_list(pts, lat0, lng0, nd=2):
    return [[round(v, nd) for v in latlng_to_local(la, lo, lat0, lng0)]
            for la, lo in pts]


# =============================================================================
# 위저드 상태 → site JSON (순수 함수 — 단위 테스트 대상)
# =============================================================================
def build_site_obj_from_wizard(s: dict) -> dict:
    """
    s: {
      name, location, lot: [(lat,lng)..](≥3), bld: [(lat,lng)..](≥3),
      bld_h, bld_fl, adj: [{pts, name, height_m, floors}],
      roads: [{pts, name, width_m}], yard: (lat,lng), nx, ny
    }
    반환: 기존 ➕탭과 동일한 site JSON dict.
    """
    from shapely.geometry import Polygon as _P

    if not s.get("lot") or len(s["lot"]) < 3:
        raise ValueError("대지 다각형이 없습니다 (꼭짓점 3개 이상 필요).")
    if not s.get("bld") or len(s["bld"]) < 3:
        raise ValueError("신축 건물 외곽이 없습니다.")
    if not s.get("yard"):
        raise ValueError("야적장 위치가 없습니다.")

    lat0, lng0 = _centroid_latlng(s["lot"])
    lot = _to_local_list(s["lot"], lat0, lng0)
    lot_poly = _P(lot)
    if not lot_poly.is_valid or lot_poly.area <= 1.0:
        raise ValueError("대지 다각형이 유효하지 않습니다 (선이 교차하거나 "
                         "면적이 0에 가깝습니다). 다시 그려 주세요.")
    area_val = lot_poly.area

    bld = _to_local_list(s["bld"], lat0, lng0)
    bxs = [p[0] for p in bld]; bys = [p[1] for p in bld]
    bx0, by0, bx1, by1 = min(bxs), min(bys), max(bxs), max(bys)
    if (bx1 - bx0) < 2.0 or (by1 - by0) < 2.0:
        raise ValueError("신축 건물이 너무 작습니다 (한 변 2 m 이상 필요).")

    adj_list = []
    for i, a in enumerate(s.get("adj", [])):
        pl = _to_local_list(a["pts"], lat0, lng0)
        xs = [p[0] for p in pl]; ys = [p[1] for p in pl]
        cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2
        w = max(xs) - min(xs); h = max(ys) - min(ys)
        if w < 0.5 or h < 0.5:
            continue
        adj_list.append({
            "key": f"adj_{i}", "name": str(a.get("name", f"인접{i+1}")),
            "footprint": {"type": "rect", "cx": round(cx, 2), "cy": round(cy, 2),
                          "w": round(w, 2), "h": round(h, 2)},
            "height_m": float(a.get("height_m", 15.0)),
            "floors": int(a.get("floors", 5)),
        })

    road_list = []
    for i, r in enumerate(s.get("roads", [])):
        pl = _to_local_list(r["pts"], lat0, lng0)
        if len(pl) < 3:
            continue
        road_list.append({"key": f"road_{i}", "name": str(r.get("name", f"도로{i+1}")),
                          "polygon": pl, "width_m": float(r.get("width_m", 6.0)),
                          "occupation_allowed": True})

    yard = latlng_to_local(s["yard"][0], s["yard"][1], lat0, lng0)
    xs = [p[0] for p in lot]; ys = [p[1] for p in lot]

    return {
        "metadata": {"site_id": "custom",
                     "display_name": s.get("name", "내 현장"),
                     "location": s.get("location", ""),
                     "official_area_m2": round(area_val, 1),
                     "map_origin_latlng": [round(lat0, 6), round(lng0, 6)],
                     "input_method": "map_wizard_v3"},
        "coordinate_system": {"origin": "site centroid", "x_axis": "East (+)",
                              "y_axis": "North (+)", "unit": "meter"},
        "lot_vertices": lot,
        "planned_building": {"footprint_box": [round(bx0, 2), round(by0, 2),
                                               round(bx1, 2), round(by1, 2)],
                             "height_m": float(s.get("bld_h", 30.0)),
                             "floors": int(s.get("bld_fl", 10)),
                             "structure": "RC", "use": "신축"},
        "adjacent_buildings": adj_list,
        "roads": road_list,
        "lift_points": {"building_grid": {"nx": int(s.get("nx", 5)),
                                          "ny": int(s.get("ny", 5))},
                        "material_yard": [round(yard[0], 1), round(yard[1], 1)]},
        "search_bounds": {"x_range": [round(min(xs) - 7, 1), round(max(xs) + 7, 1)],
                          "y_range": [round(min(ys) - 3, 1), round(max(ys) + 3, 1)]},
    }


# =============================================================================
# folium 지도 구성
# =============================================================================
def _make_map(center, zoom, draw_mode=None, state=None):
    import folium
    from folium.plugins import Draw

    m = folium.Map(location=center, zoom_start=zoom, tiles=None,
                   control_scale=True, max_zoom=22)
    folium.TileLayer("OpenStreetMap", name="일반지도", max_zoom=19).add_to(m)
    folium.TileLayer(tiles=_ESRI_URL, attr="Esri — World Imagery",
                     name="위성사진", max_native_zoom=19, max_zoom=22).add_to(m)

    # 이미 확정된 도형은 색으로 표시 (현재 단계 도형은 Draw 레이어가 담당)
    if state:
        def _poly(pts, color, name, dash=None):
            folium.Polygon(locations=pts, color=color, weight=3,
                           fill=True, fill_opacity=0.18,
                           dash_array=dash, tooltip=name).add_to(m)
        if state.get("lot"):
            _poly(state["lot"], "#F2B705", "대지")
        if state.get("bld"):
            _poly(state["bld"], "#2E6FD8", "신축 건물", dash="6,6")
        for a in state.get("adj", []):
            _poly(a["pts"], "#D85C5C", a.get("name", "인접 건물"))
        for r in state.get("roads", []):
            _poly(r["pts"], "#8A8A8A", r.get("name", "도로"))
        if state.get("yard"):
            folium.Marker(location=state["yard"], tooltip="야적장",
                          icon=folium.Icon(color="green", icon="cube",
                                           prefix="fa")).add_to(m)

    if draw_mode:
        poly_on = draw_mode == "polygon"
        opts = {"polyline": False, "circle": False, "circlemarker": False,
                "polygon": {"showArea": True, "allowIntersection": False}
                if poly_on else False,
                "rectangle": poly_on,
                "marker": draw_mode == "marker"}
        Draw(export=False, draw_options=opts,
             edit_options={"edit": True, "remove": True}).add_to(m)

    folium.LayerControl(position="topright").add_to(m)
    return m


def _read_drawings(ret):
    """st_folium 반환값에서 (폴리곤 latlng 리스트들, 마커 latlng 리스트)."""
    polys, markers = [], []
    for f in (ret or {}).get("all_drawings") or []:
        pts = _feature_latlng(f)
        if not pts:
            continue
        if f.get("geometry", {}).get("type") == "Point":
            markers.append(pts[0])
        elif len(pts) >= 3:
            polys.append(pts)
    return polys, markers


# =============================================================================
# 위저드 본체
# =============================================================================
def render_map_wizard():
    """
    지도 입력 위저드 렌더. 사용자가 마지막 단계에서 [저장] 을 누르면
    site_obj(dict) 를 반환하고, 그 외에는 None 을 반환한다.
    저장·부지 선택은 호출 측(app.py)이 기존 폼과 동일 경로로 처리.
    """
    try:
        from streamlit_folium import st_folium
    except Exception:
        st.error("지도 입력에는 `streamlit-folium` 패키지가 필요합니다. "
                 "requirements.txt 에 folium / streamlit-folium 이 포함됐는지 "
                 "확인하세요.")
        return None

    ss = st.session_state
    ss.setdefault("mw_step", 0)
    ss.setdefault("mw_center", list(_DEFAULT_CENTER))
    ss.setdefault("mw_zoom", _DEFAULT_ZOOM)
    ss.setdefault("mw_state", {"adj": [], "roads": []})
    step = ss["mw_step"]
    state = ss["mw_state"]

    # ---- 진행 표시 ----
    st.progress((step) / (len(STEPS) - 1),
                text=f"단계 {step + 1}/{len(STEPS)} — {STEPS[step]}")
    st.info(_GUIDE[step], icon="🧭")

    # ---- 0단계 전용: 좌표로 이동 ----
    if step == 0:
        c1, c2, c3 = st.columns([1.2, 1.2, 1])
        glat = c1.number_input("위도", 33.0, 39.5,
                               float(ss["mw_center"][0]), format="%.6f",
                               key="mw_glat")
        glng = c2.number_input("경도", 124.0, 132.0,
                               float(ss["mw_center"][1]), format="%.6f",
                               key="mw_glng")
        c3.markdown("&nbsp;")
        if c3.button("📍 이 좌표로 이동", width="stretch", key="mw_goto"):
            ss["mw_center"] = [glat, glng]
            ss["mw_zoom"] = 18
            st.rerun()

    # ---- 지도 ----
    draw_mode = (None if step in (0, 6)
                 else "marker" if step == 5 else "polygon")
    fmap = _make_map(ss["mw_center"], ss["mw_zoom"], draw_mode, state)
    ret = st_folium(fmap, key=f"mw_map_{step}", height=520,
                    use_container_width=True,
                    returned_objects=["all_drawings", "center", "zoom"])
    if ret:
        if ret.get("center"):
            ss["mw_center"] = [ret["center"]["lat"], ret["center"]["lng"]]
        if ret.get("zoom"):
            ss["mw_zoom"] = ret["zoom"]
    polys, markers = _read_drawings(ret)

    # ---- 단계별 부가 입력 ----
    import pandas as pd
    if step == 2:
        h1, h2 = st.columns(2)
        state["bld_h"] = h1.number_input("건물 높이 (m)", 3.0, 300.0,
                                         float(state.get("bld_h", 30.0)), 1.0,
                                         key="mw_bh")
        state["bld_fl"] = h2.number_input("층수", 1, 80,
                                          int(state.get("bld_fl", 10)), 1,
                                          key="mw_bfl")
    elif step == 3 and polys:
        meta = state.get("adj_meta", [])
        rows = [{"이름": (meta[i]["name"] if i < len(meta) else f"인접{i+1}"),
                 "높이_m": (meta[i]["height_m"] if i < len(meta) else 15.0),
                 "층수": (meta[i]["floors"] if i < len(meta) else 5)}
                for i in range(len(polys))]
        edited = st.data_editor(pd.DataFrame(rows), key="mw_adj_meta",
                                hide_index=True, width="stretch")
        state["adj_meta"] = [{"name": str(r["이름"]),
                              "height_m": float(r["높이_m"]),
                              "floors": int(r["층수"])}
                             for _, r in edited.iterrows()]
    elif step == 4 and polys:
        meta = state.get("road_meta", [])
        rows = [{"이름": (meta[i]["name"] if i < len(meta) else f"도로{i+1}"),
                 "폭_m": (meta[i]["width_m"] if i < len(meta) else 6.0)}
                for i in range(len(polys))]
        edited = st.data_editor(pd.DataFrame(rows), key="mw_road_meta",
                                hide_index=True, width="stretch")
        state["road_meta"] = [{"name": str(r["이름"]),
                               "width_m": float(r["폭_m"])}
                              for _, r in edited.iterrows()]

    # ---- 마지막 단계: 변환 미리보기 + 저장 ----
    site_obj_ready = None
    if step == 6:
        c1, c2 = st.columns(2)
        state["name"] = c1.text_input("현장 이름", state.get("name", "내 현장"),
                                      key="mw_name")
        state["location"] = c2.text_input("위치(주소, 선택)",
                                          state.get("location", ""),
                                          key="mw_loc")
        g1, g2 = st.columns(2)
        state["nx"] = g1.number_input("양중점 격자 nx", 3, 9,
                                      int(state.get("nx", 5)), key="mw_nx")
        state["ny"] = g2.number_input("양중점 격자 ny", 3, 9,
                                      int(state.get("ny", 5)), key="mw_ny")
        try:
            obj = build_site_obj_from_wizard(state)
            _preview_local(obj)
            st.metric("대지면적 (지도 측정)",
                      f"{obj['metadata']['official_area_m2']:.0f} m²")
            st.caption("⚠️ 지도 기반 좌표의 절대 정확도는 영상 정합에 따라 ±수 m "
                       "수준입니다. 모델이 사용하는 대지·건물·도로 간 상대 기하에는 "
                       "충분하며, 측량 좌표가 있으면 '직접 입력(정밀)'을 쓰세요.")
            if st.button("🚀 저장하고 이 현장으로 최적화하기", type="primary",
                         width="stretch", key="mw_save"):
                site_obj_ready = obj
        except Exception as e:
            st.error(f"변환 불가: {e}")

    # ---- 이전/다음 ----
    st.divider()
    b1, b2, b3 = st.columns([1, 1, 4])
    if b1.button("← 이전", disabled=(step == 0), key="mw_prev",
                 width="stretch"):
        ss["mw_step"] = max(0, step - 1)
        st.rerun()

    nxt_ok, why = _can_advance(step, state, polys, markers)
    if b2.button("다음 →", disabled=not nxt_ok, key="mw_next",
                 width="stretch", type="secondary"):
        _commit_step(step, state, polys, markers)
        ss["mw_step"] = step + 1
        st.rerun()
    if not nxt_ok and why and step < 6:
        b3.caption(f"➡ {why}")
    if b3.button("⟲ 처음부터 다시", key="mw_reset"):
        for k in ("mw_step", "mw_state"):
            ss.pop(k, None)
        st.rerun()

    return site_obj_ready


def _can_advance(step, state, polys, markers):
    if step == 0:
        return True, ""
    if step == 1:
        ok = bool(polys) or bool(state.get("lot"))
        return ok, "대지 다각형을 1개 그려야 합니다."
    if step == 2:
        ok = bool(polys) or bool(state.get("bld"))
        return ok, "신축 건물 외곽을 1개 그려야 합니다."
    if step in (3, 4):
        return True, ""          # 인접/도로는 0개 허용
    if step == 5:
        ok = bool(markers) or bool(state.get("yard"))
        return ok, "야적장 위치를 📍로 찍어야 합니다."
    return False, ""             # 6단계는 저장 버튼으로 종료


def _commit_step(step, state, polys, markers):
    """[다음] 클릭 시 현재 단계 도형을 상태에 반영.
    새로 그린 게 있으면 교체, 없으면 기존 유지."""
    if step == 1 and polys:
        state["lot"] = polys[-1]
    elif step == 2 and polys:
        state["bld"] = polys[-1]
    elif step == 3 and polys:
        meta = state.get("adj_meta", [])
        state["adj"] = [{"pts": p,
                         **(meta[i] if i < len(meta)
                            else {"name": f"인접{i+1}", "height_m": 15.0,
                                  "floors": 5})}
                        for i, p in enumerate(polys)]
    elif step == 4 and polys:
        meta = state.get("road_meta", [])
        state["roads"] = [{"pts": p,
                           **(meta[i] if i < len(meta)
                              else {"name": f"도로{i+1}", "width_m": 6.0})}
                          for i, p in enumerate(polys)]
    elif step == 5 and markers:
        state["yard"] = markers[-1]


def _preview_local(obj):
    """변환된 로컬 좌표 미리보기 (기존 ➕탭 미리보기와 동일 스타일)."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPoly, Rectangle as Rect

    fig, ax = plt.subplots(figsize=(6.2, 6.2))
    for r in obj["roads"]:
        ax.add_patch(MplPoly(r["polygon"], fc="#EEEEEE", ec="#999",
                             lw=0.8, zorder=1))
    for a in obj["adjacent_buildings"]:
        f = a["footprint"]
        ax.add_patch(Rect((f["cx"] - f["w"] / 2, f["cy"] - f["h"] / 2),
                          f["w"], f["h"], fc="#E8B4B4", ec="k", lw=1,
                          alpha=0.55, zorder=2))
        ax.text(f["cx"], f["cy"], a["name"][:8], ha="center", va="center",
                fontsize=7, fontweight="bold")
    ax.add_patch(MplPoly(obj["lot_vertices"], fc="#FFF3CD", ec="k",
                         lw=2.2, zorder=3))
    bx0, by0, bx1, by1 = obj["planned_building"]["footprint_box"]
    ax.add_patch(Rect((bx0, by0), bx1 - bx0, by1 - by0, fc="none",
                      ec="#2E6FD8", lw=1.6, zorder=4))
    yx, yy = obj["lift_points"]["material_yard"]
    ax.plot([yx], [yy], marker="*", ms=16, color="#2E8B57", zorder=5)
    ax.annotate("야적장", (yx, yy), textcoords="offset points",
                xytext=(6, 6), fontsize=8, color="#2E8B57",
                fontweight="bold",
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2))
    ax.text((bx0 + bx1) / 2, (by0 + by1) / 2, "신축 건물", ha="center",
            va="center", fontsize=8.5, color="#2E6FD8", fontweight="bold")
    ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xlabel("East (m)"); ax.set_ylabel("North (m)")
    xs = [p[0] for p in obj["lot_vertices"]]
    ys = [p[1] for p in obj["lot_vertices"]]
    ax.set_xlim(min(xs) - 18, max(xs) + 18)
    ax.set_ylim(min(ys) - 18, max(ys) + 18)
    st.pyplot(fig); plt.close(fig)
