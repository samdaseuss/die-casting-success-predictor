import logging
from sqlalchemy import create_engine, text
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import random
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# TimescaleDB 연결 설정
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5434'),
    'database': os.getenv('POSTGRES_DB', 'diecasting_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password')
}

def get_db_engine():
    """데이터베이스 엔진 생성"""
    try:
        connection_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        engine = create_engine(connection_string, pool_pre_ping=True)
        return engine
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return None

def init_sensor_data_table():
    """sensor_data 테이블 생성 및 초기화"""
    engine = get_db_engine()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # 기존 테이블 삭제 (필요한 경우)
            # conn.execute(text("DROP TABLE IF EXISTS sensor_data CASCADE;"))
            
            # 센서 데이터 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sensor_data (
                    time TIMESTAMPTZ NOT NULL,
                    id BIGINT,
                    line TEXT,
                    mold_name TEXT,
                    working INTEGER,
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
                    data_hash TEXT,
                    source TEXT DEFAULT 'migration'
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
            
            conn.commit()
            logger.info("TimescaleDB 테이블 초기화 완료")
            return True
            
    except Exception as e:
        logger.error(f"테이블 초기화 실패: {e}")
        return False

def generate_sample_data(count: int = 100, start_time: Optional[datetime] = None) -> List[Dict]:
    """샘플 데이터 생성"""
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=24)
    
    sample_data = []
    
    for i in range(count):
        # 시간을 순차적으로 증가
        timestamp = start_time + timedelta(minutes=i * 5)
        
        # 랜덤하게 Pass/Fail 결정 (90% Pass, 10% Fail)
        pass_or_fail = "Pass" if random.random() > 0.1 else "Fail"
        
        # Fail인 경우 일부 값들을 이상하게 설정
        if pass_or_fail == "Fail":
            molten_temp = random.uniform(580, 620)  # 정상 범위를 벗어남
            cast_pressure = random.uniform(45, 60)   # 높은 압력
            upper_temp1 = random.uniform(180, 220)   # 높은 온도
        else:
            molten_temp = random.uniform(650, 680)   # 정상 범위
            cast_pressure = random.uniform(30, 45)   # 정상 압력
            upper_temp1 = random.uniform(150, 180)   # 정상 온도
        
        data = {
            'time': timestamp.isoformat(),
            'id': 73612 + i,
            'line': f"Line_{random.randint(1, 3)}",
            'mold_name': f"Mold_{random.choice(['A', 'B', 'C'])}_{random.randint(1, 5)}",
            'working': random.randint(0, 1),
            'molten_temp': round(molten_temp, 2),
            'facility_operation_cycletime': random.randint(25, 35),
            'production_cycletime': random.randint(28, 40),
            'low_section_speed': round(random.uniform(0.1, 0.3), 3),
            'high_section_speed': round(random.uniform(1.5, 3.0), 3),
            'cast_pressure': round(cast_pressure, 2),
            'biscuit_thickness': round(random.uniform(8, 12), 2),
            'upper_mold_temp1': round(upper_temp1, 2),
            'upper_mold_temp2': round(upper_temp1 + random.uniform(-5, 5), 2),
            'lower_mold_temp1': round(random.uniform(140, 170), 2),
            'lower_mold_temp2': round(random.uniform(140, 170), 2),
            'sleeve_temperature': round(random.uniform(200, 250), 2),
            'physical_strength': round(random.uniform(200, 300), 2),
            'coolant_temperature': round(random.uniform(25, 35), 2),
            'ems_operation_time': random.randint(5, 15),
            'mold_code': random.randint(1001, 1010),
            'passorfail': pass_or_fail,
            'prediction_confidence': round(random.uniform(0.7, 0.99), 3),
            'data_hash': f"hash_{i:06d}",
            'source': 'migration_sample'
        }
        
        sample_data.append(data)
    
    return sample_data

def filter_columns_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """데이터베이스 테이블에 맞는 컬럼만 필터링"""
    # 데이터베이스 테이블의 유효한 컬럼들
    valid_columns = {
        'time', 'id', 'line', 'mold_name', 'working', 'molten_temp',
        'facility_operation_cycletime', 'production_cycletime',
        'low_section_speed', 'high_section_speed', 'cast_pressure',
        'biscuit_thickness', 'upper_mold_temp1', 'upper_mold_temp2',
        'lower_mold_temp1', 'lower_mold_temp2', 'sleeve_temperature',
        'physical_strength', 'coolant_temperature', 'ems_operation_time',
        'mold_code', 'passorfail', 'prediction_confidence', 'data_hash', 'source'
    }
    
    # 현재 DataFrame의 컬럼들
    current_columns = set(df.columns)
    
    # 유효한 컬럼만 선택
    columns_to_keep = current_columns.intersection(valid_columns)
    
    # 무시되는 컬럼들 출력
    ignored_columns = current_columns - valid_columns
    if ignored_columns:
        print(f"⚠️  무시되는 컬럼들: {list(ignored_columns)}")
    
    print(f"✅ 사용되는 컬럼들: {list(columns_to_keep)}")
    
    # 필터링된 DataFrame 반환
    filtered_df = df[list(columns_to_keep)].copy()
    
    # 기본값 추가 (필요한 경우)
    if 'source' not in filtered_df.columns:
        filtered_df['source'] = 'csv_import'
    
    return filtered_df

def insert_data_batch(data_list: List[Dict]) -> Dict[str, any]:
    """배치로 데이터 삽입"""
    engine = get_db_engine()
    if not engine:
        return {'success': False, 'message': '데이터베이스 연결 실패', 'inserted_count': 0}
    
    try:
        # DataFrame으로 변환
        df = pd.DataFrame(data_list)
        
        # time 컬럼을 datetime으로 변환
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        
        # 데이터베이스 테이블에 맞는 컬럼만 필터링
        df = filter_columns_for_db(df)
        
        # None 값 처리
        df = df.where(pd.notnull(df), None)
        
        print(f"📊 삽입할 데이터 shape: {df.shape}")
        print(f"📋 최종 컬럼 목록: {list(df.columns)}")
        
        # 데이터베이스에 삽입
        rows_inserted = df.to_sql('sensor_data', engine, if_exists='append', 
                                 index=False, method='multi')
        
        logger.info(f"배치 데이터 삽입 완료: {len(df)}개 레코드")
        
        return {
            'success': True,
            'message': f'성공적으로 {len(df)}개의 레코드를 삽입했습니다.',
            'inserted_count': len(df)
        }
        
    except Exception as e:
        logger.error(f"배치 데이터 삽입 실패: {e}")
        return {
            'success': False,
            'message': f'데이터 삽입 중 오류: {str(e)}',
            'inserted_count': 0
        }

def insert_from_json_file(file_path: str) -> Dict[str, any]:
    """JSON 파일에서 데이터 읽어서 삽입"""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return {'success': False, 'message': f'파일이 존재하지 않습니다: {file_path}', 'inserted_count': 0}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 데이터가 리스트인지 확인
        if not isinstance(data, list):
            if isinstance(data, dict) and 'data' in data:
                data = data['data']  # 메타데이터가 있는 경우
            else:
                return {'success': False, 'message': 'JSON 파일 형식이 올바르지 않습니다.', 'inserted_count': 0}
        
        return insert_data_batch(data)
        
    except Exception as e:
        logger.error(f"JSON 파일에서 데이터 읽기 실패: {e}")
        return {'success': False, 'message': f'JSON 파일 처리 중 오류: {str(e)}', 'inserted_count': 0}

def insert_from_csv_file(file_path: str, limit: Optional[int] = None) -> Dict[str, any]:
    """CSV 파일에서 데이터 읽어서 삽입"""
    try:
        # limit이 지정된 경우 해당 개수만 읽기
        if limit:
            df = pd.read_csv(file_path, nrows=limit)
            print(f"📄 CSV 파일에서 상위 {limit}개 행 읽기: {file_path}")
        else:
            df = pd.read_csv(file_path)
            print(f"📄 CSV 파일 전체 읽기: {file_path}")
        
        print(f"📊 읽은 데이터 행 수: {len(df)}")
        
        # 컬럼 정보 출력
        print(f"📋 컬럼 목록: {list(df.columns)}")
        
        # 필수 컬럼 확인 (유연하게 처리)
        time_columns = [col for col in df.columns if 'time' in col.lower() or 'timestamp' in col.lower()]
        pass_fail_columns = [col for col in df.columns if 'pass' in col.lower() or 'fail' in col.lower()]
        
        if not time_columns:
            # time 컬럼이 없으면 현재 시간으로 생성
            df['time'] = pd.date_range(start=datetime.now(), periods=len(df), freq='5T')
            print("⚠️  시간 컬럼이 없어서 자동 생성했습니다.")
        else:
            # 첫 번째 시간 컬럼 사용
            time_col = time_columns[0]
            if time_col != 'time':
                df['time'] = df[time_col]
                print(f"📅 시간 컬럼 사용: {time_col}")
        
        if not pass_fail_columns:
            # passorfail 컬럼이 없으면 랜덤 생성
            df['passorfail'] = ['Pass' if random.random() > 0.1 else 'Fail' for _ in range(len(df))]
            print("⚠️  Pass/Fail 컬럼이 없어서 랜덤 생성했습니다.")
        else:
            # 첫 번째 pass/fail 컬럼 사용
            pass_fail_col = pass_fail_columns[0]
            if pass_fail_col != 'passorfail':
                df['passorfail'] = df[pass_fail_col]
                print(f"✅ Pass/Fail 컬럼 사용: {pass_fail_col}")
        
        # 샘플 데이터 출력
        print("\n📋 읽은 데이터 샘플 (처음 3행):")
        print(df.head(3).to_string())
        
        # DataFrame을 딕셔너리 리스트로 변환
        data_list = df.to_dict('records')
        
        return insert_data_batch(data_list)
        
    except Exception as e:
        logger.error(f"CSV 파일에서 데이터 읽기 실패: {e}")
        return {'success': False, 'message': f'CSV 파일 처리 중 오류: {str(e)}', 'inserted_count': 0}

def insert_top_n_from_csv(file_path: str, n: int = 10) -> Dict[str, any]:
    """CSV 파일에서 상위 N개 행만 읽어서 삽입"""
    return insert_from_csv_file(file_path, limit=n)

def get_current_data_count() -> int:
    """현재 저장된 데이터 개수 조회"""
    engine = get_db_engine()
    if not engine:
        return -1
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM sensor_data"))
            count = result.scalar()
            return count
            
    except Exception as e:
        logger.error(f"데이터 개수 조회 중 오류: {e}")
        return -1

def main():
    """메인 실행 함수"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='TimescaleDB 데이터 마이그레이션 도구')
    parser.add_argument('--init', action='store_true', help='테이블 초기화')
    parser.add_argument('--sample', type=int, metavar='COUNT', help='샘플 데이터 생성 및 삽입')
    parser.add_argument('--json', type=str, metavar='FILE', help='JSON 파일에서 데이터 삽입')
    parser.add_argument('--csv', type=str, metavar='FILE', help='CSV 파일에서 데이터 삽입')
    parser.add_argument('--csv-top', type=str, metavar='FILE', help='CSV 파일에서 상위 10개만 삽입')
    parser.add_argument('--limit', type=int, default=10, metavar='N', help='CSV에서 읽을 행 수 (기본값: 10)')
    parser.add_argument('--count', action='store_true', help='현재 데이터 개수 확인')
    
    args = parser.parse_args()
    
    print("=== TimescaleDB 데이터 마이그레이션 도구 ===")
    
    # 현재 데이터 개수 확인
    if args.count or len(sys.argv) == 1:
        current_count = get_current_data_count()
        if current_count >= 0:
            print(f"📊 현재 저장된 데이터: {current_count:,}개")
        else:
            print("❌ 데이터베이스 연결에 실패했습니다.")
            return
    
    # 테이블 초기화
    if args.init:
        print("🔧 테이블 초기화 중...")
        if init_sensor_data_table():
            print("✅ 테이블 초기화 완료")
        else:
            print("❌ 테이블 초기화 실패")
            return
    
    # 샘플 데이터 생성
    if args.sample:
        print(f"🎲 샘플 데이터 {args.sample}개 생성 중...")
        sample_data = generate_sample_data(args.sample)
        result = insert_data_batch(sample_data)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    # JSON 파일에서 삽입
    if args.json:
        print(f"📄 JSON 파일에서 데이터 삽입 중: {args.json}")
        result = insert_from_json_file(args.json)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    # CSV 파일에서 전체 삽입
    if args.csv:
        print(f"📄 CSV 파일에서 데이터 삽입 중: {args.csv}")
        result = insert_from_csv_file(args.csv)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    # CSV 파일에서 상위 N개만 삽입
    if args.csv_top:
        print(f"📄 CSV 파일에서 상위 {args.limit}개 데이터 삽입 중: {args.csv_top}")
        result = insert_top_n_from_csv(args.csv_top, args.limit)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    # 최종 데이터 개수 확인
    if args.init or args.sample or args.json or args.csv or args.csv_top:
        final_count = get_current_data_count()
        if final_count >= 0:
            print(f"📊 최종 데이터 개수: {final_count:,}개")

if __name__ == "__main__":
    main()