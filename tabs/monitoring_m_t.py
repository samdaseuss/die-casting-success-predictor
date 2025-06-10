import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import datetime
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 3시그마 데이터 로드
@st.cache_data
def load_sigma_data():
    try:
        # CSV 데이터를 직접 생성 (실제 환경에서는 파일 경로 사용)
        csv_data = pd.read_csv(Path(project_root) / "data" / "3시그마범위데이터.csv")
        
        from io import StringIO
        df = pd.read_csv(StringIO(csv_data))
        return df
    except Exception as e:
        logger.error(f"3시그마 데이터 로드 실패: {e}")
        return pd.DataFrame()

# 모니터링할 변수 정의
MONITORING_VARIABLES = {
    'molten_temp': {'label': '용탕온도', 'unit': '°C'},
    'sleeve_temperature': {'label': '슬리브온도', 'unit': '°C'}, 
    'upper_mold_temp1': {'label': '상형온도1', 'unit': '°C'},
    'upper_mold_temp2': {'label': '상형온도2', 'unit': '°C'},
    'lower_mold_temp1': {'label': '하형온도1', 'unit': '°C'},
    'lower_mold_temp2': {'label': '하형온도2', 'unit': '°C'},
    'cast_pressure': {'label': '주조압력', 'unit': 'bar'},
    'low_section_speed': {'label': '저속구간속도', 'unit': 'm/s'},
    'high_section_speed': {'label': '고속구간속도', 'unit': 'm/s'}
}

# 몰드 코드 매핑
MOLD_CODE_MAPPING = {
    8412: 0,
    8722: 3, 
    8917: 4
}

def get_sigma_limits(mold_code, variable, sigma_df):
    """특정 몰드와 변수에 대한 3시그마 범위 반환"""
    test_label = MOLD_CODE_MAPPING.get(mold_code)
    if test_label is None or sigma_df.empty:
        return None, None
    
    condition = (sigma_df['mold_code'] == mold_code) & (sigma_df['variable'] == variable)
    filtered = sigma_df[condition]
    
    if not filtered.empty:
        return filtered['lower_3'].iloc[0], filtered['upper_3'].iloc[0]
    return None, None

def create_realtime_chart(variable, current_value, history_data, mold_code, sigma_df):
    """실시간 차트 생성"""
    fig = go.Figure()
    
    variable_info = MONITORING_VARIABLES.get(variable, {'label': variable, 'unit': ''})
    
    # 히스토리 데이터가 있는 경우 라인 차트
    if history_data and len(history_data) > 1:
        times = [data['timestamp'] for data in history_data]
        values = [data.get(variable, 0) for data in history_data]
        
        fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode='lines+markers',
            name=variable_info['label'],
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ))
    
    # 현재 값 표시
    current_time = datetime.datetime.now()
    fig.add_trace(go.Scatter(
        x=[current_time],
        y=[current_value],
        mode='markers',
        name='현재값',
        marker=dict(color='red', size=12, symbol='circle')
    ))
    
    # 3시그마 기준선 추가
    lower_limit, upper_limit = get_sigma_limits(mold_code, variable, sigma_df)
    if lower_limit is not None and upper_limit is not None:
        fig.add_hline(
            y=lower_limit, 
            line_dash="dot", 
            line_color="red",
            annotation_text=f"하한: {lower_limit:.1f}",
            annotation_position="right"
        )
        fig.add_hline(
            y=upper_limit, 
            line_dash="dot", 
            line_color="red",
            annotation_text=f"상한: {upper_limit:.1f}",
            annotation_position="right"
        )
        
        # 이상치 체크
        if current_value > upper_limit or current_value < lower_limit:
            fig.add_trace(go.Scatter(
                x=[current_time],
                y=[current_value],
                mode='markers',
                name='이상치',
                marker=dict(color='orange', size=15, symbol='triangle-up'),
                showlegend=False
            ))
    
    # 차트 레이아웃
    fig.update_layout(
        title=f"{variable_info['label']} 실시간 모니터링",
        xaxis_title="시간",
        yaxis_title=f"{variable_info['label']} ({variable_info['unit']})",
        height=300,
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

def check_anomaly(value, mold_code, variable, sigma_df):
    """이상치 체크"""
    lower_limit, upper_limit = get_sigma_limits(mold_code, variable, sigma_df)
    if lower_limit is None or upper_limit is None:
        return False, "정상"
    
    if value > upper_limit:
        return True, f"상한 초과 ({upper_limit:.1f})"
    elif value < lower_limit:
        return True, f"하한 미달 ({lower_limit:.1f})"
    else:
        return False, "정상"

def run():
    """메인 실행 함수"""
    st.markdown('<h2 class="sub-header">실시간 데이터 모니터링</h2>', unsafe_allow_html=True)
    
    # 3시그마 데이터 로드
    sigma_df = load_sigma_data()
    
    # 상태 초기화
    if 'realtime_history' not in st.session_state:
        st.session_state.realtime_history = []
    
    # 컨트롤 패널
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        # 몰드 선택
        selected_mold = st.selectbox(
            "몰드 코드 선택",
            options=list(MOLD_CODE_MAPPING.keys()),
            format_func=lambda x: f"몰드 {x}"
        )
    
    with col2:
        # 자동 새로고침 설정
        auto_refresh = st.checkbox("자동 새로고침", value=True)
        refresh_interval = st.number_input("새로고침 간격(초)", min_value=1, max_value=60, value=5)
    
    with col3:
        # 시스템 상태 표시
        collection_status = st.session_state.get('data_collection_started', False)
        if collection_status:
            st.success("데이터 수집 중")
        else:
            st.warning("데이터 수집 중지됨")
    
    # 현재 데이터 가져오기
    current_data = st.session_state.get('current_status', {})
    
    if not current_data:
        st.info("데이터를 수집하려면 사이드바에서 '시작' 버튼을 클릭하세요.")
        return
    
    # 선택된 몰드에 맞는 데이터 필터링 (실제 구현에서는 mold_code로 필터링)
    current_data['mold_code'] = selected_mold
    
    # 히스토리에 현재 데이터 추가
    current_time = datetime.datetime.now()
    current_data['timestamp'] = current_time.isoformat()
    
    # 최근 50개 데이터만 유지
    st.session_state.realtime_history.append(current_data.copy())
    if len(st.session_state.realtime_history) > 50:
        st.session_state.realtime_history = st.session_state.realtime_history[-50:]
    
    # 상태 요약
    st.markdown("### 시스템 상태 요약")
    status_cols = st.columns(4)
    
    with status_cols[0]:
        st.metric("수집된 데이터", len(st.session_state.realtime_history))
    
    with status_cols[1]:
        st.metric("선택된 몰드", f"몰드 {selected_mold}")
    
    with status_cols[2]:
        last_update = current_time.strftime("%H:%M:%S")
        st.metric("마지막 업데이트", last_update)
    
    with status_cols[3]:
        # 이상치 개수 계산
        anomaly_count = 0
        for var in MONITORING_VARIABLES.keys():
            if var in current_data:
                is_anomaly, _ = check_anomaly(
                    current_data[var], selected_mold, var, sigma_df
                )
                if is_anomaly:
                    anomaly_count += 1
        
        if anomaly_count > 0:
            st.metric("이상치 감지", f"{anomaly_count}개", delta=anomaly_count)
        else:
            st.metric("이상치 감지", "없음")
    
    # 실시간 차트 표시
    st.markdown("### 실시간 모니터링 차트")
    
    # 3x3 그리드로 차트 배치
    for i in range(0, len(MONITORING_VARIABLES), 3):
        cols = st.columns(3)
        variables = list(MONITORING_VARIABLES.keys())[i:i+3]
        
        for j, variable in enumerate(variables):
            if j < len(cols) and variable in current_data:
                with cols[j]:
                    current_value = current_data[variable]
                    
                    # 이상치 체크
                    is_anomaly, status_msg = check_anomaly(
                        current_value, selected_mold, variable, sigma_df
                    )
                    
                    # 차트 생성
                    chart = create_realtime_chart(
                        variable, current_value, 
                        st.session_state.realtime_history,
                        selected_mold, sigma_df
                    )
                    
                    # 상태에 따른 색상 표시
                    if is_anomaly:
                        st.error(f"{MONITORING_VARIABLES[variable]['label']}: {status_msg}")
                    else:
                        st.success(f"{MONITORING_VARIABLES[variable]['label']}: {status_msg}")
                    
                    # 현재값 표시
                    unit = MONITORING_VARIABLES[variable]['unit']
                    st.metric(
                        f"현재값",
                        f"{current_value:.2f} {unit}"
                    )
                    
                    # 차트 표시
                    st.plotly_chart(chart, use_container_width=True)
    
    # 상세 데이터 테이블
    with st.expander("상세 데이터 보기"):
        if st.session_state.realtime_history:
            # 최근 10개 데이터 표시
            recent_data = st.session_state.realtime_history[-10:]
            df_display = pd.DataFrame(recent_data)
            
            # 필요한 컬럼만 선택
            display_columns = ['timestamp'] + list(MONITORING_VARIABLES.keys())
            display_columns = [col for col in display_columns if col in df_display.columns]
            
            if display_columns:
                df_display = df_display[display_columns]
                df_display['timestamp'] = pd.to_datetime(df_display['timestamp']).dt.strftime('%H:%M:%S')
                st.dataframe(df_display, use_container_width=True)
    
    # 자동 새로고침
    if auto_refresh and collection_status:
        time.sleep(refresh_interval)
        st.rerun()
