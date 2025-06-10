import logging
from sqlalchemy import create_engine, text
import os
from typing import Dict

logger = logging.getLogger(__name__)

# TimescaleDB 연결 설정
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5434'),
    'database': os.getenv('POSTGRES_DB', 'diecasting_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password')
}

def check_db_config():
    """데이터베이스 설정 확인"""
    print("=== 데이터베이스 설정 확인 ===")
    env_mapping = {
        'host': 'POSTGRES_HOST',
        'port': 'POSTGRES_PORT', 
        'database': 'POSTGRES_DB',  # DATABASE가 아니라 DB
        'user': 'POSTGRES_USER',
        'password': 'POSTGRES_PASSWORD'
    }
    
    for key, value in DB_CONFIG.items():
        env_key = env_mapping[key]
        env_value = os.getenv(env_key, "설정되지 않음")
        print(f"{env_key}: {env_value}")
    
    connection_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    print(f"\n연결 문자열: {connection_string}")
    print()

def get_db_engine():
    """데이터베이스 엔진 생성"""
    try:
        connection_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        engine = create_engine(connection_string, pool_pre_ping=True)
        return engine
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return None

def clear_all_timescale_data(confirm: bool = False) -> Dict[str, any]:
    """
    TimescaleDB의 sensor_data 테이블에서 모든 데이터를 삭제
    
    Args:
        confirm: 삭제 확인 플래그 (True여야 실제 삭제 실행)
    
    Returns:
        Dict: 삭제 결과 정보
    """
    if not confirm:
        return {
            'success': False,
            'message': '데이터 삭제를 위해서는 confirm=True 파라미터가 필요합니다.',
            'deleted_count': 0
        }
    
    engine = get_db_engine()
    if not engine:
        return {
            'success': False,
            'message': '데이터베이스 연결에 실패했습니다.',
            'deleted_count': 0
        }
    
    try:
        with engine.connect() as conn:
            # 삭제 전 데이터 개수 확인
            count_result = conn.execute(text("SELECT COUNT(*) FROM sensor_data"))
            total_count = count_result.scalar()
            
            logger.info(f"삭제 예정 데이터 개수: {total_count}")
            
            if total_count == 0:
                return {
                    'success': True,
                    'message': '삭제할 데이터가 없습니다.',
                    'deleted_count': 0
                }
            
            # 모든 데이터 삭제
            delete_result = conn.execute(text("DELETE FROM sensor_data"))
            deleted_count = delete_result.rowcount
            
            # 트랜잭션 커밋
            conn.commit()
            
            logger.info(f"TimescaleDB 데이터 삭제 완료: {deleted_count}개 레코드 삭제")
            
            return {
                'success': True,
                'message': f'성공적으로 {deleted_count}개의 레코드를 삭제했습니다.',
                'deleted_count': deleted_count
            }
            
    except Exception as e:
        logger.error(f"데이터 삭제 중 오류: {e}")
        return {
            'success': False,
            'message': f'데이터 삭제 중 오류가 발생했습니다: {str(e)}',
            'deleted_count': 0
        }

def get_data_count() -> int:
    """현재 저장된 데이터 개수 조회"""
    engine = get_db_engine()
    if not engine:
        return -1
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM sensor_data"))
            count = result.scalar()
            logger.info(f"현재 저장된 데이터 개수: {count}")
            return count
            
    except Exception as e:
        logger.error(f"데이터 개수 조회 중 오류: {e}")
        return -1


def main():
    """명령줄에서 직접 실행할 때 사용"""
    import sys
    
    print("=== TimescaleDB 데이터 삭제 도구 ===")
    
    # 데이터베이스 설정 확인
    check_db_config()
    
    # 현재 데이터 개수 확인
    current_count = get_data_count()
    if current_count == -1:
        print("❌ 데이터베이스 연결에 실패했습니다.")
        print("\n해결 방법:")
        print("1. PostgreSQL이 실행 중인지 확인")
        print("2. 환경변수가 올바르게 설정되었는지 확인")
        print("3. 데이터베이스가 존재하는지 확인")
        return
    
    if current_count == 0:
        print("📝 삭제할 데이터가 없습니다.")
        return
    
    print(f"📊 현재 저장된 데이터: {current_count:,}개")
    
    # 사용자 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        # --force 옵션이 있으면 바로 삭제
        confirm_delete = True
        print("⚠️  --force 옵션으로 인해 자동으로 삭제를 진행합니다.")
    else:
        # 사용자에게 확인 요청
        user_input = input(f"\n⚠️  정말로 모든 데이터({current_count:,}개)를 삭제하시겠습니까? (yes/no): ")
        confirm_delete = user_input.lower() in ['yes', 'y', '예']
    
    if confirm_delete:
        print("🗑️  데이터 삭제를 시작합니다...")
        result = clear_all_timescale_data(confirm=True)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    else:
        print("❌ 삭제가 취소되었습니다.")

if __name__ == "__main__":
    main()