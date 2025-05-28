#!/usr/bin/env python3
"""
독립 실행 가능한 WebSocket 서버
실시간 다이캐스팅 데이터를 클라이언트에게 푸시
"""

import asyncio
import json
import logging
import websockets
import redis
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Set
import signal
import sys
import argparse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('websocket_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebSocketDataServer:
    """WebSocket 실시간 데이터 서버"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, redis_host: str = "localhost", redis_port: int = 6379):
        self.host = host
        self.port = port
        self.redis_host = redis_host
        self.redis_port = redis_port
        
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.redis_client = None
        self.running = False
        
        # 서버 통계
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'errors': 0,
            'uptime_start': datetime.now()
        }
        
    def initialize_redis(self):
        """Redis 연결 초기화"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info(f"✅ Redis 연결 성공: {self.redis_host}:{self.redis_port}")
            return True
        except Exception as e:
            logger.error(f"❌ Redis 연결 실패: {e}")
            self.redis_client = None
            return False
    
    def get_latest_predictions(self, limit: int = 100) -> List[Dict]:
        """최신 예측 결과 조회"""
        if not self.redis_client:
            return self.generate_mock_data(limit)
        
        try:
            keys = self.redis_client.keys("prediction:*")
            if not keys:
                return self.generate_mock_data(limit)
            
            predictions = []
            for key in keys[-limit:]:
                data = self.redis_client.get(key)
                if data:
                    try:
                        predictions.append(json.loads(data))
                    except json.JSONDecodeError:
                        continue
            
            predictions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return predictions[:limit]
            
        except Exception as e:
            logger.error(f"데이터 조회 오류: {e}")
            return self.generate_mock_data(limit)
    
    def generate_mock_data(self, limit: int = 100) -> List[Dict]:
        """모의 데이터 생성"""
        predictions = []
        lines = ['Line_A', 'Line_B', 'Line_C']
        molds = ['Mold_X', 'Mold_Y', 'Mold_Z']
        
        for i in range(limit):
            timestamp = datetime.now() - timedelta(seconds=i*10)
            prediction = {
                'id': f'DC_{int(timestamp.timestamp())}_{i}',
                'timestamp': timestamp.isoformat(),
                'prediction': np.random.choice(['Pass', 'Fail'], p=[0.75, 0.25]),
                'probability_pass': np.random.uniform(0.1, 0.9),
                'confidence': np.random.uniform(0.6, 0.95),
                'line': np.random.choice(lines),
                'mold_name': np.random.choice(molds),
                'machine_id': f"machine_{np.random.randint(1, 5)}",
                'molten_temp': np.random.uniform(680, 720),
                'cast_pressure': np.random.uniform(50, 70),
                'production_cycletime': np.random.uniform(25, 35)
            }
            prediction['probability_fail'] = 1 - prediction['probability_pass']
            predictions.append(prediction)
        
        return predictions
    
    def calculate_statistics(self, predictions: List[Dict]) -> Dict:
        """실시간 통계 계산"""
        if not predictions:
            return {'error': 'No data available'}
        
        total = len(predictions)
        pass_count = sum(1 for p in predictions if p['prediction'] == 'Pass')
        fail_count = total - pass_count
        
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
                line_stats[line] = {'total': 0, 'pass': 0, 'fail': 0, 'avg_confidence': 0}
            
            line_stats[line]['total'] += 1
            line_stats[line]['avg_confidence'] += pred.get('confidence', 0)
            
            if pred['prediction'] == 'Pass':
                line_stats[line]['pass'] += 1
            else:
                line_stats[line]['fail'] += 1
        
        # 평균 신뢰도 계산
        for line_data in line_stats.values():
            if line_data['total'] > 0:
                line_data['avg_confidence'] /= line_data['total']
                line_data['pass_rate'] = line_data['pass'] / line_data['total']
        
        return {
            'total_predictions': total,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'pass_rate': pass_count / total if total > 0 else 0,
            'avg_confidence': np.mean([p.get('confidence', 0) for p in predictions]),
            'line_statistics': line_stats,
            'recent_predictions_count': len(recent_predictions),
            'server_stats': self.stats.copy(),
            'last_updated': datetime.now().isoformat()
        }
    
    async def handle_client_connection(self, websocket, path):
        """클라이언트 연결 처리"""
        client_address = websocket.remote_address
        logger.info(f"🔗 새 클라이언트 연결: {client_address}")
        
        # 연결 통계 업데이트
        self.connected_clients.add(websocket)
        self.stats['total_connections'] += 1
        self.stats['active_connections'] = len(self.connected_clients)
        
        try:
            # 초기 데이터 전송
            await self.send_initial_data(websocket)
            
            # 클라이언트 메시지 수신 대기
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))
                except Exception as e:
                    logger.error(f"메시지 처리 오류: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 클라이언트 연결 종료: {client_address}")
        except Exception as e:
            logger.error(f"클라이언트 처리 오류: {e}")
            self.stats['errors'] += 1
        finally:
            # 연결 정리
            self.connected_clients.discard(websocket)
            self.stats['active_connections'] = len(self.connected_clients)
    
    async def send_initial_data(self, websocket):
        """초기 데이터 전송"""
        try:
            predictions = self.get_latest_predictions(50)
            statistics = self.calculate_statistics(predictions)
            
            initial_data = {
                'type': 'initial_data',
                'predictions': predictions,
                'statistics': statistics,
                'server_info': {
                    'version': '1.0.0',
                    'uptime': (datetime.now() - self.stats['uptime_start']).total_seconds(),
                    'data_source': 'Redis' if self.redis_client else 'Mock'
                },
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(initial_data))
            self.stats['messages_sent'] += 1
            logger.info(f"📤 초기 데이터 전송 완료")
            
        except Exception as e:
            logger.error(f"초기 데이터 전송 실패: {e}")
    
    async def handle_client_message(self, websocket, data: Dict):
        """클라이언트 메시지 처리"""
        message_type = data.get('type', 'unknown')
        
        if message_type == 'ping':
            # 핑 응답
            await websocket.send(json.dumps({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }))
            
        elif message_type == 'get_statistics':
            # 통계 요청
            predictions = self.get_latest_predictions(100)
            statistics = self.calculate_statistics(predictions)
            
            await websocket.send(json.dumps({
                'type': 'statistics',
                'data': statistics,
                'timestamp': datetime.now().isoformat()
            }))
            self.stats['messages_sent'] += 1
            
        elif message_type == 'get_latest_data':
            # 최신 데이터 요청
            limit = data.get('limit', 20)
            predictions = self.get_latest_predictions(limit)
            
            await websocket.send(json.dumps({
                'type': 'latest_data',
                'predictions': predictions,
                'timestamp': datetime.now().isoformat()
            }))
            self.stats['messages_sent'] += 1
            
        else:
            # 알 수 없는 메시지 타입
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Unknown message type: {message_type}'
            }))
    
    async def broadcast_updates(self):
        """모든 연결된 클라이언트에게 업데이트 브로드캐스트"""
        while self.running:
            try:
                if self.connected_clients:
                    # 최신 데이터 가져오기
                    predictions = self.get_latest_predictions(20)
                    statistics = self.calculate_statistics(predictions)
                    
                    update_data = {
                        'type': 'realtime_update',
                        'predictions': predictions[:10],  # 최근 10개만
                        'statistics': statistics,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # 모든 클라이언트에게 브로드캐스트
                    message = json.dumps(update_data)
                    disconnected_clients = set()
                    
                    for client in self.connected_clients.copy():
                        try:
                            await client.send(message)
                            self.stats['messages_sent'] += 1
                        except websockets.exceptions.ConnectionClosed:
                            disconnected_clients.add(client)
                        except Exception as e:
                            logger.error(f"브로드캐스트 실패: {e}")
                            disconnected_clients.add(client)
                    
                    # 연결이 끊어진 클라이언트 제거
                    self.connected_clients -= disconnected_clients
                    self.stats['active_connections'] = len(self.connected_clients)
                
                # 2초마다 업데이트
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"브로드캐스트 오류: {e}")
                await asyncio.sleep(5)  # 오류 시 대기 시간 증가
    
    async def start_server(self):
        """서버 시작"""
        logger.info(f"🚀 WebSocket 서버 시작: {self.host}:{self.port}")
        
        # Redis 초기화
        redis_connected = self.initialize_redis()
        if not redis_connected:
            logger.warning("⚠️ Redis 없이 Mock 데이터로 실행")
        
        self.running = True
        
        # 브로드캐스트 태스크 시작
        broadcast_task = asyncio.create_task(self.broadcast_updates())
        
        # WebSocket 서버 시작
        try:
            async with websockets.serve(
                self.handle_client_connection,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ):
                logger.info(f"✅ WebSocket 서버 실행 중: ws://{self.host}:{self.port}")
                logger.info("종료하려면 Ctrl+C를 누르세요...")
                
                # 서버 실행 유지
                await asyncio.Future()  # 무한 대기
                
        except Exception as e:
            logger.error(f"❌ 서버 실행 오류: {e}")
        finally:
            self.running = False
            broadcast_task.cancel()
            logger.info("🛑 WebSocket 서버 종료")

def signal_handler(signum, frame):
    """시그널 핸들러"""
    logger.info(f"시그널 수신: {signum}")
    sys.exit(0)

async def main():
    """메인 함수"""
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='WebSocket 실시간 데이터 서버')
    parser.add_argument('--host', default='localhost', help='서버 호스트 (기본값: localhost)')
    parser.add_argument('--port', type=int, default=8765, help='서버 포트 (기본값: 8765)')
    parser.add_argument('--redis-host', default='localhost', help='Redis 호스트 (기본값: localhost)')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis 포트 (기본값: 6379)')
    
    args = parser.parse_args()
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 서버 생성 및 시작
    server = WebSocketDataServer(
        host=args.host,
        port=args.port,
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"서버 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())