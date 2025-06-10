# utils/data_utils.py
import json
import logging
import pandas as pd
from sqlalchemy import create_engine, text
import os
from typing import Dict, List
from pathlib import Path
import hashlib
import streamlit as st

# datetime 관련 import - 이것만 사용
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parents[1]
snapshots_dir = project_root / "snapshots"
DATA_FILE = project_root / "data/collected_data.json"
TEST_PY_FILE = project_root / "data/test.py"
DATA_FILE_TODAY = project_root / "data/collected_data_today.json"

# TimescaleDB 연결 설정
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'timescaledb'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'diecasting_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'securepassword123')
}

def get_db_engine():
    """데이터베이스 엔진 생성"""
    try:
        connection_string = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        engine = create_engine(connection_string, pool_pre_ping=True)
        return engine
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return None

def init_timescale_db():
    """TimescaleDB 초기화 및 테이블 생성"""
    engine = get_db_engine()
    if not engine:
        logger.error("데이터베이스 엔진을 생성할 수 없습니다.")
        return False
    
    try:
        with engine.connect() as conn:
            # 센서 데이터 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sensor_data (
                    time TIMESTAMPTZ NOT NULL,
                    id BIGINT,
                    line TEXT,
                    mold_name TEXT,
                    working TEXT,
                    molten_temp REAL,
                    facility_operation_cycletime INTEGER,
                    production_cycletime INTEGER,
                    low_section_speed REAL,
                    high_section_speed REAL,
                    cast_pressure REAL,
                    biscuit_thickness REAL,
                    upper_mold_temp1 REAL,
                    upper_mold_temp2 REAL,
                    lower_mold_temp1 REAL,
                    lower_mold_temp2 REAL,
                    sleeve_temperature REAL,
                    physical_strength REAL,
                    coolant_temperature REAL,
                    ems_operation_time INTEGER,
                    mold_code INTEGER,
                    passorfail TEXT,
                    prediction_confidence REAL DEFAULT 0.0,
                    data_hash TEXT UNIQUE,
                    source TEXT DEFAULT 'test.py'
                );
            """))
            
            # 하이퍼테이블로 변환 (TimescaleDB)
            try:
                conn.execute(text("""
                    SELECT create_hypertable('sensor_data', 'time', 
                                            if_not_exists => TRUE);
                """))
                logger.info("TimescaleDB 하이퍼테이블 생성 완료")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("하이퍼테이블이 이미 존재합니다.")
                else:
                    logger.warning(f"하이퍼테이블 생성 건너뜀: {e}")
            
            # 인덱스 생성
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sensor_data_passorfail 
                ON sensor_data (passorfail, time DESC);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sensor_data_mold_code 
                ON sensor_data (mold_code, time DESC);
            """))
            
            # 데이터 해시 인덱스 생성 (중복 방지용)
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sensor_data_hash 
                ON sensor_data (data_hash);
            """))
            
            conn.commit()
            logger.info("TimescaleDB 초기화 완료")
            return True
            
    except Exception as e:
        logger.error(f"TimescaleDB 초기화 실패: {e}")
        return False

def create_data_hash(data: Dict) -> str:
    """데이터의 고유 해시값 생성 (중복 방지용)"""
    if not isinstance(data, dict):
        return None
    
    # timestamp와 source를 제외한 핵심 데이터로 해시 생성
    hash_data = {
        'id': data.get('id'),
        'mold_code': data.get('mold_code'),
        'molten_temp': data.get('molten_temp'),
        'cast_pressure': data.get('cast_pressure'),
        'passorfail': data.get('passorfail'),
        'upper_mold_temp1': data.get('upper_mold_temp1'),
        'working': data.get('working')
    }
    
    # None 값 제거
    hash_data = {k: v for k, v in hash_data.items() if v is not None}
    
    data_str = json.dumps(hash_data, sort_keys=True)
    return hashlib.md5(data_str.encode()).hexdigest()

def is_duplicate_data(data_hash: str) -> bool:
    """데이터 해시로 중복 확인"""
    engine = get_db_engine()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM sensor_data WHERE data_hash = :hash"),
                {"hash": data_hash}
            )
            count = result.scalar()
            return count > 0
    except Exception as e:
        logger.error(f"중복 확인 실패: {e}")
        return False

def save_to_timescale(data: Dict) -> bool:
    """TimescaleDB에 데이터 저장 (중복 방지 포함) - 데이터 타입 변환 추가"""
    engine = get_db_engine()
    if not engine:
        return False
    
    try:
        # 데이터 해시 생성
        data_hash = create_data_hash(data)
        if not data_hash:
            logger.warning("데이터 해시 생성 실패")
            return False
        
        # 중복 확인
        if is_duplicate_data(data_hash):
            logger.info(f"중복 데이터 감지, 저장 건너뜀: {data_hash[:8]}")
            return False
        
        # 데이터 변환 및 타입 처리
        def safe_convert_to_int(value):
            """안전한 정수 변환"""
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                # 한글이나 텍스트가 포함된 경우 None 반환
                if any(ord(char) > 127 for char in value):  # 비ASCII 문자 확인
                    return None
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return None
            return None
        
        def safe_convert_to_float(value):
            """안전한 실수 변환"""
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            return None
        
        # 데이터 변환
        db_data = {
            'time': data.get('timestamp', datetime.now().isoformat()),
            'id': safe_convert_to_int(data.get('id')),
            'line': str(data.get('line', '')) if data.get('line') is not None else None,
            'mold_name': str(data.get('mold_name', '')) if data.get('mold_name') is not None else None,
            
            # working 컬럼: 문자열 그대로 저장 (DB 스키마가 TEXT로 변경된 경우)
            'working': str(data.get('working', '')) if data.get('working') is not None else None,
            
            # 숫자 컬럼들 안전 변환
            'molten_temp': safe_convert_to_float(data.get('molten_temp')),
            'facility_operation_cycletime': safe_convert_to_int(data.get('facility_operation_cycleTime')),
            'production_cycletime': safe_convert_to_int(data.get('production_cycletime')),
            'low_section_speed': safe_convert_to_float(data.get('low_section_speed')),
            'high_section_speed': safe_convert_to_float(data.get('high_section_speed')),
            'cast_pressure': safe_convert_to_float(data.get('cast_pressure')),
            'biscuit_thickness': safe_convert_to_float(data.get('biscuit_thickness')),
            'upper_mold_temp1': safe_convert_to_float(data.get('upper_mold_temp1')),
            'upper_mold_temp2': safe_convert_to_float(data.get('upper_mold_temp2')),
            'lower_mold_temp1': safe_convert_to_float(data.get('lower_mold_temp1')),
            'lower_mold_temp2': safe_convert_to_float(data.get('lower_mold_temp2')),
            'sleeve_temperature': safe_convert_to_float(data.get('sleeve_temperature')),
            'physical_strength': safe_convert_to_float(data.get('physical_strength')),
            'coolant_temperature': safe_convert_to_float(data.get('Coolant_temperature')),
            'ems_operation_time': safe_convert_to_int(data.get('EMS_operation_time')),
            'mold_code': safe_convert_to_int(data.get('mold_code')),
            'passorfail': str(data.get('passorfail', 'Unknown')),
            'data_hash': data_hash,
            'source': str(data.get('source', 'test.py'))
        }
        
        # DataFrame으로 변환하여 저장
        df = pd.DataFrame([db_data])
        df.to_sql('sensor_data', engine, if_exists='append', index=False, method='multi')
        
        logger.info(f"TimescaleDB에 새 데이터 저장 완료: ID {data.get('id')}, Hash: {data_hash[:8]}")
        return True
        
    except Exception as e:
        logger.error(f"TimescaleDB 저장 실패: {e}")
        # 구체적인 오류 정보 로깅
        if "invalid input syntax for type integer" in str(e):
            logger.error(f"정수 변환 오류 - 문제 데이터: working={data.get('working')}")
        return False

def read_data_from_test_py():
    """test.py에서 간단하게 데이터를 읽어오는 함수 - 저장 실패와 관계없이 데이터 반환"""
    try:
        import sys
        import importlib.util
        
        module_name = "test_module"
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        spec = importlib.util.spec_from_file_location(module_name, TEST_PY_FILE)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        # 현재 ID 가져오기 (없으면 73612부터 시작)
        if 'current_data_id' not in st.session_state:
            st.session_state.current_data_id = 73612
        
        current_id = st.session_state.current_data_id
        
        # test.py에서 데이터 읽기
        if hasattr(test_module, 'get_current_data_by_id'):
            try:
                data = test_module.get_current_data_by_id(current_id)
                
                if isinstance(data, dict):
                    data['timestamp'] = datetime.now().isoformat()
                    data['source'] = 'test.py'
                    
                    # TimescaleDB에 저장 시도 (실패해도 데이터는 반환)
                    save_success = False
                    try:
                        save_success = save_to_timescale(data)
                        if save_success:
                            logger.info(f"ID {current_id} 데이터 읽기 및 저장 성공")
                        else:
                            logger.debug(f"ID {current_id} 데이터 저장 실패 (중복일 수 있음)")
                    except Exception as save_error:
                        logger.warning(f"ID {current_id} 저장 중 오류 발생: {save_error}")
                    
                    # 저장 성공 여부와 관계없이 ID 증가 및 데이터 반환
                    st.session_state.current_data_id += 1
                    logger.info(f"ID {current_id} 데이터 읽기 완료, 다음 ID: {st.session_state.current_data_id}")
                    
                    # 항상 데이터 반환 (저장 실패와 무관)
                    return data
                        
            except ValueError as ve:
                if "존재하지 않습니다" in str(ve):
                    logger.warning(f"ID {current_id}에 해당하는 데이터가 없습니다.")
                    # ID를 73612로 재설정
                    st.session_state.current_data_id = 73612
                    return None
                else:
                    logger.error(f"ID {current_id} 데이터 읽기 오류: {ve}")
                    st.session_state.current_data_id += 1
                    return None
                    
            except Exception as e:
                logger.error(f"ID {current_id} 예상치 못한 오류: {e}")
                st.session_state.current_data_id += 1
                return None
        else:
            logger.error("test.py에 get_current_data_by_id 함수가 없습니다.")
            return None
        
    except Exception as e:
        logger.error(f"test.py 읽기 중 오류: {e}")
        return None

def get_recent_fail_data(limit: int = 10) -> List[Dict]:
    """최근 불량 데이터 조회"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        query = """
            SELECT 
                time,
                id,
                mold_code,
                molten_temp,
                cast_pressure,
                passorfail,
                upper_mold_temp1,
                lower_mold_temp1
            FROM sensor_data 
            WHERE passorfail = 'Fail'
            ORDER BY time DESC 
            LIMIT %(limit)s
        """
        
        # params를 딕셔너리 형태로 변경
        df = pd.read_sql(query, engine, params={'limit': limit})
        
        # 시간 포맷 변환
        if not df.empty and 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%H:%M:%S')
        
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"불량 데이터 조회 실패: {e}")
        return []
    
def get_recent_pass_data(limit: int = 10) -> List[Dict]:
    """최근 양품 데이터 조회"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        query = """
            SELECT 
                time,
                id,
                mold_code,
                molten_temp,
                cast_pressure,
                passorfail,
                upper_mold_temp1,
                lower_mold_temp1
            FROM sensor_data 
            WHERE passorfail = 'Pass'
            ORDER BY time DESC 
        """
        
        # params를 딕셔너리 형태로 변경
        df = pd.read_sql(query, engine, params={'limit': limit})
        
        # 시간 포맷 변환
        if not df.empty and 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%H:%M:%S')
        
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"불량 데이터 조회 실패: {e}")
        return []

def get_recent_pass_data(limit: int = 10) -> List[Dict]:
    """최근 양품 데이터 조회"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        query = """
            SELECT 
                time,
                id,
                mold_code,
                molten_temp,
                cast_pressure,
                passorfail,
                upper_mold_temp1,
                lower_mold_temp1
            FROM sensor_data 
            WHERE passorfail = 'Pass'
            ORDER BY time DESC 
        """
        
        # params를 딕셔너리 형태로 변경
        df = pd.read_sql(query, engine, params={'limit': limit})
        
        # 시간 포맷 변환
        if not df.empty and 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%H:%M:%S')
        
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"불량 데이터 조회 실패: {e}")
        return []

def get_quality_statistics(hours: int = 24) -> Dict:
    """품질 통계 조회"""
    engine = get_db_engine()
    if not engine:
        return {}
    
    try:
        query = """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN passorfail = 'Pass' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN passorfail = 'Fail' THEN 1 ELSE 0 END) as fail_count,
                ROUND(
                ((SUM(CASE WHEN passorfail = 'Pass' THEN 1 ELSE 0 END)::numeric
                    / COUNT(*)) * 100),
                2
                ) AS pass_rate
            FROM sensor_data 
            WHERE time >= NOW() - INTERVAL '%(hours)s hours'
        """
        
        # params를 딕셔너리 형태로 변경
        result = pd.read_sql(query, engine, params={'hours': hours})
        
        if not result.empty:
            return result.iloc[0].to_dict()
        else:
            return {'total_count': 0, 'pass_count': 0, 'fail_count': 0, 'pass_rate': 0.0}
            
    except Exception as e:
        logger.error(f"품질 통계 조회 실패: {e}")
        return {'total_count': 0, 'pass_count': 0, 'fail_count': 0, 'pass_rate': 0.0}


def get_hourly_defect_rates(hours: int = 24) -> List[Dict]:
    """시간대별 불량률 조회"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        query = """
            SELECT 
                time_bucket('1 hour', time) AS hour,
                COUNT(*) as total_products,
                SUM(CASE WHEN passorfail = 'Fail' THEN 1 ELSE 0 END) as defects,
                ROUND(
                    (SUM(CASE WHEN passorfail = 'Fail' THEN 1 ELSE 0 END)::float / COUNT(*)) * 100, 2
                ) as defect_rate
            FROM sensor_data 
            WHERE time >= NOW() - INTERVAL '%(hours)s hours'
            GROUP BY hour
            ORDER BY hour
        """
        
        # params를 딕셔너리 형태로 변경
        df = pd.read_sql(query, engine, params={'hours': hours})
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"시간대별 불량률 조회 실패: {e}")
        return []

# 세션 기반 중복 방지를 위한 전역 변수
_processed_data_hashes = set()
_last_data_hash = None

# def read_data_from_test_py():
#     global _last_data_hash, _processed_data_hashes
    
#     try:
#         import sys
#         import importlib.util
        
#         module_name = "test_module"
#         if module_name in sys.modules:
#             del sys.modules[module_name]
        
#         spec = importlib.util.spec_from_file_location(module_name, TEST_PY_FILE)
#         test_module = importlib.util.module_from_spec(spec)
#         spec.loader.exec_module(test_module)
        
#         # 세션에서 현재 ID 관리
#         if 'current_data_id' not in st.session_state:
#             st.session_state.current_data_id = 73612
        
#         current_id = st.session_state.current_data_id
        
#         if hasattr(test_module, 'get_current_data_by_id'):
#             try:
#                 data = test_module.get_current_data_by_id(current_id)
#                 if isinstance(data, dict):
#                     # 데이터 해시 생성
#                     data_hash = create_data_hash(data)
                    
#                     # 세션 기반 중복 확인 (새로고침 대응)
#                     session_hashes = st.session_state.get('processed_data_hashes', set())
                    
#                     if data_hash and data_hash not in session_hashes:
#                         data['timestamp'] = datetime.now().isoformat()
#                         data['source'] = 'test.py'
#                         data['data_hash'] = data_hash
                        
#                         # TimescaleDB에 저장 (데이터베이스 레벨 중복 확인 포함)
#                         if save_to_timescale(data):
#                             # 성공적으로 저장된 경우에만 세션에 기록
#                             session_hashes.add(data_hash)
#                             st.session_state.processed_data_hashes = session_hashes
                            
#                             # 세션 해시 집합 크기 제한 (메모리 관리)
#                             if len(session_hashes) > 1000:
#                                 # 가장 오래된 500개 제거
#                                 hash_list = list(session_hashes)
#                                 st.session_state.processed_data_hashes = set(hash_list[-500:])
                            
#                             _last_data_hash = data_hash
#                             _processed_data_hashes.add(data_hash)
                            
#                             # 다음 호출을 위해 ID 증가
#                             st.session_state.current_data_id += 1
                            
#                             logger.info(f"ID {current_id}로 새로운 데이터 읽기 및 저장 성공, 다음 ID: {st.session_state.current_data_id}")
#                             return data
#                         else:
#                             logger.debug(f"ID {current_id}: 데이터베이스 중복 또는 저장 실패")
#                             # ID는 증가시켜서 다음 데이터로 넘어감
#                             st.session_state.current_data_id += 1
#                             return None
#                     else:
#                         logger.debug(f"ID {current_id}: 세션 중복 데이터 감지")
#                         # ID 증가시켜서 다음 데이터 시도
#                         st.session_state.current_data_id += 1
#                         return None
                        
#             except ValueError as ve:
#                 # ID에 해당하는 데이터가 없는 경우
#                 if "존재하지 않습니다" in str(ve):
#                     logger.warning(f"ID {current_id}에 해당하는 데이터가 없습니다. ID를 73612로 초기화합니다.")
#                     st.session_state.current_data_id = 73612
#                     # 재귀 호출로 다시 시도 (단, 한 번만)
#                     if current_id != 73612:
#                         return read_data_from_test_py()
#                 else:
#                     logger.error(f"ID {current_id}로 데이터 읽기 중 오류: {ve}")
#                     st.session_state.current_data_id += 1
#             except Exception as e:
#                 logger.error(f"ID {current_id}로 데이터 읽기 중 예상치 못한 오류: {e}")
#                 st.session_state.current_data_id += 1
        
#         logger.warning("test.py에서 새로운 유효한 데이터를 찾을 수 없습니다.")
#         return None
        
#     except Exception as e:
#         logger.error(f"test.py에서 데이터 읽기 중 오류: {e}")
#         return None

def read_data_from_test_py():
    """test.py에서 간단하게 데이터를 읽어오는 함수"""
    try:
        import sys
        import importlib.util
        
        module_name = "test_module"
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        spec = importlib.util.spec_from_file_location(module_name, TEST_PY_FILE)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        # 현재 ID 가져오기 (없으면 73612부터 시작)
        if 'current_data_id' not in st.session_state:
            st.session_state.current_data_id = 73612
        
        current_id = st.session_state.current_data_id
        
        # test.py에서 데이터 읽기
        if hasattr(test_module, 'get_current_data_by_id'):
            try:
                data = test_module.get_current_data_by_id(current_id)
                
                if isinstance(data, dict):
                    data['timestamp'] = datetime.now().isoformat()
                    data['source'] = 'test.py'
                    
                    # TimescaleDB에 저장
                    if save_to_timescale(data):
                        # 성공했으면 다음 ID로 증가
                        st.session_state.current_data_id += 1
                        logger.info(f"ID {current_id} 데이터 읽기 및 저장 성공, 다음 ID: {st.session_state.current_data_id}")
                        return data
                    else:
                        # 저장 실패 (중복 등)해도 ID는 증가
                        st.session_state.current_data_id += 1
                        logger.debug(f"ID {current_id} 데이터 저장 실패 (중복일 수 있음)")
                        return None
                        
            except ValueError as ve:
                if "존재하지 않습니다" in str(ve):
                    logger.warning(f"ID {current_id}에 해당하는 데이터가 없습니다.")
                    # ID를 73612로 재설정
                    st.session_state.current_data_id = 73612
                    return None
                else:
                    logger.error(f"ID {current_id} 데이터 읽기 오류: {ve}")
                    st.session_state.current_data_id += 1
                    return None
                    
            except Exception as e:
                logger.error(f"ID {current_id} 예상치 못한 오류: {e}")
                st.session_state.current_data_id += 1
                return None
        else:
            logger.error("test.py에 get_current_data_by_id 함수가 없습니다.")
            return None
        
    except Exception as e:
        logger.error(f"test.py 읽기 중 오류: {e}")
        return None


# 기존 함수들 유지 (하위 호환성)
def load_data_from_file():
    """저장된 데이터 파일에서 데이터 로드"""
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"데이터 로드 완료: {len(data)}개 레코드")
                return data
        else:
            logger.info("데이터 파일이 없어 빈 리스트 반환")
            return []
    except Exception as e:
        logger.error(f"데이터 로드 중 오류: {e}")
        return []

def save_data_to_file(data):
    """데이터를 파일에 저장"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"데이터 저장 완료: {len(data)}개 레코드")
        return True
    except Exception as e:
        logger.error(f"데이터 저장 중 오류: {e}")
        return False

def save_snapshot_batch(all_data):
    """15분마다 배치로 스냅샷 저장 (백업용)"""
    try:
        if not all_data:
            logger.info("저장할 데이터가 없습니다.")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        data_count = len(all_data)
        snapshot_file = snapshots_dir / f"batch_snapshot_{timestamp}_{data_count}records.json"
        
        snapshot_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_records": data_count,
                "snapshot_type": "batch_15min",
                "version": "1.0"
            },
            "data": all_data
        }
        
        snapshots_dir.mkdir(exist_ok=True)
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"배치 스냅샷 저장 완료: {snapshot_file} ({data_count}개 레코드)")
        
    except Exception as e:
        logger.error(f"배치 스냅샷 저장 중 오류: {e}")

# def get_max_data_id(
#     table_name: str = "sensor_data",    # 실제 테이블명으로 수정
#     id_column: str = "id"               # 실제 PK 컬럼명으로 수정
# ) -> int:
#     """
#     지정한 테이블의 id 컬럼에서 MAX 값을 읽어옵니다.
#     테이블명과 PK 컬럼명을 실제 스키마에 맞게 설정하세요.
#     """
#     engine = get_db_engine()
#     if engine is None:
#         return 0

#     query = text(f"SELECT COALESCE(MAX({id_column}), 0) FROM {table_name}")
#     with engine.connect() as conn:
#         max_id = conn.execute(query).scalar_one()
#     return max_id

def get_max_data_id(table_name: str = "sensor_data", id_column: str = "id") -> int:
    """안전한 MAX ID 조회"""
    engine = get_db_engine()
    if engine is None:
        return 0
    
    try:
        query = text(f"SELECT COALESCE(MAX({id_column}), 0) FROM {table_name}")
        with engine.connect() as conn:
            result = conn.execute(query)
            max_id = result.scalar_one()
            logger.info(f"데이터베이스 MAX ID 조회: {max_id}")
            return int(max_id) if max_id is not None else 0
    except Exception as e:
        logger.error(f"MAX ID 조회 실패: {e}")
        return 0

def get_next_data_id():
    """다음 사용할 ID 반환 및 증가"""
    if 'current_data_id' not in st.session_state:
        # 초기화 로직
        max_id = get_max_data_id()
        if max_id == 0:
            st.session_state.current_data_id = 73612
        else:
            st.session_state.current_data_id = max_id + 1
    
    # 현재 ID 반환 후 증가
    current_id = st.session_state.current_data_id
    st.session_state.current_data_id += 1
    logger.info(f"ID 할당: {current_id}, 다음 ID: {st.session_state.current_data_id}")
    return current_id

def get_fail_data_count():
    """불량 데이터의 총 개수를 조회"""
    engine = get_db_engine()
    if not engine:
        return 0
    
    try:
        query = """
            SELECT COUNT(*) as count
            FROM sensor_data 
            WHERE passorfail = 'Fail'
        """
        
        result = pd.read_sql(query, engine)
        return result.iloc[0]['count'] if not result.empty else 0
        
    except Exception as e:
        logger.error(f"불량 데이터 개수 조회 오류: {str(e)}")
        return 0

def get_fail_data_with_pagination(limit=15, offset=0):
    """페이지네이션을 적용한 불량 데이터 조회"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        query = """
            SELECT 
                id,
                time as time,
                time as registered_date,
                mold_code,
                molten_temp,
                cast_pressure,
                upper_mold_temp1,
                passorfail
            FROM sensor_data 
            WHERE passorfail = 'Fail'
            ORDER BY time DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """
        
        df = pd.read_sql(query, engine, params={'limit': limit, 'offset': offset})
        
        if df.empty:
            return []
        
        # 데이터 변환
        data_list = []
        for _, row in df.iterrows():
            data_dict = row.to_dict()
            
            # 날짜 포맷 변환
            if pd.notna(data_dict.get('time')):
                if isinstance(data_dict['time'], str):
                    try:
                        time_obj = pd.to_datetime(data_dict['time'])
                        data_dict['time'] = time_obj.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                else:
                    data_dict['time'] = pd.to_datetime(data_dict['time']).strftime('%Y-%m-%d %H:%M:%S')
            
            if pd.notna(data_dict.get('registered_date')):
                if isinstance(data_dict['registered_date'], str):
                    try:
                        reg_time = pd.to_datetime(data_dict['registered_date'])
                        data_dict['registered_date'] = reg_time.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                else:
                    data_dict['registered_date'] = pd.to_datetime(data_dict['registered_date']).strftime('%Y-%m-%d %H:%M:%S')
            
            data_list.append(data_dict)
        
        return data_list
        
    except Exception as e:
        logger.error(f"페이지네이션 불량 데이터 조회 오류: {str(e)}")
        return []

def reset_processed_hashes():
    """처리된 해시 초기화 (시스템 재시작 시 사용)"""
    global _processed_data_hashes, _last_data_hash
    _processed_data_hashes.clear()
    _last_data_hash = None
    
    # 세션 해시도 초기화
    if 'processed_data_hashes' in st.session_state:
        st.session_state.processed_data_hashes = set()
    
    logger.info("중복 방지 해시 데이터가 초기화되었습니다.")

# utils/data_utils.py에 추가할 함수들

def get_fail_data_count_by_date(start_date=None, end_date=None):
    """날짜 필터가 적용된 불량 데이터의 총 개수를 조회"""
    engine = get_db_engine()
    if not engine:
        return 0
    
    try:
        base_query = "SELECT COUNT(*) as count FROM sensor_data WHERE passorfail = 'Fail'"
        params = {}
        
        if start_date and end_date:
            base_query += " AND DATE(time) BETWEEN %(start_date)s AND %(end_date)s"
            params['start_date'] = start_date
            params['end_date'] = end_date
        elif start_date:
            base_query += " AND DATE(time) >= %(start_date)s"
            params['start_date'] = start_date
        elif end_date:
            base_query += " AND DATE(time) <= %(end_date)s"
            params['end_date'] = end_date
        
        result = pd.read_sql(base_query, engine, params=params)
        return result.iloc[0]['count'] if not result.empty else 0
        
    except Exception as e:
        logger.error(f"날짜별 불량 데이터 개수 조회 오류: {str(e)}")
        return 0


def get_fail_data_with_pagination_by_date(limit=15, offset=0, start_date=None, end_date=None):
    """날짜 필터가 적용된 페이지네이션 불량 데이터 조회"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        base_query = """
            SELECT 
                id,
                time as time,
                time as registered_date,
                mold_code,
                molten_temp,
                cast_pressure,
                upper_mold_temp1,
                passorfail
            FROM sensor_data 
            WHERE passorfail = 'Fail'
        """
        
        params = {'limit': limit, 'offset': offset}
        
        if start_date and end_date:
            base_query += " AND DATE(time) BETWEEN %(start_date)s AND %(end_date)s"
            params['start_date'] = start_date
            params['end_date'] = end_date
        elif start_date:
            base_query += " AND DATE(time) >= %(start_date)s"
            params['start_date'] = start_date
        elif end_date:
            base_query += " AND DATE(time) <= %(end_date)s"
            params['end_date'] = end_date
        
        base_query += " ORDER BY time DESC LIMIT %(limit)s OFFSET %(offset)s"
        
        df = pd.read_sql(base_query, engine, params=params)
        
        if df.empty:
            return []
        
        # 데이터 변환
        data_list = []
        for _, row in df.iterrows():
            data_dict = row.to_dict()
            
            # 날짜 포맷 변환
            if pd.notna(data_dict.get('time')):
                if isinstance(data_dict['time'], str):
                    try:
                        time_obj = pd.to_datetime(data_dict['time'])
                        data_dict['time'] = time_obj.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                else:
                    data_dict['time'] = pd.to_datetime(data_dict['time']).strftime('%Y-%m-%d %H:%M:%S')
            
            if pd.notna(data_dict.get('registered_date')):
                if isinstance(data_dict['registered_date'], str):
                    try:
                        reg_time = pd.to_datetime(data_dict['registered_date'])
                        data_dict['registered_date'] = reg_time.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                else:
                    data_dict['registered_date'] = pd.to_datetime(data_dict['registered_date']).strftime('%Y-%m-%d %H:%M:%S')
            
            data_list.append(data_dict)
        
        return data_list
        
    except Exception as e:
        logger.error(f"날짜별 페이지네이션 불량 데이터 조회 오류: {str(e)}")
        return []


def get_quality_statistics_by_date(start_date=None, end_date=None):
    """날짜별 품질 통계 조회"""
    engine = get_db_engine()
    if not engine:
        return {}
    
    try:
        base_query = """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN passorfail = 'Pass' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN passorfail = 'Fail' THEN 1 ELSE 0 END) as fail_count,
                ROUND(
                    (SUM(CASE WHEN passorfail = 'Pass' THEN 1 ELSE 0 END)::float / COUNT(*)) * 100, 2
                ) as pass_rate
            FROM sensor_data WHERE 1=1
        """
        
        params = {}
        
        if start_date and end_date:
            base_query += " AND DATE(time) BETWEEN %(start_date)s AND %(end_date)s"
            params['start_date'] = start_date
            params['end_date'] = end_date
        elif start_date:
            base_query += " AND DATE(time) >= %(start_date)s"
            params['start_date'] = start_date
        elif end_date:
            base_query += " AND DATE(time) <= %(end_date)s"
            params['end_date'] = end_date
        
        result = pd.read_sql(base_query, engine, params=params)
        
        if not result.empty:
            return result.iloc[0].to_dict()
        else:
            return {'total_count': 0, 'pass_count': 0, 'fail_count': 0, 'pass_rate': 0.0}
            
    except Exception as e:
        logger.error(f"날짜별 품질 통계 조회 오류: {str(e)}")
        return {'total_count': 0, 'pass_count': 0, 'fail_count': 0, 'pass_rate': 0.0}


def get_available_date_range():
    """데이터베이스에서 사용 가능한 날짜 범위 조회"""
    engine = get_db_engine()
    if not engine:
        return None, None
    
    try:
        query = """
            SELECT 
                MIN(DATE(time)) as min_date,
                MAX(DATE(time)) as max_date
            FROM sensor_data
        """
        
        result = pd.read_sql(query, engine)
        
        if not result.empty and result.iloc[0]['min_date'] is not None:
            return result.iloc[0]['min_date'], result.iloc[0]['max_date']
        else:
            return None, None
            
    except Exception as e:
        logger.error(f"날짜 범위 조회 오류: {str(e)}")
        return None, None
    
# utils/data_utils.py에 추가할 함수들

def get_fail_data_count_by_datetime(start_datetime=None, end_datetime=None):
    """날짜/시간 필터가 적용된 불량 데이터의 총 개수를 조회"""
    engine = get_db_engine()
    if not engine:
        return 0
    
    try:
        base_query = "SELECT COUNT(*) as count FROM sensor_data WHERE passorfail = 'Fail'"
        params = {}
        
        if start_datetime and end_datetime:
            base_query += " AND time BETWEEN %(start_datetime)s AND %(end_datetime)s"
            params['start_datetime'] = start_datetime
            params['end_datetime'] = end_datetime
        elif start_datetime:
            base_query += " AND time >= %(start_datetime)s"
            params['start_datetime'] = start_datetime
        elif end_datetime:
            base_query += " AND time <= %(end_datetime)s"
            params['end_datetime'] = end_datetime
        
        result = pd.read_sql(base_query, engine, params=params)
        return result.iloc[0]['count'] if not result.empty else 0
        
    except Exception as e:
        logger.error(f"날짜/시간별 불량 데이터 개수 조회 오류: {str(e)}")
        return 0


# def get_fail_data_with_pagination_by_datetime(limit=15, offset=0, start_datetime=None, end_datetime=None):
#     """날짜/시간 필터가 적용된 페이지네이션 불량 데이터 조회"""
#     engine = get_db_engine()
#     if not engine:
#         return []
    
#     try:
#         base_query = """
#             SELECT 
#                 id,
#                 time as time,
#                 time as registered_date,
#                 mold_code,
#                 molten_temp,
#                 cast_pressure,
#                 upper_mold_temp1,
#                 passorfail
#             FROM sensor_data 
#             WHERE passorfail = 'Fail'
#         """
        
#         params = {'limit': limit, 'offset': offset}
        
#         if start_datetime and end_datetime:
#             base_query += " AND time BETWEEN %(start_datetime)s AND %(end_datetime)s"
#             params['start_datetime'] = start_datetime
#             params['end_datetime'] = end_datetime
#         elif start_datetime:
#             base_query += " AND time >= %(start_datetime)s"
#             params['start_datetime'] = start_datetime
#         elif end_datetime:
#             base_query += " AND time <= %(end_datetime)s"
#             params['end_datetime'] = end_datetime
        
#         base_query += " ORDER BY time DESC LIMIT %(limit)s OFFSET %(offset)s"
        
#         df = pd.read_sql(base_query, engine, params=params)
        
#         if df.empty:
#             return []
        
#         # 데이터 변환
#         data_list = []
#         for _, row in df.iterrows():
#             data_dict = row.to_dict()
            
#             # 날짜 포맷 변환
#             if pd.notna(data_dict.get('time')):
#                 if isinstance(data_dict['time'], str):
#                     try:
#                         time_obj = pd.to_datetime(data_dict['time'])
#                         data_dict['time'] = time_obj.strftime('%Y-%m-%d %H:%M:%S')
#                     except:
#                         pass
#                 else:
#                     data_dict['time'] = pd.to_datetime(data_dict['time']).strftime('%Y-%m-%d %H:%M:%S')
            
#             if pd.notna(data_dict.get('registered_date')):
#                 if isinstance(data_dict['registered_date'], str):
#                     try:
#                         reg_time = pd.to_datetime(data_dict['registered_date'])
#                         data_dict['registered_date'] = reg_time.strftime('%Y-%m-%d %H:%M:%S')
#                     except:
#                         pass
#                 else:
#                     data_dict['registered_date'] = pd.to_datetime(data_dict['registered_date']).strftime('%Y-%m-%d %H:%M:%S')
            
#             data_list.append(data_dict)
        
#         return data_list
        
#     except Exception as e:
#         logger.error(f"날짜/시간별 페이지네이션 불량 데이터 조회 오류: {str(e)}")
#         return []

def get_fail_data_with_pagination_by_datetime(limit=15, offset=0, start_datetime=None, end_datetime=None):
    """날짜/시간 필터가 적용된 페이지네이션 불량 데이터 조회 - 수정된 버전"""
    engine = get_db_engine()
    if not engine:
        logger.error("데이터베이스 엔진을 가져올 수 없습니다.")
        return []
    
    try:
        # 기본 쿼리 (매개변수 바인딩을 :parameter 방식으로 변경)
        base_query = """
            SELECT 
                id,
                time as time,
                time as registered_date,
                mold_code,
                molten_temp,
                cast_pressure,
                upper_mold_temp1,
                passorfail
            FROM sensor_data 
            WHERE passorfail = 'Fail'
        """
        
        # 매개변수 딕셔너리 초기화
        params = {}
        
        # 날짜/시간 필터 조건 추가
        if start_datetime and end_datetime:
            base_query += " AND time BETWEEN :start_datetime AND :end_datetime"
            params['start_datetime'] = start_datetime
            params['end_datetime'] = end_datetime
        elif start_datetime:
            base_query += " AND time >= :start_datetime"
            params['start_datetime'] = start_datetime
        elif end_datetime:
            base_query += " AND time <= :end_datetime"
            params['end_datetime'] = end_datetime
        
        # ORDER BY와 LIMIT/OFFSET을 문자열 포맷으로 처리 (보안상 안전한 정수값이므로)
        base_query += f" ORDER BY time DESC LIMIT {limit} OFFSET {offset}"
        
        # 디버깅을 위한 로그
        # logger.info(f"실행할 쿼리: {base_query}")
        # logger.info(f"매개변수: {params}")
        
        # SQLAlchemy text() 사용하여 쿼리 실행
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(base_query), params)
            else:
                result = conn.execute(text(base_query))
            
            # 결과를 리스트로 변환
            rows = result.fetchall()
            
            if not rows:
                logger.info("쿼리 결과가 비어있습니다.")
                return []
            
            # 컬럼 이름 가져오기
            columns = result.keys()
            
            # 데이터 변환
            data_list = []
            for row in rows:
                # Row 객체를 딕셔너리로 변환
                data_dict = dict(zip(columns, row))
                
                # 날짜 포맷 변환
                for date_field in ['time', 'registered_date']:
                    if data_dict.get(date_field) is not None:
                        try:
                            if isinstance(data_dict[date_field], str):
                                # 문자열인 경우 파싱 후 포맷
                                time_obj = pd.to_datetime(data_dict[date_field])
                                data_dict[date_field] = time_obj.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                # datetime 객체인 경우 직접 포맷
                                data_dict[date_field] = pd.to_datetime(data_dict[date_field]).strftime('%Y-%m-%d %H:%M:%S')
                        except Exception as date_error:
                            logger.warning(f"날짜 포맷 변환 오류 ({date_field}): {date_error}")
                            # 변환 실패 시 원본 값 유지
                            pass
                
                data_list.append(data_dict)
            
            logger.info(f"성공적으로 {len(data_list)}개의 레코드를 조회했습니다.")
            return data_list
        
    except Exception as e:
        logger.error(f"날짜/시간별 페이지네이션 불량 데이터 조회 오류: {str(e)}")
        logger.error(f"쿼리: {base_query}")
        logger.error(f"매개변수: {params}")
        return []


def get_fail_data_count_by_datetime(start_datetime=None, end_datetime=None):
    """날짜/시간 필터가 적용된 불량 데이터의 총 개수를 조회 - 수정된 버전"""
    engine = get_db_engine()
    if not engine:
        logger.error("데이터베이스 엔진을 가져올 수 없습니다.")
        return 0
    
    try:
        base_query = "SELECT COUNT(*) as count FROM sensor_data WHERE passorfail = 'Fail'"
        params = {}
        
        if start_datetime and end_datetime:
            base_query += " AND time BETWEEN :start_datetime AND :end_datetime"
            params['start_datetime'] = start_datetime
            params['end_datetime'] = end_datetime
        elif start_datetime:
            base_query += " AND time >= :start_datetime"
            params['start_datetime'] = start_datetime
        elif end_datetime:
            base_query += " AND time <= :end_datetime"
            params['end_datetime'] = end_datetime
        
        # 디버깅을 위한 로그
        logger.info(f"카운트 쿼리: {base_query}")
        logger.info(f"매개변수: {params}")
        
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(base_query), params)
            else:
                result = conn.execute(text(base_query))
            
            count = result.scalar()
            logger.info(f"조회된 불량 데이터 개수: {count}")
            return count if count is not None else 0
        
    except Exception as e:
        logger.error(f"날짜/시간별 불량 데이터 개수 조회 오류: {str(e)}")
        logger.error(f"쿼리: {base_query}")
        logger.error(f"매개변수: {params}")
        return 0


# 추가: 디버깅을 위한 간단한 테스트 함수
def test_fail_data_query():
    """불량 데이터 쿼리 테스트"""
    logger.info("=== 불량 데이터 쿼리 테스트 시작 ===")
    
    try:
        # 1. 기본 카운트 테스트
        total_count = get_fail_data_count_by_datetime()
        logger.info(f"전체 불량 데이터 개수: {total_count}")
        
        if total_count > 0:
            # 2. 첫 페이지 데이터 조회 테스트
            first_page = get_fail_data_with_pagination_by_datetime(limit=5, offset=0)
            logger.info(f"첫 페이지 데이터 개수: {len(first_page)}")
            
            if first_page:
                logger.info("첫 번째 레코드 샘플:")
                first_record = first_page[0]
                for key, value in first_record.items():
                    logger.info(f"  {key}: {value}")
            
            # 3. 날짜 필터 테스트 (최근 24시간)
            from datetime import datetime, timedelta
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            filtered_count = get_fail_data_count_by_datetime(start_time, end_time)
            logger.info(f"최근 24시간 불량 데이터: {filtered_count}")
            
            if filtered_count > 0:
                filtered_data = get_fail_data_with_pagination_by_datetime(
                    limit=3, offset=0, start_datetime=start_time, end_datetime=end_time
                )
                logger.info(f"최근 24시간 데이터 샘플: {len(filtered_data)}개")
        
        logger.info("=== 불량 데이터 쿼리 테스트 완료 ===")
        return True
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {str(e)}")
        return False


# Streamlit에서 사용할 디버그 함수
def debug_fail_data_in_streamlit():
    """Streamlit에서 불량 데이터 디버깅"""
    import streamlit as st
    
    st.write("### 불량 데이터 쿼리 디버깅")
    
    if st.button("기본 테스트 실행"):
        with st.spinner("테스트 실행 중..."):
            result = test_fail_data_query()
            if result:
                st.success("✅ 테스트 완료! 로그를 확인하세요.")
            else:
                st.error("❌ 테스트 실패!")
    
    # 직접 쿼리 테스트
    st.write("#### 직접 쿼리 테스트")
    
    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("Limit", min_value=1, max_value=100, value=5)
    with col2:
        offset = st.number_input("Offset", min_value=0, value=0)
    
    if st.button("쿼리 실행"):
        try:
            data = get_fail_data_with_pagination_by_datetime(limit=limit, offset=offset)
            st.write(f"조회된 데이터: {len(data)}개")
            
            if data:
                import pandas as pd
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.warning("조회된 데이터가 없습니다.")
                
        except Exception as e:
            st.error(f"쿼리 실행 오류: {str(e)}")


def get_quality_statistics_by_datetime(start_datetime=None, end_datetime=None):
    """날짜/시간별 품질 통계 조회"""
    engine = get_db_engine()
    if not engine:
        return {}
    
    try:
        base_query = """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN passorfail = 'Pass' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN passorfail = 'Fail' THEN 1 ELSE 0 END) as fail_count,
                ROUND(
                    (SUM(CASE WHEN passorfail = 'Pass' THEN 1 ELSE 0 END)::float / COUNT(*)) * 100, 2
                ) as pass_rate
            FROM sensor_data WHERE 1=1
        """
        
        params = {}
        
        if start_datetime and end_datetime:
            base_query += " AND time BETWEEN %(start_datetime)s AND %(end_datetime)s"
            params['start_datetime'] = start_datetime
            params['end_datetime'] = end_datetime
        elif start_datetime:
            base_query += " AND time >= %(start_datetime)s"
            params['start_datetime'] = start_datetime
        elif end_datetime:
            base_query += " AND time <= %(end_datetime)s"
            params['end_datetime'] = end_datetime
        
        result = pd.read_sql(base_query, engine, params=params)
        
        if not result.empty:
            return result.iloc[0].to_dict()
        else:
            return {'total_count': 0, 'pass_count': 0, 'fail_count': 0, 'pass_rate': 0.0}
            
    except Exception as e:
        logger.error(f"날짜/시간별 품질 통계 조회 오류: {str(e)}")
        return {'total_count': 0, 'pass_count': 0, 'fail_count': 0, 'pass_rate': 0.0}
    



def append_today_data(data, file_path=DATA_FILE_TODAY):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []
    existing.append(data)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def get_today_sensor_data() -> List[Dict]:
    """오늘 날짜(00:00:00 ~ 23:59:59) 의 sensor_data 전체 레코드 조회"""
    engine = get_db_engine()
    if not engine:
        return []
    try:
        query = """
            SELECT
                time,
                id,
                mold_code,
                molten_temp,
                cast_pressure,
                passorfail,
                upper_mold_temp1,
                lower_mold_temp1,
                data_hash,
                source
            FROM sensor_data
            -- time 컬럼의 날짜 부분이 오늘(CURRENT_DATE) 인 것만
            WHERE time::date = CURRENT_DATE
            ORDER BY time DESC
        """
        df = pd.read_sql(text(query), engine)

        if not df.empty and 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')

        return df.to_dict('records')

    except Exception as e:
        logger.error(f"오늘 날짜 데이터 조회 실패: {e}")
        return []
    
def get_today_pass_data() -> List[Dict]:
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        # 더 유연한 조건으로 수정
        query = text("""
            SELECT
                time,
                id,
                mold_code,
                molten_temp,
                cast_pressure,
                passorfail,
                upper_mold_temp1,
                lower_mold_temp1,
                data_hash,
                source
            FROM sensor_data
            WHERE DATE(time) = CURRENT_DATE
                AND (UPPER(TRIM(passorfail)) = 'PASS' OR TRIM(passorfail) = 'Pass')
            ORDER BY time DESC
        """)
        
        df = pd.read_sql(query, engine)
        
        if not df.empty and 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"오늘 Pass 데이터 조회 실패: {e}")
        return []

# 전체 데이터베이스를 조회
def get_all_sensor_data() -> List[Dict]:
    engine = get_db_engine()
    if not engine:
        return []
    try:
        query = """
            SELECT id FROM sensor_data
        """
        df = pd.read_sql(text(query), engine)
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"전체 테이블 조회 실패: {e}")
        return []
    
def get_all_pass_sensor_data() -> List[Dict]:
    engine = get_db_engine()
    if not engine:
        return []
    try:
        query = """
            SELECT id
            FROM sensor_data
            WHERE passorfail = 'Pass'
        """
        df = pd.read_sql(text(query), engine)
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"전체 Pass 데이터 조회 실패: {e}")
        return []