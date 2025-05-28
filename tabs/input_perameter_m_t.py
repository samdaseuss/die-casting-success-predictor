import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import datetime
import time
import json
import logging
import numpy as np


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.append(str(project_root))

data_dir = project_root / "data"
snapshots_dir = project_root / "snapshots"
snapshots_dir.mkdir(exist_ok=True)
data_dir.mkdir(exist_ok=True)
DATA_FILE = data_dir / "collected_data.json"


input_fields = {
    "molten_temp": {"label": "용융 온도 (°C)", "min": 600.0, "max": 800.0, "default": 700.0, "step": 1.0},
    "production_cycletime": {"label": "생산 사이클 시간 (초)", "min": 10.0, "max": 60.0, "default": 30.0, "step": 1.0},
    "low_section_speed": {"label": "저속 구간 속도 (mm/s)", "min": 10.0, "max": 50.0, "default": 25.0, "step": 1.0},
    "high_section_speed": {"label": "고속 구간 속도 (mm/s)", "min": 50.0, "max": 150.0, "default": 100.0, "step": 5.0},
    "cast_pressure": {"label": "주조 압력 (MPa)", "min": 20.0, "max": 100.0, "default": 60.0, "step": 1.0},
    "biscuit_thickness": {"label": "비스킷 두께 (mm)", "min": 5.0, "max": 20.0, "default": 12.0, "step": 0.1},
    "upper_mold_temp1": {"label": "상부 금형 온도 1 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "upper_mold_temp2": {"label": "상부 금형 온도 2 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "upper_mold_temp3": {"label": "상부 금형 온도 3 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "lower_mold_temp1": {"label": "하부 금형 온도 1 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "lower_mold_temp2": {"label": "하부 금형 온도 2 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "lower_mold_temp3": {"label": "하부 금형 온도 3 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "sleeve_temperature": {"label": "슬리브 온도 (°C)", "min": 180.0, "max": 280.0, "default": 230.0, "step": 1.0},
    "physical_strength": {"label": "물리적 강도 (MPa)", "min": 200.0, "max": 400.0, "default": 300.0, "step": 5.0},
    "Coolant_temperature": {"label": "냉각수 온도 (°C)", "min": 15.0, "max": 35.0, "default": 25.0, "step": 0.5}
}

def save_data_to_file(data):
    """데이터를 파일에 저장"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"데이터 저장 완료: {len(data)}개 레코드")
        return True
    except Exception as e:
        logger.error(f"데이터 저장 중 오류: {e}")
        return False

def run():
    st.markdown('<h2 class="sub-header">⚙️ 공정 파라미터 수동 입력</h2>', unsafe_allow_html=True) 
    col1, col2 = st.columns([1, 1])
    
    with col1:
        input_data = {}
        
        with st.expander("🌡️ 온도 파라미터", expanded=True):
            temp_cols = st.columns(2)
            with temp_cols[0]:
                for key in ["molten_temp", "upper_mold_temp1", "upper_mold_temp2", "upper_mold_temp3"]:
                    input_data[key] = st.number_input(
                        input_fields[key]["label"],
                        min_value=input_fields[key]["min"],
                        max_value=input_fields[key]["max"],
                        value=input_fields[key]["default"],
                        step=input_fields[key]["step"],
                        key=key
                    )
            
            with temp_cols[1]:
                for key in ["lower_mold_temp1", "lower_mold_temp2", "lower_mold_temp3", "sleeve_temperature", "Coolant_temperature"]:
                    input_data[key] = st.number_input(
                        input_fields[key]["label"],
                        min_value=input_fields[key]["min"],
                        max_value=input_fields[key]["max"],
                        value=input_fields[key]["default"],
                        step=input_fields[key]["step"],
                        key=key
                    )
        
        with st.expander("⚙️ 공정 파라미터", expanded=True):
            process_cols = st.columns(2)
            with process_cols[0]:
                for key in ["production_cycletime", "low_section_speed", "cast_pressure"]:
                    input_data[key] = st.number_input(
                        input_fields[key]["label"],
                        min_value=input_fields[key]["min"],
                        max_value=input_fields[key]["max"],
                        value=input_fields[key]["default"],
                        step=input_fields[key]["step"],
                        key=key
                    )
            
            with process_cols[1]:
                for key in ["high_section_speed", "biscuit_thickness", "physical_strength"]:
                    input_data[key] = st.number_input(
                        input_fields[key]["label"],
                        min_value=input_fields[key]["min"],
                        max_value=input_fields[key]["max"],
                        value=input_fields[key]["default"],
                        step=input_fields[key]["step"],
                        key=key
                    )
        
        # Pass/Fail 선택
        input_data["passorfail"] = st.selectbox(
            "품질 판정 기준",
            options=["Pass", "Fail"],
            index=0
        )
        
        # 수동 데이터 추가 버튼
        if st.button("📥 수동 데이터 추가"):
            input_data["timestamp"] = datetime.datetime.now().isoformat()
            input_data["manual"] = True
            st.session_state.collected_data.append(input_data)
            save_data_to_file(st.session_state.collected_data)
            st.success("✅ 데이터가 성공적으로 추가되었습니다!")
            st.rerun()
    
    with col2:
        st.markdown('<h3 class="sub-header">📋 입력 데이터 확인</h3>', unsafe_allow_html=True)
        st.markdown('<div class="result-box fade-in">', unsafe_allow_html=True)
        
        df_display = pd.DataFrame([input_data]).T
        df_display.columns = ['값']
        df_display.index.name = '파라미터'
        
        df_display['값'] = df_display['값'].astype(str)

        st.dataframe(df_display, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("### 📊 입력 데이터 통계")
        
        numeric_data = {k: v for k, v in input_data.items() if isinstance(v, (int, float))}
        
        stats_cols = st.columns(3)
        with stats_cols[0]:
            st.markdown('<div class="metric-card stats-card">', unsafe_allow_html=True)
            st.metric("총 파라미터 수", len(input_data))
            st.markdown('</div>', unsafe_allow_html=True)
        with stats_cols[1]:
            st.markdown('<div class="metric-card stats-card">', unsafe_allow_html=True)
            st.metric("평균값", f"{np.mean(list(numeric_data.values())):.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with stats_cols[2]:
            st.markdown('<div class="metric-card stats-card">', unsafe_allow_html=True)
            st.metric("최댓값", f"{max(numeric_data.values()):.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("### 🔧 JSON 형태 데이터")
        st.json(input_data)
        
        # 다운로드 버튼
        json_string = json.dumps(input_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 JSON 파일 다운로드",
            data=json_string,
            file_name=f"diecasting_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json")