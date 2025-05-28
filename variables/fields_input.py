# variables/fields_input.py

fields_input = {
    "molten_temp": {"label": "용융 온도 (°C)", "min": 600.0, "max": 800.0, "default": 700.0, "step": 1.0},
    "production_cycletime": {"label": "생산 사이클 시간 (초)", "min": 10.0, "max": 60.0, "default": 30.0, "step": 1.0},
    "low_section_speed": {"label": "저속 구간 속도 (mm/s)", "min": 10.0, "max": 50.0, "default": 25.0, "step": 1.0},
    "high_section_speed": {"label": "고속 구간 속도 (mm/s)", "min": 50.0, "max": 150.0, "default": 100.0, "step": 5.0},
    "cast_pressure": {"label": "주조 압력 (MPa)", "min": 20.0, "max": 100.0, "default": 60.0, "step": 1.0},
    "biscuit_thickness": {"label": "비스킷 두께 (mm)", "min": 5.0, "max": 20.0, "default": 12.0, "step": 0.1},
    "upper_mold_temp1": {"label": "상부 금형 온도 1 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "upper_mold_temp2": {"label": "상부 금형 온도 2 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "upper_mold_temp3": {"label": "상부 금형 온도 3 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "lower_mold_temp1": {"label": "하부 금형 온도 1 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "lower_mold_temp2": {"label": "하부 금형 온도 2 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "lower_mold_temp3": {"label": "하부 금형 온도 3 (°C)", "min": 150.0, "max": 250.0, "default": 200.0, "step": 1.0},
    "sleeve_temperature": {"label": "슬리브 온도 (°C)", "min": 180.0, "max": 280.0, "default": 230.0, "step": 1.0},
    "physical_strength": {"label": "물리적 강도 (MPa)", "min": 200.0, "max": 400.0, "default": 300.0, "step": 5.0},
    "Coolant_temperature": {"label": "냉각수 온도 (°C)", "min": 15.0, "max": 35.0, "default": 25.0, "step": 0.5}
}

def get_input_fields():
    return fields_input