import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import logging
import pandas as pd
import datetime
import plotly.graph_objects as go
from utils.data_utils import save_data_to_file
from variables import fields_input

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.append(str(project_root))

input_fields = fields_input.get_input_fields()

def create_time_series_chart(data, parameter):
    """시계열 차트 생성 (면적 색상 포함, 스크롤 기능)"""
    try:
        if not data or len(data) == 0:
            return None
            
        df = pd.DataFrame(data)
        if 'timestamp' not in df.columns:
            return None
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # 데이터 포인트가 너무 많으면 최근 100개만 표시 (스크롤 효과)
        if len(df) > 100:
            df = df.tail(100)
        
        fig = go.Figure()
        
        # 에러 데이터와 정상 데이터 분리
        if 'error' in df.columns:
            normal_data = df[~df['error']]
            error_data = df[df['error']]
        else:
            normal_data = df
            error_data = pd.DataFrame()
        
        if not normal_data.empty and parameter in normal_data.columns:
            # 정상 데이터 - 면적 포함 선 그래프
            fig.add_trace(go.Scatter(
                x=normal_data['timestamp'],
                y=normal_data[parameter],
                mode='lines+markers',
                name=f'{input_fields[parameter]["label"]} (정상)',
                line=dict(color='#1f77b4', width=2),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.3)',  # 반투명 파란색
                marker=dict(size=6, symbol='circle')
            ))
        
        if not error_data.empty and parameter in error_data.columns:
            # 에러 데이터 - 0값으로 표시
            fig.add_trace(go.Scatter(
                x=error_data['timestamp'],
                y=error_data[parameter],
                mode='markers',
                name='데이터 수집 실패',
                marker=dict(color='red', size=8, symbol='x'),
                showlegend=True
            ))
        
        fig.update_layout(
            title=f'{input_fields[parameter]["label"]} 시계열 변화',
            xaxis_title='시간',
            yaxis_title=input_fields[parameter]["label"],
            hovermode='x unified',
            height=400,
            showlegend=True,
            xaxis=dict(
                rangeslider=dict(visible=True),  # 하단 슬라이더 추가
                type="date"
            )
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"차트 생성 중 오류: {e}")
        return None

def run():
    st.markdown('<h2 class="sub-header">📈 실시간 차트 모니터링</h2>', unsafe_allow_html=True)
        
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("수집 상태", "🟢 진행중" if st.session_state.data_collection_started else "🔴 중지")
    with col2:
        st.metric("총 데이터 수", len(st.session_state.collected_data))
    with col3:
        error_count = len([d for d in st.session_state.collected_data if d.get('error', False)])
        st.metric("오류 데이터 수", error_count)
    with col4:
        if st.session_state.collected_data:
            last_update = st.session_state.collected_data[-1].get('timestamp', 'N/A')
            st.metric("마지막 업데이트", last_update[:19] if last_update != 'N/A' else 'N/A')
    
    # 실시간 차트 표시
    if st.session_state.collected_data and len(st.session_state.collected_data) > 0:
        st.markdown("### 📈 주요 파라미터 실시간 차트")
        
        # 차트를 표시할 파라미터 선택
        selected_params = st.multiselect(
            "표시할 파라미터 선택",
            options=list(input_fields.keys()),
            default=["molten_temp", "cast_pressure", "physical_strength"]
        )
        
        # 선택된 파라미터들의 차트 표시
        for param in selected_params:
            if param in input_fields:
                chart = create_time_series_chart(st.session_state.collected_data, param)
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
                else:
                    st.warning(f"⚠️ {param} 차트를 생성할 수 없습니다. 데이터를 확인해주세요.")
    else:
        st.info("📡 데이터 수집을 시작하면 실시간 차트가 표시됩니다.")
        
        # 테스트용 차트 데이터 생성 버튼
        if st.button("🔧 테스트 데이터 생성"):
            test_data = []
            for i in range(10):
                data = {}
                for key, config in input_fields.items():
                    noise_factor = (config["max"] - config["min"]) * 0.05
                    noise = np.random.uniform(-noise_factor, noise_factor)
                    value = config["default"] + noise
                    value = max(config["min"], min(config["max"], value))
                    data[key] = round(value, 2)
                
                data["passorfail"] = "Pass" if np.random.random() > 0.2 else "Fail"
                data["timestamp"] = (datetime.datetime.now() + datetime.timedelta(minutes=i)).isoformat()
                test_data.append(data)
            
            st.session_state.collected_data.extend(test_data)
            save_data_to_file(st.session_state.collected_data)
            st.success("✅ 테스트 데이터 10개가 생성되었습니다!")
            st.rerun()