import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
import sys
from pathlib import Path


project_root = Path(__file__).parent
sys.path.append(str(project_root))

from utils.style_loader import apply_preset, apply_theme

st.set_page_config(
    page_title="다이캐스팅 품질 예측 대시보드",
    page_icon="🏮",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_preset('with_themes')

st.sidebar.markdown("### 🎨 테마 설정")
theme_choice = st.sidebar.selectbox(
    "테마 선택",
    ["light", "dark", "manufacturing"],
    index=0
)

apply_theme(theme_choice)

date_input_fields = {}

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

def main():

    st.markdown('<h1 class="main-header fade-in">🏭 다이캐스팅 품질 예측 시스템</h1>', unsafe_allow_html=True)
    st.sidebar.markdown("### ⚙️ 설정")
    st.sidebar.markdown("---")

    st.markdown("### 요약통계량 보기")
    today = datetime.datetime.now()
    next_year = today.year + 1
    jan_1 = datetime.date(next_year, 1, 1)
    dec_31 = datetime.date(next_year, 12, 31)

    d = st.date_input(
        "Select your vacation for next year",
        (jan_1, datetime.date(next_year, 1, 7)),
        jan_1,
        dec_31,
        format="MM.DD.YYYY",
    )
    d

    st.markdown("### 요약통계량 보기")

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<h2 class="sub-header">📊 공정 파라미터 입력</h2>', unsafe_allow_html=True)
        
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
    
    with col2:
        st.markdown('<h2 class="sub-header">📋 입력 데이터 확인</h2>', unsafe_allow_html=True)
        
        # 결과 표시 (CSS 클래스 적용)
        st.markdown('<div class="result-box fade-in">', unsafe_allow_html=True)
        
        # 데이터프레임으로 표시
        df_display = pd.DataFrame([input_data]).T
        df_display.columns = ['값']
        df_display.index.name = '파라미터'
        
        st.dataframe(df_display, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 통계 정보 (CSS 클래스 적용)
        st.markdown("### 📊 입력 데이터 통계")
        
        # 숫자형 데이터만 필터링
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
        
        # JSON 형태로 표시
        st.markdown("### 🔧 JSON 형태 데이터")
        st.json(input_data)
        
        # 다운로드 버튼
        json_string = json.dumps(input_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 JSON 파일 다운로드",
            data=json_string,
            file_name=f"diecasting_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    st.markdown("---")
    st.markdown("### ℹ️ 시스템 정보")
    info_cols = st.columns(4)
    
    info_data = [
        ("생성 시간", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ("데이터 포인트", f"{len(input_data)}개 파라미터"),
        ("품질 상태", input_data['passorfail']),
        ("평균 온도", f"{np.mean([v for k, v in input_data.items() if 'temp' in k.lower() and isinstance(v, (int, float))]):.1f}°C")
    ]
    
    for i, (label, value) in enumerate(info_data):
        with info_cols[i]:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown(f"**{label}**<br>{value}", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()