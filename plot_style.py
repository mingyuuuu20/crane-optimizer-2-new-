"""
================================================================================
plot_style.py — 앱 전체 matplotlib 공통 테마 (v3 품질 패스)
================================================================================
역할:
 1) 한글 폰트 자동 등록 — packages.txt(fonts-nanum)가 설치한 TTF를
    matplotlib 폰트 매니저에 직접 addfont (폰트 캐시 미갱신 문제 회피).
    ※ 기존 앱은 PDF 경로(report_figures)에만 폰트 지정이 있어, UI 그림은
      클라우드에서 한글이 □ 로 깨질 수 있었음 — 본 모듈이 근본 해결.
 2) 네이비·골드 팔레트와 spine/grid/legend 통일 — 히어로 헤더와 같은 톤.

사용: app 시작 시 `from plot_style import apply_style; apply_style()` 1회.
"""

import os

# 히어로/테마와 동일 계열
NAVY = "#16335B"
NAVY_LT = "#27497E"
GOLD = "#F2B705"
RED = "#C0392B"
GREEN = "#2E8B57"
GRAY = "#8A8A8A"
CYCLE = [NAVY, RED, GOLD, GREEN, "#6A5ACD", GRAY]

_FONT_PATHS = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",        # fonts-nanum (Streamlit Cloud)
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", # 일부 리눅스
]
_FAMILIES = ["NanumGothic", "Noto Sans CJK KR", "Malgun Gothic",
             "AppleGothic", "DejaVu Sans"]


def apply_style():
    import matplotlib as mpl
    from matplotlib import font_manager as fm
    from cycler import cycler

    for p in _FONT_PATHS:
        if os.path.exists(p):
            try:
                fm.fontManager.addfont(p)
            except Exception:
                pass

    mpl.rcParams.update({
        # 한글
        "font.family": "sans-serif",
        "font.sans-serif": _FAMILIES,
        "axes.unicode_minus": False,
        # 크기·해상도 (st.pyplot 선명도)
        "figure.dpi": 110,
        "font.size": 10.5,
        "axes.titlesize": 12.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        # 프레임·그리드
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#3A4456",
        "axes.linewidth": 0.9,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        # 색
        "axes.prop_cycle": cycler(color=CYCLE),
        # 범례
        "legend.frameon": True,
        "legend.framealpha": 0.92,
        "legend.edgecolor": "#D7DDE6",
        "legend.fontsize": 9.5,
        # 저장
        "savefig.bbox": "tight",
        "savefig.dpi": 150,
    })
