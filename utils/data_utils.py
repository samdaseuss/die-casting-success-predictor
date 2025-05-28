import json
import logging
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parents[1]
snapshots_dir = project_root / "snapshots"
DATA_FILE = project_root / "data/collected_data.json"
TEST_PY_FILE = project_root / "data/test.py"


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


def cleanup_old_snapshots():
    """오래된 스냅샷 파일 정리"""
    try:
        # 배치 스냅샷과 개별 스냅샷 모두 정리
        all_snapshot_files = list(snapshots_dir.glob("*snapshot*.json"))
        if len(all_snapshot_files) > 50:  # 15분 간격이므로 보관 개수 줄임
            # 날짜순 정렬 후 오래된 것부터 삭제
            all_snapshot_files.sort(key=lambda x: x.stat().st_mtime)
            for old_file in all_snapshot_files[:-50]:
                old_file.unlink()
                logger.info(f"오래된 스냅샷 삭제: {old_file}")
    except Exception as e:
        logger.error(f"스냅샷 정리 중 오류: {e}")


def prepare_postgresql_data(data):
    """PostgreSQL 저장을 위한 데이터 준비"""
    try:
        # PostgreSQL 연결 준비를 위한 데이터 검증 및 정리
        cleaned_data = []
        for record in data:
            # 데이터 검증 및 정리
            if isinstance(record, dict) and 'timestamp' in record:
                # PostgreSQL에 맞는 형식으로 데이터 정리
                cleaned_record = {}
                for key, value in record.items():
                    if value is not None:
                        cleaned_record[key] = value
                cleaned_data.append(cleaned_record)
        
        # TODO: PostgreSQL 연결 시 여기에 INSERT 쿼리 추가
        logger.info(f"PostgreSQL 저장 준비 완료: {len(cleaned_data)}개 레코드")
        
    except Exception as e:
        logger.error(f"PostgreSQL 데이터 준비 중 오류: {e}")


def save_snapshot_batch(all_data):
    """15분마다 배치로 스냅샷 저장"""
    try:
        if not all_data:
            logger.info("저장할 데이터가 없습니다.")
            return
            
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        data_count = len(all_data)
        snapshot_file = snapshots_dir / f"batch_snapshot_{timestamp}_{data_count}records.json"
        
        # 스냅샷 메타데이터 추가
        snapshot_data = {
            "metadata": {
                "created_at": datetime.datetime.now().isoformat(),
                "total_records": data_count,
                "snapshot_type": "batch_15min",
                "version": "1.0"
            },
            "data": all_data
        }
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"배치 스냅샷 저장 완료: {snapshot_file} ({data_count}개 레코드)")
        
        # 오래된 스냅샷 정리 (최근 50개만 유지 - 15분 간격이므로 개수 줄임)
        cleanup_old_snapshots()
        
        # PostgreSQL 저장 준비 (추후 연결 시 사용)
        prepare_postgresql_data(all_data)
        
    except Exception as e:
        logger.error(f"배치 스냅샷 저장 중 오류: {e}")


def create_test_py_if_not_exists():
    """test.py 파일이 없으면 샘플 파일 생성"""
    if not TEST_PY_FILE.exists():
        sample_content = '''# 다이캐스팅 실시간 데이터 파일
# 이 파일을 수정하면 대시보드에서 자동으로 감지하여 데이터를 수집합니다.

import datetime
import random

def get_current_data():
    """현재 다이캐스팅 공정 데이터 반환"""
    return {
        "molten_temp": round(random.uniform(680, 720), 1),
        "production_cycletime": round(random.uniform(25, 35), 1),
        "low_section_speed": round(random.uniform(20, 30), 1),
        "high_section_speed": round(random.uniform(90, 110), 0),
        "cast_pressure": round(random.uniform(55, 85), 1),
        "biscuit_thickness": round(random.uniform(10, 14), 1),
        "upper_mold_temp1": round(random.uniform(190, 210), 1),
        "upper_mold_temp2": round(random.uniform(190, 210), 1),
        "upper_mold_temp3": round(random.uniform(190, 210), 1),
        "lower_mold_temp1": round(random.uniform(190, 210), 1),
        "lower_mold_temp2": round(random.uniform(190, 210), 1),
        "lower_mold_temp3": round(random.uniform(190, 210), 1),
        "sleeve_temperature": round(random.uniform(220, 240), 1),
        "physical_strength": round(random.uniform(280, 320), 0),
        "Coolant_temperature": round(random.uniform(20, 30), 1),
        "passorfail": "Pass" if random.random() > 0.15 else "Fail",
        "timestamp": datetime.datetime.now().isoformat()
    }

# 현재 데이터 (이 부분을 수정하면 대시보드에서 자동 감지)
current_data = get_current_data()
'''
        try:
            with open(TEST_PY_FILE, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            logger.info("test.py 샘플 파일이 생성되었습니다.")
        except Exception as e:
            logger.error(f"test.py 파일 생성 중 오류: {e}")


def read_data_from_test_py():
    """test.py에서 실제 데이터 읽기"""
    try:
        if not TEST_PY_FILE.exists():
            create_test_py_if_not_exists()
            return None
            
        # test.py 파일 읽기
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("test_module", TEST_PY_FILE)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        # current_data 또는 get_current_data() 함수 확인
        if hasattr(test_module, 'current_data'):
            data = test_module.current_data
            if isinstance(data, dict):
                data['timestamp'] = datetime.datetime.now().isoformat()
                data['source'] = 'test.py'
                return data
        elif hasattr(test_module, 'get_current_data'):
            data = test_module.get_current_data()
            if isinstance(data, dict):
                data['timestamp'] = datetime.datetime.now().isoformat()
                data['source'] = 'test.py'
                return data
                
        logger.warning("test.py에서 유효한 데이터를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        logger.error(f"test.py에서 데이터 읽기 중 오류: {e}")
        return None
    

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