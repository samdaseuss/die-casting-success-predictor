import streamlit as st
import numpy as np
import datetime
import sys
import time
from pathlib import Path
import logging
from tabs import (
    input_perameter_m_t, analysis_m_t, monitoring_m_t, 
    realtime_manufacturing_m_t
)
from utils.data_utils import (
    load_data_from_file, create_test_py_if_not_exists,
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

try:
    from utils.style_loader import apply_preset, apply_theme, load_custom_css
except ImportError:
    def apply_preset(preset): pass
    def apply_theme(theme): pass
    def load_custom_css(path): pass

load_custom_css("styles/custom_style.css")
apply_preset('with_themes')

st.set_page_config(
    page_title="다이캐스팅 품질 예측 대시보드",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'data_collection_started' not in st.session_state:
    st.session_state.data_collection_started = False
if 'collected_data' not in st.session_state:
    st.session_state.collected_data = []
if 'current_status' not in st.session_state:
    st.session_state.current_status = {}
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = time.time()
if 'last_snapshot_time' not in st.session_state:
    st.session_state.last_snapshot_time = time.time()

input_fields = fields_input.get_input_fields()


def main():
    st.markdown(
        '<h1 class="main-header fade-in"> 다이캐스팅 품질 예측 시스템</h1>', 
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown("### 대쉬보드 기본 설정")
    auto_refresh = st.sidebar.checkbox("자동 새로고침 (5초마다)", value=True )
    
    # 데이터 수집 시작/중지 버튼
    if st.sidebar.button("실시간 데이터 수집 시작"):
        st.session_state.data_collection_started = True
        st.session_state.collected_data = load_data_from_file()
        st.sidebar.success("실시간 데이터 수집이 시작되었습니다!")
    
    if st.sidebar.button("데이터 수집 중지"):
        st.session_state.data_collection_started = False
        st.sidebar.success("데이터 수집이 중지되었습니다.")
    
    # 수집된 데이터 초기화
    if st.sidebar.button("수집된 데이터 초기화"):
        st.session_state.collected_data = []
        st.session_state.current_status = {}
        st.session_state.last_snapshot_time = time.time()  # 시간 초기화
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        for snapshot_file in snapshots_dir.glob("*.json"):
            snapshot_file.unlink()
        st.sidebar.success("모든 데이터가 초기화되었습니다!")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 파일 정보")
    st.sidebar.info(f"데이터 소스: `{TEST_PY_FILE.name}`")
    st.sidebar.info(f"데이터 저장: `snapshots/` 폴더")
    
    # 저장 주기 정보
    if st.session_state.data_collection_started:
        last_snapshot_minutes = (time.time() - st.session_state.last_snapshot_time) / 60
        next_snapshot_minutes = 15 - last_snapshot_minutes
        if next_snapshot_minutes > 0:
            st.sidebar.info(f"다음 데이터 저장 시간: {next_snapshot_minutes:.1f}분 후")
        else:
            st.sidebar.info("데이터 저장 예정")
    
    # 실시간 데이터 수집 (데이터 수집이 시작된 경우)
    if st.session_state.data_collection_started:
        current_time = time.time()
        
        # 10초마다 새 데이터 수집
        if current_time - st.session_state.last_update_time > 10:
            new_data = read_data_from_test_py()
            if new_data:
                st.session_state.collected_data.append(new_data)
                st.session_state.current_status = new_data
                save_data_to_file(st.session_state.collected_data)
                st.session_state.last_update_time = current_time
                logger.info(f"새 데이터 수집됨: {len(st.session_state.collected_data)}개 총 레코드")
        
        # 15분(900초)마다 저장
        if current_time - st.session_state.last_snapshot_time > 900:
            if st.session_state.collected_data:
                save_snapshot_batch(st.session_state.collected_data)
                st.session_state.last_snapshot_time = current_time
                logger.info("15분 누적데이터 저장 완료")
    
    (
        realtime_manufacturing_m,
        realtime_monitoring_m, 
        input_perameter_m, 
        analysis_m
    ) = st.tabs([
        "실시간 현황", 
        "차트 모니터링", 
        "파라미터 입력",
        "데이터 분석"
    ])
    
    with realtime_manufacturing_m:
        realtime_manufacturing_m_t.run()

    with realtime_monitoring_m:
        monitoring_m_t.run()
    
    with input_perameter_m:
        input_perameter_m_t.run()
    
    with analysis_m:
        analysis_m_t.run()
    
    if auto_refresh and st.session_state.data_collection_started:
        time.sleep(3)
        st.rerun()


if __name__ == "__main__":
    main()