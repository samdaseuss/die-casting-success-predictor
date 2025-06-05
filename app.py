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
from variables import fields_input

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
        # 라이트 모드 색상
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
    /* 전체 앱 스타일 */
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_primary} !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    
    /* 메인 컨테이너 */
    .main .block-container {{
        padding: 1.5rem 1rem;
        background: {bg_color} !important;
        max-width: 1200px;
    }}
    
    /* 사이드바 스타일 */
    .css-1d391kg, [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}
    
    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: {text_primary} !important;
    }}
    
    /* 메트릭 컨테이너 */
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
    
    /* 버튼 스타일 */
    .stButton > button {{
        background: {accent_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600 !important;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,122,255,0.3);
    }}
    
    .stButton > button:hover {{
        background: {accent_color}dd !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,122,255,0.4);
    }}
    
    .stButton > button:focus {{
        outline: none !important;
        box-shadow: 0 0 0 3px {accent_color}40 !important;
    }}
    
    /* 탭 스타일 */
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
    
    /* 텍스트 요소 */
    h1, h2, h3, h4, h5, h6 {{
        color: {text_primary} !important;
        font-weight: 600;
    }}
    
    p, div, span, label {{
        color: {text_primary} !important;
    }}
    
    /* 입력 필드 */
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
    
    /* 데이터프레임 */
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
    
    /* 알림 스타일 */
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
    
    /* 상태 인디케이터 */
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
    
    /* 체크박스 */
    .stCheckbox > label {{
        color: {text_primary} !important;
    }}
    
    .stCheckbox > label > div {{
        color: {text_primary} !important;
    }}
    
    /* 선택박스 라벨 */
    .stSelectbox > label {{
        color: {text_primary} !important;
    }}
    
    /* 로딩 스피너 */
    .stSpinner {{
        color: {accent_color} !important;
    }}
    
    /* 실시간 상태 표시 (작고 간단하게) */
    .realtime-status {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background: rgba({text_secondary.replace("#", "").replace("98989d", "152, 152, 157") if dark_mode else text_secondary.replace("#", "").replace("6e6e73", "110, 110, 115")}, 0.1) !important;
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
    
    /* 몰드 상태 카드 스타일 */
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
        content: '● LIVE';
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
    
    /* 공정 시각화 스타일 */
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
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="다이캐스팅 품질 예측 대시보드",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_synchronized_start_time():
    """시스템 시작 시간을 30초 주기로 동기화"""
    if 'system_start_time' not in st.session_state:
        # 현재 시간을 30초 단위로 맞춤
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

def main():
    apply_global_style(st.session_state.dark_mode)
    
    with st.sidebar:
        st.markdown("### 시스템 제어")
        
        st.markdown("---")
        st.markdown("### 테마 설정")
        
        theme_col1, theme_col2 = st.columns(2)
        with theme_col1:
            if st.button("라이트", use_container_width=True, disabled=not st.session_state.dark_mode):
                st.session_state.dark_mode = False
                st.rerun()
        
        with theme_col2:
            if st.button("다크", use_container_width=True, disabled=st.session_state.dark_mode):
                st.session_state.dark_mode = True
                st.rerun()
        
        st.markdown("---")
        
        # 데이터 수집 시작/중지 버튼
        st.markdown("### 데이터 수집")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("시작", use_container_width=True, disabled=st.session_state.data_collection_started):
                st.session_state.data_collection_started = True
                st.session_state.collected_data = load_data_from_file()
                
                # 시스템 시작 시간을 30초 주기로 동기화
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
        
        if st.session_state.data_collection_started:
            st.markdown('<div class="status-running">시스템 가동중</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-stopped">시스템 중지</div>', unsafe_allow_html=True)
        
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

                # 시스템 시작 시간 초기화
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
        
        if current_time - st.session_state.last_snapshot_time > 900:  # 15분 = 900초
            if st.session_state.collected_data:
                save_snapshot_batch(st.session_state.collected_data)
                st.session_state.last_snapshot_time = current_time
                logger.info("15분 누적데이터 저장 완료")
    
    st.markdown('<h1 class="main-header">다이캐스팅 품질 예측 대시보드</h1>', unsafe_allow_html=True)
    
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
    
    # == 자동 새로고침 ==
    if auto_refresh and st.session_state.data_collection_started:
        time.sleep(3)
        st.rerun()

if __name__ == "__main__":
    main()