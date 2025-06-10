# tabs/realtime_manufacturing_m_t.py

import streamlit as st
import time
from pathlib import Path
import sys
from streamlit_echarts import st_echarts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import json
import hashlib
import sqlite3
from styles import (
    create_control_chart_options,
    create_gauge_chart_options,
    create_status_html,
    create_mold_card_html,
    create_process_indicator_html,
    create_timer_html)
from utils.data_utils import (
    get_fail_data_count, 
    get_fail_data_with_pagination, 
    get_fail_data_with_pagination_by_datetime, 
    get_available_date_range, 
    get_fail_data_count_by_datetime,
    get_today_sensor_data,
    get_today_pass_data,
    get_all_sensor_data,
    get_all_pass_sensor_data)

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

snapshots_dir = project_root / "snapshots"
database_dir = project_root / "database"
CONTROL_CHART_DB = database_dir / "control_chart.db"

# 데이터베이스 디렉토리 생성
database_dir.mkdir(exist_ok=True)

def init_control_chart_database():
    """관리도 데이터베이스 테이블 초기화"""
    conn = sqlite3.connect(CONTROL_CHART_DB)
    cursor = conn.cursor()
    
    # 관리도 데이터 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS control_chart_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            defect_rate REAL NOT NULL,
            total_count INTEGER NOT NULL,
            defect_count INTEGER NOT NULL,
            mean_rate REAL,
            std_rate REAL,
            ucl REAL,
            lcl REAL,
            usl REAL,
            lsl REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 실시간 버퍼 데이터 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS realtime_buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            mold_code INTEGER,
            molten_temp REAL,
            cast_pressure REAL,
            passorfail TEXT,
            defect INTEGER,
            data_id TEXT UNIQUE,
            data_hash TEXT,
            registration_time TEXT,
            original_timestamp TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 인덱스 생성
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_control_chart_timestamp ON control_chart_data(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_buffer_timestamp ON realtime_buffer(timestamp)')
    
    conn.commit()
    conn.close()

def get_synchronized_start_time():
    if 'system_start_time' not in st.session_state:
        current_time = time.time()
        # 시작 시점을 현재 시간으로 설정 (30초 단위 정렬하지 않음)
        st.session_state.system_start_time = current_time
        st.session_state.cycle_count = 0
    return st.session_state.system_start_time

class RealTimeDataManager:    
    @staticmethod
    def initialize_session_state():
        # 데이터베이스 초기화
        init_control_chart_database()
        
        defaults = {
            'ng_history': [],
            'collected_data': [],
            'control_chart_data': RealTimeDataManager._load_or_generate_chart_data(),
            'realtime_buffer': deque(maxlen=100),
            'last_chart_update': time.time(),
            'chart_update_interval': 180,
            'data_collection_started': False,
            'current_status': {},
            'last_collected_id': None,
            'processed_data_hashes': set()
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        # 데이터베이스에서 버퍼 복원
        RealTimeDataManager._restore_from_database()
    
    @staticmethod
    def _load_or_generate_chart_data():
        """데이터베이스에서 관리도 데이터 로드 또는 기본 데이터 생성"""
        conn = sqlite3.connect(CONTROL_CHART_DB)
        cursor = conn.cursor()
        
        # 최근 30개 데이터 조회
        cursor.execute('''
            SELECT timestamp, defect_rate, mean_rate, std_rate, ucl, lcl, usl, lsl
            FROM control_chart_data 
            ORDER BY timestamp DESC 
            LIMIT 30
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            # 데이터베이스에서 복원 (시간순 정렬)
            rows.reverse()
            time_points = [datetime.fromisoformat(row[0]) for row in rows]
            defect_rates = [row[1] for row in rows]
            
            # 최신 관리한계값 사용
            latest_row = rows[-1]
            control_limits = {
                'mean': latest_row[2],
                'std': latest_row[3],
                'ucl': latest_row[4],
                'lcl': latest_row[5],
                'usl': latest_row[6],
                'lsl': latest_row[7]
            } if latest_row[2] is not None else None
            
            chart_data = {
                'time_points': time_points,
                'defect_rates': defect_rates
            }
            
            if control_limits:
                chart_data['control_limits'] = control_limits
                
            return chart_data
        else:
            # 빈 데이터로 시작
            return {
                'time_points': [],
                'defect_rates': []
            }
    
    @staticmethod
    def _restore_from_database():
        """데이터베이스에서 버퍼 복원"""
        conn = sqlite3.connect(CONTROL_CHART_DB)
        cursor = conn.cursor()
        
        # 최근 24시간 버퍼 데이터 복원
        cutoff_time = datetime.now() - timedelta(hours=24)
        cursor.execute('''
            SELECT timestamp, mold_code, molten_temp, cast_pressure, passorfail, 
                defect, data_id, data_hash, original_timestamp
            FROM realtime_buffer 
            WHERE timestamp > ?
            ORDER BY timestamp
        ''', (cutoff_time.isoformat(),))
        
        buffer_rows = cursor.fetchall()
        
        for row in buffer_rows:
            data_point = {
                'timestamp': datetime.fromisoformat(row[0]),
                'mold_code': row[1],
                'molten_temp': row[2],
                'cast_pressure': row[3],
                'passorfail': row[4],
                'defect': row[5],
                'data_id': row[6],
                'data_hash': row[7],
                'original_timestamp': row[8]
            }
            st.session_state.realtime_buffer.append(data_point)
            st.session_state.processed_data_hashes.add(row[7])
        
        conn.close()
    
    @staticmethod
    def create_data_hash(data):
        """데이터의 고유 해시값 생성 (중복 방지용)"""
        if not isinstance(data, dict):
            return None
        
        hash_data = {
            'id': data.get('id'),
            'mold_code': data.get('mold_code'),
            'molten_temp': data.get('molten_temp'),
            'cast_pressure': data.get('cast_pressure'),
            'passorfail': data.get('passorfail')
        }
        data_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    @staticmethod
    def collect_realtime_data():
        current_data = st.session_state.get("current_status", {})
        
        if current_data and 'passorfail' in current_data:
            data_hash = RealTimeDataManager.create_data_hash(current_data)
            
            if data_hash in st.session_state.processed_data_hashes:
                return False
            
            current_timestamp = datetime.now().isoformat()
            data_id = f"{current_timestamp}_{data_hash}"
            
            data_point = {
                'id': current_data.get('id'),
                'timestamp': datetime.now(),
                'molten_temp': current_data.get('molten_temp', 0),
                'cast_pressure': current_data.get('cast_pressure', 0),
                'passorfail': current_data.get('passorfail', 'Pass'),
                'defect': 1 if current_data.get('passorfail') == 'Fail' else 0,
                'data_id': data_id,
                'data_hash': data_hash,
                'mold_code': current_data.get('mold_code', 0),
                'registration_time': current_data.get('registration_time', ''),
                'original_timestamp': current_data.get('timestamp', '')
            }
            
            st.session_state.realtime_buffer.append(data_point)
            st.session_state.processed_data_hashes.add(data_hash)
            st.session_state.last_collected_id = data_id
            
            RealTimeDataManager._save_buffer_point_to_db(data_point)
            
            return True
        return False
    
    @staticmethod
    def _save_buffer_point_to_db(data_point):
        try:
            conn = sqlite3.connect(CONTROL_CHART_DB)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO realtime_buffer 
                ( id,timestamp, molten_temp, cast_pressure, passorfail, 
                defect, data_id, data_hash,mold_code, registration_time,original_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data_point['id'],
                data_point['timestamp'].isoformat(),
                data_point['molten_temp'],
                data_point['cast_pressure'],
                data_point['passorfail'],
                data_point['defect'],
                data_point['data_id'],
                data_point['data_hash'],
                data_point['mold_code'],
                data_point['registration_time'],
                data_point['original_timestamp']
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"버퍼 데이터 저장 오류: {str(e)}")
    
    @staticmethod
    def calculate_defect_rate_from_buffer(time_window_minutes=60):
        if not st.session_state.realtime_buffer:
            return None
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=time_window_minutes)
        
        recent_data = [
            point for point in st.session_state.realtime_buffer 
            if point['timestamp'] >= cutoff_time
        ]
        
        if not recent_data:
            return None
        
        total_count = len(recent_data)
        defect_count = sum(point['defect'] for point in recent_data)
        defect_rate = (defect_count / total_count) * 100
        
        return {
            'timestamp': now,
            'defect_rate': defect_rate,
            'total_count': total_count,
            'defect_count': defect_count
        }
    
    @staticmethod
    def should_update_chart():
        current_time = time.time()
        last_update = st.session_state.get('last_chart_update', 0)
        interval = st.session_state.get('chart_update_interval', 180)
        
        return (current_time - last_update) >= interval
    
    @staticmethod
    def update_control_chart():
        if not st.session_state.realtime_buffer:
            return False
        defect_data = RealTimeDataManager.calculate_defect_rate_from_buffer()
        
        if defect_data is None:
            return False
        
        chart_data = st.session_state.control_chart_data
        chart_data['time_points'].append(defect_data['timestamp'])
        chart_data['defect_rates'].append(defect_data['defect_rate'])
        
        # 30개 제한
        if len(chart_data['time_points']) > 30:
            chart_data['time_points'] = chart_data['time_points'][-30:]
            chart_data['defect_rates'] = chart_data['defect_rates'][-30:]
        
        # 관리한계 재계산
        ucl, lcl, usl, lsl, mean_rate = RealTimeDataManager._recalculate_control_limits(chart_data)
        
        # 데이터베이스에 저장
        RealTimeDataManager._save_control_chart_to_db(defect_data, mean_rate, 
                                                       chart_data.get('control_limits', {}))
        
        st.session_state.last_chart_update = time.time()
        
        return True
    
    @staticmethod
    def _save_control_chart_to_db(defect_data, mean_rate, control_limits):
        """관리도 데이터를 데이터베이스에 저장"""
        try:
            conn = sqlite3.connect(CONTROL_CHART_DB)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO control_chart_data 
                (timestamp, defect_rate, total_count, defect_count, 
                 mean_rate, std_rate, ucl, lcl, usl, lsl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                defect_data['timestamp'].isoformat(),
                defect_data['defect_rate'],
                defect_data['total_count'],
                defect_data['defect_count'],
                mean_rate,
                control_limits.get('std'),
                control_limits.get('ucl'),
                control_limits.get('lcl'),
                control_limits.get('usl'),
                control_limits.get('lsl')
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"관리도 데이터 저장 오류: {str(e)}")
    
    @staticmethod
    def _recalculate_control_limits(chart_data):
        if len(chart_data['defect_rates']) < 5:
            recent_rates = chart_data['defect_rates']
            mean_rate = np.mean(recent_rates) if recent_rates else 5.0
            std_rate = np.std(recent_rates) if len(recent_rates) > 1 else 1.5
        else:
            recent_rates = chart_data['defect_rates']
            mean_rate = np.mean(recent_rates)
            std_rate = np.std(recent_rates)
        
        ucl = mean_rate + 3 * std_rate
        lcl = max(0, mean_rate - 3 * std_rate)
        usl = mean_rate + 2 * std_rate
        lsl = max(0, mean_rate - 2 * std_rate)
        
        chart_data['control_limits'] = {
            'mean': mean_rate,
            'std': std_rate,
            'ucl': ucl,
            'lcl': lcl,
            'usl': usl,
            'lsl': lsl
        }
        
        return ucl, lcl, usl, lsl, mean_rate
    
    @staticmethod
    def save_buffer_to_file():
        """파일로 버퍼 저장 (백업용)"""
        if not st.session_state.realtime_buffer:
            return False
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = snapshots_dir / f"realtime_buffer_{timestamp}.json"
            
            buffer_data = []
            for point in st.session_state.realtime_buffer:
                serializable_point = point.copy()
                serializable_point['timestamp'] = point['timestamp'].isoformat()
                buffer_data.append(serializable_point)
            
            snapshots_dir.mkdir(exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(buffer_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            st.error(f"버퍼 저장 오류: {str(e)}")
            return False

def reset_control_chart_database():
    """관리도 데이터베이스를 완전히 초기화"""
    try:
        # 기존 데이터베이스 파일 삭제
        if CONTROL_CHART_DB.exists():
            CONTROL_CHART_DB.unlink()
            print("기존 데이터베이스 파일 삭제 완료")
        
        # 새로운 데이터베이스 생성
        init_control_chart_database()
        print("새로운 데이터베이스 생성 완료")
        
        return True
    except Exception as e:
        print(f"데이터베이스 초기화 오류: {str(e)}")
        return False

def create_toast_notification(message, severity='info', duration=5000):
    """
    토스트 스타일 알림 생성
    
    Args:
        message (str): 알림 메시지
        severity (str): 'info', 'warning', 'critical', 'success'
        duration (int): 표시 시간 (밀리초)
    """
    toast_css = f"""
    <style>
    .toast-notification {{
        position: fixed;
        top: 100px;
        right: 20px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.2);
        z-index: 10001;
        animation: toastSlideIn 0.3s ease-out, toastSlideOut 0.3s ease-out {duration}ms forwards;
        max-width: 350px;
        word-wrap: break-word;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    
    .toast-notification.success {{
        background: rgba(52, 199, 89, 0.95);
        color: white;
        border-left: 4px solid #34c759;
    }}
    
    .toast-notification.warning {{
        background: rgba(255, 149, 0, 0.95);
        color: white;
        border-left: 4px solid #ff9500;
    }}
    
    .toast-notification.error {{
        background: rgba(255, 59, 48, 0.95);
        color: white;
        border-left: 4px solid #ff3b30;
    }}
    
    @keyframes toastSlideIn {{
        from {{
            transform: translateX(100%);
            opacity: 0;
        }}
        to {{
            transform: translateX(0);
            opacity: 1;
        }}
    }}
    
    @keyframes toastSlideOut {{
        from {{
            transform: translateX(0);
            opacity: 1;
        }}
        to {{
            transform: translateX(100%);
            opacity: 0;
        }}
    }}
    </style>
    """
    
    severity_class = {
        'info': '',
        'warning': 'warning',
        'critical': 'error',
        'success': 'success'
    }.get(severity, '')
    
    toast_html = f"""
    {toast_css}
    <div class="toast-notification {severity_class}">
        {message}
    </div>
    <script>
    setTimeout(function() {{
        const toast = document.querySelector('.toast-notification');
        if (toast && toast.parentNode) {{
            toast.parentNode.removeChild(toast);
        }}
    }}, {duration + 300});
    </script>
    """
    
    st.components.v1.html(toast_html, height=0)

def get_current_process_stage():
    if 'system_start_time' not in st.session_state:
        return "waiting", 0, 30  # 시스템 시작 전 대기 상태
    
    start_time = st.session_state.system_start_time
    current_time = time.time()
    elapsed_time = current_time - start_time
    time_in_cycle = elapsed_time % 30
    current_cycle = int(elapsed_time // 30)
    
    # 첫 번째 사이클 완료 여부 확인
    first_cycle_completed = st.session_state.get('first_cycle_completed', False)
    
    # 단계 결정
    if time_in_cycle < 10:
        stage = "melting"
        progress = int(time_in_cycle)
        max_progress = 10
    elif time_in_cycle < 25:
        stage = "casting"
        progress = int(time_in_cycle - 10)
        max_progress = 15
    else:
        stage = "cooling"
        progress = int(time_in_cycle - 25)
        max_progress = 5
    
    # 첫 번째 사이클인 경우 표시 텍스트 조정
    if current_cycle == 0 and not first_cycle_completed:
        # 첫 번째 사이클 진행 중
        return f"{stage}_first", progress, max_progress
    
    return stage, progress, max_progress

def create_control_chart():
    dark_mode = st.session_state.get('dark_mode', False)
    
    if RealTimeDataManager.should_update_chart():
        if RealTimeDataManager.update_control_chart():
            create_toast_notification("관리도가 자동 업데이트되었습니다!", "success")
            RealTimeDataManager.save_buffer_to_file()
    
    data = st.session_state.control_chart_data
    
    # 데이터가 없으면 빈 차트 표시
    if not data['defect_rates']:
        st.info("실시간 데이터 수집을 시작하면 관리도가 표시됩니다.")
        return
    
    if 'control_limits' in data and len(data['defect_rates']) >= 5:
        limits = data['control_limits']
        mean_rate = limits['mean']
        ucl = limits['ucl']
        lcl = limits['lcl']
        usl = limits['usl']
        lsl = limits['lsl']
    else:
        mean_rate = np.mean(data['defect_rates'])
        std_rate = np.std(data['defect_rates'])
        ucl = mean_rate + 3 * std_rate
        lcl = max(0, mean_rate - 3 * std_rate)
        usl = mean_rate + 2 * std_rate
        lsl = max(0, mean_rate - 2 * std_rate)
    
    # 스타일 모듈에서 차트 옵션 생성
    option = create_control_chart_options(data, ucl, lcl, usl, lsl, mean_rate, dark_mode)
    st_echarts(options=option, height="500px")
    
    # 간단한 상태 표시
    display_compact_update_status()
    
    col1, col2, col3, col4 = st.columns(4)
    
    out_of_control = sum(1 for rate in data['defect_rates'] if rate > ucl or rate < lcl)
    warning_points = sum(1 for rate in data['defect_rates'] if (lsl < rate <= usl) or (usl <= rate <= ucl))
    
    with col1:
        st.metric("평균 불량률 (CL)", f"{mean_rate:.2f}%")
    
    with col2:
        st.metric("관리한계 이탈", f"{out_of_control}회", delta=f"{out_of_control-2}" if out_of_control > 2 else None)
    
    with col3:
        st.metric("경고 구간", f"{warning_points}회")
    
    with col4:
        current_rate = data['defect_rates'][-1]
        if current_rate > ucl or current_rate < lcl:
            status = "관리이탈"
        elif current_rate > usl or current_rate < lsl:
            status = "경고"
        else:
            status = "정상"
        
        st.metric("현재 상태", status)

def display_compact_update_status():
    current_time = time.time()
    last_update = st.session_state.get('last_chart_update', 0)
    interval = st.session_state.get('chart_update_interval', 180)
    buffer_size = len(st.session_state.get('realtime_buffer', []))
    
    time_since_update = current_time - last_update
    time_until_next = interval - time_since_update
    
    if time_until_next > 0:
        minutes = int(time_until_next // 60)
        seconds = int(time_until_next % 60)
        next_update_str = f"{minutes}:{seconds:02d}"
    else:
        next_update_str = "대기중"
    
    collection_status = "활성" if st.session_state.get('data_collection_started', False) else "중지"
    last_collected = st.session_state.get('last_collected_id', None)
    collection_indicator = "수집중" if last_collected else "대기중"
    
    # 스타일 모듈에서 상태 HTML 생성
    status_html = create_status_html(collection_status, buffer_size, collection_indicator, next_update_str)
    st.markdown(status_html, unsafe_allow_html=True)

def create_mold_status_overview():
    mold_codes = [8412, 8573, 8600, 8722, 8917]
    current_data = st.session_state.get("current_status", {})
    current_mold = current_data.get("mold_code", None)
    dark_mode = st.session_state.get('dark_mode', False)
    
    mold_info = {
        8412: {"name": "A Mold", "type": "Heavy Duty"},
        8573: {"name": "B Mold", "type": "Precision"},
        8600: {"name": "C Mold", "type": "Standard"},
        8722: {"name": "D Mold", "type": "Electronics"},
        8917: {"name": "E Mold", "type": "Custom"}
    }
    
    mold_mapping = {
        0.0: 8412, 0: 8412,
        1.0: 8573, 1: 8573,
        2.0: 8600, 2: 8600,
        3.0: 8722, 3: 8722,
        4.0: 8917, 4: 8917
    }
    
    cols = st.columns(len(mold_codes))
    
    for i, mold_code in enumerate(mold_codes):
        with cols[i]:
            is_active = False
            if current_mold is not None:
                try:
                    mapped_mold = mold_mapping.get(float(current_mold))
                    is_active = (mapped_mold == mold_code)
                except (ValueError, TypeError):
                    try:
                        mapped_mold = mold_mapping.get(int(float(str(current_mold))))
                        is_active = (mapped_mold == mold_code)
                    except:
                        is_active = False
            
            info = mold_info.get(mold_code, {"name": "Unknown", "type": "Standard"})
            
            # 스타일 모듈에서 몰드 카드 HTML 생성
            card_html = create_mold_card_html(mold_code, info, is_active, dark_mode)
            st.markdown(card_html, unsafe_allow_html=True)

def create_process_visualization():
    stage_info = get_current_process_stage()
    
    if len(stage_info) == 3:
        stage, progress, max_progress = stage_info
    else:
        stage, progress, max_progress = "waiting", 0, 30
    
    dark_mode = st.session_state.get('dark_mode', False)
    
    # 첫 번째 사이클인지 확인
    is_first_cycle = stage.endswith('_first')
    base_stage = stage.replace('_first', '') if is_first_cycle else stage
    
    stages = [
        {
            "id": "melting", 
            "label": "용융/가열" + (" (첫 사이클)" if is_first_cycle and base_stage == "melting" else ""), 
            "icon": "HEAT", 
            "desc": "용융온도 제어", 
            "duration": "10초"
        },
        {
            "id": "casting", 
            "label": "주조/압력" + (" (첫 사이클)" if is_first_cycle and base_stage == "casting" else ""), 
            "icon": "CAST", 
            "desc": "주조압력 적용", 
            "duration": "15초"
        },
        {
            "id": "cooling", 
            "label": "냉각/완료" + (" (첫 사이클)" if is_first_cycle and base_stage == "cooling" else ""), 
            "icon": "COOL", 
            "desc": "금형 냉각", 
            "duration": "5초"
        }
    ]
    
    # 대기 상태 처리
    if stage == "waiting":
        st.info("데이터 수집을 시작하면 공정 단계가 표시됩니다.")
        return "waiting", 0
    
    # 스타일 모듈에서 공정 표시 HTML 생성
    progress_html = create_process_indicator_html(stages, base_stage, progress, max_progress, dark_mode)
    st.markdown(progress_html, unsafe_allow_html=True)
    
    # 타이머 표시
    if 'system_start_time' in st.session_state:
        start_time = st.session_state.system_start_time
        current_time = time.time()
        elapsed_time = current_time - start_time
        time_in_cycle = elapsed_time % 30
        remaining_time = 30 - time_in_cycle
        
        # 첫 번째 사이클 정보 표시
        current_cycle = int(elapsed_time // 30)
        first_cycle_completed = st.session_state.get('first_cycle_completed', False)
        
        if current_cycle == 0 and not first_cycle_completed:
            cycle_info = f"첫 번째 사이클 진행 중 (데이터 수집 준비)"
        elif not first_cycle_completed:
            cycle_info = f"첫 번째 사이클 완료됨, 데이터 수집 시작"
        else:
            cycle_info = f"사이클 {current_cycle + 1} 진행 중"
        
        # 스타일 모듈에서 타이머 HTML 생성 (사이클 정보 포함)
        timer_html = create_timer_html(remaining_time, dark_mode, cycle_info)
        st.markdown(timer_html, unsafe_allow_html=True)
    
    return base_stage, progress

def create_app_gauge(title, value, min_val=0, max_val=100, unit="", target_range=None):
    dark_mode = st.session_state.get('dark_mode', False)
    
    # 스타일 모듈에서 게이지 차트 옵션 생성
    option = create_gauge_chart_options(title, value, min_val, max_val, unit, target_range, dark_mode)
    st_echarts(options=option, height="280px")

key_metrics = [
        {"key": "molten_temp", "label": "용융온도", "unit": "°C"},
        {"key": "cast_pressure", "label": "주조압력", "unit": "MPa"},
        {"key": "upper_mold_temp1", "label": "상금형온도", "unit": "°C"},
        {"key": "passorfail", "label": "품질판정", "unit": ""}
    ]

def create_key_metrics(key_metrics):
    current_data = st.session_state.get("current_status", {})
    
    if not current_data:
        st.info("실시간 데이터를 기다리는 중...")
        return
    
    cols = st.columns(4)
    for i, metric in enumerate(key_metrics):
        key = metric["key"]
        if key in current_data:
            value = current_data[key]
            
            with cols[i]:
                if key == "passorfail":
                    delta = None
                    if value == "Pass":
                        st.metric(f"{metric['label']}", "Pass", delta=delta)
                    else:
                        st.metric(f"{metric['label']}", "Fail", delta=delta)
                else:
                    prev_key = f"prev_{key}"
                    prev_value = st.session_state.get(prev_key)
                    delta = None
                    
                    if prev_value is not None:
                        diff = value - prev_value
                        if abs(diff) > 0.01:
                            delta = f"{diff:+.1f}"
                    
                    st.session_state[prev_key] = value
                    st.metric(
                        f"{metric['label']}", 
                        f"{value:.1f} {metric['unit']}", 
                        delta=delta
                    )

def create_ng_data_from_db_with_pagination():
    try:
        min_date, max_date = get_available_date_range()
        
        # 빠른 날짜 선택과 사용자 지정 선택
        filter_type_col, quick_select_col = st.columns([1, 3])
        
        with filter_type_col:
            filter_mode = st.selectbox(
                "필터 유형",
                ["빠른 선택", "사용자 지정"],
                key="filter_mode"
            )
        
        # 적용된 필터 상태를 세션에 저장
        if 'applied_filter_settings' not in st.session_state:
            st.session_state.applied_filter_settings = {
                'mode': '빠른 선택',
                'quick_option': '전체',
                'start_date': min_date if min_date else datetime.now().date() - timedelta(days=7),
                'end_date': max_date if max_date else datetime.now().date(),
                'start_time': datetime.strptime("00:00", "%H:%M").time(),
                'end_time': datetime.strptime("23:59", "%H:%M").time()
            }
        
        temp_start_date = None
        temp_end_date = None
        temp_start_time = None
        temp_end_time = None
        temp_quick_option = None
        
        if filter_mode == "빠른 선택":
            with quick_select_col:
                temp_quick_option = st.selectbox(
                    "기간 선택",
                    ["오늘", "최근 7일", "최근 한달", "전체"],
                    key="temp_quick_date_option"
                )
                
                today = datetime.now().date()
                
                if temp_quick_option == "오늘":
                    temp_start_date = today
                    temp_end_date = today
                elif temp_quick_option == "최근 7일":
                    temp_start_date = today - timedelta(days=7)
                    temp_end_date = today
                elif temp_quick_option == "최근 한달":
                    temp_start_date = today - timedelta(days=30)
                    temp_end_date = today
                else:
                    temp_start_date = min_date if min_date else today - timedelta(days=365)
                    temp_end_date = max_date if max_date else today
        
        else:
            with quick_select_col:
                date_col1, date_col2 = st.columns(2)
                
                with date_col1:
                    temp_start_date = st.date_input(
                        "시작 날짜",
                        value=st.session_state.applied_filter_settings['start_date'],
                        min_value=min_date if min_date else datetime.now().date() - timedelta(days=365),
                        max_value=max_date if max_date else datetime.now().date(),
                        key="temp_ng_start_date"
                    )
                
                with date_col2:
                    temp_end_date = st.date_input(
                        "종료 날짜", 
                        value=st.session_state.applied_filter_settings['end_date'],
                        min_value=min_date if min_date else datetime.now().date() - timedelta(days=365),
                        max_value=max_date if max_date else datetime.now().date(),
                        key="temp_ng_end_date"
                    )
                
                # 시간 선택
                st.markdown("**시간 범위 (선택사항)**")
                time_col1, time_col2 = st.columns(2)
                
                with time_col1:
                    temp_start_time = st.time_input(
                        "시작 시간",
                        value=st.session_state.applied_filter_settings['start_time'],
                        key="temp_ng_start_time"
                    )
                
                with time_col2:
                    temp_end_time = st.time_input(
                        "종료 시간",
                        value=st.session_state.applied_filter_settings['end_time'],
                        key="temp_ng_end_time"
                    )
        
        # 공통 제어 버튼
        control_col1, control_col2,control_col3, control_col4, control_col5, control_col6 = st.columns([1, 1, 1, 1,1,1])
        
        # 필터 적용 버튼
        filter_applied = False
        with control_col5:
            if st.button("필터 적용", key="apply_date_filter", use_container_width=True):
                # 임시 설정을 적용된 설정으로 저장
                st.session_state.applied_filter_settings = {
                    'mode': filter_mode,
                    'quick_option': temp_quick_option if temp_quick_option else '전체',
                    'start_date': temp_start_date,
                    'end_date': temp_end_date,
                    'start_time': temp_start_time if temp_start_time else datetime.strptime("00:00", "%H:%M").time(),
                    'end_time': temp_end_time if temp_end_time else datetime.strptime("23:59", "%H:%M").time()
                }
                st.session_state.ng_current_page = 1
                filter_applied = True
                create_toast_notification("필터가 적용되었습니다", "success")
                st.rerun()
        
        with control_col6:
            if st.button("초기화", key="reset_date_filter", use_container_width=True):
                st.session_state.ng_current_page = 1
                # 기본값으로 초기화
                st.session_state.applied_filter_settings = {
                    'mode': '빠른 선택',
                    'quick_option': '전체',
                    'start_date': min_date if min_date else datetime.now().date() - timedelta(days=7),
                    'end_date': max_date if max_date else datetime.now().date(),
                    'start_time': datetime.strptime("00:00", "%H:%M").time(),
                    'end_time': datetime.strptime("23:59", "%H:%M").time()
                }
                # 임시 선택값들도 초기화
                keys_to_reset = ['temp_ng_start_date', 'temp_ng_end_date', 'temp_ng_start_time', 
                            'temp_ng_end_time', 'filter_mode', 'temp_quick_date_option']
                for key in keys_to_reset:
                    if key in st.session_state:
                        del st.session_state[key]
                create_toast_notification("필터가 초기화되었습니다", "info")
                st.rerun()
        
        # 현재 적용된 설정을 사용하여 쿼리 수행
        applied_settings = st.session_state.applied_filter_settings
        
        # 날짜 및 시간 검증 (적용된 설정 기준)
        if applied_settings['mode'] == "사용자 지정":
            if applied_settings['start_date'] and applied_settings['end_date']:
                start_dt = datetime.combine(applied_settings['start_date'], applied_settings['start_time'])
                end_dt = datetime.combine(applied_settings['end_date'], applied_settings['end_time'])
                if start_dt > end_dt:
                    st.error("시작 날짜/시간이 종료 날짜/시간보다 늦을 수 없습니다.")
                    return
            elif applied_settings['start_date'] and applied_settings['end_date'] and applied_settings['start_date'] > applied_settings['end_date']:
                st.error("시작 날짜가 종료 날짜보다 늦을 수 없습니다.")
                return
        
        # 쿼리용 날짜/시간 준비 (적용된 설정 기준)
        query_start_datetime = None
        query_end_datetime = None
        
        if applied_settings['mode'] == "빠른 선택":
            # 빠른 선택은 전체 날짜 범위 (00:00 ~ 23:59)
            if applied_settings['start_date'] and applied_settings['end_date']:
                query_start_datetime = datetime.combine(applied_settings['start_date'], datetime.min.time())
                query_end_datetime = datetime.combine(applied_settings['end_date'], datetime.max.time())
        else:
            # 사용자 지정은 선택한 시간 포함
            if applied_settings['start_date'] and applied_settings['end_date']:
                query_start_datetime = datetime.combine(applied_settings['start_date'], applied_settings['start_time'])
                query_end_datetime = datetime.combine(applied_settings['end_date'], applied_settings['end_time'])
        
        # 선택된 날짜/시간 범위로 불량 데이터 개수 조회
        total_count = get_fail_data_count_by_datetime(query_start_datetime, query_end_datetime)
        
        # 현재 적용된 필터 정보 표시
        if applied_settings['mode'] == "빠른 선택":
            date_range_info = f"**{applied_settings['quick_option']}** 기간의 불량 데이터"
        else:
            if query_start_datetime and query_end_datetime:
                start_str = query_start_datetime.strftime("%Y-%m-%d %H:%M")
                end_str = query_end_datetime.strftime("%Y-%m-%d %H:%M")
                date_range_info = f"**{start_str}** ~ **{end_str}** 기간의 불량 데이터"
            else:
                date_range_info = f"**{applied_settings['start_date']}** ~ **{applied_settings['end_date']}** 기간의 불량 데이터"
        
        # 현재 설정이 임시 설정과 다른지 확인하여 알림 표시
        settings_changed = False
        if filter_mode == "빠른 선택":
            if temp_quick_option and temp_quick_option != applied_settings['quick_option']:
                settings_changed = True
        else:
            if (temp_start_date != applied_settings['start_date'] or 
                temp_end_date != applied_settings['end_date'] or
                temp_start_time != applied_settings['start_time'] or
                temp_end_time != applied_settings['end_time']):
                settings_changed = True
        
        if settings_changed:
            st.info("설정이 변경되었습니다. '필터 적용' 버튼을 눌러 적용하세요.")
            
        if total_count == 0:
            st.info(f"{date_range_info}: 데이터가 없습니다.")
            return
        
        st.markdown(f"{date_range_info}: **{total_count:,}개**")
        
        # 페이지네이션 설정
        items_per_page = 15
        total_pages = (total_count + items_per_page - 1) // items_per_page
        
        # 페이지네이션 상태 초기화
        if 'ng_current_page' not in st.session_state:
            st.session_state.ng_current_page = 1
        
        # 현재 페이지가 유효 범위를 벗어난 경우 조정
        if st.session_state.ng_current_page > total_pages:
            st.session_state.ng_current_page = max(1, total_pages)
        
        # 현재 페이지 데이터 조회 (날짜/시간 필터 적용)
        current_page = st.session_state.ng_current_page
        offset = (current_page - 1) * items_per_page
        current_page_data = get_fail_data_with_pagination_by_datetime(
            limit=items_per_page, 
            offset=offset,
            start_datetime=query_start_datetime,
            end_datetime=query_end_datetime
        )
        
        # 데이터 요약 정보
        start_idx = offset + 1
        end_idx = min(offset + items_per_page, total_count)
        
        if current_page_data:
            # 데이터 포맷 변환
            formatted_data = []
            for fail_data in current_page_data:
                formatted_entry = {
                    "ID": fail_data.get("id", ""),
                    "생성시간": fail_data.get("time", ""),
                    "등록시간": fail_data.get("registered_date", ""),
                    "몰드코드": fail_data.get("mold_code", ""),
                    "용융온도": f"{fail_data.get('molten_temp', 0):.1f}",
                    "주조압력": f"{fail_data.get('cast_pressure', 0):.1f}",
                    "상금형온도": f"{fail_data.get('upper_mold_temp1', 0):.1f}",
                    "판정": fail_data.get("passorfail", "")
                }
                formatted_data.append(formatted_entry)
            
            # 데이터프레임 표시
            df_ng = pd.DataFrame(formatted_data)
            st.dataframe(df_ng, use_container_width=True, hide_index=True)
            
            # 페이지네이션 컨트롤
            col1, col2, col3 = st.columns([1, 5, 1])
            
            with col2:
                # 페이지네이션 컨트롤을 한 줄로 배치
                pagination_container = st.container()
                
                with pagination_container:
                    # 페이지 정보와 직접 입력을 한 줄로 배치
                    info_col, input_col, btn_col = st.columns([2, 1, 1])
                    
                    with info_col:
                        st.markdown(f"**페이지 {current_page} / {total_pages}** (총 {total_count}개)")
                        st.markdown(f"<small>표시: {start_idx}-{end_idx}번째 데이터</small>", unsafe_allow_html=True)
                    
                    with input_col:
                        new_page = st.number_input(
                            "페이지 이동", 
                            min_value=1, 
                            max_value=total_pages,
                            value=current_page,
                            key="direct_pagination_input",
                            label_visibility="collapsed"
                        )
                    
                    with btn_col:
                        if st.button("이동", key="direct_go_button", use_container_width=True):
                            st.session_state.ng_current_page = new_page
                            st.rerun()
                    
                    # 네비게이션 버튼들을 한 줄로 예쁘게 배치
                    st.markdown("---")
                    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5, nav_col6 = st.columns([2, 2, 3, 2, 3, 3])
                    
                    with nav_col1:
                        if st.button("처음", disabled=(current_page <= 1), key="backup_first", use_container_width=True):
                            st.session_state.ng_current_page = 1
                            st.rerun()
                    
                    with nav_col2:
                        if st.button("이전", disabled=(current_page <= 1), key="backup_prev", use_container_width=True):
                            st.session_state.ng_current_page -= 1
                            st.rerun()
                    
                    with nav_col3:
                        # 현재 페이지 표시 (비활성화된 버튼으로)
                        st.button(f"현재: {current_page}", disabled=True, key="current_page_indicator", use_container_width=True)
                    
                    with nav_col4:
                        if st.button("다음", disabled=(current_page >= total_pages), key="backup_next", use_container_width=True):
                            st.session_state.ng_current_page += 1
                            st.rerun()
                    
                    with nav_col5:
                        if st.button("마지막", disabled=(current_page >= total_pages), key="backup_last", use_container_width=True):
                            st.session_state.ng_current_page = total_pages
                            st.rerun()
                    
                    with nav_col6:
                        if st.button("새로고침", key="refresh_button", use_container_width=True):
                            st.rerun()
                        
        else:
            st.warning("해당 페이지에 데이터가 없습니다.")
            
    except Exception as e:
        st.error(f"불량 데이터 조회 오류: {str(e)}")
        
        # 오류 발생 시 기본 기능으로 폴백
        st.info("날짜 필터링 중 오류가 발생하여 전체 데이터를 표시합니다.")
        
        # 기존 코드 (날짜 필터 없는 버전)
        total_count = get_fail_data_count()
        
        if total_count == 0:
            st.info("데이터베이스에 불량 데이터가 없습니다.")
            return
        
        items_per_page = 15
        total_pages = (total_count + items_per_page - 1) // items_per_page
        
        if 'ng_current_page' not in st.session_state:
            st.session_state.ng_current_page = 1
        
        current_page = st.session_state.ng_current_page
        offset = (current_page - 1) * items_per_page
        current_page_data = get_fail_data_with_pagination(
            limit=items_per_page, 
            offset=offset
        )
        
        if current_page_data:
            formatted_data = []
            for fail_data in current_page_data:
                formatted_entry = {
                    "ID": fail_data.get("id", ""),
                    "생성시간": fail_data.get("time", ""),
                    "등록시간": fail_data.get("registered_date", ""),
                    "몰드코드": fail_data.get("mold_code", ""),
                    "용융온도": f"{fail_data.get('molten_temp', 0):.1f}",
                    "주조압력": f"{fail_data.get('cast_pressure', 0):.1f}",
                    "상금형온도": f"{fail_data.get('upper_mold_temp1', 0):.1f}",
                    "판정": fail_data.get("passorfail", "")
                }
                formatted_data.append(formatted_entry)
            
            df_ng = pd.DataFrame(formatted_data)
            st.dataframe(df_ng, use_container_width=True, hide_index=True)

def render_cast_pressure():
    st.markdown("#### 주조압력 모니터링")
    
    current_pressure = 0
    if st.session_state.current_status and "cast_pressure" in st.session_state.current_status:
        current_pressure = st.session_state.current_status["cast_pressure"]
    
    try:
        create_app_gauge(
            title="주조압력", 
            value=current_pressure, 
            min_val=0, 
            max_val=100,
            unit=" MPa",
            target_range=(70, 80)
        )
    except Exception as e:
        st.error(f"게이지 차트 오류: {e}")
        st.metric("주조압력", f"{current_pressure:.1f} MPa")

def render_production_status():
    st.markdown("### 생산 현황")
    overall_cols = st.columns(3)
    total_count = len(get_all_sensor_data())
    pass_count  = len(get_all_pass_sensor_data())
    fail_count  = total_count - pass_count
    pass_rate   = (pass_count / total_count * 100) if total_count else 0.0
    
    with overall_cols[0]:
        st.metric("총 생산량", f"{total_count:,}")
    with overall_cols[1]:
        st.metric("양품 / 불량품", f"{pass_count:,} / {fail_count:,}")
    with overall_cols[2]:
        st.metric("양품률", f"{pass_rate:.1f}%")

    # 오늘 생산 현황
    today_cols = st.columns(3)
    today_total = len(get_today_sensor_data())
    today_pass  = len(get_today_pass_data())
    today_fail  = today_total - today_pass
    today_rate  = (today_pass / today_total * 100) if today_total else 0.0

    with today_cols[0]:
        st.metric("오늘 총 생산량", f"{today_total:,}")
    with today_cols[1]:
        st.metric("오늘 양품 / 불량품", f"{today_pass:,} / {today_fail:,}")
    with today_cols[2]:
        st.metric("오늘 양품률", f"{today_rate:.1f}%")

def render_quality_overview():
    st.markdown("#### 핵심 품질 지표")
    create_mold_status_overview()
    create_key_metrics(key_metrics)
    st.markdown("---")
    
    info1, info2 = st.columns(2)
    with info1:
        try:
            count = len(list(snapshots_dir.glob("*snapshot*.json")))
        except:
            count = 0
        st.metric("저장된 스냅샷", f"{count}개")
    
    with info2:
        if st.session_state.get("data_collection_started", False):
            last = st.session_state.get("last_snapshot_time", time.time())
            mins = (time.time() - last) / 60
            next_in = max(0, 60 - mins)
            label = f"{next_in:.1f}분 후" if next_in>0 else "곧 저장"
        else:
            label = "60분 간격"
        st.metric("다음 저장", label)
    # 현재 사이클 정보 표시
    if st.session_state.get('data_collection_started', False) and 'system_start_time' in st.session_state:
        start_time = st.session_state.system_start_time
        current_time = time.time()
        elapsed_time = current_time - start_time
        current_cycle = int(elapsed_time // 30) + 1
        first_cycle_completed = st.session_state.get('first_cycle_completed', False)
            
        cycle_cols = st.columns(2)
        with cycle_cols[0]:
            st.metric("현재 사이클", f"{current_cycle}")
        with cycle_cols[1]:
            status = "데이터 수집 중" if first_cycle_completed else "준비 중"
            st.metric("수집 상태", status)

def get_control_chart_statistics():
    """관리도 통계 정보 조회"""
    try:
        conn = sqlite3.connect(CONTROL_CHART_DB)
        cursor = conn.cursor()
        
        # 최근 24시간 통계
        yesterday = datetime.now() - timedelta(hours=24)
        cursor.execute('''
            SELECT COUNT(*), AVG(defect_rate), MIN(defect_rate), MAX(defect_rate)
            FROM control_chart_data 
            WHERE timestamp > ?
        ''', (yesterday.isoformat(),))
        
        stats = cursor.fetchone()
        conn.close()
        
        if stats and stats[0] > 0:
            return {
                'count': stats[0],
                'avg_rate': stats[1],
                'min_rate': stats[2],
                'max_rate': stats[3]
            }
        else:
            return None
    except Exception as e:
        st.error(f"통계 조회 오류: {str(e)}")
        return None

def run():
    # reset_control_chart_database()
    st.markdown("### 실시간 공정 현황")
    RealTimeDataManager.initialize_session_state()

    if st.session_state.get('data_collection_started', False):
        if st.session_state.get('current_status', {}):
            RealTimeDataManager.collect_realtime_data()
    
    try:
        create_control_chart()
    except Exception as e:
        st.error(f"관리도 생성 오류: {str(e)}")
        st.info("관리도를 로드하는 중입니다...")
    
    st.markdown("---")
    st.markdown("#### 다이캐스팅 공정 단계")
    try:
        current_stage, progress = create_process_visualization()
    except Exception as e:
        st.error(f"공정 시각화 오류: {str(e)}")
        stage, progress, max_progress = get_current_process_stage()
        progress_percent = (progress / max_progress) * 100
        st.info(f"현재 단계: {stage} ({progress_percent:.0f}% 진행중)")

    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        render_cast_pressure()
        render_production_status()
    
    with col_right:
        render_quality_overview()
    
    st.markdown("---")
    st.markdown("### 최근 불량 데이터 이력")
    try:
        create_ng_data_from_db_with_pagination()
        
        from utils.data_utils import get_quality_statistics
        stats = get_quality_statistics(hours=24)
        
        st.markdown("---")
        if stats.get('total_count', 0) > 0:
            st.markdown("#### 24시간 품질 통계")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("총 생산", f"{stats['total_count']:,}개")
            with col2:
                st.metric("양품", f"{stats['pass_count']:,}개")
                st.metric("불량품", f"{stats['fail_count']:,}개")
            with col4:
                st.metric("양품률", f"{stats['pass_rate']:.1f}%")
        
        # 관리도 통계 표시
        chart_stats = get_control_chart_statistics()
        if chart_stats:
            st.markdown("#### 24시간 관리도 통계")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("측정 횟수", f"{chart_stats['count']:,}회")
            with col2:
                st.metric("평균 불량률", f"{chart_stats['avg_rate']:.2f}%")
            with col3:
                st.metric("최소 불량률", f"{chart_stats['min_rate']:.2f}%")
            with col4:
                st.metric("최대 불량률", f"{chart_stats['max_rate']:.2f}%")
    
    except Exception as e:
        st.error(f"데이터베이스 연동 오류: {str(e)}")
        st.info("임시로 세션 데이터를 사용합니다.")
        
        current_data = st.session_state.get("current_status", None)
        if current_data and current_data.get("passorfail") == "Fail":
            ng_entry = {
                "시간": current_data.get("timestamp", ""),
                "몰드코드": current_data.get("mold_code", ""),
                "용융온도": current_data.get("molten_temp", 0),
                "주조압력": current_data.get("cast_pressure", 0),
                "판정": current_data.get("passorfail", "")
            }
            if 'ng_history' not in st.session_state:
                st.session_state.ng_history = []
            if not any(e.get("시간") == ng_entry["시간"] for e in st.session_state.ng_history):
                st.session_state.ng_history.append(ng_entry)
        
        if st.session_state.get('ng_history', []):
            recent_ng = st.session_state.ng_history[-5:]
            df_ng = pd.DataFrame(recent_ng)
            st.dataframe(df_ng, use_container_width=True, hide_index=True)
        else:
            st.info("아직 불량 데이터가 없습니다.")