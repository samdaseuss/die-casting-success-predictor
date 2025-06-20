# test.py
import pandas as pd
import joblib
from datetime import datetime
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", message=".*InconsistentVersionWarning.*")

project_root = Path(__file__).resolve().parents[1]
test_path = project_root / "data/test.csv"
model_path = project_root / "models/best_model_20250610_1.pkl"

def preprocess_input(df):
    """CustomCleaner와 동일한 전처리 로직"""
    df = df.copy()
    
    # 불필요한 컬럼 제거
    df = df.drop(columns=[
        'mold_name', 'name', 'line', 'emergency_stop', 'count',
        'tryshot_signal', 'upper_mold_temp3', 'lower_mold_temp3',
        'molten_volume', 'time', 'date', 'heating_furnace'
    ], errors='ignore')

    # working이 null인 행 제거
    df = df[~df['working'].isna()]
    
    # registration_time을 datetime으로 변환
    df['registration_time'] = pd.to_datetime(df['registration_time'], errors='coerce')
    
    # 데이터 타입 변경
    df['EMS_operation_time'] = df['EMS_operation_time'].astype('object')
    df['mold_code'] = df['mold_code'].astype('object')
    
    # 이상치 필터링
    df = df[~((df['molten_temp'] == 0) |
              (df['low_section_speed'] >= 60000) |
              (df['production_cycletime'] == 0) |
              (df['upper_mold_temp1'] >= 1449) |
              (df['sleeve_temperature'] >= 1449) |
              (df['physical_strength'] >= 60000) |
              (df['Coolant_temperature'] >= 1449) |
              (df['upper_mold_temp2'] >= 4000))]
    
    # hour 피처 추가 (중요: 이 부분이 빠져있었음!)
    df['hour'] = df['registration_time'].dt.hour
    
    # registration_time 컬럼 제거
    df = df.drop(columns=['registration_time'])
    
    # working 컬럼 인코딩
    df['working'] = df['working'].map({'가동': 1, '비가동': 0})

    # 범주형 변수 인코딩
    for col in ['EMS_operation_time', 'mold_code']:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))

    # 결측치 처리
    df = df.fillna(df.median(numeric_only=True))
    
    return df.reset_index(drop=True)

# 모델과 데이터 로드
model = joblib.load(model_path)
test = pd.read_csv(test_path)
test = preprocess_input(test)

# 디버깅: 피처 수 확인
print(f"전처리된 테스트 데이터 피처 수: {test.shape[1]}")
print(f"컬럼명: {list(test.columns)}")

def get_current_data_by_id(id):
    if 'id' not in test.columns:
        raise ValueError("데이터셋에 'id' 컬럼이 없습니다. 원본 CSV 파일을 확인하세요.")
    
    sample = test[test['id'] == id]

    if sample.empty:
        raise ValueError(f"ID {id}에 해당하는 데이터가 존재하지 않습니다.")

    sample_row = sample.iloc[0].copy()
    
    # 예측을 위한 피처 준비 (id 컬럼 제외)
    feature_columns = [col for col in test.columns if col != 'id']
    
    # DataFrame 형태로 입력 준비 (파이프라인이 DataFrame을 기대함)
    sample_input_df = sample_row[feature_columns].to_frame().T
    
    # 디버깅: 입력 피처 수 확인
    print(f"모델 입력 피처 수: {sample_input_df.shape[1]}")
    print(f"피처 컬럼들: {feature_columns}")
    print(f"sample_input_df shape: {sample_input_df.shape}")
    print(f"sample_input_df type: {type(sample_input_df)}")
    
    try:
        # 예측 (DataFrame을 직접 전달)
        prediction = model.predict(sample_input_df)[0]
        proba_array = model.predict_proba(sample_input_df)[0]
        proba = proba_array[1] if len(proba_array) > 1 else proba_array[0]
        pred_label = "Pass" if prediction == 0 else "Fail"
    except Exception as e:
        print(f"예측 중 오류: {e}")
        print(f"sample_input_df columns: {sample_input_df.columns.tolist()}")
        print(f"sample_input_df dtypes: {sample_input_df.dtypes}")
        raise
    
    # 결과 딕셔너리 생성
    result = sample_row.to_dict()
    
    # 데이터 타입 정리
    for key, value in result.items():
        if pd.isna(value):
            result[key] = None
        elif hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        elif isinstance(value, (pd.Timestamp, datetime)):
            result[key] = value.isoformat()
    
    # 예측 결과 추가
    result['passorfail'] = pred_label
    result['proba'] = float(proba * 100)  # numpy 타입을 float로 변환
    result['timestamp'] = datetime.now().isoformat()
    result['debug_info'] = f"id={id}, features={sample_input_df.shape[1]}"

    return result