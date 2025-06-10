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
model_path = project_root / "models/best_model_20250604_1.pkl"

def preprocess_input(df):
    df = df.drop(columns=[
        'mold_name', 'name', 'line', 'emergency_stop', 'count',
        'tryshot_signal', 'upper_mold_temp3', 'lower_mold_temp3',
        'molten_volume', 'time', 'date', 'heating_furnace'
    ], errors='ignore')

    df = df[df['working'].notna()]
    df['registration_time'] = pd.to_datetime(df['registration_time'], errors='coerce')
    df['EMS_operation_time'] = df['EMS_operation_time'].astype('object')
    df['mold_code'] = df['mold_code'].astype('object')
    df['molten_temp'] = df['molten_temp'].fillna(df['molten_temp'].median())

    df = df[~((df['molten_temp'] == 0) |
        (df['low_section_speed'] >= 60000) |
        (df['production_cycletime'] == 0) |
        (df['upper_mold_temp1'] >= 1449) |
        (df['sleeve_temperature'] >= 1449) |
        (df['physical_strength'] >= 60000) |
        (df['Coolant_temperature'] >= 1449) |
        (df['upper_mold_temp2'] >= 4000))]

    df['working'] = df['working'].map({'가동': 1, '비가동': 0})

    for col in ['EMS_operation_time', 'mold_code']:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))

    df = df.fillna(df.median(numeric_only=True))
    return df

model = joblib.load(model_path)
test = pd.read_csv(test_path)
test = preprocess_input(test)

call_count = 0

def get_current_data_by_id(id):
    if 'id' not in test.columns:
        raise ValueError("데이터셋에 'id' 컬럼이 없습니다. 원본 CSV 파일을 확인하세요.")
    
    sample = test[test['id'] == id]

    if sample.empty:
        raise ValueError(f"ID {id}에 해당하는 데이터가 존재하지 않습니다.")

    sample = sample.iloc[0].copy()
    sample_input = sample.drop(labels=['id', 'registration_time'], errors='ignore').values.reshape(1, -1)

    prediction = model.predict(sample_input)[0]
    pred_label = "Pass" if prediction == 0 else "Fail"

    result = sample.to_dict()
    
    for key, value in result.items():
        # NaN 값 처리
        if pd.isna(value):
            result[key] = None
        # Timestamp 객체인 경우
        elif hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        elif isinstance(value, (pd.Timestamp, datetime)):  # 수정: datetime.datetime → datetime
            result[key] = value.isoformat()
    
    result['passorfail'] = pred_label
    result['timestamp'] = datetime.now().isoformat()  # 수정: datetime.datetime.now() → datetime.now()
    result['debug_info'] = f"id={id}"

    return result