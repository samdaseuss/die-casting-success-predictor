import streamlit as st
import time
from pathlib import Path
import sys
import datetime
import logging
from utils.data_utils import save_data_to_file, save_snapshot_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.append(str(project_root))


snapshots_dir = project_root / "snapshots"
data_dir = project_root / "data"
TEST_PY_FILE = data_dir / "test.py"

def create_test_py_if_not_exists():
    """test.py 파일이 없으면 샘플 파일 생성"""
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
    
    # 주요 파라미터만 표시
    key_params = {
        "molten_temp": "용융온도",
        "cast_pressure": "주조압력", 
        "passorfail": "품질판정",
        "timestamp": "시간"
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
                if key == "molten_temp":
                    display_value = f"{value:.1f} °C"
                elif key == "cast_pressure":
                    display_value = f"{value:.1f} MPa"
                else:
                    display_value = f"{value:.1f}"
            
            # 컬럼에 메트릭 표시
            with cols[col_idx % 2]:
                st.metric(label=label, value=display_value)
            
            col_idx += 1

def run():
    st.markdown('<h2 class="sub-header">📊 실시간 공정 현황</h2>', unsafe_allow_html=True)
        
    # 실시간 상태 표시
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🔄 시스템 상태")
        status_indicator = "🟢 진행중" if st.session_state.data_collection_started else "🔴 중지"
        st.markdown(f'<span class="realtime-indicator"></span><strong>{status_indicator}</strong>', unsafe_allow_html=True)
        
        # 상태 메트릭
        st.metric("총 데이터 수", len(st.session_state.collected_data))
        error_count = len([d for d in st.session_state.collected_data if d.get('error', False)])
        st.metric("오류 데이터 수", error_count)
        
        # 스냅샷 개수 및 다음 저장 시간
        snapshot_count = len(list(snapshots_dir.glob("*snapshot*.json")))
        st.metric("저장된 스냅샷", f"{snapshot_count}개")
        
        # 다음 스냅샷 저장까지 남은 시간
        if st.session_state.data_collection_started:
            last_snapshot_minutes = (time.time() - st.session_state.last_snapshot_time) / 60
            next_snapshot_minutes = 15 - last_snapshot_minutes
            if next_snapshot_minutes > 0:
                st.metric("다음 스냅샷", f"{next_snapshot_minutes:.1f}분 후")
            else:
                st.metric("다음 스냅샷", "곧 저장")
        else:
            st.metric("스냅샷 주기", "15분 간격")
        
    with col2:
        st.markdown("### 📋 현재 공정 데이터")
        
        # 컨테이너로 감싸서 깔끔하게 표시
        with st.container():
            # 현재 상태 표시
            if st.session_state.current_status:
                create_status_display(st.session_state.current_status)
            else:
                st.info("📡 실시간 데이터를 기다리는 중...")
        
        st.markdown("---")
        
        # 수동 조작 버튼들
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            # 수동 데이터 읽기 버튼
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
            # 수동 배치 스냅샷 저장 버튼
            if st.button("💾 즉시 스냅샷 저장", use_container_width=True):
                if st.session_state.collected_data:
                    save_snapshot_batch(st.session_state.collected_data)
                    st.session_state.last_snapshot_time = time.time()
                    st.success("✅ 스냅샷이 즉시 저장되었습니다!")
                else:
                    st.warning("⚠️ 저장할 데이터가 없습니다.")