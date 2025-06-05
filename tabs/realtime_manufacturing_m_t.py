# tabs/realtime_manufacturing_m_t.py
import streamlit as st
import time
from pathlib import Path
import sys
from utils.data_utils import save_data_to_file, save_snapshot_batch, read_data_from_test_py
from streamlit_echarts import st_echarts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import json

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

snapshots_dir = project_root / "snapshots"
TEST_PY_FILE = project_root / "data/test.py"

def get_synchronized_start_time():
    if 'system_start_time' not in st.session_state:
        current_time = time.time()
        aligned_time = (int(current_time) // 30) * 30
        st.session_state.system_start_time = aligned_time
    return st.session_state.system_start_time

class RealTimeDataManager:    
    @staticmethod
    def initialize_session_state():
        defaults = {
            'ng_history': [],
            'collected_data': [],
            'control_chart_data': RealTimeDataManager._generate_initial_chart_data(),
            'realtime_buffer': deque(maxlen=100),
            'last_chart_update': time.time(),
            'chart_update_interval': 180,
            'data_collection_started': False,
            'current_status': {},
            'last_collected_id': None
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def _generate_initial_chart_data():
        np.random.seed(42)
        base_rate = 5.0
        time_points = [datetime.now() - timedelta(hours=29-i) for i in range(30)]
        
        defect_rates = []
        for i in range(30):
            trend = 0.1 * i
            noise = np.random.normal(0, 1.5)
            special_cause = 3.0 if i in [15, 20, 25] else 0
            rate = max(0, base_rate + trend + noise + special_cause)
            defect_rates.append(rate)
        
        return {
            'time_points': time_points,
            'defect_rates': defect_rates
        }
    
    @staticmethod
    def collect_realtime_data():
        current_data = st.session_state.get("current_status", {})
        
        if current_data and 'passorfail' in current_data:
            current_timestamp = datetime.now().isoformat()
            data_hash = hash(str(current_data))
            data_id = f"{current_timestamp}_{data_hash}"
            
            if st.session_state.get('last_collected_id') == data_id:
                return False
            
            data_point = {
                'timestamp': datetime.now(),
                'mold_code': current_data.get('mold_code', 0),
                'molten_temp': current_data.get('molten_temp', 0),
                'cast_pressure': current_data.get('cast_pressure', 0),
                'passorfail': current_data.get('passorfail', 'Pass'),
                'defect': 1 if current_data.get('passorfail') == 'Fail' else 0,
                'data_id': data_id,
                'original_timestamp': current_data.get('timestamp', '')
            }
            
            st.session_state.realtime_buffer.append(data_point)
            st.session_state.last_collected_id = data_id
            
            return True
        return False
    
    @staticmethod
    def calculate_defect_rate_from_buffer(time_window_minutes=60):
        if not st.session_state.realtime_buffer:
            return None
        
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=time_window_minutes)
        
        recent_data = [
            point for point in st.session_state.realtime_buffer 
            if point['timestamp'] >= cutoff_time
        ]
        
        if not recent_data:
            return None
        
        total_count = len(recent_data)
        defect_count = sum(point['defect'] for point in recent_data)
        defect_rate = (defect_count / total_count) * 100
        
        return {
            'timestamp': now,
            'defect_rate': defect_rate,
            'total_count': total_count,
            'defect_count': defect_count
        }
    
    @staticmethod
    def should_update_chart():
        current_time = time.time()
        last_update = st.session_state.get('last_chart_update', 0)
        interval = st.session_state.get('chart_update_interval', 180)
        
        return (current_time - last_update) >= interval
    
    @staticmethod
    def update_control_chart():
        if not st.session_state.realtime_buffer:
            return False
        
        defect_data = RealTimeDataManager.calculate_defect_rate_from_buffer()
        
        if defect_data is None:
            return False
        
        chart_data = st.session_state.control_chart_data
        chart_data['time_points'].append(defect_data['timestamp'])
        chart_data['defect_rates'].append(defect_data['defect_rate'])
        
        if len(chart_data['time_points']) > 30:
            chart_data['time_points'] = chart_data['time_points'][-30:]
            chart_data['defect_rates'] = chart_data['defect_rates'][-30:]
        
        RealTimeDataManager._recalculate_control_limits(chart_data)
        
        st.session_state.last_chart_update = time.time()
        
        return True
    
    @staticmethod
    def _recalculate_control_limits(chart_data):
        if len(chart_data['defect_rates']) < 5:
            return
        
        recent_rates = chart_data['defect_rates']
        mean_rate = np.mean(recent_rates)
        std_rate = np.std(recent_rates)
        
        chart_data['control_limits'] = {
            'mean': mean_rate,
            'std': std_rate,
            'ucl': mean_rate + 3 * std_rate,
            'lcl': max(0, mean_rate - 3 * std_rate),
            'usl': mean_rate + 2 * std_rate,
            'lsl': max(0, mean_rate - 2 * std_rate)
        }
    
    @staticmethod
    def save_buffer_to_file():
        if not st.session_state.realtime_buffer:
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = snapshots_dir / f"realtime_buffer_{timestamp}.json"
            
            buffer_data = []
            for point in st.session_state.realtime_buffer:
                serializable_point = point.copy()
                serializable_point['timestamp'] = point['timestamp'].isoformat()
                buffer_data.append(serializable_point)
            
            snapshots_dir.mkdir(exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(buffer_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            st.error(f"버퍼 저장 오류: {str(e)}")
            return False

def get_current_process_stage():
    if 'system_start_time' not in st.session_state:
        return "melting", 0, 10
    
    start_time = st.session_state.system_start_time
    current_time = time.time()
    time_in_cycle = (current_time - start_time) % 30
    
    if time_in_cycle < 10:
        return "melting", int(time_in_cycle), 10
    elif time_in_cycle < 25:
        return "casting", int(time_in_cycle - 10), 15
    else:
        return "cooling", int(time_in_cycle - 25), 5

def create_control_chart():
    dark_mode = st.session_state.get('dark_mode', False)
    
    if RealTimeDataManager.should_update_chart():
        if RealTimeDataManager.update_control_chart():
            st.success("관리도가 자동 업데이트되었습니다!")
            RealTimeDataManager.save_buffer_to_file()
    
    data = st.session_state.control_chart_data
    
    if 'control_limits' in data and len(data['defect_rates']) >= 5:
        limits = data['control_limits']
        mean_rate = limits['mean']
        ucl = limits['ucl']
        lcl = limits['lcl']
        usl = limits['usl']
        lsl = limits['lsl']
    else:
        mean_rate = np.mean(data['defect_rates'])
        std_rate = np.std(data['defect_rates'])
        ucl = mean_rate + 3 * std_rate
        lcl = max(0, mean_rate - 3 * std_rate)
        usl = mean_rate + 2 * std_rate
        lsl = max(0, mean_rate - 2 * std_rate)
    
    time_labels = [t.strftime("%H:%M") for t in data['time_points']]
    
    if dark_mode:
        grid_color = "#48484a"
        text_color = "#ffffff"
        axis_color = "#98989d"
        bg_color = "transparent"
        normal_color = "#32d74b"
        warning_color = "#ff9f0a"
        critical_color = "#ff453a"
        control_line_color = "#0a84ff"
    else:
        grid_color = "#f2f2f7"
        text_color = "#1d1d1f"
        axis_color = "#6e6e73"
        bg_color = "transparent"
        normal_color = "#34c759"
        warning_color = "#ff9500"
        critical_color = "#ff3b30"
        control_line_color = "#007aff"
    
    option = {
        "backgroundColor": bg_color,
        "animation": True,
        "grid": {
            "left": "10%",
            "right": "8%",
            "top": "15%",
            "bottom": "20%",
            "containLabel": True
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.95)" if dark_mode else "rgba(255, 255, 255, 0.95)",
            "borderColor": control_line_color,
            "textStyle": {"color": text_color},
            "formatter": """function(params) {
                const time = params[0].name;
                const rate = params[0].value.toFixed(2);
                return `시간: ${time}<br/>불량률: ${rate}%`;
            }"""
        },
        "xAxis": {
            "type": "category",
            "data": time_labels,
            "axisLine": {
                "lineStyle": {"color": axis_color, "width": 1}
            },
            "axisTick": {
                "lineStyle": {"color": axis_color}
            },
            "axisLabel": {
                "color": axis_color,
                "fontSize": 11,
                "interval": 4
            },
            "splitLine": {
                "show": True,
                "lineStyle": {"color": grid_color, "type": "dashed"}
            }
        },
        "yAxis": {
            "type": "value",
            "name": "불량률 (%)",
            "nameTextStyle": {"color": text_color, "fontSize": 13, "fontWeight": "600"},
            "axisLine": {
                "lineStyle": {"color": axis_color, "width": 1}
            },
            "axisTick": {
                "lineStyle": {"color": axis_color}
            },
            "axisLabel": {
                "color": axis_color,
                "fontSize": 11,
                "formatter": "{value}%"
            },
            "splitLine": {
                "show": True,
                "lineStyle": {"color": grid_color, "type": "dashed"}
            }
        },
        "series": [
            {
                "name": "상한관리선 (UCL)",
                "type": "line",
                "data": [ucl] * len(time_labels),
                "lineStyle": {
                    "color": critical_color,
                    "width": 2,
                    "type": "solid"
                },
                "symbol": "none",
                "markLine": {
                    "silent": True,
                    "label": {
                        "show": True,
                        "position": "end",
                        "formatter": "UCL",
                        "color": critical_color,
                        "fontSize": 10,
                        "fontWeight": "600"
                    }
                }
            },
            {
                "name": "상한경고선 (USL)",
                "type": "line",
                "data": [usl] * len(time_labels),
                "lineStyle": {
                    "color": warning_color,
                    "width": 1,
                    "type": "dashed"
                },
                "symbol": "none"
            },
            {
                "name": "중심선 (CL)",
                "type": "line",
                "data": [mean_rate] * len(time_labels),
                "lineStyle": {
                    "color": control_line_color,
                    "width": 2,
                    "type": "solid"
                },
                "symbol": "none"
            },
            {
                "name": "하한경고선 (LSL)",
                "type": "line",
                "data": [lsl] * len(time_labels),
                "lineStyle": {
                    "color": warning_color,
                    "width": 1,
                    "type": "dashed"
                },
                "symbol": "none"
            },
            {
                "name": "하한관리선 (LCL)",
                "type": "line",
                "data": [lcl] * len(time_labels),
                "lineStyle": {
                    "color": critical_color,
                    "width": 2,
                    "type": "solid"
                },
                "symbol": "none"
            },
            {
                "name": "불량률",
                "type": "line",
                "data": data['defect_rates'],
                "lineStyle": {
                    "color": control_line_color,
                    "width": 3,
                    "shadowColor": f"{control_line_color}40",
                    "shadowBlur": 8
                },
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {
                    "color": control_line_color,
                    "shadowColor": f"{control_line_color}60",
                    "shadowBlur": 6
                },
                "emphasis": {
                    "scale": 1.5,
                    "itemStyle": {
                        "shadowBlur": 20,
                        "shadowColor": f"{control_line_color}80"
                    }
                },
                "smooth": 0.3,
                "animationDuration": 2000,
                "animationEasing": "cubicOut"
            }
        ],
        "legend": {
            "show": False
        }
    }
    
    st_echarts(options=option, height="400px")
    
    display_compact_update_status()
    
    col1, col2, col3, col4 = st.columns(4)
    
    out_of_control = sum(1 for rate in data['defect_rates'] if rate > ucl or rate < lcl)
    warning_points = sum(1 for rate in data['defect_rates'] if (lsl < rate <= usl) or (usl <= rate <= ucl))
    
    with col1:
        st.metric("평균 불량률", f"{mean_rate:.2f}%")
    
    with col2:
        st.metric("관리한계 이탈", f"{out_of_control}회", 
                 delta=f"{out_of_control-2}" if out_of_control > 2 else None)
    
    with col3:
        st.metric("경고 구간", f"{warning_points}회")
    
    with col4:
        current_rate = data['defect_rates'][-1]
        status = "정상" if lsl <= current_rate <= usl else ("경고" if usl < current_rate <= ucl else "이탈")
        st.metric("현재 상태", status)

def display_compact_update_status():
    current_time = time.time()
    last_update = st.session_state.get('last_chart_update', 0)
    interval = st.session_state.get('chart_update_interval', 180)
    buffer_size = len(st.session_state.get('realtime_buffer', []))
    
    time_since_update = current_time - last_update
    time_until_next = interval - time_since_update
    
    if time_until_next > 0:
        minutes = int(time_until_next // 60)
        seconds = int(time_until_next % 60)
        next_update_str = f"{minutes}:{seconds:02d}"
    else:
        next_update_str = "대기중"
    
    last_update_str = datetime.fromtimestamp(last_update).strftime("%H:%M:%S")
    
    collection_status = "활성" if st.session_state.get('data_collection_started', False) else "중지"
    last_collected = st.session_state.get('last_collected_id', None)
    collection_indicator = "수집중" if last_collected else "대기중"
    
    status_html = f'''
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
    
    st.markdown(status_html, unsafe_allow_html=True)

def create_mold_status_overview():
    mold_codes = [8412, 8573, 8600, 8722, 8917]
    current_data = st.session_state.get("current_status", {})
    current_mold = current_data.get("mold_code", None)
    
    mold_info = {
        8412: {"name": "A Mold", "type": "Heavy Duty"},
        8573: {"name": "B Mold", "type": "Precision"},
        8600: {"name": "C Mold", "type": "Standard"},
        8722: {"name": "D Mold", "type": "Electronics"},
        8917: {"name": "E Mold", "type": "Custom"}
    }
    
    mold_mapping = {
        0.0: 8412, 0: 8412,
        1.0: 8573, 1: 8573,
        2.0: 8600, 2: 8600,
        3.0: 8722, 3: 8722,
        4.0: 8917, 4: 8917
    }
    cols = st.columns(len(mold_codes))
    
    for i, mold_code in enumerate(mold_codes):
        with cols[i]:
            is_active = False
            if current_mold is not None:
                try:
                    mapped_mold = mold_mapping.get(float(current_mold))
                    is_active = (mapped_mold == mold_code)
                except (ValueError, TypeError):
                    try:
                        mapped_mold = mold_mapping.get(int(float(str(current_mold))))
                        is_active = (mapped_mold == mold_code)
                    except:
                        is_active = False
            
            info = mold_info.get(mold_code, {"name": "Unknown", "type": "Standard"})
            
            card_class = "active" if is_active else ""
            badge_class = "active" if is_active else ""
            
            status_text = "ACTIVE" if is_active else "STANDBY"
            
            card_html = f'''
            <div class="mold-status-card {card_class}">
                <div class="mold-header">
                    <div class="mold-title">
                        MOLD {mold_code}
                    </div>
                    <div class="mold-badge {badge_class}">
                        {status_text}
                    </div>
                </div>
                <div style="font-size: 14px; font-weight: 600; color: {"#0a84ff" if st.session_state.get('dark_mode', False) else "#007aff"};">
                    {info["name"]}
                </div>
                <div style="font-size: 12px; color: {"#98989d" if st.session_state.get('dark_mode', False) else "#6e6e73"}; margin-top: 4px;">
                    {info["type"]}
                </div>
            </div>
            '''
            
            st.markdown(card_html, unsafe_allow_html=True)

def create_process_visualization():
    stage, progress, max_progress = get_current_process_stage()
    
    dark_mode = st.session_state.get('dark_mode', False)
    if dark_mode:
        text_secondary = "#98989d"
        accent_color = "#0a84ff"
        card_bg = "#2c2c2e"
        text_primary = "#ffffff"
        success_color = "#32d74b"
        border_color = "#48484a"
    else:
        text_secondary = "#6e6e73"
        accent_color = "#007aff"
        card_bg = "#ffffff"
        text_primary = "#1d1d1f"
        success_color = "#34c759"
        border_color = "#e5e5e7"
    
    stages = [
        {"id": "melting", "label": "용융/가열", "icon": "HEAT", "desc": "용융온도 제어", "duration": "10초"},
        {"id": "casting", "label": "주조/압력", "icon": "CAST", "desc": "주조압력 적용", "duration": "15초"},
        {"id": "cooling", "label": "냉각/완료", "icon": "COOL", "desc": "금형 냉각", "duration": "5초"}
    ]
    
    progress_html = '<div class="process-indicator">'
    
    for i, step in enumerate(stages):
        if step["id"] == stage:
            status_class = "active"
            progress_percent = (progress / max_progress) * 100
        elif (stage == "casting" and step["id"] == "melting") or (stage == "cooling" and step["id"] in ["melting", "casting"]):
            status_class = "completed"
            progress_percent = 100
        else:
            status_class = "inactive"
            progress_percent = 0
        
        progress_html += f'''<div class="process-step {status_class}">
            <div class="step-icon {status_class}">
                {step["icon"]}
            </div>
            <div class="step-label {status_class}">
                {step["label"]}
            </div>
            <div style="font-size: 0.7rem; color: {text_secondary}; margin-top: 2px;">
                {step["desc"]}
            </div>
            <div style="font-size: 0.65rem; color: {text_secondary}; margin-top: 2px;">
                ({step["duration"]})
            </div>
            <div style="font-size: 0.75rem; color: {accent_color}; margin-top: 4px; font-weight: 600;">
                {progress_percent:.0f}%
            </div></div>'''
    
    progress_html += '</div>'
    st.markdown(progress_html, unsafe_allow_html=True)
    
    if 'system_start_time' in st.session_state:
        start_time = st.session_state.system_start_time
        current_time = time.time()
        time_in_cycle = (current_time - start_time) % 30
        remaining_time = 30 - time_in_cycle
        
        timer_html = f'''
        <div style="text-align: center; margin-top: 10px; font-size: 0.9rem; color: {text_secondary};">
            <strong>주기 타이머:</strong> <span style="color: {accent_color}; font-weight: 600;">{remaining_time:.1f}초</span> 후 초기화
        </div>
        '''
        st.markdown(timer_html, unsafe_allow_html=True)
    
    return stage, progress

def create_app_gauge(title, value, min_val=0, max_val=100, unit="", target_range=None):
    if target_range:
        if target_range[0] <= value <= target_range[1]:
            color = "#34c759"
        else:
            color = "#ff3b30"
    else:
        progress = value / max_val
        if progress <= 0.6:
            color = "#34c759"
        elif progress <= 0.8:
            color = "#ff9500"
        else:
            color = "#ff3b30"
    
    bg_color = "#2c2c2e" if st.session_state.get('dark_mode', False) else "#ffffff"
    text_color = "#ffffff" if st.session_state.get('dark_mode', False) else "#1d1d1f"
    
    option = {
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
                "color": text_color,
                "formatter": "{value}"
            },
            "title": {
                "show": True,
                "offsetCenter": [0, "80%"],
                "fontSize": 14,
                "fontWeight": "600",
                "color": text_color
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
    
    st_echarts(options=option, height="280px")

def create_key_metrics():
    current_data = st.session_state.get("current_status", {})
    
    if not current_data:
        st.info("실시간 데이터를 기다리는 중...")
        return
    
    key_metrics = [
        {"key": "molten_temp", "label": "용융온도", "unit": "°C"},
        {"key": "cast_pressure", "label": "주조압력", "unit": "MPa"},
        {"key": "upper_mold_temp1", "label": "상금형온도", "unit": "°C"},
        {"key": "passorfail", "label": "품질판정", "unit": ""}
    ]
    
    cols = st.columns(4)
    
    for i, metric in enumerate(key_metrics):
        key = metric["key"]
        if key in current_data:
            value = current_data[key]
            
            with cols[i]:
                if key == "passorfail":
                    delta = None
                    if value == "Pass":
                        st.metric(f"{metric['label']}", "Pass", delta=delta)
                    else:
                        st.metric(f"{metric['label']}", "Fail", delta=delta)
                else:
                    prev_key = f"prev_{key}"
                    prev_value = st.session_state.get(prev_key)
                    delta = None
                    
                    if prev_value is not None:
                        diff = value - prev_value
                        if abs(diff) > 0.01:
                            delta = f"{diff:+.1f}"
                    
                    st.session_state[prev_key] = value
                    st.metric(
                        f"{metric['label']}", 
                        f"{value:.1f} {metric['unit']}", 
                        delta=delta
                    )

def create_production_summary():
    if not st.session_state.collected_data:
        st.info("수집된 데이터가 없습니다.")
        return
    
    total_count = len(st.session_state.collected_data)
    pass_count = len([d for d in st.session_state.collected_data if d.get("passorfail") == "Pass"])
    fail_count = total_count - pass_count
    pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 생산량", f"{total_count:,}")
    
    with col2:
        st.metric("양품 / 불량품", f"{pass_count:,} / {fail_count:,}")
    
    with col3:
        delta_rate = f"{pass_rate-95:.1f}%" if total_count > 10 else None
        st.metric("양품률", f"{pass_rate:.1f}%", delta=delta_rate)

def run():
    RealTimeDataManager.initialize_session_state()

    if st.session_state.get('data_collection_started', False):
        if st.session_state.get('current_status', {}):
            RealTimeDataManager.collect_realtime_data()

    try:
        create_control_chart()
    except Exception as e:
        st.error(f"관리도 생성 오류: {str(e)}")
        st.info("관리도를 로드하는 중입니다...")
    
    st.markdown("---")
    
    st.markdown("### 실시간 공정 현황")
    st.markdown("#### 다이캐스팅 공정 단계")
    try:
        current_stage, progress = create_process_visualization()
    except Exception as e:
        st.error(f"공정 시각화 오류: {str(e)}")
        stage, progress, max_progress = get_current_process_stage()
        progress_percent = (progress / max_progress) * 100
        st.info(f"현재 단계: {stage} ({progress_percent:.0f}% 진행중)")
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 주조압력 모니터링")
        
        current_pressure = 0
        if st.session_state.current_status and "cast_pressure" in st.session_state.current_status:
            current_pressure = st.session_state.current_status["cast_pressure"]
        
        try:
            create_app_gauge(
                title="주조압력", 
                value=current_pressure, 
                min_val=0, 
                max_val=100,
                unit=" MPa",
                target_range=(70, 80)
            )
        except Exception as e:
            st.error(f"게이지 차트 오류: {str(e)}")
            st.metric("주조압력", f"{current_pressure:.1f} MPa")
        
        st.markdown("### 생산 현황")
        create_production_summary()
    
    with col2:
        st.markdown("#### 핵심 품질 지표")
        create_mold_status_overview()
        create_key_metrics()
        
        st.markdown("---")
        
        st.markdown("### 시스템 제어")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("수동 데이터 읽기", use_container_width=True):
                with st.spinner("데이터 읽는 중..."):
                    try:
                        new_data = read_data_from_test_py()
                        if new_data:
                            prev_buffer_size = len(st.session_state.get('realtime_buffer', []))
                            prev_collected_count = len(st.session_state.get('collected_data', []))
                            
                            st.session_state.current_status = new_data
                            st.session_state.collected_data.append(new_data)
                            save_data_to_file(st.session_state.collected_data)
                            
                            collected = RealTimeDataManager.collect_realtime_data()
                            current_buffer_size = len(st.session_state.get('realtime_buffer', []))
                            current_collected_count = len(st.session_state.get('collected_data', []))
                            
                            st.success(f"""데이터 수집 완료!
                            - 수집된 데이터: {current_collected_count}개 (이전: {prev_collected_count}개)
                            - 실시간 버퍼: {current_buffer_size}개 (이전: {prev_buffer_size}개)
                            - 버퍼 추가 여부: {'성공' if collected else '중복/실패'}""")
                            
                            with st.expander("수집된 데이터 내용"):
                                st.json(new_data)
                            
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.error("데이터를 읽어올 수 없습니다.")
                    except Exception as e:
                        st.error(f"데이터 읽기 오류: {str(e)}")
                        st.write(f"오류 상세: {e}")

        with col_btn2:
            if st.button("즉시 데이터 저장", use_container_width=True):
                if st.session_state.collected_data:
                    with st.spinner("저장 중..."):
                        try:
                            save_snapshot_batch(st.session_state.collected_data)
                            st.session_state.last_snapshot_time = time.time()
                            st.success("데이터가 즉시 저장되었습니다!")
                        except Exception as e:
                            st.error(f"저장 오류: {str(e)}")
                else:
                    st.warning("저장할 데이터가 없습니다.")

        if st.button("관리도 데이터 갱신", use_container_width=True):
            with st.spinner("관리도 데이터 갱신 중..."):
                try:
                    if RealTimeDataManager.update_control_chart():
                        RealTimeDataManager.save_buffer_to_file()
                        st.success("관리도 데이터가 갱신되었습니다!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("갱신할 데이터가 없습니다.")
                except Exception as e:
                    st.error(f"관리도 데이터 갱신 오류: {str(e)}")

        st.markdown("---")
        info_cols = st.columns(2)
        
        with info_cols[0]:
            try:
                snapshot_count = len(list(snapshots_dir.glob("*snapshot*.json")))
                st.metric("저장된 스냅샷", f"{snapshot_count}개")
            except:
                st.metric("저장된 스냅샷", "0개")
        
        with info_cols[1]:
            if st.session_state.get('data_collection_started', False):
                try:
                    last_minutes = (time.time() - st.session_state.get('last_snapshot_time', time.time())) / 60
                    next_minutes = 15 - last_minutes
                    if next_minutes > 0:
                        st.metric("다음 저장", f"{next_minutes:.1f}분 후")
                    else:
                        st.metric("다음 저장", "곧 저장")
                except:
                    st.metric("다음 저장", "계산 중...")
            else:
                st.metric("저장 주기", "15분 간격")
    
    st.markdown("---")
    st.markdown("### 최근 불량 데이터 이력")
    
    try:
        current_data = st.session_state.get("current_status", None)
        if current_data and current_data.get("passorfail") == "Fail":
            ng_entry = {
                "시간": current_data.get("timestamp", ""),
                "몰드코드": current_data.get("mold_code", ""),
                "용융온도": current_data.get("molten_temp", 0),
                "주조압력": current_data.get("cast_pressure", 0),
                "판정": current_data.get("passorfail", "")
            }
            if not any(e.get("시간") == ng_entry["시간"] for e in st.session_state.ng_history):
                st.session_state.ng_history.append(ng_entry)
        
        if st.session_state.ng_history:
            recent_ng = st.session_state.ng_history[-5:]
            df_ng = pd.DataFrame(recent_ng)
            
            if "시간" in df_ng.columns and len(df_ng) > 0:
                try:
                    df_ng["시간"] = pd.to_datetime(df_ng["시간"]).dt.strftime("%H:%M:%S")
                except:
                    pass
            
            st.dataframe(df_ng, use_container_width=True, hide_index=True)
            
            if len(st.session_state.ng_history) > 5:
                st.caption(f"총 {len(st.session_state.ng_history)}개의 불량 데이터 중 최근 5개를 표시합니다.")
        else:
            st.info("아직 불량 데이터가 없습니다.")
    
    except Exception as e:
        st.error(f"불량 데이터 이력 처리 오류: {str(e)}")
        st.info("아직 불량 데이터가 없습니다.")