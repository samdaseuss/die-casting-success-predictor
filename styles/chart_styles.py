# styles/chart_styles.py
import streamlit as st
from .style_manager import get_theme_colors

def get_echarts_colors(dark_mode=False):
    """ECharts용 색상 팔레트 반환"""
    if dark_mode:
        return {
            'grid_color': "#48484a",
            'text_color': "#ffffff",
            'axis_color': "#98989d",
            'bg_color': "transparent",
            'normal_color': "#32d74b",
            'warning_color': "#ff9f0a",
            'critical_color': "#ff453a",
            'control_line_color': "#0a84ff",
            'legend_bg': "#1c1c1e",
            'legend_border': "#48484a"
        }
    else:
        return {
            'grid_color': "#f2f2f7",
            'text_color': "#1d1d1f",
            'axis_color': "#6e6e73",
            'bg_color': "transparent",
            'normal_color': "#34c759",
            'warning_color': "#ff9500",
            'critical_color': "#ff3b30",
            'control_line_color': "#007aff",
            'legend_bg': "#ffffff",
            'legend_border': "#e5e5e7"
        }

def create_control_chart_options(data, ucl, lcl, usl, lsl, mean_rate, dark_mode=False):
    """관리도 차트 옵션 생성"""
    colors = get_echarts_colors(dark_mode)
    time_labels = [t.strftime("%H:%M") for t in data['time_points']]
    
    return {
        "backgroundColor": colors['bg_color'],
        "animation": True,
        "title": {
            "text": "통계적 공정관리 관리도 (SPC Control Chart)",
            "textStyle": {
                "color": colors['text_color'],
                "fontSize": 16,
                "fontWeight": "600"
            },
            "top": "2%",
            "left": "center"
        },
        "grid": {
            "left": "10%",
            "right": "8%",
            "top": "20%",
            "bottom": "25%",
            "containLabel": True
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.95)" if dark_mode else "rgba(255, 255, 255, 0.95)",
            "borderColor": colors['control_line_color'],
            "textStyle": {"color": colors['text_color']},
            "formatter": """function(params) {
                const time = params[0].name;
                const rate = params[0].value !== undefined ? params[0].value.toFixed(2) : '';
                return '시간: ' + time + '<br/>불량률: ' + rate + '%';
            }"""
        },
        "legend": {
            "show": True,
            "data": [
                {"name": "관리 상한선 (UCL)", "icon": "line", "textStyle": {"color": colors['text_color'], "fontSize": 12}},
                {"name": "관리 하한선 (LCL)", "icon": "line", "textStyle": {"color": colors['text_color'], "fontSize": 12}},
                {"name": "중심선 (CL)", "icon": "line", "textStyle": {"color": colors['text_color'], "fontSize": 12}},
                {"name": "경고선 (±2σ)", "icon": "line", "textStyle": {"color": colors['text_color'], "fontSize": 12}},
                {"name": "불량률 데이터", "icon": "circle", "textStyle": {"color": colors['text_color'], "fontSize": 12}}
            ],
            "bottom": "5%",
            "left": "center",
            "orient": "horizontal",
            "itemGap": 20,
            "backgroundColor": colors['legend_bg'],
            "borderColor": colors['legend_border'],
            "borderWidth": 1,
            "borderRadius": 5,
            "padding": [10, 15],
            "textStyle": {"color": colors['text_color'], "fontSize": 11}
        },
        "xAxis": {
            "type": "category",
            "data": time_labels,
            "name": "시간",
            "nameLocation": "middle",
            "nameGap": 25,
            "nameTextStyle": {"color": colors['text_color'], "fontSize": 12, "fontWeight": "600"},
            "axisLine": {"lineStyle": {"color": colors['axis_color'], "width": 1}},
            "axisTick": {"lineStyle": {"color": colors['axis_color']}},
            "axisLabel": {"color": colors['axis_color'], "fontSize": 11, "interval": 4},
            "splitLine": {"show": True, "lineStyle": {"color": colors['grid_color'], "type": "dashed"}}
        },
        "yAxis": {
            "type": "value",
            "name": "불량률 (%)",
            "nameLocation": "middle",
            "nameGap": 50,
            "nameTextStyle": {"color": colors['text_color'], "fontSize": 13, "fontWeight": "600"},
            "axisLine": {"lineStyle": {"color": colors['axis_color'], "width": 1}},
            "axisTick": {"lineStyle": {"color": colors['axis_color']}},
            "axisLabel": {"color": colors['axis_color'], "fontSize": 11, "formatter": "{value}%"},
            "splitLine": {"show": True, "lineStyle": {"color": colors['grid_color'], "type": "dashed"}}
        },
        "series": [
            {
                "name": "관리 상한선 (UCL)",
                "type": "line",
                "data": [ucl] * len(time_labels),
                "lineStyle": {"color": colors['critical_color'], "width": 2, "type": "solid"},
                "symbol": "none",
                "emphasis": {"disabled": True},
                "tooltip": {"formatter": f"관리 상한선 (UCL): {ucl:.2f}%<br/>공정의 안정상태 최대 허용 우연원인 변동"}
            },
            {
                "name": "경고선 (±2σ)",
                "type": "line",
                "data": [usl] * len(time_labels),
                "lineStyle": {"color": colors['warning_color'], "width": 1, "type": "dashed"},
                "symbol": "none",
                "emphasis": {"disabled": True}
            },
            {
                "name": "중심선 (CL)",
                "type": "line",
                "data": [mean_rate] * len(time_labels),
                "lineStyle": {"color": colors['control_line_color'], "width": 2, "type": "solid"},
                "symbol": "none",
                "emphasis": {"disabled": True},
                "tooltip": {"formatter": f"중심선 (CL): {mean_rate:.2f}%<br/>안정상태에 있는 공정의 평균 품질 특성"}
            },
            {
                "name": "경고선 (±2σ)",
                "type": "line",
                "data": [lsl] * len(time_labels),
                "lineStyle": {"color": colors['warning_color'], "width": 1, "type": "dashed"},
                "symbol": "none",
                "emphasis": {"disabled": True}
            },
            {
                "name": "관리 하한선 (LCL)",
                "type": "line",
                "data": [lcl] * len(time_labels),
                "lineStyle": {"color": colors['critical_color'], "width": 2, "type": "solid"},
                "symbol": "none",
                "emphasis": {"disabled": True},
                "tooltip": {"formatter": f"관리 하한선 (LCL): {lcl:.2f}%<br/>공정의 안정상태 최소 허용 우연원인 변동"}
            },
            {
                "name": "불량률 데이터",
                "type": "line",
                "data": data['defect_rates'],
                "lineStyle": {
                    "color": colors['control_line_color'],
                    "width": 3,
                    "shadowColor": f"{colors['control_line_color']}40",
                    "shadowBlur": 8
                },
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {
                    "color": colors['control_line_color'],
                    "shadowColor": f"{colors['control_line_color']}60",
                    "shadowBlur": 6
                },
                "emphasis": {
                    "scale": 1.5,
                    "itemStyle": {
                        "shadowBlur": 20,
                        "shadowColor": f"{colors['control_line_color']}80"
                    }
                },
                "smooth": 0.3,
                "animationDuration": 2000,
                "animationEasing": "cubicOut",
                "markPoint": {
                    "data": [
                        {
                            "coord": [i, rate],
                            "value": rate,
                            "itemStyle": {"color": colors['critical_color']},
                            "symbol": "pin",
                            "symbolSize": 50
                        } for i, rate in enumerate(data['defect_rates']) 
                        if rate > ucl or rate < lcl
                    ],
                    "label": {
                        "show": True,
                        "formatter": "이탈",
                        "color": "#ffffff",
                        "fontSize": 10,
                        "fontWeight": "600"
                    }
                }
            }
        ]
    }

def create_gauge_chart_options(title, value, min_val=0, max_val=100, unit="", target_range=None, dark_mode=False):
    """게이지 차트 옵션 생성"""
    colors = get_theme_colors(dark_mode)
    
    if target_range:
        if target_range[0] <= value <= target_range[1]:
            color = colors['success_color']
        else:
            color = colors['error_color']
    else:
        progress = value / max_val
        if progress <= 0.6:
            color = colors['success_color']
        elif progress <= 0.8:
            color = colors['warning_color']
        else:
            color = colors['error_color']
    
    return {
        "backgroundColor": "transparent",
        "series": [{
            "type": "gauge",
            "startAngle": 200,
            "endAngle": -20,
            "min": min_val,
            "max": max_val,
            "splitNumber": 4,
            "radius": "75%",
            "center": ["50%", "55%"],
            "axisLine": {
                "lineStyle": {
                    "width": 20,
                    "color": [[value/max_val, color], [1, "#e5e5e7"]]
                }
            },
            "pointer": {
                "show": True,
                "length": "60%",
                "width": 6,
                "itemStyle": {"color": color}
            },
            "axisTick": {"show": False},
            "splitLine": {
                "show": True,
                "length": 12,
                "lineStyle": {"color": "#e5e5e7", "width": 2}
            },
            "axisLabel": {
                "show": True,
                "distance": 25,
                "fontSize": 12,
                "color": colors['text_primary'],
                "formatter": "{value}"
            },
            "title": {
                "show": True,
                "offsetCenter": [0, "80%"],
                "fontSize": 14,
                "fontWeight": "600",
                "color": colors['text_primary']
            },
            "detail": {
                "fontSize": 24,
                "fontWeight": "700",
                "color": color,
                "offsetCenter": [0, "25%"],
                "formatter": f"{{value}}{unit}"
            },
            "data": [{"value": value, "name": title}]
        }]
    }

def create_status_html(collection_status, buffer_size, collection_indicator, next_update_str):
    """상태 표시 HTML 생성"""
    return f'''
    <div class="realtime-status">
        <div class="status-item">
            <span>수집상태:</span>
            <span class="status-value">{collection_status}</span>
        </div>
        <div class="status-item">
            <span>버퍼:</span>
            <span class="status-value">{buffer_size}</span>
        </div>
        <div class="status-item">
            <span>데이터:</span>
            <span class="status-value">{collection_indicator}</span>
        </div>
        <div class="status-item">
            <span>다음 업데이트:</span>
            <span class="status-value">{next_update_str}</span>
        </div>
    </div>
    '''

def create_mold_card_html(mold_code, info, is_active, dark_mode=False):
    """몰드 상태 카드 HTML 생성"""
    colors = get_theme_colors(dark_mode)
    
    card_class = "active" if is_active else ""
    badge_class = "active" if is_active else ""
    status_text = "ACTIVE" if is_active else "STANDBY"
    
    return f'''
    <div class="mold-status-card {card_class}">
        <div class="mold-header">
            <div class="mold-title">
                MOLD {mold_code}
            </div>
            <div class="mold-badge {badge_class}">
                {status_text}
            </div>
        </div>
        <div style="font-size: 14px; font-weight: 600; color: {colors['accent_color']};">
            {info["name"]}
        </div>
        <div style="font-size: 12px; color: {colors['text_secondary']}; margin-top: 4px;">
            {info["type"]}
        </div>
    </div>
    '''

def create_process_indicator_html(stages, current_stage, progress, max_progress, dark_mode=False):
    colors = get_theme_colors(dark_mode)
    progress_html = '<div class="process-indicator">'
    
    # 1) stages 리스트에서 현재 스테이지 인덱스 찾기
    stage_ids = [s["id"] for s in stages]
    try:
        current_idx = stage_ids.index(current_stage)
    except ValueError:
        # current_stage 값이 stages에 없을 때
        current_idx = -1

    for idx, step in enumerate(stages):
        if idx < current_idx:
            status_class = "completed"
            progress_percent = 100
        elif idx == current_idx:
            status_class = "active"
            progress_percent = (progress / max_progress) * 100
        else:
            status_class = "inactive"
            progress_percent = 0
        
        progress_html += f'''
        <div class="process-step {status_class}">
            <div class="step-icon {status_class}">
                {step["icon"]}
            </div>
            <div class="step-label {status_class}">
                {step["label"]}
            </div>
            <div style="font-size: 0.7rem; color: {colors['text_secondary']}; margin-top: 2px;">
                {step["desc"]}
            </div>
            <div style="font-size: 0.65rem; color: {colors['text_secondary']}; margin-top: 2px;">
                ({step["duration"]})
            </div>
            <div style="font-size: 0.75rem; color: {colors['accent_color']}; margin-top: 4px; font-weight: 600;">
                {progress_percent:.0f}%
            </div>
        </div>'''
    
    progress_html += '</div>'
    return progress_html


def create_timer_html(remaining_time, dark_mode, cycle_info=None):
    """
    타이머 HTML 생성 (사이클 정보 포함)
    
    Args:
        remaining_time (float): 남은 시간 (초)
        dark_mode (bool): 다크 모드 여부
        cycle_info (str): 사이클 정보 텍스트 (선택사항)
    """
    
    # 기본 색상 설정
    if dark_mode:
        bg_color = "rgba(45, 45, 45, 0.95)"
        text_color = "#ffffff"
        border_color = "rgba(255, 255, 255, 0.1)"
        timer_color = "#9df892"
        cycle_text_color = "#a0a0a0"
    else:
        bg_color = "rgba(255, 255, 255, 0.95)"
        text_color = "#333333"
        border_color = "rgba(0, 0, 0, 0.1)"
        timer_color = "#9df892"
        cycle_text_color = "#666666"
    
    # 시간 포맷팅
    minutes = int(remaining_time // 60)
    seconds = int(remaining_time % 60)
    time_display = f"{minutes:02d}:{seconds:02d}"
    
    # 사이클 정보 HTML
    cycle_info_html = ""
    if cycle_info:
        cycle_info_html = f"""
        <div style="font-size: 12px; color: {cycle_text_color}; margin-top: 8px; text-align: center; font-weight: 500;">{cycle_info}</div>
        """
    
    timer_html = f"""
    <div style="
        background: {bg_color};
        backdrop-filter: blur(10px);
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);">
        <div style="
            font-size: 14px;
            color: {text_color};
            margin-bottom: 8px;
            font-weight: 600;
        ">다음 사이클까지</div>
        <div style="font-size: 28px;font-weight: bold;color: {timer_color};font-family: 'Courier New', monospace;letter-spacing: 2px;">{time_display}</div>{cycle_info_html}<div style="
            width: 100%;
            height: 4px;
            background: rgba(128, 128, 128, 0.2);
            border-radius: 2px;
            margin-top: 12px;
            overflow: hidden;">
            <div style="
                width: {((30 - remaining_time) / 30) * 100}%;
                height: 100%;
                background: linear-gradient(90deg, {timer_color}, #00a8cc);
                border-radius: 2px;
                transition: width 0.5s ease;
            "></div></div></div>
    """
    
    return timer_html