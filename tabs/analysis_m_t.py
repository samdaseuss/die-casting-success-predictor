import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
from pathlib import Path

# project_root = Path(__file__).parent
# sys.path.append(str(project_root))

def run():
    st.markdown('<h2 class="sub-header">모델 성능 분석</h2>', unsafe_allow_html=True)
    
    # 모델 개요 - 깔끔한 디자인
    st.markdown("### 모델 개요")
    
    # 3개 열로 주요 정보를 간단하고 깔끔하게 표시 - 카드 높이 통일
    overview_col1, overview_col2, overview_col3 = st.columns(3)
    
    with overview_col1:
        st.markdown("""
        <div style="padding: 20px; border-radius: 8px; background-color: #f8f9fa; border: 1px solid #e9ecef; text-align: center; margin: 10px 0; min-height: 120px;">
            <h4 style="margin: 0 0 10px 0; color: #495057; font-size: 16px;">선정 모델</h4>
            <h3 style="margin: 5px 0; color: #212529; font-size: 24px; font-weight: bold;">Random Forest</h3>
            <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 14px;">앙상블 기반 예측 모델</p>
        </div>
        """, unsafe_allow_html=True)
    
    with overview_col2:
        st.markdown("""
        <div style="padding: 20px; border-radius: 8px; background-color: #f8f9fa; border: 1px solid #e9ecef; text-align: center; margin: 10px 0; min-height: 120px;">
            <h4 style="margin: 0 0 10px 0; color: #495057; font-size: 16px;">예측 목적</h4>
            <h3 style="margin: 5px 0; color: #212529; font-size: 18px; font-weight: bold; line-height: 1.3;">다이캐스팅 공정<br>품질 불량 예측</h3>
            <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 14px;">실시간 품질 관리</p>
        </div>
        """, unsafe_allow_html=True)
    
    with overview_col3:
        st.markdown("""
        <div style="padding: 20px; border-radius: 8px; background-color: #f8f9fa; border: 1px solid #e9ecef; text-align: center; margin: 10px 0; min-height: 120px;">
            <h4 style="margin: 0 0 10px 0; color: #495057; font-size: 16px;">전체 정확도</h4>
            <h3 style="margin: 5px 0; color: #28a745; font-size: 28px; font-weight: bold;">98.85%</h3>
            <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 14px;">14,613건 데이터 기준</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 성능 지표 섹션
    st.markdown("### 성능 지표")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 혼동행렬")
        
        # 실제 모델 결과 데이터
        confusion_data = {
            'Predicted Normal': [13853, 36],
            'Predicted Defect': [132, 592]
        }
        confusion_df = pd.DataFrame(confusion_data, index=['Actual Normal', 'Actual Defect'])
        
        # 혼동행렬 히트맵
        fig_cm = px.imshow(
            confusion_df.values,
            labels=dict(x="예측", y="실제", color="개수"),
            x=['정상 예측', '불량 예측'],
            y=['실제 정상', '실제 불량'],
            color_continuous_scale='Blues',
            text_auto='.0f'
        )
        fig_cm.update_layout(
            title="혼동행렬 (Confusion Matrix)",
            height=400
        )
                
        st.plotly_chart(fig_cm, use_container_width=True)

    
    with col2:
        st.markdown("#### 성능 지표 상세")
        
        # 성능 지표 계산 (실제 데이터 기반)
        metrics_data = {
            '지표': [
                '불량 예측 정확률 (Precision)', 
                '불량품 탐지율 (Recall)', 
                '종합 성능 점수 (F1-Score)', 
                '전체 예측 정확도 (Accuracy)'
            ],
            '정상 클래스': ['99.74%', '99.06%', '99.40%', '98.85%'],
            '불량 클래스': ['81.77%', '94.27%', '87.57%', '98.85%'],
            '실무 의미': [
                '불량 예측 시 실제 불량일 확률',
                '실제 불량품 중 놓치지 않고 찾은 비율', 
                '정확률과 탐지율의 균형 점수',
                '전체 제품 중 올바르게 판정한 비율'
            ]
        }
        
        metrics_df = pd.DataFrame(metrics_data)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        
        # 성능 지표 시각화
        fig_metrics = go.Figure()
        
        categories = ['불량 예측 정확률', '불량품 탐지율', '종합 성능 점수']
        normal_scores = [99.74, 99.06, 99.40]
        defect_scores = [81.77, 94.27, 87.57]
        
        fig_metrics.add_trace(go.Bar(
            name='정상 클래스',
            x=categories,
            y=normal_scores,
            marker_color='lightblue'
        ))
        
        fig_metrics.add_trace(go.Bar(
            name='불량 클래스', 
            x=categories,
            y=defect_scores,
            marker_color='lightcoral'
        ))
        
        fig_metrics.update_layout(
            title='클래스별 성능 지표',
            yaxis_title='점수 (%)',
            barmode='group',
            height=300
        )
        
        st.plotly_chart(fig_metrics, use_container_width=True)
    
    col1, col2 = st.columns(2)
    # 변수 중요도 분석
    with col1:
        st.markdown("### 주요 변수 분석")

        # 세션 스테이트 초기화
        if 'selected_variable' not in st.session_state:
            st.session_state.selected_variable = None

        feature_importance = {
            'cast_pressure': 0.146106,
            'lower_mold_temp2': 0.065445,
            'low_section_speed': 0.060389,
            'lower_mold_temp1': 0.054311,
            'upper_mold_temp1': 0.051218,
            'upper_mold_temp2': 0.047888,
            'sleeve_temperature': 0.037132,
            'Coolant_temperature': 0.025875,
            'biscuit_thickness': 0.022397,
            'mold_code_8722': 0.017521,
            'high_section_speed': 0.017154,
            'molten_temp': 0.011894,
            'facility_operation_cycleTime': 0.009968,
            'mold_code_8412': 0.008408,
            'physical_strength': 0.007018,
            'production_cycletime': 0.006810,
            'mold_code_8917': 0.004344,
            'EMS_operation_time_23': 0.003926,
            'EMS_operation_time_6': 0.002654,
            'mold_code_8600': 0.001956
            }

        # 한글 변수명 매핑
        var_names = {
            'cast_pressure': '주조 압력',
            'lower_mold_temp2': '하부 금형 온도2',
            'low_section_speed': '저속구간 속도',
            'lower_mold_temp1': '하부 금형 온도1',
            'upper_mold_temp1': '상부 금형 온도1',
            'upper_mold_temp2': '상부 금형 온도2',
            'sleeve_temperature': '슬리브 온도',
            'Coolant_temperature': '냉각수 온도',
            'biscuit_thickness': '비스킷 두께',
            'mold_code_8722': '금형코드 8722',
            'high_section_speed': '고속구간 속도',
            'molten_temp': '용탕 온도',
            'facility_operation_cycleTime': '설비 사이클타임',
            'mold_code_8412': '금형코드 8412',
            'physical_strength': '인장 강도',
            'production_cycletime': '생산 사이클타임',
            'mold_code_8917': '금형코드 8917',
            'EMS_operation_time_23': 'EMS 작동시간 23',
            'EMS_operation_time_6': 'EMS 작동시간 6',
            'mold_code_8600': '금형코드 8600'
        }

        # 정렬
        sorted_items = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        variables, importances = zip(*sorted_items)
        variables = list(variables)[::-1]
        importances = list(importances)[::-1]
        korean_labels = [var_names.get(v, v) for v in variables]

        # 막대 차트
        fig = go.Figure(go.Bar(
            x=importances,
            y=korean_labels,
            orientation='h',
            marker=dict(color='#1f77b4'),
            text=[f"{v:.3f}" for v in importances],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>중요도: %{x:.4f}<extra></extra>'
        ))

        fig.update_layout(
            title='SHAP Feature Importance (불량 예측 기준) - 상위 20개',
            xaxis_title='mean(|SHAP value|) (평균 기여도)',
            yaxis_title='변수',
            height=700,
            margin=dict(l=130, r=40, t=60, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)
        with st.expander(" ### SHAP feature importance 설명"):
            st.markdown("불량 예측에 가장 많은 영향을 준 변수 top 20")
            st.markdown("""
                        | 구성 요소 | 설명 |
                        |----------|------|
                        | **목적** | 불량 예측에 가장 큰 영향을 미치는 변수들을 중요도 순으로 시각화 |
                        | **X축** | mean(\|SHAP value\|) - 각 변수의 평균 절댓값 기여도 (0~0.15) |
                        | **Y축** | 변수명 (중요도 기준 상위 20개, 내림차순 정렬) |
                        | **막대 길이** | 해당 변수가 모델 예측에 미치는 영향의 크기 |
                        | **수치** | 각 막대 끝에 표시된 정확한 중요도 값 |
                        """)

            st.markdown("""
                        **주요 변수별 중요도 분석:**
                        - **주조 압력** (`cast_pressure`): 중요도 0.146으로 **가장 중요한 변수** - 불량 예측에 압력이 핵심 요인
                        - **하부 금형 온도2** (`lower_mold_temp2`): 중요도 0.065로 **2위** - 금형 온도 관리의 중요성
                        - **저속 구간 속도** (`low_section_speed`): 중요도 0.060으로 **3위** - 주조 속도 제어의 영향
                        """)

        with col2:
            st.markdown("### SHAP Summary Plot 시각화")
            import os
            from PIL import Image
            current_dir = os.path.dirname(__file__)
            image_path = os.path.join(current_dir, "data", "summary_plot.jpg")
            try:
                img = Image.open(image_path)
                st.image(img, caption="SHAP Summary Plot", use_container_width=True)
            except Exception as e:
                st.error(f"이미지를 불러오는 데 실패했습니다: {e}")
            with st.expander(" ### SHAP Summary Plot 구성 요소 설명"):

                st.markdown("""
                | 구성 요소     | 설명 |
                |--------------|------|
                | **목적**      | 모델이 불량 여부에 영향을 준 주요 변수와 그 영향의 방향을 시각화 |
                | **X축**       | 각 변수의 SHAP 값, 0보다 크면 (예측값)불량 발생 확률 **증가**, 0보다 작으면 **감소** |
                | **Y축**       | 변수명 (feature importance 기준 상위 20개) |
                | **색상**      | 변수의 원래 값 크기 — 🔵 낮은 값, 🔴 높은 값 |
                | **점 하나**   | 하나의 데이터 샘플 |
                """)
                st.markdown("""
                - **주조 압력 (`cast_pressure`)**: 압력이 낮을수록 불량 발생 가능성 **증가**

                - **하부 금형 온도2 (`lower_mold_temp2`)**: 온도가 낮을수록 불량 발생 가능성 **증가**

                - **저속 구간 속도 (`low_section_speed`)**: 속도가 낮을수록 불량 발생 가능성 **증가**
                """)
if __name__ == "__main__":
    run()
