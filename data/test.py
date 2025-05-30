# 다이캐스팅 실시간 데이터 파일
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

current_data = get_current_data()
