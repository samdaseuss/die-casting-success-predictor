# styles/__init__.py
"""
다이캐스팅 품질 예측 대시보드 스타일 관리 패키지

이 패키지는 Streamlit 애플리케이션의 모든 스타일 관련 기능을 제공합니다.
- 전역 CSS 스타일
- 테마 관리
- 색상 팔레트
- 컴포넌트별 스타일
- 차트 스타일
- 페이지네이션 스타일
"""

from .style_manager import apply_global_style, get_theme_colors
from .chart_styles import (
    get_echarts_colors,
    create_control_chart_options,
    create_gauge_chart_options,
    create_status_html,
    create_mold_card_html,
    create_process_indicator_html,
    create_timer_html
)
from .pagination_styles import create_pagination_html

__all__ = [
    'apply_global_style',
    'get_theme_colors',
    'get_echarts_colors',
    'create_control_chart_options',
    'create_gauge_chart_options',
    'create_status_html',
    'create_mold_card_html',
    'create_process_indicator_html',
    'create_timer_html',
    'create_pagination_html'
]

__version__ = "2.0.0"