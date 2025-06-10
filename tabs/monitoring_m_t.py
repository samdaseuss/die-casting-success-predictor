import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import logging
import pandas as pd
import datetime
import numpy as np 
import plotly.graph_objects as go
from utils.data_utils import save_data_to_file
from variables import fields_input
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.append(str(project_root))

input_fields = fields_input.get_input_fields()


'''
# 3시그마를 사용한 그래프 
'''

try:
    sigma_df = pd.read_csv("project_root/tabs/data/3시그마범위데이터.csv")
except FileNotFoundError:
    logger.warning("3시그마 범위 데이터 파일을 찾을 수 없습니다.")
    sigma_df = pd.DataFrame()
    logger.info(sigma_df)

def get_parameter_status_info(row, selected_label, current_param):
    """각 시점에서 모든 parameter들의 상한/하한 초과 상태를 분석"""
    status_info = []
    
    if sigma_df.empty:
        return ""
    
    for param_name in input_fields.keys():
        if param_name == current_param or param_name not in row:
            continue
            
        try:
            # 해당 parameter의 3시그마 범위 찾기
            cond = (sigma_df['test_label'] == selected_label) & (sigma_df['variable'] == param_name)
            param_sigma = sigma_df[cond]
            
            if not param_sigma.empty:
                lower = param_sigma['lower_3'].values[0]
                upper = param_sigma['upper_3'].values[0]
                value = row[param_name]
                
                param_label = input_fields.get(param_name, {}).get("label", param_name)
                
                if pd.notna(value):
                    if value > upper:
                        status_info.append(f"{param_label}: {value:.2f} (상한 {upper:.2f} 초과)")
                    elif value < lower:
                        status_info.append(f"{param_label}: {value:.2f} (하한 {lower:.2f} 미달)")
        except Exception as e:
            continue
        
    return "<br>".join(status_info) if status_info else "다른 parameter는 정상 범위"

def create_time_series_chart(data, parameter, selected_mold):  # selected_label -> selected_mold로 변경
    try:
        # 1. 기본 데이터 검증
        if not data or len(data) == 0:
            logger.warning("데이터가 비어있습니다.")
            return None

        df1 = pd.DataFrame(data)
        
        # 2. 필수 컬럼 확인
        if 'timestamp' not in df1.columns:
            logger.warning("timestamp 컬럼이 없습니다.")
            return None
        
        # 3. parameter 컬럼 확인
        if parameter not in df1.columns:
            logger.warning(f"파라미터 '{parameter}' 컬럼이 데이터에 없습니다.")
            logger.info(f"사용 가능한 컬럼들: {df1.columns.tolist()}")
            return None
        
        # 4. mold_code 필터링 - 선택된 몰드 코드에 해당하는 데이터만
        if 'mold_code' in df1.columns:
            df = df1[df1['mold_code'] == selected_mold]  # selected_label -> selected_mold로 변경
            if df.empty:
                logger.warning(f"선택된 몰드 코드 '{selected_mold}'에 대한 데이터가 없습니다.")
                logger.info(f"사용 가능한 mold_code 값들: {df1['mold_code'].unique()}")
                return None
        else:
            df = df1.copy()   
        
        # 5. 시간 컬럼 처리
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        except Exception as e:
            logger.error(f"timestamp 변환 실패: {e}")
            return None
        
        # registration_time이 없는 경우 timestamp 사용
        if 'registration_time' not in df.columns:
            df['registration_time'] = df['timestamp']
        else:
            try:
                df['registration_time'] = pd.to_datetime(df['registration_time'])
            except Exception as e:
                logger.warning(f"registration_time 변환 실패, timestamp 사용: {e}")
                df['registration_time'] = df['timestamp']
                
        df = df.sort_values('registration_time')
        
        # 6. parameter 값 확인
        param_values = df[parameter].dropna()
        if param_values.empty:
            logger.warning(f"파라미터 '{parameter}'의 유효한 값이 없습니다.")
            return None
        
        # 7. 1시간 윈도우 적용 - 최신 시간부터 1시간 전까지
        latest_time = df['registration_time'].max()
        start_time = latest_time - pd.Timedelta(hours=1)

        fig = go.Figure()

        # 8. error 컬럼이 있는지 확인
        if 'error' in df.columns:
            normal_data = df[~df['error']]
            error_data = df[df['error']]
        else:
            normal_data = df.copy()
            error_data = pd.DataFrame()

        # 9. 정상 데이터 처리
        if not normal_data.empty and parameter in normal_data.columns:
            y_vals = normal_data[parameter]
            
            # NaN이 아닌 값들만으로 min/max 계산
            valid_vals = y_vals.dropna()
            if not valid_vals.empty:
                y_min = valid_vals.min() * 0.95
                y_max = valid_vals.max() * 1.05

                if y_max - y_min < 1:
                    mid = (y_min + y_max) / 2
                    y_min = mid - 1
                    y_max = mid + 1

                # 메인 데이터 trace
                parameter_label = input_fields.get(parameter, {}).get("label", parameter)
                fig.add_trace(go.Scatter(
                    x=normal_data['registration_time'],
                    y=y_vals,
                    mode='lines+markers',
                    name=f'{parameter_label}',
                    line=dict(color='#1f77b4', width=2),
                    marker=dict(size=6, symbol='circle'),
                    connectgaps=False
                ))

                # 10. 3시그마 기준선 처리 (mold_code를 label로 변환)
                if not sigma_df.empty:
                    try:
                        # mold_code를 label로 변환
                        mold_code_to_label = {8412: 0, 8722: 3, 8917: 4}
                        selected_label = mold_code_to_label.get(selected_mold, selected_mold)
                        
                        cond = (sigma_df['test_label'] == selected_label) & (sigma_df['variable'] == parameter)
                        sigma_filtered = sigma_df[cond]
                        
                        if not sigma_filtered.empty:
                            lower = sigma_filtered['lower_3'].values[0]
                            upper = sigma_filtered['upper_3'].values[0]
                            
                            # 기준선 추가
                            fig.add_hline(y=lower, line_dash="dot", line_color="red", 
                                        annotation_text=f"3σ 하한 {lower:.2f}", 
                                        annotation_position='right bottom')
                            fig.add_hline(y=upper, line_dash="dot", line_color="red", 
                                        annotation_text=f"3σ 상한 {upper:.2f}")

                            # 상한/하한 초과 데이터 처리
                            exceed_data = normal_data[normal_data[parameter] > upper].copy()
                            below_data = normal_data[normal_data[parameter] < lower].copy()

                            # 상한 초과 데이터
                            if not exceed_data.empty:
                                fig.add_trace(go.Scatter(
                                    x=exceed_data['registration_time'],
                                    y=exceed_data[parameter],
                                    mode='markers',
                                    name='상한 초과',
                                    marker=dict(color='red', size=10, symbol='triangle-up'),
                                    hovertemplate=(
                                        f"<b>상한 초과</b><br>"
                                        f"{parameter_label}: %{{y:.2f}}<br>"
                                        f"상한: {upper:.2f}<br>"
                                        "<extra></extra>"
                                    ),
                                    showlegend=True
                                ))

                            # 하한 미달 데이터
                            if not below_data.empty:
                                fig.add_trace(go.Scatter(
                                    x=below_data['registration_time'],
                                    y=below_data[parameter],
                                    mode='markers',
                                    name='하한 미달',
                                    marker=dict(color='red', size=10, symbol='triangle-down'),
                                    hovertemplate=(
                                        f"<b>하한 미달</b><br>"
                                        f"{parameter_label}: %{{y:.2f}}<br>"
                                        f"하한: {lower:.2f}<br>"
                                        "<extra></extra>"
                                    ),
                                    showlegend=True
                                ))
                    except Exception as e:
                        logger.warning(f"3시그마 기준선 처리 중 오류: {e}")
                        # 기준선 실패해도 기본 차트는 표시
                
        # 11. 에러 데이터 처리
        if not error_data.empty and parameter in error_data.columns:
            time_col = 'registration_time' if 'registration_time' in error_data.columns else 'timestamp'
            fig.add_trace(go.Scatter(
                x=error_data[time_col],
                y=error_data[parameter],
                mode='markers',
                name='데이터 수집 실패',
                marker=dict(color='red', size=8, symbol='x'),
                showlegend=True
            ))

        # 12. 레이아웃 설정
        parameter_label = input_fields.get(parameter, {}).get("label", parameter)
        
        fig.update_layout(
            title=f'{parameter_label} 시계열 변화 (몰드 코드: {selected_mold})',
            xaxis_title='시간',
            yaxis_title=parameter_label,
            hovermode='x unified',
            height=400,
            showlegend=True,
            xaxis=dict(
                range=[start_time, latest_time],
                rangeslider=dict(visible=True),
                type="date"
            )
        )

        return fig

    except Exception as e:
        logger.error(f"차트 생성 중 오류 발생 - 파라미터: {parameter}, 오류: {str(e)}")
        import traceback
        logger.error(f"상세 오류 정보: {traceback.format_exc()}")
        return None

def debug_data_info(data, parameter):
    """데이터 구조를 디버깅하기 위한 함수"""
    st.write("### 디버깅 정보")
    
    if not data:
        st.write("❌ 데이터가 없습니다.")
        return
    
    df = pd.DataFrame(data)
    st.write(f"✅ 전체 데이터 개수: {len(df)}")
    st.write(f"✅ 컬럼 목록: {df.columns.tolist()}")
    
    if parameter in df.columns:
        param_data = df[parameter]
        st.write(f"✅ {parameter} 컬럼 존재")
        st.write(f"✅ {parameter} 유효한 값 개수: {param_data.dropna().shape[0]}")
        if not param_data.dropna().empty:
            st.write(f"✅ {parameter} 값 범위: {param_data.min():.2f} ~ {param_data.max():.2f}")
        else:
            st.write(f"❌ {parameter} 컬럼에 유효한 값이 없습니다.")
    else:
        st.write(f"❌ {parameter} 컬럼이 없습니다.")
    
    if 'mold_code' in df.columns:
        st.write(f"✅ mold_code 값들: {df['mold_code'].unique()}")
        # 각 mold_code별 데이터 개수 표시
        mold_code_counts = df['mold_code'].value_counts()
        st.write(f"✅ mold_code별 데이터 개수:")
        for code, count in mold_code_counts.items():
            st.write(f"   - {code}: {count}개")
    else:
        st.write("❌ mold_code 컬럼이 없습니다.")
    
    # 샘플 데이터 표시
    st.write("### 샘플 데이터 (처음 3개)")
    st.dataframe(df.head(3))

def run():
    st.markdown('<h2 class="sub-header">실시간 차트 모니터링</h2>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    /* multiselect 선택된 항목의 글자 색깔 변경 */
    .stMultiSelect [data-baseweb="tag"] {
        color: white !important; /* 흰색 글자 */
        background-color: #007aff !important;  /* 초록색 배경 */
    }
    
    /* multiselect 선택된 항목의 배경색만 변경하고 싶다면 */
    .stMultiSelect [data-baseweb="tag"] span {
        color: white !important;  /* 검은색 글자 */
    }
    
    /* multiselect 드롭다운 옵션 글자 색깔 변경 */
    .stMultiSelect [role="option"] {
        color: #333333 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3,3,4])
    with col1:
        st.metric("수집 상태", "🟢 진행중" if st.session_state.get('data_collection_started', False) else "🔴 중지")
    with col2:
        collected_data = st.session_state.get('collected_data', [])
        st.metric("총 데이터 수", len(collected_data))
    with col3:
        if collected_data:
            last_update = collected_data[-1].get('timestamp', 'N/A')
            st.metric("마지막 업데이트", last_update[:10]+" "+last_update[11:19] if last_update != 'N/A' else 'N/A')

    # 몰드 코드 선택
    mold_codes = [8412, 8722, 8917]
    selected_mold = st.selectbox("몰드 코드 선택", mold_codes)
    
    # 디버깅 모드 체크박스 추가
    debug_mode = st.checkbox("디버깅 모드 활성화", value=False)

    if collected_data and len(collected_data) > 0:
        # 카테고리별 기본 파라미터 그룹 정의
        param_groups = {
            "온도 관련": [
                "molten_temp",
                "sleeve_temperature",
                "upper_mold_temp1",
                "upper_mold_temp2",
                "lower_mold_temp1",
                "lower_mold_temp2",
            ],
            "압력 관련": [
                "cast_pressure"
            ],
            "속도 관련": [
                "low_section_speed",
                "high_section_speed"
            ]
        }

        # 선택된 파라미터: 기본은 모든 그룹 통합
        default_params = sum(param_groups.values(), [])
        # input_fields에 실제 존재하는 파라미터만 필터링
        available_params = [p for p in default_params if p in input_fields]
        
        exclude_keys = ["upper_mold_temp3", "lower_mold_temp3"]
        selected_params = st.multiselect(
            "표시할 파라미터 선택",
            options=[key for key in input_fields.keys() if key not in exclude_keys],
            default=available_params
        )

        # 그룹별로 출력
        for group_label, param_list in param_groups.items():
            # 해당 그룹에서 실제 선택된 변수만 출력
            filtered = [p for p in param_list if p in selected_params and p in input_fields]
            if filtered:
                st.markdown(f"### {group_label}")
                for i in range(0, len(filtered), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(filtered):
                            param = filtered[i + j]
                            with cols[j]:
                                try:
                                    # 디버깅 모드가 활성화되어 있고 molten_temp인 경우
                                    if debug_mode and param == "molten_temp":
                                        debug_data_info(collected_data, param)
                                    
                                    # selected_label 대신 selected_mold 전달
                                    chart = create_time_series_chart(collected_data, param, selected_mold)
                                    if chart:
                                        st.plotly_chart(chart, use_container_width=True)
                                    else:
                                        st.error(f"❌ {param} 차트를 생성할 수 없습니다.")
                                        
                                        # 구체적인 오류 정보 표시
                                        if debug_mode:
                                            st.write("**오류 진단:**")
                                            df_test = pd.DataFrame(collected_data)
                                            
                                            if param not in df_test.columns:
                                                st.write(f"- {param} 컬럼이 데이터에 없습니다.")
                                            elif df_test[param].dropna().empty:
                                                st.write(f"- {param} 컬럼에 유효한 데이터가 없습니다.")
                                            elif 'mold_code' in df_test.columns:
                                                filtered_df = df_test[df_test['mold_code'] == selected_mold]
                                                if filtered_df.empty:
                                                    st.write(f"- 선택된 mold_code({selected_mold})에 대한 데이터가 없습니다.")
                                                    st.write(f"- 사용 가능한 mold_code: {df_test['mold_code'].unique()}")
                                            else:
                                                st.write("- 알 수 없는 오류가 발생했습니다.")
                                        
                                except Exception as e:
                                    st.error(f"❌ {param} 차트 생성 중 예외 발생: {str(e)}")
                                    if debug_mode:
                                        st.write("**상세 오류 정보:**")
                                        import traceback
                                        st.code(traceback.format_exc())
    else:
        st.info("데이터 수집을 시작하면 실시간 차트가 표시됩니다.")

        if st.button("테스트 데이터 생성"):
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
                data["mold_code"] = selected_mold  # 현재 선택된 mold_code 사용
                data["registration_time"] = data["timestamp"]  # registration_time 추가
                test_data.append(data)

            if 'collected_data' not in st.session_state:
                st.session_state.collected_data = []
            st.session_state.collected_data.extend(test_data)
            save_data_to_file(st.session_state.collected_data)
            st.success("✅ 테스트 데이터 10개가 생성되었습니다!")
            st.rerun()
