# styles/table_styles.py
"""
데이터 표시를 위한 스타일링 모듈
다크모드와 라이트모드에 따른 테이블, 페이지네이션 스타일 관리
"""

import streamlit as st

def get_table_styles(dark_mode=False):
    """테이블 스타일 CSS 반환"""
    if dark_mode:
        return """
        <style>
        /* 다크모드 데이터프레임 스타일링 - 강화된 선택자 */
        div[data-testid="stDataFrame"],
        .stDataFrame,
        .dataframe {
            background-color: #1e1e1e !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        }
        
        div[data-testid="stDataFrame"] > div,
        .stDataFrame > div,
        .stDataFrame [data-testid="stDataFrameResizeHandle"] {
            background-color: #1e1e1e !important;
            border-radius: 8px !important;
        }
        
        div[data-testid="stDataFrame"] table,
        .stDataFrame table,
        .dataframe table,
        table {
            background-color: #1e1e1e !important;
            color: #e8e8e8 !important;
            border: 1px solid #404040 !important;
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif !important;
            border-collapse: collapse !important;
        }
        
        div[data-testid="stDataFrame"] thead,
        .stDataFrame thead,
        .dataframe thead,
        table thead {
            background-color: #2d2d2d !important;
        }
        
        div[data-testid="stDataFrame"] thead th,
        .stDataFrame thead th,
        .dataframe thead th,
        table thead th,
        th {
            background-color: #2d2d2d !important;
            color: #ffffff !important;
            border-bottom: 2px solid #4a4a4a !important;
            border-right: 1px solid #404040 !important;
            font-weight: 600 !important;
            padding: 12px 8px !important;
            text-align: center !important;
            font-size: 14px !important;
        }
        
        div[data-testid="stDataFrame"] tbody td,
        .stDataFrame tbody td,
        .dataframe tbody td,
        table tbody td,
        td {
            background-color: #1e1e1e !important;
            color: #e8e8e8 !important;
            border-bottom: 1px solid #333333 !important;
            border-right: 1px solid #333333 !important;
            padding: 10px 8px !important;
            text-align: center !important;
            font-size: 13px !important;
        }
        
        div[data-testid="stDataFrame"] tbody tr:nth-child(even) td,
        .stDataFrame tbody tr:nth-child(even) td,
        .dataframe tbody tr:nth-child(even) td,
        table tbody tr:nth-child(even) td {
            background-color: #252525 !important;
        }
        
        div[data-testid="stDataFrame"] tbody tr:hover td,
        .stDataFrame tbody tr:hover td,
        .dataframe tbody tr:hover td,
        table tbody tr:hover td {
            background-color: #2a2a2a !important;
            color: #ffffff !important;
            transform: scale(1.001) !important;
            transition: all 0.2s ease !important;
        }
        
        /* Fail 텍스트 강조 */
        div[data-testid="stDataFrame"] tbody td:last-child,
        .stDataFrame tbody td:last-child,
        .dataframe tbody td:last-child,
        table tbody td:last-child {
            font-weight: 600 !important;
        }
        
        div[data-testid="stDataFrame"] tbody tr,
        .stDataFrame tbody tr,
        .dataframe tbody tr,
        table tbody tr {
            transition: all 0.2s ease !important;
        }
        
        div[data-testid="stDataFrame"] tbody tr:hover,
        .stDataFrame tbody tr:hover,
        .dataframe tbody tr:hover,
        table tbody tr:hover {
            box-shadow: 0 2px 8px rgba(255,255,255,0.1) !important;
        }
        
        /* 추가 스타일 - 더 구체적인 선택자 */
        [data-testid="stDataFrame"] .stDataFrame,
        [data-testid="stDataFrame"] iframe {
            background-color: #1e1e1e !important;
            border-radius: 8px !important;
        }
        
        /* 전체 컨테이너 배경 강제 적용 */
        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrame"] > div,
        div[data-testid="stDataFrame"] > div > div {
            background-color: #1e1e1e !important;
            border: 1px solid #404040 !important;
            border-radius: 8px !important;
        }
        
        /* 스크롤바 스타일 - 강화된 선택자 */
        div[data-testid="stDataFrame"] ::-webkit-scrollbar,
        .stDataFrame ::-webkit-scrollbar,
        .dataframe ::-webkit-scrollbar {
            width: 8px !important;
            height: 8px !important;
        }
        
        div[data-testid="stDataFrame"] ::-webkit-scrollbar-track,
        .stDataFrame ::-webkit-scrollbar-track,
        .dataframe ::-webkit-scrollbar-track {
            background: #1e1e1e !important;
            border-radius: 4px !important;
        }
        
        div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb,
        .stDataFrame ::-webkit-scrollbar-thumb,
        .dataframe ::-webkit-scrollbar-thumb {
            background: #4a4a4a !important;
            border-radius: 4px !important;
        }
        
        div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb:hover,
        .stDataFrame ::-webkit-scrollbar-thumb:hover,
        .dataframe ::-webkit-scrollbar-thumb:hover {
            background: #5a5a5a !important;
        }
        
        /* iframe 내부 스타일 강제 적용 */
        iframe {
            background-color: #1e1e1e !important;
        }
        
        /* 컨테이너 스타일 */
        .table-container-dark {
            background: linear-gradient(135deg, #1e1e1e 0%, #252525 100%);
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #404040;
            margin: 8px 0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }
        </style>
        """
    else:
        return """
        <style>
        /* 라이트모드 데이터프레임 스타일링 */
        .stDataFrame {
            background-color: #ffffff !important;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .stDataFrame table {
            background-color: #ffffff !important;
            color: #262730 !important;
            border: 1px solid #e0e0e0 !important;
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .stDataFrame thead th {
            background-color: #f8f9fa !important;
            color: #262730 !important;
            border-bottom: 2px solid #dee2e6 !important;
            border-right: 1px solid #e0e0e0 !important;
            font-weight: 600;
            padding: 12px 8px;
            text-align: center;
            font-size: 14px;
        }
        
        .stDataFrame tbody td {
            background-color: #ffffff !important;
            color: #262730 !important;
            border-bottom: 1px solid #e0e0e0 !important;
            border-right: 1px solid #e0e0e0 !important;
            padding: 10px 8px;
            text-align: center;
            font-size: 13px;
        }
        
        .stDataFrame tbody tr:nth-child(even) td {
            background-color: #f8f9fa !important;
        }
        
        .stDataFrame tbody tr:hover td {
            background-color: #e7f3ff !important;
            transform: scale(1.001);
            transition: all 0.2s ease;
        }
        
        .stDataFrame tbody tr {
            transition: all 0.2s ease;
        }
        
        .stDataFrame tbody tr:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        /* 컨테이너 스타일 */
        .table-container-light {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            margin: 8px 0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }
        </style>
        """


def get_pagination_styles(dark_mode=False):
    """페이지네이션 스타일 CSS 반환"""
    if dark_mode:
        return """
        <style>
        /* 다크모드 페이지네이션 스타일 */
        .pagination-info-dark {
            color: #e8e8e8;
            font-weight: 600;
            padding: 8px 0;
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
            border-radius: 8px;
            text-align: center;
            border: 1px solid #404040;
            margin-bottom: 12px;
        }
        
        .pagination-container-dark {
            background-color: #1e1e1e;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #404040;
            margin: 8px 0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }
        
        /* 버튼 스타일 */
        .stButton > button {
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%) !important;
            border: 1px solid #505050 !important;
            color: #fafafa !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
            font-weight: 500 !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #3d3d3d 0%, #4d4d4d 100%) !important;
            border-color: #606060 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0px) !important;
        }
        
        .stButton > button:disabled {
            background: #1a1a1a !important;
            border-color: #333333 !important;
            color: #666666 !important;
            cursor: not-allowed !important;
            transform: none !important;
        }
        
        /* 입력 필드 스타일 */
        .stNumberInput > div > div > input {
            background-color: #2d2d2d !important;
            border: 1px solid #404040 !important;
            color: #fafafa !important;
            border-radius: 8px !important;
            text-align: center !important;
        }
        
        .stNumberInput > div > div > input:focus {
            border-color: #4a9eff !important;
            box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2) !important;
        }
        </style>
        """
    else:
        return """
        <style>
        /* 라이트모드 페이지네이션 스타일 */
        .pagination-info-light {
            color: #262730;
            font-weight: 600;
            padding: 8px 0;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 8px;
            text-align: center;
            border: 1px solid #dee2e6;
            margin-bottom: 12px;
        }
        
        .pagination-container-light {
            background-color: #ffffff;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            margin: 8px 0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }
        
        /* 버튼 스타일 */
        .stButton > button {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
            border: 1px solid #dee2e6 !important;
            color: #262730 !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
            font-weight: 500 !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #e7f3ff 0%, #cce7ff 100%) !important;
            border-color: #4a9eff !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0px) !important;
        }
        
        .stButton > button:disabled {
            background: #f8f9fa !important;
            border-color: #e9ecef !important;
            color: #adb5bd !important;
            cursor: not-allowed !important;
            transform: none !important;
        }
        </style>
        """


def get_alert_styles(dark_mode=False):
    """알림 메시지 스타일 CSS 반환"""
    if dark_mode:
        return """
        <style>
        .alert-warning-dark {
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
            color: #ffa726;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #ffa726;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        
        .alert-error-dark {
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
            color: #f44336;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #f44336;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        
        .alert-info-dark {
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
            color: #4a9eff;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #4a9eff;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        
        .alert-success-dark {
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
            color: #4caf50;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #4caf50;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        </style>
        """
    else:
        return """
        <style>
        .alert-warning-light {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            color: #856404;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .alert-error-light {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            color: #721c24;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #dc3545;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .alert-info-light {
            background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
            color: #0c5460;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #17a2b8;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .alert-success-light {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            color: #155724;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #28a745;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        </style>
        """


def get_global_dark_mode_styles():
    """전역 다크모드 스타일 CSS 반환"""
    return """
    <style>
    /* 전역 다크모드 스타일 */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #1a1d29 100%);
        color: #fafafa;
    }
    
    /* 사이드바 다크모드 */
    .css-1d391kg {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
    }
    
    /* 메트릭 카드 다크모드 */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%) !important;
        border: 1px solid #404040 !important;
        color: #fafafa !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    
    /* 구분선 다크모드 */
    hr {
        border-color: #404040 !important;
        margin: 16px 0 !important;
    }
    
    /* 텍스트 입력 필드 다크모드 */
    .stTextInput > div > div > input {
        background-color: #2d2d2d !important;
        border: 1px solid #404040 !important;
        color: #fafafa !important;
        border-radius: 8px !important;
    }
    
    /* 선택 박스 다크모드 */
    .stSelectbox > div > div > select {
        background-color: #2d2d2d !important;
        border: 1px solid #404040 !important;
        color: #fafafa !important;
        border-radius: 8px !important;
    }
    
    /* 탭 다크모드 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e1e1e !important;
        border-radius: 8px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #2d2d2d !important;
        color: #fafafa !important;
        border-radius: 6px !important;
        margin: 2px !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4a9eff !important;
        color: #ffffff !important;
    }
    
    /* 확장 가능한 요소 다크모드 */
    .streamlit-expander {
        background-color: #1e1e1e !important;
        border: 1px solid #404040 !important;
        border-radius: 8px !important;
    }
    
    /* 제목 스타일 */
    h1, h2, h3, h4, h5, h6 {
        color: #fafafa !important;
    }
    
    /* 코드 블록 다크모드 */
    .stCode {
        background-color: #1e1e1e !important;
        border: 1px solid #404040 !important;
        border-radius: 8px !important;
    }
    </style>
    """


def apply_table_styles(dark_mode=False):
    """테이블 스타일 적용"""
    st.markdown(get_table_styles(dark_mode), unsafe_allow_html=True)


def apply_pagination_styles(dark_mode=False):
    """페이지네이션 스타일 적용"""
    st.markdown(get_pagination_styles(dark_mode), unsafe_allow_html=True)


def apply_alert_styles(dark_mode=False):
    """알림 메시지 스타일 적용"""
    st.markdown(get_alert_styles(dark_mode), unsafe_allow_html=True)


def apply_all_styles(dark_mode=False):
    """모든 스타일 일괄 적용"""
    if dark_mode:
        st.markdown(get_global_dark_mode_styles(), unsafe_allow_html=True)
    
    apply_table_styles(dark_mode)
    apply_pagination_styles(dark_mode)
    apply_alert_styles(dark_mode)


def create_styled_container(content, dark_mode=False, container_type="table"):
    """스타일이 적용된 컨테이너 생성"""
    if dark_mode:
        if container_type == "table":
            return f'<div class="table-container-dark">{content}</div>'
        elif container_type == "pagination":
            return f'<div class="pagination-container-dark">{content}</div>'
    else:
        if container_type == "table":
            return f'<div class="table-container-light">{content}</div>'
        elif container_type == "pagination":
            return f'<div class="pagination-container-light">{content}</div>'


def create_styled_alert(message, alert_type="info", dark_mode=False):
    """스타일이 적용된 알림 메시지 생성"""
    # 알림 접두사 추가
    prefix_map = {
        "warning": "[경고]",
        "error": "[오류]", 
        "info": "[정보]",
        "success": "[성공]"
    }
    
    prefix = prefix_map.get(alert_type, "[알림]")
    
    if dark_mode:
        class_name = f"alert-{alert_type}-dark"
    else:
        class_name = f"alert-{alert_type}-light"
    
    return f'<div class="{class_name}">{prefix} {message}</div>'


def create_pagination_info(current_page, total_pages, total_count, dark_mode=False):
    """페이지네이션 정보 표시 HTML 생성"""
    if dark_mode:
        class_name = "pagination-info-dark"
    else:
        class_name = "pagination-info-light"
    
    return f'''
    <div class="{class_name}">
        페이지 {current_page} / {total_pages} (총 {total_count:,}개)
    </div>
    '''

# styles/table_styles.py에 추가할 함수들

def apply_dataframe_dark_mode_fix():
    """데이터프레임 다크모드 강제 적용"""
    st.markdown("""
    <style>
    /* 데이터프레임 다크모드 강제 적용 */
    .stApp [data-testid="stDataFrame"] {
        background: #1e1e1e !important;
        border: 1px solid #404040 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    
    .stApp [data-testid="stDataFrame"] > div {
        background: #1e1e1e !important;
        border-radius: 8px !important;
    }
    
    .stApp [data-testid="stDataFrame"] iframe {
        background: #1e1e1e !important;
        border-radius: 6px !important;
        border: none !important;
    }
    
    /* 강제 색상 적용 */
    .stApp table,
    .stApp thead,
    .stApp tbody,
    .stApp tr,
    .stApp th,
    .stApp td {
        background-color: #1e1e1e !important;
        color: #e8e8e8 !important;
        border-color: #404040 !important;
    }
    
    .stApp th {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #4a4a4a !important;
    }
    
    .stApp tr:nth-child(even) td {
        background-color: #252525 !important;
    }
    
    .stApp tr:hover td {
        background-color: #2a2a2a !important;
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)


def create_dark_dataframe(df, height=400):
    """다크모드에 최적화된 데이터프레임 생성"""
    dark_mode = st.session_state.get('dark_mode', False)
    
    if dark_mode:
        # 다크모드용 강화된 스타일 적용
        apply_dataframe_dark_mode_fix()
        
        # 컨테이너로 감싸서 배경색 강제 적용
        st.markdown("""
        <div style="
            background-color: #1e1e1e;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #404040;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            margin: 8px 0;
        ">
        """, unsafe_allow_html=True)
        
        # 데이터프레임 표시
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=height
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 스타일 재적용 (강제)
        st.markdown("""
        <script>
        setTimeout(function() {
            // iframe 내부 스타일 강제 적용
            const dataframes = document.querySelectorAll('[data-testid="stDataFrame"]');
            dataframes.forEach(function(df) {
                df.style.backgroundColor = '#1e1e1e';
                df.style.border = '1px solid #404040';
                df.style.borderRadius = '8px';
                
                const iframe = df.querySelector('iframe');
                if (iframe) {
                    iframe.style.backgroundColor = '#1e1e1e';
                    iframe.style.borderRadius = '6px';
                }
            });
        }, 100);
        </script>
        """, unsafe_allow_html=True)
        
    else:
        # 라이트모드는 기본 스타일 사용
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=height
        )


def styled_dataframe(df, dark_mode=False, height=400, title=None):
    """완전한 스타일링이 적용된 데이터프레임"""
    
    if title:
        if dark_mode:
            st.markdown(f"""
            <div style="
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 8px;
                padding: 8px 12px;
                background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
                border-radius: 8px 8px 0 0;
                border: 1px solid #404040;
                border-bottom: none;
            ">
                {title}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"#### {title}")
    
    if dark_mode:
        # 전체 컨테이너
        container_style = """
        background: linear-gradient(135deg, #1e1e1e 0%, #252525 100%);
        border: 1px solid #404040;
        border-radius: 8px;
        padding: 0;
        margin: 8px 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        overflow: hidden;
        """
        
        if title:
            container_style += "border-top: none; border-radius: 0 0 8px 8px;"
        
        st.markdown(f'<div style="{container_style}">', unsafe_allow_html=True)
        
        # 내부 패딩 컨테이너
        st.markdown("""
        <div style="
            padding: 16px;
            background-color: #1e1e1e;
        ">
        """, unsafe_allow_html=True)
        
        # 강화된 스타일 적용
        apply_dataframe_dark_mode_fix()
        
        # 데이터프레임
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=height
        )
        
        # 컨테이너 닫기
        st.markdown("</div></div>", unsafe_allow_html=True)
        
    else:
        # 라이트모드 컨테이너
        if title:
            container_style = "border-top: none; border-radius: 0 0 8px 8px;"
        else:
            container_style = "border-radius: 8px;"
            
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border: 1px solid #e0e0e0;
            {container_style}
            padding: 16px;
            margin: 8px 0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        ">
        """, unsafe_allow_html=True)
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=height
        )
        
        st.markdown("</div>", unsafe_allow_html=True)