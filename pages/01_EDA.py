import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="데이터 분석", page_icon="📊")

st.title("📊 제조 공정 데이터 분석")

st.markdown("""
제조 공정 데이터의 다양한 분석을 수행할 수 있습니다.
""")

@st.cache_data
def generate_sample_data():
    np.random.seed(42)
    n_samples = 100
    data = {
        'molten_temp': np.random.normal(700, 20, n_samples),
        'production_cycletime': np.random.normal(30, 5, n_samples),
        'cast_pressure': np.random.normal(60, 10, n_samples),
        'physical_strength': np.random.normal(300, 30, n_samples),
        'passorfail': np.random.choice(['Pass', 'Fail'], n_samples, p=[0.8, 0.2])
    }
    return pd.DataFrame(data)

df = generate_sample_data()

col1, col2 = st.columns(2)

with col1:
    st.subheader("온도 분포")
    fig = px.histogram(df, x='molten_temp', title='용융 온도 분포')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("품질 vs 강도")
    fig = px.box(df, x='passorfail', y='physical_strength', title='품질별 물리적 강도')
    st.plotly_chart(fig, use_container_width=True)

st.subheader("상관관계 분석")
numeric_cols = ['molten_temp', 'production_cycletime', 'cast_pressure', 'physical_strength']
corr_matrix = df[numeric_cols].corr()

fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", title="파라미터 상관관계")
st.plotly_chart(fig, use_container_width=True)
