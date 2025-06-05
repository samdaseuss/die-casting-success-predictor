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
    """시계열 차트 생성 (꺾은선, y축 범위 자동 조정, 스크롤 기능 포함)"""
    try:
        if not data or len(data) == 0:
            return None
            
        df = pd.DataFrame(data)
        if 'timestamp' not in df.columns:
            return None
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        latest_time = df['timestamp'].max()
        start_time = latest_time - pd.Timedelta(minutes=30)
        
        # 최근 100개만 사용
        if len(df) > 100:
            df = df.tail(100)
        
        fig = go.Figure()
        
        # 에러/정상 데이터 분리
        if 'error' in df.columns:
            normal_data = df[~df['error']]
            error_data = df[df['error']]
        else:
            normal_data = df
            error_data = pd.DataFrame()

        # 정상 데이터 꺾은선 그래프 (면적 제거)
        if not normal_data.empty and parameter in normal_data.columns:
            y_vals = normal_data[parameter]
            y_min = y_vals.min() * 0.95
            y_max = y_vals.max() * 1.05

            # 최소 폭 보정
            if y_max - y_min < 1:
                mid = (y_min + y_max) / 2
                y_min = mid - 1
                y_max = mid + 1

            fig.add_trace(go.Scatter(
                x=normal_data['timestamp'],
                y=y_vals,
                mode='lines+markers',
                name=f'{input_fields[parameter]["label"]} (정상)',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6, symbol='circle')
            ))

            fig.update_yaxes(
                title_font=dict(size=14, color="gray"),
                tickfont=dict(size=12)
)
            fig.update_traces(
                hovertemplate='%{x}<br>온도: %{y}°C'
            )

            # 기준선 정보 (변수별 상한/하한이 설정된 경우만 표시)
            control_min = input_fields[parameter].get("control_min")
            control_max = input_fields[parameter].get("control_max")

            if parameter == "molten_temp":
                fig.add_hline(
                    y=680,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="최소 기준 (680°C)",
                    annotation_position="bottom right"
                )
                fig.add_hline(
                    y=720,
                    line_dash="dash",
                    line_color="orange",
                    annotation_text="최대 기준 (720°C)",
                    annotation_position="top right"
                )


        # 에러 데이터 점 표시
        if not error_data.empty and parameter in error_data.columns:
            fig.add_trace(go.Scatter(
                x=error_data['timestamp'],
                y=error_data[parameter],
                mode='markers',
                name='데이터 수집 실패',
                marker=dict(color='red', size=8, symbol='x'),
                showlegend=True
            ))

        # 전체 레이아웃 설정
        fig.update_layout(
            title=f'{input_fields[parameter]["label"]} 시계열 변화',
            xaxis_title='시간',
            yaxis_title=input_fields[parameter]["label"],
            hovermode='x unified',
            height=400,
            showlegend=True,
            xaxis=dict(
                range=[start_time, latest_time],  # 자동 스크롤처럼 작동
                rangeslider=dict(visible=True),
                type="date"
            )
        )

        return fig
        
    except Exception as e:
        logger.error(f"차트 생성 중 오류: {e}")
        st.error(f"차트 생성 중 오류 발생: {e}")
        return None

def run():
    st.markdown('<h2 class="sub-header">실시간 차트 모니터링</h2>', unsafe_allow_html=True)

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

    if st.session_state.collected_data and len(st.session_state.collected_data) > 0:
        st.markdown("### 📈 주요 파라미터 실시간 차트")

        # 카테고리별 기본 파라미터 그룹 정의
        param_groups = {
            "🌡️ 온도 관련": [
                "molten_temp",
                "upper_mold_temp1",
                "sleeve_temperature",
                "lower_mold_temp2",
                "upper_mold_temp2",
                "lower_mold_temp1"
            ],
            "🔥 압력 관련": [
                "cast_pressure"
            ],
            "🚗 속도 관련": [
                "low_section_speed",
                "high_section_speed"
            ]
        }

        # 선택된 파라미터: 기본은 모든 그룹 통합
        default_params = sum(param_groups.values(), [])
        selected_params = st.multiselect(
            "표시할 파라미터 선택",
            options=list(input_fields.keys()),
            default=default_params
        )

        # 그룹별로 출력
        for group_label, param_list in param_groups.items():
            # 해당 그룹에서 실제 선택된 변수만 출력
            filtered = [p for p in param_list if p in selected_params]
            if filtered:
                st.markdown(f"### {group_label}")
                for i in range(0, len(filtered), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(filtered):
                            param = filtered[i + j]
                            if param in input_fields:
                                with cols[j]:
                                    chart = create_time_series_chart(st.session_state.collected_data, param)
                                    if chart:
                                        st.plotly_chart(chart, use_container_width=True)
                                    else:
                                        st.warning(f"⚠️ {param} 차트를 생성할 수 없습니다.")
    else:
        st.info("📡 데이터 수집을 시작하면 실시간 차트가 표시됩니다.")

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