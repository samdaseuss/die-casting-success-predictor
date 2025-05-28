"""유틸리티 헬퍼 함수들"""

def validate_input_range(value, min_val, max_val, param_name):
    """입력값이 유효한 범위에 있는지 확인"""
    if value < min_val or value > max_val:
        raise ValueError(f"{param_name}는 {min_val}과 {max_val} 사이의 값이어야 합니다.")
    return True

def calculate_process_score(input_data):
    """공정 점수를 계산"""
    # 간단한 점수 계산 로직
    temp_score = (input_data.get('molten_temp', 0) - 600) / 200 * 100
    pressure_score = input_data.get('cast_pressure', 0) / 100 * 100
    
    return (temp_score + pressure_score) / 2
