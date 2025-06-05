# app.py
import streamlit as st
import sys
import time
from pathlib import Path
import logging
from tabs import (
    input_perameter_m_t, analysis_m_t, monitoring_m_t, 
    realtime_manufacturing_m_t
)
from utils.data_utils import (
    load_data_from_file,
    save_snapshot_batch, prepare_postgresql_data, 
    read_data_from_test_py, save_data_to_file
)
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.append(str(project_root))

data_dir = project_root / "data"
snapshots_dir = project_root / "snapshots"

data_dir.mkdir(exist_ok=True)
snapshots_dir.mkdir(exist_ok=True)

DATA_FILE = data_dir / "collected_data.json"
TEST_PY_FILE = data_dir / "test.py"

def apply_global_style(dark_mode=False):
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
    
    st.markdown(f"""
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
        background: {"linear-gradient(135deg, #32d74b, #28ca42)" if dark_mode else "linear-gradient(135deg, #ff453a, #ff3b30)"};
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        box-shadow: 0 2px 8px {"rgba(50, 215, 75, 0.3)" if dark_mode else "rgba(255, 69, 58, 0.3)"};
        border: 2px solid {"rgba(50, 215, 75, 0.5)" if dark_mode else "rgba(255, 69, 58, 0.5)"};
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
    
    .stTabs [data-baseweb="tab-list"] {{
        background: {card_bg} !important;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
        border: 1px solid {border_color};
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600 !important;
        color: {text_secondary} !important;
        transition: all 0.2s ease;
        border: none !important;
    }}
    
    .stTabs [aria-selected="true"] {{
        background: {accent_color} !important;
        color: white !important;
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
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="다이캐스팅 품질 예측 대시보드",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_synchronized_start_time():
    if 'system_start_time' not in st.session_state:
        current_time = time.time()
        aligned_time = (int(current_time) // 30) * 30
        st.session_state.system_start_time = aligned_time
    return st.session_state.system_start_time

if 'data_collection_started' not in st.session_state:
    st.session_state.data_collection_started = False
if 'collected_data' not in st.session_state:
    st.session_state.collected_data = []
if 'current_status' not in st.session_state:
    st.session_state.current_status = {}
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = 0
if 'last_snapshot_time' not in st.session_state:
    st.session_state.last_snapshot_time = time.time()
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
if 'ng_history' not in st.session_state:
    st.session_state.ng_history = []


class RealTimeDataManager:    
    @staticmethod
    def initialize_session_state():
        defaults = {
            'ng_history': [],
            'collected_data': [],
            'control_chart_data': RealTimeDataManager._generate_initial_chart_data(),
            'realtime_buffer': deque(maxlen=100),
            'last_chart_update': time.time(),
            'chart_update_interval': 180,
            'data_collection_started': False,
            'current_status': {},
            'last_collected_id': None
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def _generate_initial_chart_data():
        np.random.seed(42)
        base_rate = 5.0
        time_points = [datetime.now() - timedelta(hours=29-i) for i in range(30)]
        
        defect_rates = []
        for i in range(30):
            trend = 0.1 * i
            noise = np.random.normal(0, 1.5)
            special_cause = 3.0 if i in [15, 20, 25] else 0
            rate = max(0, base_rate + trend + noise + special_cause)
            defect_rates.append(rate)
        
        return {
            'time_points': time_points,
            'defect_rates': defect_rates
        }
    
    @staticmethod
    def collect_realtime_data():
        current_data = st.session_state.get("current_status", {})
        
        if current_data and 'passorfail' in current_data:
            current_timestamp = datetime.now().isoformat()
            data_hash = hash(str(current_data))
            data_id = f"{current_timestamp}_{data_hash}"
            
            if st.session_state.get('last_collected_id') == data_id:
                return False
            
            data_point = {
                'timestamp': datetime.now(),
                'mold_code': current_data.get('mold_code', 0),
                'molten_temp': current_data.get('molten_temp', 0),
                'cast_pressure': current_data.get('cast_pressure', 0),
                'passorfail': current_data.get('passorfail', 'Pass'),
                'defect': 1 if current_data.get('passorfail') == 'Fail' else 0,
                'data_id': data_id,
                'original_timestamp': current_data.get('timestamp', '')
            }
            
            st.session_state.realtime_buffer.append(data_point)
            st.session_state.last_collected_id = data_id
            
            return True
        return False
    
    @staticmethod
    def calculate_defect_rate_from_buffer(time_window_minutes=60):
        if not st.session_state.realtime_buffer:
            return None
        
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=time_window_minutes)
        
        recent_data = [
            point for point in st.session_state.realtime_buffer 
            if point['timestamp'] >= cutoff_time
        ]
        
        if not recent_data:
            return None
        
        total_count = len(recent_data)
        defect_count = sum(point['defect'] for point in recent_data)
        defect_rate = (defect_count / total_count) * 100
        
        return {
            'timestamp': now,
            'defect_rate': defect_rate,
            'total_count': total_count,
            'defect_count': defect_count
        }
    
    @staticmethod
    def should_update_chart():
        current_time = time.time()
        last_update = st.session_state.get('last_chart_update', 0)
        interval = st.session_state.get('chart_update_interval', 180)
        
        return (current_time - last_update) >= interval
    
    @staticmethod
    def update_control_chart():
        if not st.session_state.realtime_buffer:
            return False
        
        defect_data = RealTimeDataManager.calculate_defect_rate_from_buffer()
        
        if defect_data is None:
            return False
        
        chart_data = st.session_state.control_chart_data
        chart_data['time_points'].append(defect_data['timestamp'])
        chart_data['defect_rates'].append(defect_data['defect_rate'])
        
        if len(chart_data['time_points']) > 30:
            chart_data['time_points'] = chart_data['time_points'][-30:]
            chart_data['defect_rates'] = chart_data['defect_rates'][-30:]
        
        RealTimeDataManager._recalculate_control_limits(chart_data)
        
        st.session_state.last_chart_update = time.time()
        
        return True
    
    @staticmethod
    def _recalculate_control_limits(chart_data):
        if len(chart_data['defect_rates']) < 5:
            return
        
        recent_rates = chart_data['defect_rates']
        mean_rate = np.mean(recent_rates)
        std_rate = np.std(recent_rates)
        
        chart_data['control_limits'] = {
            'mean': mean_rate,
            'std': std_rate,
            'ucl': mean_rate + 3 * std_rate,
            'lcl': max(0, mean_rate - 3 * std_rate),
            'usl': mean_rate + 2 * std_rate,
            'lsl': max(0, mean_rate - 2 * std_rate)
        }
    
    @staticmethod
    def save_buffer_to_file():
        if not st.session_state.realtime_buffer:
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = snapshots_dir / f"realtime_buffer_{timestamp}.json"
            
            buffer_data = []
            for point in st.session_state.realtime_buffer:
                serializable_point = point.copy()
                serializable_point['timestamp'] = point['timestamp'].isoformat()
                buffer_data.append(serializable_point)
            
            snapshots_dir.mkdir(exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(buffer_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            st.error(f"버퍼 저장 오류: {str(e)}")
            return False


def main():
    apply_global_style(st.session_state.dark_mode)
    
    system_status_class = "system-status-indicator online" if st.session_state.data_collection_started else "system-status-indicator offline"
    system_status_text = "시스템 가동중" if st.session_state.data_collection_started else "시스템 중지"
    
    # 헤더 컨트롤과 토글을 위한 컬럼 레이아웃
    header_col1, header_col2 = st.columns([8, 2])
    
    with header_col1:
        # 시각적 표시용 헤더 컨트롤
        st.markdown(f'''
        <div class="header-controls">
            <div class="{system_status_class}">{system_status_text}</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with header_col2:
        # 다크모드 토글을 오른쪽 상단에 배치
        dark_mode_toggle = st.toggle("", value=st.session_state.dark_mode, key="header_dark_toggle")
        if dark_mode_toggle != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode_toggle
            st.rerun()
    
    with st.sidebar:
        st.markdown("### 데이터 수집")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("시작", use_container_width=True, disabled=st.session_state.data_collection_started):
                st.session_state.data_collection_started = True
                st.session_state.collected_data = load_data_from_file()
                get_synchronized_start_time()
                st.success("시작됨!")
                time.sleep(1)
                st.rerun()
        with col2:
            if st.button("중지", use_container_width=True, disabled=not st.session_state.data_collection_started):
                st.session_state.data_collection_started = False
                st.success("중지됨!")
                time.sleep(1)
                st.rerun()
        st.markdown("---")

        st.markdown("### 시스템 제어")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("수동 데이터 읽기", use_container_width=True):
                with st.spinner("데이터 읽는 중..."):
                    try:
                        new_data = read_data_from_test_py()
                        if new_data:
                            prev_buffer_size = len(st.session_state.get('realtime_buffer', []))
                            prev_collected_count = len(st.session_state.get('collected_data', []))
                            
                            st.session_state.current_status = new_data
                            st.session_state.collected_data.append(new_data)
                            save_data_to_file(st.session_state.collected_data)
                            
                            collected = RealTimeDataManager.collect_realtime_data()
                            current_buffer_size = len(st.session_state.get('realtime_buffer', []))
                            current_collected_count = len(st.session_state.get('collected_data', []))
                            
                            st.success(f"""데이터 수집 완료!
                            - 수집된 데이터: {current_collected_count}개 (이전: {prev_collected_count}개)
                            - 실시간 버퍼: {current_buffer_size}개 (이전: {prev_buffer_size}개)
                            - 버퍼 추가 여부: {'성공' if collected else '중복/실패'}""")
                            
                            with st.expander("수집된 데이터 내용"):
                                st.json(new_data)
                            
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.error("데이터를 읽어올 수 없습니다.")
                    except Exception as e:
                        st.error(f"데이터 읽기 오류: {str(e)}")
                        st.write(f"오류 상세: {e}")

        with col_btn2:
            if st.button("즉시 데이터 저장", use_container_width=True):
                if st.session_state.collected_data:
                    with st.spinner("저장 중..."):
                        try:
                            save_snapshot_batch(st.session_state.collected_data)
                            st.session_state.last_snapshot_time = time.time()
                            st.success("데이터가 즉시 저장되었습니다!")
                        except Exception as e:
                            st.error(f"저장 오류: {str(e)}")
                else:
                    st.warning("저장할 데이터가 없습니다.")

        if st.button("관리도 데이터 갱신", use_container_width=True):
            with st.spinner("관리도 데이터 갱신 중..."):
                try:
                    if RealTimeDataManager.update_control_chart():
                        RealTimeDataManager.save_buffer_to_file()
                        st.success("관리도 데이터가 갱신되었습니다!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("갱신할 데이터가 없습니다.")
                except Exception as e:
                    st.error(f"관리도 데이터 갱신 오류: {str(e)}")

        st.markdown("---")
        
        st.markdown("### 새로고침 설정")
        auto_refresh = st.checkbox("자동 새로고침 (3초)", value=True)
        
        st.markdown("---")
        
        st.markdown("### 데이터 관리")
        if st.button("전체 데이터 초기화", use_container_width=True):
            if st.session_state.data_collection_started:
                st.error("시스템을 먼저 중지해주세요!")
            else:
                st.session_state.collected_data = []
                st.session_state.current_status = {}
                st.session_state.last_snapshot_time = time.time()
                st.session_state.last_update_time = 0
                if 'system_start_time' in st.session_state:
                    del st.session_state.system_start_time
                if DATA_FILE.exists():
                    DATA_FILE.unlink()
                for snapshot_file in snapshots_dir.glob("*.json"):
                    snapshot_file.unlink()
                st.success("초기화 완료!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("### 시스템 정보")
        st.info(f"데이터 소스\n`{TEST_PY_FILE.name}`")
        
        total_data = len(st.session_state.collected_data)
        st.metric("수집된 데이터", f"{total_data:,}개")
        
        snapshot_count = len(list(snapshots_dir.glob("*snapshot*.json")))
        st.metric("저장된 스냅샷", f"{snapshot_count}개")
        
        if st.session_state.data_collection_started:
            start_time = get_synchronized_start_time()
            current_time = time.time()
            time_in_cycle = (current_time - start_time) % 30
            next_collection_seconds = 30 - time_in_cycle
            
            time_since_last = current_time - st.session_state.last_update_time
            should_collect_cycle = time_in_cycle >= 28.0
            should_collect_time = time_since_last >= 25
            
            st.metric("다음 수집", f"{next_collection_seconds:.1f}초 후")
            
            with st.expander("수집 상태 디버깅"):
                st.write(f"주기 내 시간: {time_in_cycle:.1f}초")
                st.write(f"마지막 수집 후: {time_since_last:.1f}초")
                st.write(f"주기 조건: {should_collect_cycle}")
                st.write(f"시간 조건: {should_collect_time}")
                st.write(f"수집 준비: {should_collect_cycle or should_collect_time}")
        
        if st.session_state.data_collection_started:
            last_snapshot_minutes = (time.time() - st.session_state.last_snapshot_time) / 60
            next_snapshot_minutes = 15 - last_snapshot_minutes
            if next_snapshot_minutes > 0:
                st.metric("다음 저장", f"{next_snapshot_minutes:.1f}분 후")
            else:
                st.info("저장 예정")

    if st.session_state.data_collection_started:
        start_time = get_synchronized_start_time()
        current_time = time.time()
        
        time_in_cycle = (current_time - start_time) % 30
        
        should_collect = False
        
        if time_in_cycle >= 28.0:
            should_collect = True
        
        time_since_last = current_time - st.session_state.last_update_time
        if time_since_last >= 25:
            should_collect = True
        
        if should_collect:
            new_data = read_data_from_test_py()
            if new_data:
                st.session_state.collected_data.append(new_data)
                st.session_state.current_status = new_data
                save_data_to_file(st.session_state.collected_data)
                st.session_state.last_update_time = current_time
                logger.info(f"자동 데이터 수집됨: {len(st.session_state.collected_data)}개 총 레코드")
                
                try:
                    from tabs.realtime_manufacturing_m_t import RealTimeDataManager
                    collected = RealTimeDataManager.collect_realtime_data()
                    if collected:
                        logger.info("실시간 버퍼에 데이터 추가됨")
                except Exception as e:
                    logger.warning(f"실시간 버퍼 업데이트 실패: {str(e)}")
        
        if current_time - st.session_state.last_snapshot_time > 900:
            if st.session_state.collected_data:
                save_snapshot_batch(st.session_state.collected_data)
                st.session_state.last_snapshot_time = current_time
                logger.info("15분 누적데이터 저장 완료")
    
    st.markdown('<h2 class="main-header">다이캐스팅 품질 예측 대시보드</h1>', unsafe_allow_html=True)
    
    tabs = st.tabs([
        "실시간 현황", 
        "차트 모니터링", 
        "파라미터 입력",
        "데이터 분석"
    ])
    
    with tabs[0]:
        realtime_manufacturing_m_t.run()

    with tabs[1]:
        monitoring_m_t.run()
    
    with tabs[2]:
        input_perameter_m_t.run()
    
    with tabs[3]:
        analysis_m_t.run()
    
    if auto_refresh and st.session_state.data_collection_started:
        time.sleep(3)
        st.rerun()

if __name__ == "__main__":
    main()