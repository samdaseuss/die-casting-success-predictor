"""
WebSocket 클라이언트 유틸리티
Streamlit에서 WebSocket 서버와 통신하기 위한 유틸리티
"""
import asyncio
import json
import logging
import websockets
import threading
import queue
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import streamlit as st

logger = logging.getLogger(__name__)

class StreamlitWebSocketClient:
    """Streamlit용 WebSocket 클라이언트"""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.websocket = None
        self.is_connected = False
        self.data_queue = queue.Queue(maxsize=100)
        self.connection_thread = None
        self.running = False
        self.last_data = None
        self.connection_status = "disconnected"
        
    def start_connection(self):
        """백그라운드에서 WebSocket 연결 시작"""
        if self.connection_thread and self.connection_thread.is_alive():
            return
        
        self.running = True
        self.connection_thread = threading.Thread(target=self._connection_worker, daemon=True)
        self.connection_thread.start()
    
    def stop_connection(self):
        """연결 중단"""
        self.running = False
        if self.connection_thread:
            self.connection_thread.join(timeout=2)
    
    def _connection_worker(self):
        """백그라운드 연결 워커"""
        while self.running:
            try:
                # 새 이벤트 루프 생성 (쓰레드용)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                loop.run_until_complete(self._connect_and_listen())
                
            except Exception as e:
                logger.error(f"WebSocket 연결 오류: {e}")
                self.connection_status = "error"
                time.sleep(5)  # 5초 후 재연결 시도
            finally:
                try:
                    loop.close()
                except:
                    pass
    
    async def _connect_and_listen(self):
        """WebSocket 연결 및 메시지 수신"""
        try:
            async with websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            ) as websocket:
                self.websocket = websocket
                self.is_connected = True
                self.connection_status = "connected"
                logger.info(f"WebSocket 연결 성공: {self.uri}")
                
                # 초기 데이터 요청
                await websocket.send(json.dumps({"type": "get_latest_data", "limit": 100}))
                
                # 메시지 수신 루프
                async for message in websocket:
                    if not self.running:
                        break
                    
                    try:
                        data = json.loads(message)
                        self._handle_message(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 파싱 오류: {e}")
                    except Exception as e:
                        logger.error(f"메시지 처리 오류: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket 연결이 종료되었습니다")
            self.connection_status = "disconnected"
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
            self.connection_status = "failed"
        finally:
            self.is_connected = False
            self.websocket = None
    
    def _handle_message(self, data: Dict):
        """수신된 메시지 처리"""
        message_type = data.get('type', 'unknown')
        
        # 큐에 데이터 저장 (큐가 가득 차면 오래된 데이터 제거)
        try:
            if self.data_queue.full():
                self.data_queue.get_nowait()  # 오래된 데이터 제거
            
            self.data_queue.put_nowait({
                'type': message_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
            
            # 최신 데이터 저장
            if message_type in ['initial_data', 'realtime_update', 'latest_data']:
                self.last_data = data
                
        except queue.Full:
            pass  # 큐가 가득 찬 경우 무시
    
    def get_latest_data(self) -> Optional[Dict]:
        """최신 데이터 반환"""
        return self.last_data
    
    def get_connection_status(self) -> str:
        """연결 상태 반환"""
        return self.connection_status
    
    def send_message(self, message: Dict) -> bool:
        """메시지 전송 (비동기적으로)"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            # 메시지 전송을 위한 별도 스레드
            def send_worker():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.websocket.send(json.dumps(message)))
                    loop.close()
                except Exception as e:
                    logger.error(f"메시지 전송 실패: {e}")
            
            thread = threading.Thread(target=send_worker, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            logger.error(f"메시지 전송 오류: {e}")
            return False

# Streamlit 세션 상태를 사용한 WebSocket 클라이언트 관리
@st.cache_resource
def get_websocket_client(uri: str = "ws://localhost:8765") -> StreamlitWebSocketClient:
    """WebSocket 클라이언트 싱글톤 인스턴스 반환"""
    client = StreamlitWebSocketClient(uri)
    client.start_connection()
    return client

def get_realtime_data_from_websocket(uri: str = "ws://localhost:8765") -> tuple:
    """WebSocket에서 실시간 데이터 가져오기"""
    try:
        # 캐시된 클라이언트 가져오기
        client = get_websocket_client(uri)
        
        # 연결 상태 확인
        status = client.get_connection_status()
        
        # 최신 데이터 가져오기
        latest_data = client.get_latest_data()
        
        if latest_data:
            predictions = latest_data.get('predictions', [])
            statistics = latest_data.get('statistics', {})
            return predictions, statistics, status
        else:
            return [], {}, status
            
    except Exception as e:
        logger.error(f"WebSocket 데이터 가져오기 실패: {e}")
        return [], {}, "error"

# HTTP 방식 백업 (WebSocket 실패 시)
import requests

def get_websocket_server_status(host: str = "localhost", port: int = 8765) -> bool:
    """WebSocket 서버 상태 확인 (포트 체크)"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

class MockDataGenerator:
    """WebSocket 연결 실패 시 사용할 Mock 데이터 생성기"""
    
    def __init__(self):
        self.last_generated = datetime.now()
        self.data_cache = None
        
    def generate_realtime_data(self, limit: int = 100) -> tuple:
        """실시간 변화하는 Mock 데이터 생성"""
        import numpy as np
        
        # 30초마다 새 데이터 생성
        now = datetime.now()
        if self.data_cache is None or (now - self.last_generated).seconds > 30:
            self._generate_fresh_data(limit)
            self.last_generated = now
        
        return self.data_cache
    
    def _generate_fresh_data(self, limit: int):
        """새로운 Mock 데이터 생성"""
        import numpy as np
        from datetime import timedelta
        
        # 시간 기반 시드로 변화 있는 데이터
        np.random.seed(int(time.time()) % 10000)
        
        predictions = []
        lines = ['Line_A', 'Line_B', 'Line_C']
        molds = ['Mold_X', 'Mold_Y', 'Mold_Z']
        
        # 시간대별로 합격률 변화 (주간: 높음, 야간: 낮음)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # 주간
            pass_probability = 0.85
        elif 18 <= current_hour <= 22:  # 저녁
            pass_probability = 0.75
        else:  # 야간
            pass_probability = 0.70
        
        for i in range(limit):
            timestamp = datetime.now() - timedelta(seconds=i*45)
            
            # 약간의 랜덤 변화 추가
            current_pass_prob = pass_probability + np.random.uniform(-0.1, 0.1)
            current_pass_prob = max(0.5, min(0.95, current_pass_prob))
            
            prediction = {
                'id': f'DC_{int(timestamp.timestamp())}_{i}',
                'timestamp': timestamp.isoformat(),
                'prediction': np.random.choice(['Pass', 'Fail'], p=[current_pass_prob, 1-current_pass_prob]),
                'probability_pass': np.random.uniform(0.3, 0.95),
                'confidence': np.random.uniform(0.7, 0.98),
                'line': np.random.choice(lines),
                'mold_name': np.random.choice(molds),
                'molten_temp': np.random.normal(700, 15),
                'cast_pressure': np.random.normal(60, 8),
                'production_cycletime': np.random.normal(30, 3),
                'physical_strength': np.random.normal(300, 25)
            }
            prediction['probability_fail'] = 1 - prediction['probability_pass']
            predictions.append(prediction)
        
        # 통계 계산
        total = len(predictions)
        pass_count = sum(1 for p in predictions if p['prediction'] == 'Pass')
        fail_count = total - pass_count
        
        statistics = {
            'total_predictions': total,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'pass_rate': pass_count / total if total > 0 else 0,
            'avg_confidence': np.mean([p['confidence'] for p in predictions]),
            'last_updated': datetime.now().isoformat()
        }
        
        self.data_cache = (predictions, statistics, "mock_data")

# 전역 Mock 데이터 생성기
@st.cache_resource
def get_mock_data_generator() -> MockDataGenerator:
    """Mock 데이터 생성기 싱글톤 인스턴스"""
    return MockDataGenerator()

def get_realtime_data_with_fallback(websocket_uri: str = "ws://localhost:8765") -> tuple:
    """WebSocket 연결을 시도하고 실패 시 Mock 데이터 반환"""
    
    # 1차: WebSocket 서버 상태 확인
    if get_websocket_server_status():
        try:
            # 2차: WebSocket 데이터 가져오기 시도
            predictions, statistics, status = get_realtime_data_from_websocket(websocket_uri)
            
            if predictions or statistics:
                return predictions, statistics, f"websocket_{status}"
        except Exception as e:
            logger.warning(f"WebSocket 데이터 가져오기 실패: {e}")
    
    # 3차: Mock 데이터 생성
    mock_generator = get_mock_data_generator()
    predictions, statistics, status = mock_generator.generate_realtime_data()
    
    return predictions, statistics, status

# Streamlit 컴포넌트용 헬퍼 함수들
def display_connection_status(status: str):
    """연결 상태를 시각적으로 표시"""
    status_info = {
        "connected": ("🟢 WebSocket 연결됨", "success"),
        "disconnected": ("🔴 WebSocket 연결 안됨", "error"),
        "failed": ("❌ WebSocket 연결 실패", "error"),
        "error": ("⚠️ WebSocket 오류", "warning"),
        "mock_data": ("🎭 Mock 데이터 모드", "info"),
        "websocket_connected": ("🟢 WebSocket 실시간 연결", "success"),
        "websocket_disconnected": ("🟡 WebSocket 연결 끊어짐", "warning")
    }
    
    message, alert_type = status_info.get(status, ("❓ 상태 불명", "info"))
    
    if alert_type == "success":
        st.success(message)
    elif alert_type == "error":
        st.error(message)
    elif alert_type == "warning":
        st.warning(message)
    else:
        st.info(message)

def create_websocket_debug_panel():
    """WebSocket 디버그 패널 생성"""
    with st.expander("🔧 WebSocket 디버그 정보", expanded=False):
        client = get_websocket_client()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**연결 정보:**")
            st.write(f"- URI: {client.uri}")
            st.write(f"- 상태: {client.get_connection_status()}")
            st.write(f"- 연결됨: {client.is_connected}")
            st.write(f"- 실행 중: {client.running}")
        
        with col2:
            st.write("**데이터 정보:**")
            latest_data = client.get_latest_data()
            if latest_data:
                st.write(f"- 마지막 업데이트: {latest_data.get('timestamp', 'N/A')}")
                st.write(f"- 데이터 타입: {latest_data.get('type', 'N/A')}")
                predictions = latest_data.get('predictions', [])
                st.write(f"- 예측 데이터: {len(predictions)}개")
            else:
                st.write("- 데이터 없음")
        
        # 수동 연결 테스트
        if st.button("🔄 연결 테스트"):
            with st.spinner("연결 테스트 중..."):
                server_available = get_websocket_server_status()
                if server_available:
                    st.success("✅ WebSocket 서버 응답 정상")
                    # 새 데이터 요청
                    if client.send_message({"type": "get_latest_data", "limit": 50}):
                        st.info("📡 데이터 요청 전송됨")
                else:
                    st.error("❌ WebSocket 서버 응답 없음")

# 사용 예제
if __name__ == "__main__":
    # 간단한 테스트
    print("WebSocket 클라이언트 테스트")
    
    predictions, statistics, status = get_realtime_data_with_fallback()
    
    print(f"상태: {status}")
    print(f"예측 데이터: {len(predictions)}개")
    print(f"통계: {statistics}")
    
    if predictions:
        print("최신 예측:")
        latest = predictions[0]
        print(f"  - ID: {latest['id']}")
        print(f"  - 예측: {latest['prediction']}")
        print(f"  - 확신도: {latest['confidence']:.1%}")
        print(f"  - 라인: {latest['line']}")