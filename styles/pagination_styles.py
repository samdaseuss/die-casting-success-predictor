# styles/pagination_styles.py
import streamlit as st
from .style_manager import get_theme_colors

def create_pagination_html(current_page, total_pages, total_count, start_idx, end_idx, dark_mode=False):
    """완전히 작동하는 JavaScript 페이지네이션 컴포넌트 HTML 생성"""
    
    colors = get_theme_colors(dark_mode)
    
    if dark_mode:
        button_bg = "#2c2c2e"
        button_hover = "#3c3c3e"
        active_bg = "#0a84ff"
        page_info_bg = "#1c1c1e"
    else:
        button_bg = "#f8f9fa"
        button_hover = "#e9ecef"
        active_bg = "#007aff"
        page_info_bg = "#f8f9fa"
    
    # 페이지 범위 계산
    start_page = max(1, current_page - 2)
    end_page = min(total_pages, current_page + 2)
    
    if end_page - start_page < 4:
        if start_page == 1:
            end_page = min(total_pages, start_page + 4)
        else:
            start_page = max(1, end_page - 4)
    
    # CSS 스타일
    css_styles = f"""
    <style>
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}
    
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
        background: transparent;
        padding: 20px;
    }}
    
    .data-summary {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding: 16px 20px;
        background: {colors['card_bg']};
        border-radius: 16px;
        border: 1px solid {colors['border_color']};
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }}
    
    .data-count {{
        font-size: 16px;
        font-weight: 700;
        color: {colors['text_primary']};
    }}
    
    .page-info {{
        font-size: 14px;
        color: {colors['text_secondary']};
        font-weight: 500;
    }}
    
    .modern-pagination-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
        padding: 24px;
        background: {colors['card_bg']};
        border-radius: 16px;
        border: 1px solid {colors['border_color']};
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }}
    
    .pagination-info {{
        background: {page_info_bg};
        padding: 12px 20px;
        border-radius: 12px;
        border: 1px solid {colors['border_color']};
        color: {colors['text_secondary']};
        font-size: 14px;
        font-weight: 500;
        text-align: center;
    }}
    
    .pagination-controls {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: center;
    }}
    
    .pagination-button {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        border: 2px solid {colors['border_color']};
        background: {button_bg};
        color: {colors['text_primary']};
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-decoration: none;
        user-select: none;
        position: relative;
        overflow: hidden;
    }}
    
    .pagination-button::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: {colors['accent_color']};
        transform: scale(0);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border-radius: 50%;
        z-index: 1;
    }}
    
    .pagination-button span {{
        position: relative;
        z-index: 2;
        transition: color 0.3s ease;
    }}
    
    .pagination-button:hover:not(.disabled):not(.active) {{
        border-color: {colors['accent_color']};
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,122,255,0.25);
    }}
    
    .pagination-button:hover:not(.disabled):not(.active)::before {{
        transform: scale(0.2);
    }}
    
    .pagination-button.active {{
        background: {active_bg};
        color: white;
        border-color: {active_bg};
        box-shadow: 0 8px 25px {active_bg}50;
        transform: scale(1.1);
        animation: pulse-active 2s infinite;
    }}
    
    .pagination-button.active::before {{
        transform: scale(1);
        background: {active_bg};
    }}
    
    .pagination-button.active span {{
        color: white;
    }}
    
    .pagination-button.disabled {{
        opacity: 0.3;
        cursor: not-allowed;
        background: {button_bg};
    }}
    
    .pagination-button.disabled:hover {{
        transform: none;
        box-shadow: none;
    }}
    
    .pagination-ellipsis {{
        color: {colors['text_secondary']};
        font-weight: 600;
        padding: 0 8px;
        font-size: 16px;
    }}
    
    .pagination-nav {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        border-radius: 12px;
        border: 2px solid {colors['border_color']};
        background: {button_bg};
        color: {colors['text_primary']};
        font-size: 18px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}
    
    .pagination-nav::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: {colors['accent_color']};
        transform: translateX(-100%);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 1;
    }}
    
    .pagination-nav span {{
        position: relative;
        z-index: 2;
        transition: color 0.3s ease;
    }}
    
    .pagination-nav:hover:not(.disabled) {{
        border-color: {colors['accent_color']};
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,122,255,0.3);
    }}
    
    .pagination-nav:hover:not(.disabled)::before {{
        transform: translateX(0);
    }}
    
    .pagination-nav:hover:not(.disabled) span {{
        color: white;
    }}
    
    .pagination-nav.disabled {{
        opacity: 0.3;
        cursor: not-allowed;
    }}
    
    .pagination-nav.disabled:hover {{
        transform: none;
        box-shadow: none;
    }}
    
    @keyframes pulse-active {{
        0%, 100% {{ 
            box-shadow: 0 8px 25px {active_bg}50;
        }}
        50% {{ 
            box-shadow: 0 12px 35px {active_bg}70;
        }}
    }}
    </style>
    """
    
    # HTML 구조
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        {css_styles}
    </head>
    <body>
        <div class="data-summary">
            <div class="data-count">불량 데이터 총 {total_count:,}개</div>
            <div class="page-info">{start_idx}-{end_idx}번째 표시중</div>
        </div>
        
        <div class="modern-pagination-container">
            <div class="pagination-info">{current_page} / {total_pages} 페이지</div>
            <div class="pagination-controls">
    """
    
    # 맨 처음/이전 버튼
    if current_page > 1:
        html_content += f'''
                <div class="pagination-nav" onclick="goToPage(1)">
                    <span>⟨⟨</span>
                </div>
                <div class="pagination-nav" onclick="goToPage({current_page - 1})">
                    <span>⟨</span>
                </div>
        '''
    else:
        html_content += '''
                <div class="pagination-nav disabled">
                    <span>⟨⟨</span>
                </div>
                <div class="pagination-nav disabled">
                    <span>⟨</span>
                </div>
        '''
    
    # 첫 페이지 (범위에 포함되지 않은 경우)
    if start_page > 1:
        active_class = "active" if current_page == 1 else ""
        html_content += f'''
                <div class="pagination-button {active_class}" onclick="goToPage(1)">
                    <span>1</span>
                </div>
        '''
        if start_page > 2:
            html_content += '<span class="pagination-ellipsis">...</span>'
    
    # 페이지 번호들
    for page_num in range(start_page, end_page + 1):
        active_class = "active" if page_num == current_page else ""
        html_content += f'''
                <div class="pagination-button {active_class}" onclick="goToPage({page_num})">
                    <span>{page_num}</span>
                </div>
        '''
    
    # 마지막 페이지 (범위에 포함되지 않은 경우)
    if end_page < total_pages:
        if end_page < total_pages - 1:
            html_content += '<span class="pagination-ellipsis">...</span>'
        active_class = "active" if current_page == total_pages else ""
        html_content += f'''
                <div class="pagination-button {active_class}" onclick="goToPage({total_pages})">
                    <span>{total_pages}</span>
                </div>
        '''
    
    # 다음/맨 마지막 버튼
    if current_page < total_pages:
        html_content += f'''
                <div class="pagination-nav" onclick="goToPage({current_page + 1})">
                    <span>⟩</span>
                </div>
                <div class="pagination-nav" onclick="goToPage({total_pages})">
                    <span>⟩⟩</span>
                </div>
        '''
    else:
        html_content += '''
                <div class="pagination-nav disabled">
                    <span>⟩</span>
                </div>
                <div class="pagination-nav disabled">
                    <span>⟩⟩</span>
                </div>
        '''
    
    # JavaScript 추가
    html_content += f'''
            </div>
        </div>
        
        <script>
        function goToPage(pageNum) {{
            const totalPages = {total_pages};
            const currentPage = {current_page};
            
            if (pageNum >= 1 && pageNum <= totalPages && pageNum !== currentPage) {{
                try {{
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: {{ page: pageNum, action: 'goto', timestamp: Date.now() }}
                    }}, '*');
                }} catch(e) {{
                    console.log('PostMessage failed');
                }}
                
                setTimeout(() => {{
                    window.location.reload();
                }}, 100);
            }}
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('Pagination component loaded successfully');
        }});
        
        document.addEventListener('keydown', function(event) {{
            const currentPage = {current_page};
            const totalPages = {total_pages};
            
            if (event.key === 'ArrowLeft' && currentPage > 1) {{
                event.preventDefault();
                goToPage(currentPage - 1);
            }} else if (event.key === 'ArrowRight' && currentPage < totalPages) {{
                event.preventDefault();
                goToPage(currentPage + 1);
            }} else if (event.key === 'Home') {{
                event.preventDefault();
                goToPage(1);
            }} else if (event.key === 'End') {{
                event.preventDefault();
                goToPage(totalPages);
            }}
        }});
        
        let touchStartX = 0;
        let touchEndX = 0;
        
        document.addEventListener('touchstart', function(event) {{
            touchStartX = event.changedTouches[0].screenX;
        }});
        
        document.addEventListener('touchend', function(event) {{
            touchEndX = event.changedTouches[0].screenX;
            handleSwipeGesture();
        }});
        
        function handleSwipeGesture() {{
            const swipeThreshold = 100;
            const currentPage = {current_page};
            const totalPages = {total_pages};
            
            if (touchEndX < touchStartX - swipeThreshold && currentPage < totalPages) {{
                goToPage(currentPage + 1);
            }} else if (touchEndX > touchStartX + swipeThreshold && currentPage > 1) {{
                goToPage(currentPage - 1);
            }}
        }}
        
        window.paginationGoToPage = goToPage;
        </script>
    </body>
    </html>
    '''
    
    return html_content