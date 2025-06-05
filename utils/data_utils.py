import json
import logging
import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parents[1]
snapshots_dir = project_root / "snapshots"
DATA_FILE = project_root / "data/collected_data.json"
TEST_PY_FILE = project_root / "data/test.py"

# 마지막으로 읽은 데이터의 해시값 저장
_last_data_hash = None

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
        all_snapshot_files = list(snapshots_dir.glob("*snapshot*.json"))
        if len(all_snapshot_files) > 50:
            all_snapshot_files.sort(key=lambda x: x.stat().st_mtime)
            for old_file in all_snapshot_files[:-50]:
                old_file.unlink()
                logger.info(f"오래된 스냅샷 삭제: {old_file}")
    except Exception as e:
        logger.error(f"스냅샷 정리 중 오류: {e}")

def prepare_postgresql_data(data):
    """PostgreSQL 저장을 위한 데이터 준비"""
    try:
        cleaned_data = []
        for record in data:
            if isinstance(record, dict) and 'timestamp' in record:
                cleaned_record = {}
                for key, value in record.items():
                    if value is not None:
                        cleaned_record[key] = value
                cleaned_data.append(cleaned_record)
        
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
        cleanup_old_snapshots()
        prepare_postgresql_data(all_data)
        
    except Exception as e:
        logger.error(f"배치 스냅샷 저장 중 오류: {e}")

def create_data_hash(data):
    """데이터의 고유 해시값 생성 (timestamp 제외)"""
    if not isinstance(data, dict):
        return None
    
    # timestamp를 제외한 데이터로 해시 생성
    data_for_hash = {k: v for k, v in data.items() if k not in ['timestamp', 'source']}
    data_str = json.dumps(data_for_hash, sort_keys=True)
    return hashlib.md5(data_str.encode()).hexdigest()

def read_data_from_test_py():
    """test.py에서 실제 데이터 읽기 - 중복 방지 강화"""
    global _last_data_hash
    
    try:
        import sys
        import importlib.util
        
        # 기존 모듈 캐시 제거
        module_name = "test_module"
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        # 파일에서 직접 새로 로드
        spec = importlib.util.spec_from_file_location(module_name, TEST_PY_FILE)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        # 최대 10번 시도하여 새로운 데이터 얻기
        max_attempts = 10
        for attempt in range(max_attempts):
            if hasattr(test_module, 'get_current_data'):
                data = test_module.get_current_data()
                if isinstance(data, dict):
                    # 데이터 해시 생성
                    data_hash = create_data_hash(data)
                    
                    # 새로운 데이터인지 확인
                    if data_hash != _last_data_hash:
                        data['timestamp'] = datetime.datetime.now().isoformat()
                        data['source'] = 'test.py'
                        data['data_hash'] = data_hash
                        _last_data_hash = data_hash
                        logger.info(f"새로운 데이터 읽기 성공 (시도 {attempt + 1}회)")
                        return data
                    else:
                        logger.debug(f"중복 데이터 감지, 재시도 중... ({attempt + 1}/{max_attempts})")
                        continue
        
        # 모든 시도 실패 시
        logger.warning(f"{max_attempts}번 시도 후에도 새로운 데이터를 얻지 못했습니다.")
        
        # current_data 변수 백업 시도
        if hasattr(test_module, 'current_data'):
            data = test_module.current_data
            if isinstance(data, dict):
                data_hash = create_data_hash(data)
                if data_hash != _last_data_hash:
                    data['timestamp'] = datetime.datetime.now().isoformat()
                    data['source'] = 'test.py'
                    data['data_hash'] = data_hash
                    _last_data_hash = data_hash
                    return data
                
        logger.warning("test.py에서 새로운 유효한 데이터를 찾을 수 없습니다.")
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