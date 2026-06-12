"""Headless UI test of the fixed sidebar flow using st.testing."""
from streamlit.testing.v1 import AppTest
import json, time, glob, os

at = AppTest.from_file("app.py", default_timeout=120)
at.run()
assert not at.exception, at.exception
names0 = at.sidebar.selectbox[0].options
print(f"run1: {len(names0)} sites, selected = {at.sidebar.selectbox[0].value!r}")

# simulate the ➕ tab save: write the file + set the pending keys like the button does
demo = {
 "metadata": {"site_id": "custom", "display_name": "테스트현장", "location": "", "official_area_m2": 1200.0},
 "coordinate_system": {"origin":"site centroid","x_axis":"East (+)","y_axis":"North (+)","unit":"meter"},
 "lot_vertices": [[-20,-15],[20,-15],[20,15],[-20,15]],
 "planned_building": {"footprint_box":[-12,-10,12,10],"height_m":30,"floors":10,"structure":"RC","use":"신축"},
 "adjacent_buildings": [{"key":"adj_0","name":"북측건물","footprint":{"type":"rect","cx":0,"cy":30,"w":24,"h":12},"height_m":18,"floors":6}],
 "roads": [{"key":"road_0","name":"서측도로","polygon":[[-31,-20],[-25,-20],[-25,20],[-31,20]],"width_m":6,"occupation_allowed":True}],
 "lift_points": {"building_grid":{"nx":5,"ny":5},"material_yard":[-23.0,0.0]},
 "search_bounds": {"x_range":[-27,27],"y_range":[-18,18]},
}
json.dump(demo, open(f"/tmp/custom_site_{int(time.time())}.json","w",encoding="utf-8"), ensure_ascii=False)
at.session_state["pending_site_sel"] = "⭐ 테스트현장"
at.session_state["flash_msg"] = "saved"
at.run()
assert not at.exception, at.exception
sb = at.sidebar.selectbox[0]
print(f"run2: {len(sb.options)} sites, selected = {sb.value!r}")
assert "⭐ 테스트현장" in sb.options, "new site missing from list (old cache bug)"
assert sb.value == "⭐ 테스트현장", "auto-select failed"
print("✅ sidebar refresh + auto-select verified")
