import streamlit as st
import time
from pathlib import Path
import sys
import datetime
import logging
from utils.data_utils import save_data_to_file, save_snapshot_batch
from streamlit_echarts import st_echarts
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.append(str(project_root))


snapshots_dir = project_root / "snapshots"
data_dir = project_root / "data"
TEST_PY_FILE = data_dir / "test.py"

if "ng_history" not in st.session_state:
    st.session_state.ng_history = []

current_data = st.session_state.get("current_status", None)

def create_test_py_if_not_exists():
    if not TEST_PY_FILE.exists():
        sample_content = '''# 다이캐스팅 실시간 데이터 파일
# 이 파일을 수정하면 대시보드에서 자동으로 감지하여 데이터를 수집합니다.

import datetime
import random

def get_current_data():
    """현재 다이캐스팅 공정 데이터 반환"""
    return {
        "molten_temp": round(random.uniform(680, 720), 1),
        "production_cycletime": round(random.uniform(25, 35), 1),
        "low_section_speed": round(random.uniform(20, 30), 1),
        "high_section_speed": round(random.uniform(90, 110), 0),
        "cast_pressure": round(random.uniform(55, 85), 1),
        "biscuit_thickness": round(random.uniform(10, 14), 1),
        "upper_mold_temp1": round(random.uniform(190, 210), 1),
        "upper_mold_temp2": round(random.uniform(190, 210), 1),
        "upper_mold_temp3": round(random.uniform(190, 210), 1),
        "lower_mold_temp1": round(random.uniform(190, 210), 1),
        "lower_mold_temp2": round(random.uniform(190, 210), 1),
        "lower_mold_temp3": round(random.uniform(190, 210), 1),
        "sleeve_temperature": round(random.uniform(220, 240), 1),
        "physical_strength": round(random.uniform(280, 320), 0),
        "Coolant_temperature": round(random.uniform(20, 30), 1),
        "passorfail": "Pass" if random.random() > 0.15 else "Fail",
        "timestamp": datetime.datetime.now().isoformat()
    }

# 현재 데이터 (이 부분을 수정하면 대시보드에서 자동 감지)
current_data = get_current_data()
'''
        try:
            with open(TEST_PY_FILE, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            logger.info("test.py 샘플 파일이 생성되었습니다.")
        except Exception as e:
            logger.error(f"test.py 파일 생성 중 오류: {e}")

def read_data_from_test_py():
    """test.py에서 실제 데이터 읽기"""
    try:
        if not TEST_PY_FILE.exists():
            create_test_py_if_not_exists()
            return None
            
        # test.py 파일 읽기
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("test_module", TEST_PY_FILE)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        # current_data 또는 get_current_data() 함수 확인
        if hasattr(test_module, 'current_data'):
            data = test_module.current_data
            if isinstance(data, dict):
                data['timestamp'] = datetime.datetime.now().isoformat()
                data['source'] = 'test.py'
                return data
        elif hasattr(test_module, 'get_current_data'):
            data = test_module.get_current_data()
            if isinstance(data, dict):
                data['timestamp'] = datetime.datetime.now().isoformat()
                data['source'] = 'test.py'
                return data
                
        logger.warning("test.py에서 유효한 데이터를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        logger.error(f"test.py에서 데이터 읽기 중 오류: {e}")
        return None

def create_status_display(current_data):
    """현재 상태 표시 (Streamlit 네이티브 컴포넌트 사용)"""
    if not current_data:
        st.info("📡 실시간 데이터를 기다리는 중...")
        return
    
    key_params = {
        "molten_temp": "용융온도",
        "cast_pressure": "주조압력", 
        "passorfail": "품질판정",
        "timestamp": "시간",
    }
    
    # 메트릭 카드 스타일로 표시
    cols = st.columns(2)
    col_idx = 0
    
    for key, label in key_params.items():
        if key in current_data:
            value = current_data[key]
            display_value = value
            
            if key == "timestamp":
                # 시간 포맷팅
                try:
                    dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
                    display_value = dt.strftime("%H:%M:%S")
                except:
                    display_value = str(value)[:8]
                    
            elif key == "passorfail":
                # Pass/Fail 이모지 추가
                if value == "Pass":
                    display_value = f"✅ {value}"
                else:
                    display_value = f"❌ {value}"
                    
            elif isinstance(value, (int, float)):
                # 숫자 포맷팅
                if key == "molten_temp-":
                    display_value = f"{value:.1f} °C"
                elif key == "cast_pressure":
                    display_value = f"{value:.1f} MPa"
                else:
                    display_value = f"{value:.1f}"
            
            # 컬럼에 메트릭 표시
            with cols[col_idx % 2]:
                st.metric(label=label, value=display_value)
            
            col_idx += 1

def half_gauge_chart(title, value, min_val=0, max_val=100):
    option = {
        "grid": {
            "top": 0,
            "bottom": -100  # ✅ 차트 아래 여백 제거
        },
        "series": [
            {
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "min": min_val,
                "max": max_val,
                "splitNumber": 1,
                "axisLine": {
                    "lineStyle": {
                        "width": 50,
                        "color": [
                            [value / max_val, "red"],  # 채워진 부분
                            [1, "#ccc"]                 # 나머지 회색
                        ]
                    }
                },
                "pointer": {
                    "show": False
                },
                "detail": {
                    "fontSize": 30,
                    "offsetCenter": [0, "20%"],
                    "formatter": "{value}"
                },
                "title": {
                    "show": False
                },
                "data": [{"value": value}]
            }
        ]
    }
    st_echarts(options=option, width="100%",height="280px")

def run():
    st.markdown('<h2 class="sub-header">📊 실시간 공정 현황</h2>', unsafe_allow_html=True)
    # 실시간 상태 표시
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🔄 시스템 상태")

        status_indicator = "🟢 진행중" if st.session_state.data_collection_started else "🔴 중지"
        st.markdown(
            f'<span class="realtime-indicator" style="background-color:blue"></span><strong>{status_indicator}</strong>',
            unsafe_allow_html=True,
        )

        # 게이지 차트
        half_gauge_chart("주조압력", 73.8)

        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)

        with row1_col1:
            st.metric(label="불량데이터", value="0개")

        with row1_col2:
            st.metric(label="받은 데이터수", value="1개")

        with row2_col1:
            st.metric(label="불량비율", value="4%")

        with row2_col2:
            st.metric(label="양품데이터", value="0")
        
        # ## 상태 메트릭
        # st.metric("총 데이터 수", len(st.session_state.collected_data))
        # error_count = len([d for d in st.session_state.collected_data if d.get('error', False)])
        # st.metric("오류 데이터 수", error_count)
        
    with col2:
        st.markdown("### 📋 현재 공정 데이터")
        
        # 컨테이너로 감싸서 깔끔하게 표시
        # with st.container():
        #     # 현재 상태 표시
        #     if st.session_state.current_status:
        #         create_status_display(st.session_state.current_status)
        #     else:
        #         st.info("📡 실시간 데이터를 기다리는 중...")
        # with st.container():
        #     st

        def create_value_card(title, value, unit, direction=None, time=None):
            """값 카드 형태를 출력하는 유틸 함수"""
            arrow = ""
            
            st.metric(label=title, value=f"{value} {unit}", delta=arrow)

        with st.container():
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                create_value_card("주조압력", 73.8, "MPa", direction="up", time="10:29:47")

            with col2:
                create_value_card("상금형 온도 1", 689.2, "°C", direction="down")

            with col3:
                create_value_card("저속 속도", 0.35, "m/s", direction="up")

            with col4:
                create_value_card("고속 구간 속도", 1.8, "m/s", direction="up")

            col5, col6, col7, col8 = st.columns(4)

            with col5:
                create_value_card("슬리브 온도", 220.0, "°C", direction="up")

            with col6:
                create_value_card("하금형 온도 2", 315.6, "°C", direction="up")

            with col7:
                create_value_card("상금형 온도 2", 300.4, "°C", direction="down")

            with col8:
                create_value_card("하금형 온도 1", 298.9, "°C", direction="down")
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🔄 수동 데이터 읽기", use_container_width=True):
                new_data = read_data_from_test_py()
                if new_data:
                    st.session_state.current_status = new_data
                    st.session_state.collected_data.append(new_data)
                    save_data_to_file(st.session_state.collected_data)
                    st.success("✅ 새 데이터를 성공적으로 읽어왔습니다!")
                    st.rerun()
                else:
                    st.error("❌ 데이터를 읽어올 수 없습니다.")
        
        with col_btn2:
            if st.button("💾 즉시 데이터 저장하기", use_container_width=True):
                if st.session_state.collected_data:
                    save_snapshot_batch(st.session_state.collected_data)
                    st.session_state.last_snapshot_time = time.time()
                    st.success("✅ 데이터가 즉시 저장되었습니다!")
                else:
                    st.warning("⚠️ 저장할 데이터가 없습니다.")
    
        with st.container():
            # 열 비율: 왼쪽 여백 6 / 오른쪽 실제 내용 2씩
            col0, col1, col2 = st.columns([6, 2, 2])

            # 스냅샷 개수
            with col1:
                snapshot_count = len(list(snapshots_dir.glob("*snapshot*.json")))
                st.metric("저장된 스냅샷", f"{snapshot_count}개")

            # 다음 저장 시간
            with col2:
                if st.session_state.data_collection_started:
                    last_snapshot_minutes = (time.time() - st.session_state.last_snapshot_time) / 60
                    next_snapshot_minutes = 15 - last_snapshot_minutes
                    if next_snapshot_minutes > 0:
                        st.metric("다음 스냅샷", f"{next_snapshot_minutes:.1f}분 후")
                    else:
                        st.metric("다음 스냅샷", "곧 저장")
                else:
                    st.metric("스냅샷 주기", "15분 간격")
        


