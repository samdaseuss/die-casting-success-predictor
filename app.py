# ./app.py

import streamlit as st
import sys, time, logging
from pathlib import Path
from styles.style_manager import apply_global_style
from utils.data_utils import (
    load_data_from_file,
    save_snapshot_batch,
    read_data_from_test_py,
    save_data_to_file,
    reset_processed_hashes,
    get_recent_fail_data,
    get_recent_pass_data,
    get_max_data_id,
    append_today_data)
from tabs import (
    input_perameter_m_t, 
    analysis_m_t, 
    monitoring_m_t, 
    realtime_manufacturing_m_t)
from utils.clear_timescale_data import get_data_count
from utils.data_utils import init_timescale_db
from streamlit_autorefresh import st_autorefresh


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.append(str(project_root))

data_dir = project_root / "data"
snapshots_dir = project_root / "snapshots"

data_dir.mkdir(exist_ok=True)
snapshots_dir.mkdir(exist_ok=True)

DATA_FILE = data_dir / "collected_data.json"
TEST_PY_FILE = data_dir / "test.py"


st.set_page_config(
    page_title="다이캐스팅 품질 예측 대시보드",
    page_icon="⛔︎",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_synchronized_start_time():
    if 'system_start_time' not in st.session_state:
        current_time = time.time()
        st.session_state.system_start_time = current_time
        # 이미 위에서 초기화된 변수들이므로 여기서는 설정만 함
        st.session_state.cycle_count = 0
        st.session_state.data_collection_count = 0
        st.session_state.last_collected_cycle = -1
        st.session_state.first_cycle_completed = False
    return st.session_state.system_start_time


if 'data_collection_started' not in st.session_state:
    st.session_state.data_collection_started = False
if 'collected_data' not in st.session_state:
    st.session_state.collected_data = []
if 'current_status' not in st.session_state:
    st.session_state.current_status = {}
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = 0
if 'last_snapshot_time' not in st.session_state:
    st.session_state.last_snapshot_time = time.time()
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
if 'ng_history' not in st.session_state:
    st.session_state.ng_history = []
if 'current_data_id' not in st.session_state:
    try:
        max_id = get_max_data_id()
        if max_id == 0:
            next_id = 73612
            logger.info("데이터베이스가 비어있어 ID를 73612로 초기화")
        else:
            next_id = max_id + 1
            logger.info(f"데이터베이스 최대 ID({max_id}) 기반으로 다음 ID 설정: {next_id}")
    except Exception as e:
        logger.warning(f"데이터베이스 ID 조회 실패: {e}, 기본값 73612 사용")
        next_id = 73612
    st.session_state.current_data_id = next_id
    logger.info(f"초기 데이터 ID 설정: {next_id}")
if 'processed_data_hashes' not in st.session_state:
    st.session_state.processed_data_hashes = set()
if 'data_collection_count' not in st.session_state:
    st.session_state.data_collection_count = 0
if 'last_collected_cycle' not in st.session_state:
    st.session_state.last_collected_cycle = -1
if 'first_cycle_completed' not in st.session_state:
    st.session_state.first_cycle_completed = False
if 'cycle_count' not in st.session_state:
    st.session_state.cycle_count = 0
if 'collected_data_today' not in st.session_state:
    st.session_state.collected_data_today = []

@st.cache_data(ttl=30)
def _get_counts():
    data_cnt = get_data_count()
    pass_cnt = len(get_recent_pass_data())
    fail_cnt = len(get_recent_fail_data())
    return data_cnt, fail_cnt, pass_cnt

st_autorefresh(interval=60 * 1000, key="data_refresh")
data_cnt, fail_cnt, pass_cnt = _get_counts()
st.session_state.current_database_data_count = data_cnt
st.session_state.current_database_pass_data_count = pass_cnt
st.session_state.current_database_fail_data_count = fail_cnt

apply_global_style(st.session_state.dark_mode)

def main():
    if 'db_initialized' not in st.session_state:
        if init_timescale_db():
            st.session_state.db_initialized = True
            logger.info("DB 초기화 완료")
        else:
            st.warning("DB 연결에 실패했습니다. 로컬 파일 모드로 실행됩니다.")
            st.session_state.db_initialized = False
    
    system_status_class = "system-status-indicator online" if st.session_state.data_collection_started else "system-status-indicator offline"
    system_status_text = "시스템 가동중" if st.session_state.data_collection_started else "시스템 중지"
    
    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.markdown(f'<div class="header-controls"><div class="{system_status_class}">{system_status_text}</div></div>', unsafe_allow_html=True)
    
    with header_col2:
        dark_mode_toggle = st.toggle("🌙", value=st.session_state.dark_mode, key="header_dark_toggle", help="다크 모드")
        if dark_mode_toggle != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode_toggle
    
    with st.sidebar:
        st.markdown("### 데이터 수집")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("시작", use_container_width=True, disabled=st.session_state.data_collection_started):
                st.session_state.data_collection_started = True
                st.session_state.collected_data = load_data_from_file()
                
                # 새로운 사이클 시작 - 현재 시간을 시작점으로 설정
                current_time = time.time()
                st.session_state.system_start_time = current_time
                st.session_state.cycle_count = 0
                st.session_state.data_collection_count = 0
                st.session_state.last_collected_cycle = -1
                st.session_state.last_update_time = 0  # 초기화하여 첫 번째 사이클에서 수집하지 않도록
                
                # 첫 번째 사이클 완료 후 데이터 수집 시작을 위한 플래그
                st.session_state.first_cycle_completed = False
                
                st.success("시작됨! 공정 사이클이 시작되었습니다.")
                # time.sleep(1)
                # st.rerun()

        with col2:
            if st.button("중지", use_container_width=True, disabled=not st.session_state.data_collection_started):
                st.session_state.data_collection_started = False
                st.success("중지됨!")
                time.sleep(1)
                st.rerun()
        st.markdown("---")
        st.markdown("### 시스템 제어")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("수동 데이터 읽기", use_container_width=True):
                with st.spinner("데이터 읽는 중..."):
                    try:
                        new_data = read_data_from_test_py()
                        logger.info(f"***{new_data}***")
                        if new_data:
                            st.session_state.current_status = new_data
                            append_today_data(new_data)
                            st.session_state.collected_data_today.append(new_data)
                            try:
                                from tabs.realtime_manufacturing_m_t import RealTimeDataManager
                                collected = RealTimeDataManager.collect_realtime_data()
                                
                                # 수정: 버퍼 크기 체크 및 관리도 자동 업데이트
                                buffer_size = len(st.session_state.get('realtime_buffer', []))
                                logger.info(f"현재 버퍼 크기: {buffer_size}")
                                
                                # 버퍼에 10개 이상 데이터가 있으면 관리도 업데이트 시도
                                if buffer_size >= 10:
                                    if RealTimeDataManager.update_control_chart():
                                        logger.info("관리도 자동 업데이트 성공")
                                        st.success("관리도가 자동으로 업데이트되었습니다!")
                                    else:
                                        logger.warning("관리도 자동 업데이트 실패")
                                
                                st.success(f"데이터 수집 완료! (총 {len(st.session_state.collected_data_today)}개, 버퍼: {buffer_size}개)")
                                
                                # 수정: collected_data_today 초기화 조건 변경
                                if len(st.session_state.collected_data_today) >= 20:  # 10에서 20으로 증가
                                    st.session_state.collected_data_today = []
                                    
                            except Exception as e:
                                st.success(f"데이터 수집 완료! (총 {len(st.session_state.collected_data_today)}개)")
                                logger.warning(f"실시간 버퍼 업데이트 실패: {str(e)}")
                            with st.expander("수집된 데이터 내용"):
                                st.json(new_data)
                        else:
                            st.info("새로운 데이터가 없거나 중복 데이터입니다.")
                    except Exception as e:
                        st.error(f"데이터 읽기 오류: {str(e)}")
        with col_btn2:
            if st.button("즉시 데이터 저장", use_container_width=True):
                if st.session_state.collected_data_today:
                    with st.spinner("저장 중..."):
                        try:
                            save_snapshot_batch(st.session_state.collected_data_today)
                            st.session_state.last_snapshot_time = time.time()
                            st.success("데이터가 저장되었습니다!") # 스냅샷에 저장
                        except Exception as e:
                            st.error(f"저장 오류: {str(e)}")
                else:
                    st.warning("저장할 데이터가 없습니다.")
        if st.button("관리도 데이터 갱신", use_container_width=True):
            with st.spinner("관리도 데이터 갱신 중..."):
                try:
                    from tabs.realtime_manufacturing_m_t import RealTimeDataManager
                    if RealTimeDataManager.update_control_chart():
                       # RealTimeDataManager.save_buffer_to_file()
                        st.success("관리도 데이터가 갱신되었습니다!")
                    else:
                        st.warning("갱신할 데이터가 없습니다.")
                except Exception as e:
                    st.error(f"관리도 데이터 갱신 오류: {str(e)}")

        st.markdown("---")
        st.markdown("### 새로고침 설정")
        auto_refresh = st.checkbox("자동 새로고침 (10초)", value=True)

        st.markdown("---")
        st.markdown("### 데이터 관리")
        if st.button("전체 데이터 초기화", use_container_width=True):
            if st.session_state.data_collection_started:
                st.error("시스템을 먼저 중지해주세요!")
            else:
                st.session_state.collected_data = []
                st.session_state.current_status = {}
                st.session_state.last_snapshot_time = time.time()
                st.session_state.last_update_time = 0
                
                # 시스템 시작 관련 상태 초기화
                reset_keys = [
                    'system_start_time', 
                    'cycle_count', 
                    'first_cycle_completed',
                    'last_collected_cycle',
                    'data_collection_count'
                ]
                for key in reset_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # 공정 동기화 관련 상태 초기화
                process_keys = [
                    'process_cycle_start_time', 
                    'process_stage', 
                    'pending_data', 
                    'current_display_data', 
                    'last_data_id', 
                    'realtime_buffer'
                ]
                for key in process_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # 중복 방지 해시 초기화
                st.session_state.processed_data_hashes = set()
                reset_processed_hashes()
                
                # 파일 삭제
                if DATA_FILE.exists():
                    DATA_FILE.unlink()
                for snapshot_file in snapshots_dir.glob("*.json"):
                    snapshot_file.unlink()
                st.success("초기화 완료!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 시스템 정보")
        st.info(f"데이터 소스\n`{TEST_PY_FILE.name}`")
        
        total_data = len(st.session_state.collected_data)
        st.metric("수집된 데이터", f"{total_data:,}개")
        
        snapshot_count = len(list(snapshots_dir.glob("*snapshot*.json")))
        st.metric("저장된 스냅샷", f"{snapshot_count}개")
        
        # 중복 방지 현황 표시
        processed_hashes = len(st.session_state.get('processed_data_hashes', set()))
        st.metric("처리된 해시", f"{processed_hashes}개")
        
        if st.session_state.data_collection_started:
            start_time = get_synchronized_start_time()
            current_time = time.time()
            elapsed_time = current_time - start_time
            current_cycle = int(elapsed_time // 30)
            time_in_cycle = elapsed_time % 30
            
            # 사이클 카운터 업데이트
            if current_cycle > st.session_state.get('cycle_count', 0):
                st.session_state.cycle_count = current_cycle
                if current_cycle >= 1:  # 첫 번째 사이클(0번) 완료 후
                    st.session_state.first_cycle_completed = True
            
            # ===== 핵심 수정: 데이터 수집 타이밍 조정 =====
            should_collect = False
            collection_window_start = 29.5  # 사이클 끝 0.5초 전부터
            collection_window_end = 30.0    # 사이클 끝까지
            
            # 첫 번째 사이클이 완료된 후에만 데이터 수집 시작
            if st.session_state.get('first_cycle_completed', False):
                # 방법 1: 사이클 완료 직전 구간에서 수집 (추천)
                if collection_window_start <= time_in_cycle < collection_window_end:
                    # 이 사이클에서 아직 수집하지 않았는지 확인
                    if st.session_state.get('last_collected_cycle', -1) < current_cycle:
                        should_collect = True
                
                # 방법 2: 추가 안전장치 - 마지막 수집 후 최소 29초 경과
                time_since_last = current_time - st.session_state.last_update_time
                if time_since_last >= 29:  # 거의 한 사이클 시간
                    should_collect = True
            
            if should_collect:
                new_data = read_data_from_test_py()
                if new_data:
                    st.session_state.collected_data.append(new_data)
                    st.session_state.current_status = new_data
                    save_data_to_file(st.session_state.collected_data)
                    st.session_state.last_update_time = current_time
                    st.session_state.last_collected_cycle = current_cycle  # 수집한 사이클 기록
                    st.session_state.data_collection_count += 1  # 수집 횟수 증가
                    
                    logger.info(f"사이클 {current_cycle + 1} 완료 - 데이터 수집됨 (총 {st.session_state.data_collection_count}회)")
                    
                    # 실시간 버퍼 업데이트
                    try:
                        from tabs.realtime_manufacturing_m_t import RealTimeDataManager
                        collected = RealTimeDataManager.collect_realtime_data()
                        if collected:
                            logger.info("실시간 버퍼에 데이터 추가됨")
                    except Exception as e:
                        logger.warning(f"실시간 버퍼 업데이트 실패: {str(e)}")
                else:
                    logger.debug("자동 수집: 새로운 데이터 없음 또는 중복")
            
            # 시스템 정보 표시 개선
            st.metric("현재 사이클", f"{current_cycle + 1}번째")
            st.metric("데이터 수집", f"{st.session_state.get('data_collection_count', 0)}회")
            
            # 현재 공정 단계 표시
            if time_in_cycle < 10:
                stage = "용융/가열"
                stage_progress = time_in_cycle / 10 * 100
            elif time_in_cycle < 25:
                stage = "주조/압력"
                stage_progress = (time_in_cycle - 10) / 15 * 100
            else:
                stage = "냉각/완료"
                stage_progress = (time_in_cycle - 25) / 5 * 100
            
            st.metric("현재 단계", f"{stage} ({stage_progress:.0f}%)")
            
            # 다음 수집까지 남은 시간
            if st.session_state.get('first_cycle_completed', False):
                if time_in_cycle < collection_window_start:
                    next_collection = collection_window_start - time_in_cycle
                    st.metric("다음 수집", f"{next_collection:.1f}초 후")
                elif time_in_cycle < collection_window_end:
                    st.metric("수집 구간", "진행 중")
                else:
                    next_collection = 30 - time_in_cycle + collection_window_start
                    st.metric("다음 수집", f"{next_collection:.1f}초 후")
            else:
                remaining_first_cycle = 30 - elapsed_time if elapsed_time < 30 else 0
                if remaining_first_cycle > 0:
                    st.metric("첫 사이클 완료", f"{remaining_first_cycle:.1f}초 후")
                else:
                    st.metric("데이터 수집", "준비됨")
            
            with st.expander("수집 상태 디버깅"):
                st.write(f"전체 경과 시간: {elapsed_time:.1f}초")
                st.write(f"현재 사이클: {current_cycle + 1}")
                st.write(f"사이클 내 시간: {time_in_cycle:.1f}초")
                st.write(f"현재 단계: {stage}")
                st.write(f"첫 사이클 완료: {st.session_state.get('first_cycle_completed', False)}")
                st.write(f"마지막 수집 사이클: {st.session_state.get('last_collected_cycle', -1)}")
                st.write(f"수집 가능 구간: {collection_window_start:.1f}~{collection_window_end:.1f}초")
                st.write(f"수집 조건 만족: {should_collect}")
                st.write(f"총 수집 횟수: {st.session_state.get('data_collection_count', 0)}")
            
            # 1시간마다 자동 저장으로 변경
            if current_time - st.session_state.last_snapshot_time > 3600:
                if st.session_state.collected_data:
                    save_snapshot_batch(st.session_state.collected_data)
                    st.session_state.last_snapshot_time = current_time
                    logger.info("1시간 누적데이터 저장 완료")
    
    
    st.markdown(
        '<h1 class="main-header">다이캐스팅 품질 예측 대시보드</h1>', 
        unsafe_allow_html=True
    )
    
    # 탭 구성
    tabs = st.tabs([
        "실시간 현황", 
        "차트 모니터링", 
        "파라미터 입력",
        "데이터 분석"
    ])
    
    with tabs[0]:
        realtime_manufacturing_m_t.run()

    with tabs[1]:
        monitoring_m_t.run()
    
    with tabs[2]:
        input_perameter_m_t.run()
    
    with tabs[3]:
        analysis_m_t.run()
    
    if auto_refresh and st.session_state.data_collection_started:
        time.sleep(2.5)
        st.rerun()

if __name__ == "__main__":
    main()