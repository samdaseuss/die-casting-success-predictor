# styles/style_manager.py
import streamlit as st

def apply_global_style(dark_mode=False):
    """전역 스타일을 적용하는 함수"""
    
    if dark_mode:
        bg_color = "#1c1c1e"
        secondary_bg = "#2c2c2e"
        card_bg = "#2c2c2e"
        text_primary = "#ffffff"
        text_secondary = "#98989d"
        accent_color = "#0a84ff"
        success_color = "#32d74b"
        warning_color = "#ff9f0a"
        error_color = "#ff453a"
        border_color = "#48484a"
        input_bg = "#2c2c2e"
        sidebar_bg = "#1c1c1e"
        tab_inactive_color = "#98989d"
        tab_active_color = "#ffffff"
    else:
        bg_color = "#ffffff"
        secondary_bg = "#f8f9fa"
        card_bg = "#ffffff"
        text_primary = "#1d1d1f"
        text_secondary = "#6e6e73"
        accent_color = "#007aff"
        success_color = "#34c759"
        warning_color = "#ff9500"
        error_color = "#ff3b30"
        border_color = "#e5e5e7"
        input_bg = "#ffffff"
        sidebar_bg = "#f8f9fa"
        tab_inactive_color = "#6e6e73"  # 라이트 모드에서 비활성 탭 색상
        tab_active_color = "#ffffff"   # 라이트 모드에서 활성 탭 색상 (흰색 유지)
    
    # 전체 CSS 스타일 정의
    css_styles = f"""
    <style>
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_primary} !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    
    /* Deploy 버튼 숨기기 */
    [data-testid="stToolbar"] {{
        display: none !important;
    }}
    
    .stDeployButton {{
        display: none !important;
    }}
    
    button[title="Deploy this app"] {{
        display: none !important;
    }}
    
    [data-testid="stHeader"] .css-18ni7ap,
    [data-testid="stHeader"] .css-1dp5vir,
    [data-testid="stHeader"] .css-164nlkn {{
        display: none !important;
    }}
    
    /* 헤더 영역 커스터마이징 */
    [data-testid="stHeader"] {{
        background-color: {bg_color} !important;
        height: 60px !important;
        position: relative !important;
    }}
    
    /* 헤더 우상단 컨트롤 영역 */
    .header-controls {{
        position: fixed;
        top: 15px;
        right: 20px;
        z-index: 999999;
        display: flex;
        gap: 15px;
        align-items: center;
        background: {bg_color};
        padding: 5px;
        border-radius: 25px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}
    
    /* 시스템 상태 표시 */
    .system-status-indicator {{
        background: {"linear-gradient(135deg, #32d74b, #28ca42)" if st.session_state.get('data_collection_started', False) else "linear-gradient(135deg, #ff453a, #ff3b30)"};
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        box-shadow: 0 2px 8px {"rgba(50, 215, 75, 0.3)" if st.session_state.get('data_collection_started', False) else "rgba(255, 69, 58, 0.3)"};
        border: 2px solid {"rgba(50, 215, 75, 0.5)" if st.session_state.get('data_collection_started', False) else "rgba(255, 69, 58, 0.5)"};
        min-width: 100px;
        text-align: center;
    }}
    
    .system-status-indicator.online {{
        background: linear-gradient(135deg, #32d74b, #28ca42);
        border-color: rgba(50, 215, 75, 0.5);
        box-shadow: 0 2px 8px rgba(50, 215, 75, 0.3);
    }}
    
    .system-status-indicator.offline {{
        background: linear-gradient(135deg, #ff453a, #ff3b30);
        border-color: rgba(255, 69, 58, 0.5);
        box-shadow: 0 2px 8px rgba(255, 69, 58, 0.3);
    }}
    
    /* 헤더 스타일 수정 */
    header[data-testid="stHeader"] {{
        background-color: {bg_color} !important;
        color: {text_primary} !important;
    }}
    
    header[data-testid="stHeader"] * {{
        color: {text_primary} !important;
    }}
    
    [data-testid="stHeader"] .main-header {{
        color: {text_primary} !important;
    }}
    
    .main .block-container {{
        padding: 1.5rem 1rem;
        background: {bg_color} !important;
        max-width: 1200px;
    }}
    
    .css-1d391kg, [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}
    
    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: {text_primary} !important;
    }}
    
    [data-testid="metric-container"] {{
        background: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }}
    
    [data-testid="metric-container"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    
    [data-testid="metric-container"] [data-testid="metric-value"] {{
        color: {text_primary} !important;
        font-weight: 700;
    }}
    
    [data-testid="metric-container"] [data-testid="metric-label"] {{
        color: {text_secondary} !important;
        font-weight: 500;
    }}
    
    /* 강화된 버튼 스타일 - 모든 가능한 선택자 포함 */
    .stButton > button,
    .stButton button,
    button[kind="primary"],
    button[kind="secondary"],
    div[data-testid="stButton"] > button,
    .element-container .stButton > button {{
        background: {accent_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0,122,255,0.3) !important;
        text-decoration: none !important;
    }}
    
    .stButton > button:hover,
    .stButton button:hover,
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover,
    div[data-testid="stButton"] > button:hover,
    .element-container .stButton > button:hover {{
        background: {accent_color}dd !important;
        color: white !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,122,255,0.4) !important;
    }}
    
    .stButton > button:focus,
    .stButton button:focus,
    button[kind="primary"]:focus,
    button[kind="secondary"]:focus,
    div[data-testid="stButton"] > button:focus,
    .element-container .stButton > button:focus {{
        outline: none !important;
        color: white !important;
        background: {accent_color} !important;
        box-shadow: 0 0 0 3px {accent_color}40 !important;
    }}
    
    .stButton > button:active,
    .stButton button:active,
    button[kind="primary"]:active,
    button[kind="secondary"]:active,
    div[data-testid="stButton"] > button:active,
    .element-container .stButton > button:active {{
        color: white !important;
        background: {accent_color}cc !important;
        transform: translateY(0px) !important;
    }}
    
    /* 버튼 내부 텍스트 요소들 */
    .stButton > button span,
    .stButton > button div,
    .stButton > button p,
    .stButton button span,
    .stButton button div,
    .stButton button p,
    button[kind="primary"] span,
    button[kind="primary"] div,
    button[kind="primary"] p,
    button[kind="secondary"] span,
    button[kind="secondary"] div,
    button[kind="secondary"] p {{
        color: white !important;
    }}
    
    /* 비활성화된 버튼 스타일 */
    .stButton > button:disabled,
    .stButton button:disabled,
    button[kind="primary"]:disabled,
    button[kind="secondary"]:disabled {{
        background: {text_secondary} !important;
        color: white !important;
        opacity: 0.6 !important;
        cursor: not-allowed !important;
        transform: none !important;
        box-shadow: none !important;
    }}
    
    .stButton > button:disabled span,
    .stButton > button:disabled div,
    .stButton > button:disabled p,
    .stButton button:disabled span,
    .stButton button:disabled div,
    .stButton button:disabled p {{
        color: white !important;
    }}
    
    /* 토글 스타일 커스터마이징 */
    .stToggle > div {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    
    .stToggle > div > div {{
        order: 2;
    }}
    
    .stToggle > div > label {{
        order: 1;
        font-size: 14px !important;
        font-weight: 600 !important;
        color: {text_primary} !important;
        margin: 0 !important;
    }}
    
    /* 탭 스타일 수정 - 색상 문제 해결 */
    .stTabs [data-baseweb="tab-list"] {{
        background: {card_bg} !important;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
        border: 1px solid {border_color};
    }}
    
    /* 비활성 탭 스타일 */
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600 !important;
        color: {tab_inactive_color} !important;
        transition: all 0.2s ease;
        border: none !important;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(0, 122, 255, 0.1) !important;
        color: {tab_inactive_color} !important;
    }}
    
    /* 활성 탭 스타일 - 라이트 모드에서 흰색 글자 보장 */
    .stTabs [aria-selected="true"] {{
        background: {accent_color} !important;
        color: {tab_active_color} !important;
    }}
    
    .stTabs [aria-selected="true"]:hover {{
        background: {accent_color} !important;
        color: {tab_active_color} !important;
    }}
    
    /* 탭 내부 텍스트 요소들 - 더 구체적인 선택자로 강제 적용 */
    .stTabs [data-baseweb="tab"] > div,
    .stTabs [data-baseweb="tab"] > span,
    .stTabs [data-baseweb="tab"] > p,
    .stTabs [data-baseweb="tab"] div,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] p {{
        color: {tab_inactive_color} !important;
    }}
    
    /* 활성 탭의 모든 텍스트 요소 강제 흰색 적용 */
    .stTabs [aria-selected="true"] > div,
    .stTabs [aria-selected="true"] > span,
    .stTabs [aria-selected="true"] > p,
    .stTabs [aria-selected="true"] div,
    .stTabs [aria-selected="true"] span,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] * {{
        color: {tab_active_color} !important;
    }}
    
    /* 추가 보장을 위한 !important 강화 */
    .stTabs [aria-selected="true"] {{
        background: {accent_color} !important;
    }}
    
    .stTabs [aria-selected="true"] * {{
        color: {tab_active_color} !important;
        font-weight: 600 !important;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        color: {text_primary} !important;
        font-weight: 600;
    }}
    
    p, div, span, label {{
        color: {text_primary} !important;
    }}
    
    .stSelectbox > div > div {{
        background-color: {input_bg} !important;
        border: 1px solid {border_color} !important;
        color: {text_primary} !important;
    }}
    
    .stTextInput > div > div > input {{
        background-color: {input_bg} !important;
        border: 1px solid {border_color} !important;
        color: {text_primary} !important;
    }}
    
    .stNumberInput > div > div > input {{
        background-color: {input_bg} !important;
        border: 1px solid {border_color} !important;
        color: {text_primary} !important;
    }}
    
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid {border_color};
    }}
    
    .stDataFrame [data-testid="stTable"] {{
        background-color: {card_bg} !important;
    }}
    
    .stDataFrame th {{
        background-color: {secondary_bg} !important;
        color: {text_primary} !important;
        border-bottom: 1px solid {border_color} !important;
    }}
    
    .stDataFrame td {{
        background-color: {card_bg} !important;
        color: {text_primary} !important;
        border-bottom: 1px solid {border_color} !important;
    }}
    
    .stSuccess {{
        background: rgba(52, 199, 89, 0.1) !important;
        border: 1px solid {success_color} !important;
        border-radius: 8px;
        color: {success_color} !important;
    }}
    
    .stError {{
        background: rgba(255, 59, 48, 0.1) !important;
        border: 1px solid {error_color} !important;
        border-radius: 8px;
        color: {error_color} !important;
    }}
    
    .stWarning {{
        background: rgba(255, 149, 0, 0.1) !important;
        border: 1px solid {warning_color} !important;
        border-radius: 8px;
        color: {warning_color} !important;
    }}
    
    .stInfo {{
        background: rgba(0, 122, 255, 0.1) !important;
        border: 1px solid {accent_color} !important;
        border-radius: 8px;
        color: {accent_color} !important;
    }}
    
    .status-running {{
        background: rgba(52, 199, 89, 0.15) !important;
        color: {success_color} !important;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
        margin: 10px 0;
        border: 1px solid {success_color};
    }}
    
    .status-stopped {{
        background: rgba(255, 59, 48, 0.15) !important;
        color: {error_color} !important;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
        margin: 10px 0;
        border: 1px solid {error_color};
    }}
    
    .stCheckbox > label {{
        color: {text_primary} !important;
    }}
    
    .stCheckbox > label > div {{
        color: {text_primary} !important;
    }}
    
    .stSelectbox > label {{
        color: {text_primary} !important;
    }}
    
    .stSpinner {{
        color: {accent_color} !important;
    }}
    
    .realtime-status {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background: rgba(110, 110, 115, 0.1) !important;
        border-radius: 8px;
        margin: 8px 0;
        font-size: 11px;
        color: {text_secondary} !important;
    }}
    
    .realtime-status .status-item {{
        display: flex;
        align-items: center;
        gap: 4px;
    }}
    
    .realtime-status .status-value {{
        font-weight: 600;
        color: {accent_color} !important;
    }}
    
    .mold-status-card {{
        background: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        position: relative;
    }}
    
    .mold-status-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }}
    
    .mold-status-card.active {{
        border: 3px solid {accent_color} !important;
        background: linear-gradient(135deg, {accent_color}15, {accent_color}08) !important;
        box-shadow: 0 8px 30px {accent_color}30;
        transform: scale(1.02);
    }}
    
    .mold-status-card.active::before {{
        content: 'LIVE';
        position: absolute;
        top: -10px;
        right: 15px;
        background: {success_color} !important;
        color: white !important;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        animation: pulse-live 2s infinite;
        box-shadow: 0 2px 8px {success_color}40;
    }}
    
    @keyframes pulse-live {{
        0%, 100% {{ transform: scale(1); opacity: 1; }}
        50% {{ transform: scale(1.05); opacity: 0.9; }}
    }}
    
    .mold-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 15px;
    }}
    
    .mold-title {{
        font-size: 18px;
        font-weight: 700;
        color: {text_primary} !important;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    
    .mold-badge {{
        background: {border_color} !important;
        color: {text_secondary} !important;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }}
    
    .mold-badge.active {{
        background: {accent_color} !important;
        color: white !important;
        animation: pulse-badge 2s infinite;
        box-shadow: 0 2px 8px {accent_color}40;
    }}
    
    @keyframes pulse-badge {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.9; transform: scale(1.05); }}
    }}
    
    .process-indicator {{
        display: flex;
        justify-content: space-around;
        align-items: center;
        padding: 30px 20px;
        background: {card_bg} !important;
        border-radius: 16px;
        margin: 20px 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        border: 1px solid {border_color} !important;
    }}
    
    .process-step {{
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        position: relative;
        flex: 1;
    }}
    
    .process-step:not(:last-child)::after {{
        content: '';
        position: absolute;
        top: 30px;
        right: -50%;
        width: 100%;
        height: 2px;
        background: {border_color} !important;
        z-index: 1;
    }}
    
    .process-step.completed:not(:last-child)::after {{
        background: {success_color} !important;
    }}
    
    .process-step.active:not(:last-child)::after {{
        background: {accent_color} !important;
    }}
    
    .step-icon {{
        width: 60px;
        height: 60px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        margin-bottom: 10px;
        transition: all 0.3s ease;
        z-index: 2;
        position: relative;
    }}
    
    .step-icon.active {{
        background: linear-gradient(135deg, {accent_color}, #5856d6) !important;
        color: white !important;
        transform: scale(1.1);
        box-shadow: 0 8px 20px rgba(0, 122, 255, 0.3);
        animation: pulse 2s infinite;
    }}
    
    .step-icon.completed {{
        background: {success_color} !important;
        color: white !important;
    }}
    
    .step-icon.inactive {{
        background: {border_color} !important;
        color: {text_secondary} !important;
    }}
    
    .step-label {{
        font-weight: 600;
        color: {text_primary} !important;
        margin-bottom: 5px;
        font-size: 14px;
    }}
    
    .step-label.active {{
        color: {accent_color} !important;
        font-weight: 700;
    }}
    
    .step-label.completed {{
        color: {success_color} !important;
    }}
    
    @keyframes pulse {{
        0% {{ transform: scale(1.1); }}
        50% {{ transform: scale(1.15); }}
        100% {{ transform: scale(1.1); }}
    }}
    
    /* 추가적인 버튼 스타일 강화 */
    [data-testid="stVerticalBlock"] .stButton > button,
    [data-testid="stHorizontalBlock"] .stButton > button,
    .row-widget .stButton > button {{
        background: {accent_color} !important;
        color: white !important;
        border: none !important;
    }}
    
    [data-testid="stVerticalBlock"] .stButton > button span,
    [data-testid="stHorizontalBlock"] .stButton > button span,
    .row-widget .stButton > button span {{
        color: white !important;
    }}
    </style>
    """
    
    # 스타일 적용
    st.markdown(css_styles, unsafe_allow_html=True)

def get_theme_colors(dark_mode=False):
    """테마별 색상 정보를 반환하는 함수"""
    
    if dark_mode:
        return {
            'bg_color': "#1c1c1e",
            'secondary_bg': "#2c2c2e",
            'card_bg': "#2c2c2e",
            'text_primary': "#ffffff",
            'text_secondary': "#98989d",
            'accent_color': "#0a84ff",
            'success_color': "#32d74b",
            'warning_color': "#ff9f0a",
            'error_color': "#ff453a",
            'border_color': "#48484a",
            'input_bg': "#2c2c2e",
            'sidebar_bg': "#1c1c1e"
        }
    else:
        return {
            'bg_color': "#ffffff",
            'secondary_bg': "#f8f9fa",
            'card_bg': "#ffffff",
            'text_primary': "#1d1d1f",
            'text_secondary': "#6e6e73",
            'accent_color': "#007aff",
            'success_color': "#34c759",
            'warning_color': "#ff9500",
            'error_color': "#ff3b30",
            'border_color': "#e5e5e7",
            'input_bg': "#ffffff",
            'sidebar_bg': "#f8f9fa"
        }