"""v3 헤드리스 UI 테스트:
 (1) 기본 부팅(지도 위저드 모드) 예외 없음
 (2) 직접입력 모드 전환 → 야적장 입력 렌더 → 🚀 버튼 실제 클릭 E2E
 (3) 사이드바 갱신+자동선택 (v2 회귀)
"""
from streamlit.testing.v1 import AppTest
import sys, glob, os
sys.path.insert(0, ".")

for f in glob.glob("/tmp/custom_site_*.json"): os.remove(f)

# (1) 기본 부팅 — 지도 위저드가 기본 모드
at = AppTest.from_file("app.py", default_timeout=180)
at.run()
assert not at.exception, at.exception
n0 = len(at.sidebar.selectbox[0].options)
print(f"(1) boot OK — sites={n0}, 기본 입력모드 =", at.radio(key="nb_inputmode").value)

# (2) 직접입력 모드 → 야적장 입력 확인 → 현장 이름 바꾸고 🚀 클릭
at.radio(key="nb_inputmode").set_value("✍️ 직접 입력 (정밀 좌표)")
at.run(); assert not at.exception, at.exception
keys = [w.key for w in at.number_input]
assert "nb_yx" in keys and "nb_yy" in keys, "야적장 입력 누락"
at.text_input(key="nb_name").set_value("E2E현장")
at.number_input(key="nb_yx").set_value(-25.0)
at.run(); assert not at.exception, at.exception
btn = [b for b in at.button if "이 현장으로 최적화하기" in (b.label or "")]
assert btn, "🚀 버튼 못 찾음"
btn[0].click()
at.run(); assert not at.exception, at.exception
sb = at.sidebar.selectbox[0]
print(f"(2) 🚀 E2E — sites={len(sb.options)}, selected={sb.value!r}")
assert sb.value == "⭐ E2E현장", "폼 저장 후 자동선택 실패"
import json
saved = sorted(glob.glob("/tmp/custom_site_*.json"))[-1]
yard = json.load(open(saved))["lift_points"]["material_yard"]
assert yard == [-25.0, 0.0], f"야적장 입력 미반영: {yard}"
print(f"    저장된 야적장 = {yard} ✅ (UI 입력 반영)")

# (3) v2 사이드바 회귀 (파일+pending 키 시뮬레이션)
import time
demo = json.load(open(saved)); demo["metadata"]["display_name"] = "테스트현장"
json.dump(demo, open(f"/tmp/custom_site_{int(time.time())+1}.json","w",encoding="utf-8"), ensure_ascii=False)
at.session_state["pending_site_sel"] = "⭐ 테스트현장"
at.run(); assert not at.exception, at.exception
sb = at.sidebar.selectbox[0]
assert "⭐ 테스트현장" in sb.options and sb.value == "⭐ 테스트현장"
print(f"(3) 사이드바 회귀 OK — sites={len(sb.options)}, selected={sb.value!r}")
print("\n✅ v3 AppTest 전체 통과")
