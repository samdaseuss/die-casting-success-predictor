import streamlit as st
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import redis
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os

# utils 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
utils_dir = os.path.join(parent_dir, 'utils')
if utils_dir not in sys.path:
    sys.path.append(utils_dir)

# WebSocket 클라이언트 유틸리티 import
try:
    from websocket_client import (
        get_realtime_data_with_fallback,
        display_connection_status,
        create_websocket_debug_panel,
        get_websocket_server_status
    )
    WEBSOCKET_UTILS_AVAILABLE = True
except ImportError as e:
    st.warning(f"WebSocket 유틸리티를 불러올 수 없습니다: {e}")
    WEBSOCKET_UTILS_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="실시간 다이캐스팅 품질 모니터링",
    page_icon="📊",
    layout="wide"
)

# CSS 스타일
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.75rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        margin-bottom: 1rem;
    }
    
    .alert-success {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .alert-danger {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .live-indicator {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .connection-status {
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    .connected {
        background-color: #d4edda;
        color: #155724;
    }
    
    .disconnected {
        background-color: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

class RealtimeDashboard:
    """실시간 대시보드 클래스"""
    
    def __init__(self):
        self.redis_client = None
        self.websocket_url = "ws://localhost:8765"
        self.last_update = datetime.now()
        self.connection_status = "initializing"
        self.initialize_connections()
    
    def initialize_connections(self):
        """Redis 및 WebSocket 연결 초기화"""
        # Redis 연결 시도
        try:
            self.redis_client = redis.Redis(
                host='localhost', 
                port=6379, 
                db=0, 
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self.redis_client.ping()
            self.connection_status = "redis_connected"
        except Exception:
            self.redis_client = None
            
            # WebSocket 서버 연결 테스트
            if WEBSOCKET_UTILS_AVAILABLE and get_websocket_server_status():
                self.connection_status = "websocket_available"
            else:
                self.connection_status = "mock_data_only"
    
    def get_latest_predictions(self, limit: int = 100) -> tuple:
        """최신 예측 결과 조회 (데이터, 상태 메시지 반환)"""
        # 1순위: Redis에서 실제 데이터 가져오기
        if self.redis_client:
            try:
                keys = self.redis_client.keys("prediction:*")
                if keys:
                    predictions = []
                    for key in keys[-limit:]:
                        data = self.redis_client.get(key)
                        if data:
                            try:
                                predictions.append(json.loads(data))
                            except json.JSONDecodeError:
                                continue
                    
                    if predictions:
                        predictions.sort(key=lambda x: x['timestamp'], reverse=True)
                        return predictions[:limit], "Redis 실시간 데이터"
                        
            except Exception as e:
                st.warning(f"Redis 데이터 조회 오류: {e}")
        
        # 2순위: WebSocket 서버에서 데이터 가져오기
        if WEBSOCKET_UTILS_AVAILABLE:
            try:
                predictions, statistics, status = get_realtime_data_with_fallback(self.websocket_url)
                
                if predictions:
                    status_message = {
                        "websocket_connected": "WebSocket 실시간 데이터",
                        "websocket_disconnected": "WebSocket 캐시 데이터",
                        "mock_data": "WebSocket Mock 데이터"
                    }.get(status, f"WebSocket 데이터 ({status})")
                    
                    return predictions, status_message
                    
            except Exception as e:
                st.warning(f"WebSocket 데이터 가져오기 오류: {e}")
        
        # 3순위: 로컬 Mock 데이터 생성
        return self.generate_mock_data(limit), "로컬 Mock 데이터"
    
    def generate_mock_data(self, limit: int = 100) -> List[Dict]:
        """로컬 Mock 데이터 생성"""
        np.random.seed(int(time.time()) % 1000)
        predictions = []
        lines = ['Line_A', 'Line_B', 'Line_C']
        molds = ['Mold_X', 'Mold_Y', 'Mold_Z']
        
        # 시간대별 합격률 변화
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:
            base_pass_rate = 0.82
        elif 18 <= current_hour <= 22:
            base_pass_rate = 0.75
        else:
            base_pass_rate = 0.68
        
        for i in range(limit):
            timestamp = datetime.now() - timedelta(seconds=i*40)
            
            # 라인별로 다른 성능
            line = np.random.choice(lines)
            line_modifier = {'Line_A': 0.05, 'Line_B': 0.0, 'Line_C': -0.03}
            pass_rate = base_pass_rate + line_modifier.get(line, 0) + np.random.uniform(-0.05, 0.05)
            pass_rate = max(0.5, min(0.95, pass_rate))
            
            prediction = {
                'id': f'DC_{int(timestamp.timestamp())}_{i}',
                'timestamp': timestamp.isoformat(),
                'prediction': np.random.choice(['Pass', 'Fail'], p=[pass_rate, 1-pass_rate]),
                'probability_pass': np.random.uniform(0.3, 0.95),
                'confidence': np.random.uniform(0.65, 0.98),
                'line': line,
                'mold_name': np.random.choice(molds),
                'molten_temp': np.random.normal(700, 12),
                'cast_pressure': np.random.normal(60, 6),
                'production_cycletime': np.random.normal(30, 2.5),
                'physical_strength': np.random.normal(300, 20)
            }
            prediction['probability_fail'] = 1 - prediction['probability_pass']
            predictions.append(prediction)
        
        return predictions
    
    def get_connection_status_info(self):
        """연결 상태 정보 반환"""
        if self.connection_status == "redis_connected":
            return "🟢 Redis 실시간 연결", "success"
        elif self.connection_status == "websocket_available":
            return "🟡 WebSocket 서버 연결", "warning"
        elif self.connection_status == "mock_data_only":
            return "🔴 Mock 데이터 모드", "error"
        else:
            return "❓ 연결 상태 확인 중", "info"
    
    def get_live_statistics(self, predictions: List[Dict]) -> Dict:
        """실시간 통계 계산"""
        if not predictions:
            return {}
        
        total = len(predictions)
        pass_count = sum(1 for p in predictions if p['prediction'] == 'Pass')
        fail_count = total - pass_count
        
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        
        # 최근 1시간 데이터 필터링
        recent_predictions = [
            p for p in predictions 
            if datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00').replace('+00:00', '')) 
            > datetime.now() - timedelta(hours=1)
        ]
        
        # 라인별 통계
        line_stats = {}
        for pred in predictions:
            line = pred.get('line', 'Unknown')
            if line not in line_stats:
                line_stats[line] = {'total': 0, 'pass': 0, 'fail': 0}
            
            line_stats[line]['total'] += 1
            if pred['prediction'] == 'Pass':
                line_stats[line]['pass'] += 1
            else:
                line_stats[line]['fail'] += 1
        
        # 시간대별 트렌드 (최근 4시간)
        hourly_stats = {}
        recent_4h_predictions = [
            p for p in predictions 
            if datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00').replace('+00:00', '')) 
            > datetime.now() - timedelta(hours=4)
        ]
        
        for pred in recent_4h_predictions:
            timestamp = datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00').replace('+00:00', ''))
            hour_key = timestamp.strftime('%H:00')
            
            if hour_key not in hourly_stats:
                hourly_stats[hour_key] = {'total': 0, 'pass': 0, 'fail': 0}
            
            hourly_stats[hour_key]['total'] += 1
            if pred['prediction'] == 'Pass':
                hourly_stats[hour_key]['pass'] += 1
            else:
                hourly_stats[hour_key]['fail'] += 1
        
        return {
            'total_predictions': total,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'pass_rate': pass_count / total if total > 0 else 0,
            'avg_confidence': avg_confidence,
            'line_statistics': line_stats,
            'hourly_statistics': hourly_stats,
            'recent_predictions_count': len(recent_predictions),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_live_statistics(self, predictions: List[Dict]) -> Dict:
        """실시간 통계 계산"""
        if not predictions:
            return {}
        
        total = len(predictions)
        pass_count = sum(1 for p in predictions if p['prediction'] == 'Pass')
        fail_count = total - pass_count
        
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        
        # 최근 1시간 데이터 필터링
        recent_predictions = [
            p for p in predictions 
            if datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00').replace('+00:00', '')) 
            > datetime.now() - timedelta(hours=1)
        ]
        
        # 라인별 통계
        line_stats = {}
        for pred in predictions:
            line = pred.get('line', 'Unknown')
            if line not in line_stats:
                line_stats[line] = {'total': 0, 'pass': 0, 'fail': 0}
            
            line_stats[line]['total'] += 1
            if pred['prediction'] == 'Pass':
                line_stats[line]['pass'] += 1
            else:
                line_stats[line]['fail'] += 1
        
        # 시간대별 트렌드 (최근 4시간)
        hourly_stats = {}
        recent_4h_predictions = [
            p for p in predictions 
            if datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00').replace('+00:00', '')) 
            > datetime.now() - timedelta(hours=4)
        ]
        
        for pred in recent_4h_predictions:
            timestamp = datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00').replace('+00:00', ''))
            hour_key = timestamp.strftime('%H:00')
            
            if hour_key not in hourly_stats:
                hourly_stats[hour_key] = {'total': 0, 'pass': 0, 'fail': 0}
            
            hourly_stats[hour_key]['total'] += 1
            if pred['prediction'] == 'Pass':
                hourly_stats[hour_key]['pass'] += 1
            else:
                hourly_stats[hour_key]['fail'] += 1
        
        return {
            'total_predictions': total,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'pass_rate': pass_count / total if total > 0 else 0,
            'avg_confidence': avg_confidence,
            'line_statistics': line_stats,
            'hourly_statistics': hourly_stats,
            'recent_predictions_count': len(recent_predictions),
            'last_updated': datetime.now().isoformat()
        }

def create_realtime_charts(predictions: List[Dict], stats: Dict):
    """실시간 차트 생성"""
    
    if not predictions or not stats:
        st.warning("표시할 데이터가 없습니다.")
        return
    
    # 1. 실시간 품질 현황 차트
    df = pd.DataFrame(predictions)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # 시계열 차트 (최근 50개만 표시)
    fig_timeline = go.Figure()
    
    df_recent = df.tail(50)  # 최근 50개만
    
    for prediction_type in ['Pass', 'Fail']:
        filtered_df = df_recent[df_recent['prediction'] == prediction_type]
        color = '#28a745' if prediction_type == 'Pass' else '#dc3545'
        
        fig_timeline.add_trace(go.Scatter(
            x=filtered_df['timestamp'],
            y=filtered_df['confidence'],
            mode='markers+lines',
            name=prediction_type,
            marker=dict(
                color=color,
                size=6,
                opacity=0.8
            ),
            line=dict(width=1, color=color),
            hovertemplate=f'<b>{prediction_type}</b><br>' +
                         'Time: %{x}<br>' +
                         'Confidence: %{y:.1%}<br>' +
                         '<extra></extra>'
        ))
    
    fig_timeline.update_layout(
        title="📈 실시간 품질 예측 현황 (최근 50개)",
        xaxis_title="시간",
        yaxis_title="예측 확신도",
        height=400,
        showlegend=True,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # 2. 라인별 성능 및 품질 분포
    col1, col2 = st.columns(2)
    
    with col1:
        if stats.get('line_statistics'):
            line_data = []
            for line, data in stats['line_statistics'].items():
                line_data.append({
                    'Line': line,
                    'Pass': data['pass'],
                    'Fail': data['fail'],
                    'Total': data['total'],
                    'Pass Rate': data['pass'] / data['total'] if data['total'] > 0 else 0
                })
            
            line_df = pd.DataFrame(line_data)
            
            fig_lines = px.bar(
                line_df, 
                x='Line', 
                y=['Pass', 'Fail'],
                title="📊 라인별 품질 현황",
                color_discrete_map={'Pass': '#28a745', 'Fail': '#dc3545'},
                text_auto=True
            )
            fig_lines.update_layout(height=400)
            st.plotly_chart(fig_lines, use_container_width=True)
    
    with col2:
        # 품질율 파이 차트
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Pass', 'Fail'],
            values=[stats['pass_count'], stats['fail_count']],
            marker_colors=['#28a745', '#dc3545'],
            hole=0.4,
            textinfo='label+percent+value',
            textfont_size=12
        )])
        
        fig_pie.update_layout(
            title="🎯 전체 품질 분포",
            height=400,
            annotations=[dict(
                text=f"합격률<br>{stats['pass_rate']:.1%}", 
                x=0.5, y=0.5, 
                font_size=16, 
                showarrow=False
            )]
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # 3. 시간대별 트렌드
    if stats.get('hourly_statistics'):
        hourly_data = []
        for hour, data in sorted(stats['hourly_statistics'].items()):
            hourly_data.append({
                'Hour': hour,
                'Pass Rate': data['pass'] / data['total'] if data['total'] > 0 else 0,
                'Total': data['total'],
                'Pass': data['pass'],
                'Fail': data['fail']
            })
        
        if hourly_data:
            hourly_df = pd.DataFrame(hourly_data)
            
            # 서브플롯 생성
            fig_trend = make_subplots(
                rows=2, cols=1,
                subplot_titles=('시간대별 합격률', '시간대별 생산량'),
                vertical_spacing=0.1
            )
            
            # 합격률 그래프
            fig_trend.add_trace(
                go.Scatter(
                    x=hourly_df['Hour'],
                    y=hourly_df['Pass Rate'],
                    mode='lines+markers',
                    name='합격률',
                    line=dict(color='#007bff', width=3),
                    marker=dict(size=8)
                ),
                row=1, col=1
            )
            
            # 생산량 바 차트
            fig_trend.add_trace(
                go.Bar(
                    x=hourly_df['Hour'],
                    y=hourly_df['Total'],
                    name='총 생산량',
                    marker_color='#6c757d'
                ),
                row=2, col=1
            )
            
            fig_trend.update_layout(
                title="⏰ 시간대별 품질 트렌드 및 생산량",
                height=500,
                showlegend=False
            )
            
            fig_trend.update_yaxes(tickformat='.1%', row=1, col=1)
            fig_trend.update_xaxes(title_text="시간", row=2, col=1)
            fig_trend.update_yaxes(title_text="생산량", row=2, col=1)
            
            st.plotly_chart(fig_trend, use_container_width=True)

def create_alert_panel(predictions: List[Dict]):
    """알림 패널 생성"""
    st.subheader("🚨 실시간 알림")
    
    # 최근 불량 예측 찾기 (최근 20개 중에서)
    recent_failures = [
        p for p in predictions[:20]
        if p['prediction'] == 'Fail' and p['confidence'] > 0.75
    ]
    
    # 연속 불량 감지
    consecutive_failures = []
    for i in range(min(5, len(predictions)-1)):
        if all(p['prediction'] == 'Fail' for p in predictions[i:i+2]):
            consecutive_failures.extend(predictions[i:i+2])
    
    if recent_failures or consecutive_failures:
        if consecutive_failures:
            st.markdown("""
            <div class="alert-danger">
                <strong>🚨 연속 불량 감지!</strong><br>
                여러 연속된 제품에서 불량이 예측되었습니다. 즉시 라인 점검이 필요합니다.
            </div>
            """, unsafe_allow_html=True)
        
        for failure in recent_failures[:3]:  # 최대 3개만 표시
            timestamp = datetime.fromisoformat(failure['timestamp'].replace('Z', '+00:00').replace('+00:00', ''))
            time_ago = datetime.now() - timestamp
            minutes_ago = max(0, time_ago.seconds // 60)
            
            st.markdown(f"""
            <div class="alert-danger">
                <strong>⚠️ 불량 감지 알림</strong><br>
                라인: {failure['line']} | 금형: {failure['mold_name']}<br>
                불량 확률: {failure['probability_fail']:.1%} | 확신도: {failure['confidence']:.1%}<br>
                발생 시간: {minutes_ago}분 전
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-success">
            <strong>✅ 정상 운영 중</strong><br>
            현재 심각한 품질 이상이 감지되지 않았습니다.
        </div>
        """, unsafe_allow_html=True)

def display_system_info(dashboard, data_status):
    """시스템 정보 표시"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_text, status_type = dashboard.get_connection_status_info()
        if status_type == "success":
            st.success(status_text)
        elif status_type == "warning":
            st.warning(status_text)
        elif status_type == "error":
            st.error(status_text)
        else:
            st.info(status_text)
    
    with col2:
        st.info(f"📊 데이터 소스: {data_status}")
    
    with col3:
        st.info(f"⏰ 업데이트: {datetime.now().strftime('%H:%M:%S')}")
    
    # WebSocket 디버그 패널 (유틸리티 사용 가능한 경우만)
    if WEBSOCKET_UTILS_AVAILABLE:
        create_websocket_debug_panel()

def main():
    """메인 대시보드 함수"""
    
    # 제목과 실시간 표시
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📊 실시간 다이캐스팅 품질 모니터링")
    with col2:
        st.markdown(f"""
        <div class="live-indicator" style="text-align: right; color: #28a745; font-size: 1.2em;">
            🟢 LIVE | {datetime.now().strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
    
    # 대시보드 인스턴스 생성
    dashboard = RealtimeDashboard()
    
    # 시스템 정보 표시
    display_system_info(dashboard, data_status)
    
    # 사이드바 설정
    st.sidebar.header("⚙️ 대시보드 설정")
    
    auto_refresh = st.sidebar.checkbox("자동 새로고침", value=True)
    refresh_interval = st.sidebar.slider("새로고침 간격 (초)", 2, 30, 5)
    data_limit = st.sidebar.slider("표시할 데이터 개수", 50, 500, 100)
    
    # 수동 새로고침 버튼
    if st.sidebar.button("🔄 수동 새로고침"):
        st.rerun()
    
    # 연결 테스트 버튼
    if st.sidebar.button("🔌 연결 테스트"):
        with st.sidebar:
            with st.spinner("연결 테스트 중..."):
                dashboard.initialize_connections()
                
                # WebSocket 서버 상태 확인
                if WEBSOCKET_UTILS_AVAILABLE:
                    ws_status = get_websocket_server_status()
                    if ws_status:
                        st.success("✅ WebSocket 서버 연결 가능")
                    else:
                        st.warning("⚠️ WebSocket 서버 연결 불가")
                else:
                    st.info("WebSocket 유틸리티 비활성화")
                
                st.success("연결 테스트 완료!")
        st.rerun()
    
    # 데이터 로딩
    with st.spinner("실시간 데이터 로딩 중..."):
        predictions, data_status = dashboard.get_latest_predictions(data_limit)
        stats = dashboard.get_live_statistics(predictions)
    
    # 메인 메트릭 표시
    if stats:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{stats['total_predictions']}</h3>
                <p>총 예측 건수</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            pass_rate_color = "#28a745" if stats['pass_rate'] > 0.8 else "#ffc107" if stats['pass_rate'] > 0.6 else "#dc3545"
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, {pass_rate_color} 0%, {pass_rate_color}dd 100%);">
                <h3>{stats['pass_rate']:.1%}</h3>
                <p>합격률</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{stats['pass_count']}</h3>
                <p>합격 건수</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{stats['fail_count']}</h3>
                <p>불량 건수</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            confidence_color = "#28a745" if stats['avg_confidence'] > 0.8 else "#ffc107" if stats['avg_confidence'] > 0.6 else "#dc3545"
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, {confidence_color} 0%, {confidence_color}dd 100%);">
                <h3>{stats['avg_confidence']:.1%}</h3>
                <p>평균 확신도</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 알림 패널
    create_alert_panel(predictions)
    
    # 차트 섹션
    st.header("📊 실시간 분석 차트")
    create_realtime_charts(predictions, stats)
    
    # 상세 데이터 테이블
    st.header("📋 최근 예측 결과")
    
    if predictions:
        # 표시할 데이터 개수 선택
        display_count = st.selectbox("표시할 데이터 개수", [10, 20, 50, 100], index=1)
        
        # 데이터프레임 생성
        df_display = pd.DataFrame(predictions[:display_count])
        df_display['timestamp'] = pd.to_datetime(df_display['timestamp'])
        df_display = df_display.sort_values('timestamp', ascending=False)
        
        # 컬럼 선택 및 포맷팅
        display_columns = ['timestamp', 'line', 'mold_name', 'prediction', 'confidence', 'probability_pass']
        if 'molten_temp' in df_display.columns:
            display_columns.extend(['molten_temp', 'cast_pressure'])
        
        df_display = df_display[display_columns].copy()
        
        # 컬럼명 한글화
        column_mapping = {
            'timestamp': '시간',
            'line': '라인',
            'mold_name': '금형',
            'prediction': '예측결과',
            'confidence': '확신도',
            'probability_pass': '합격확률',
            'molten_temp': '용융온도',
            'cast_pressure': '주조압력'
        }
        
        df_display = df_display.rename(columns=column_mapping)
        
        # 포맷팅
        if '확신도' in df_display.columns:
            df_display['확신도'] = df_display['확신도'].apply(lambda x: f"{x:.1%}")
        if '합격확률' in df_display.columns:
            df_display['합격확률'] = df_display['합격확률'].apply(lambda x: f"{x:.1%}")
        if '용융온도' in df_display.columns:
            df_display['용융온도'] = df_display['용융온도'].apply(lambda x: f"{x:.1f}°C")
        if '주조압력' in df_display.columns:
            df_display['주조압력'] = df_display['주조압력'].apply(lambda x: f"{x:.1f}MPa")
        
        # 스타일 적용
        def highlight_prediction(val):
            if val == 'Pass':
                return 'background-color: #d4edda; color: #155724'
            elif val == 'Fail':
                return 'background-color: #f8d7da; color: #721c24'
            return ''
        
        styled_df = df_display.style.applymap(highlight_prediction, subset=['예측결과'])
        st.dataframe(styled_df, use_container_width=True)
        
        # CSV 다운로드 버튼
        csv = df_display.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name=f"diecasting_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # 자동 새로고침
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
