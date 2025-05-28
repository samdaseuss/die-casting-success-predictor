import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import datetime
import time


project_root = Path(__file__).parent
sys.path.append(str(project_root))

snapshots_dir = project_root / "snapshots"

def run():
    st.markdown('<h2 class="sub-header">📈 수집된 데이터 분석</h2>', unsafe_allow_html=True)
        
    if st.session_state.collected_data:
        df = pd.DataFrame(st.session_state.collected_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📊 기본 통계")
            st.write(f"전체 데이터 포인트: {len(df)}")
            st.write(f"Pass 비율: {(df['passorfail'] == 'Pass').sum() / len(df) * 100:.1f}%")
            st.write(f"오류 데이터: {df.get('error', pd.Series(False)).sum()}개")
            
        with col2:
            st.markdown("### 📅 데이터 수집 기간")
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                st.write(f"시작 시간: {df['timestamp'].min()}")
                st.write(f"종료 시간: {df['timestamp'].max()}")
                st.write(f"수집 기간: {df['timestamp'].max() - df['timestamp'].min()}")
        
        st.markdown("### 📂 스냅샷 관리 (15분 배치 저장)")
        snapshot_files = list(snapshots_dir.glob("*snapshot*.json"))
        st.write(f"저장된 스냅샷: {len(snapshot_files)}개")
        
        # 마지막 스냅샷 저장 시간
        if st.session_state.data_collection_started:
            last_snapshot_minutes = (time.time() - st.session_state.last_snapshot_time) / 60
            st.write(f"마지막 스냅샷: {last_snapshot_minutes:.1f}분 전")
            next_snapshot_minutes = 15 - last_snapshot_minutes
            if next_snapshot_minutes > 0:
                st.write(f"다음 스냅샷: {next_snapshot_minutes:.1f}분 후")
        
        if snapshot_files:
            # 최근 스냅샷 5개 표시
            recent_snapshots = sorted(snapshot_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            st.write("**최근 스냅샷:**")
            for snapshot in recent_snapshots:
                # 파일 크기 정보 추가
                file_size = snapshot.stat().st_size / 1024  # KB
                st.write(f"- {snapshot.name} ({file_size:.1f} KB)")
                
            # PostgreSQL 연결 준비 상태 표시
            st.markdown("### 🗄️ PostgreSQL 연결 준비")
            st.info("💡 PostgreSQL 연결 설정 후 자동으로 데이터베이스에 저장됩니다.")
        
        # 전체 데이터 다운로드
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📊 전체 데이터 CSV 다운로드",
            data=csv_data,
            file_name=f"collected_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
    else:
        st.info("📊 분석할 데이터가 없습니다. 데이터 수집을 시작해주세요.")