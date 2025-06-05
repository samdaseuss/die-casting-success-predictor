import pandas as pd
import joblib
import datetime
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
import numpy as np
import time

project_root = Path(__file__).resolve().parents[1]
test_path = project_root / "data/test.csv"
model_path = project_root / "models/best_model_20250604_1.pkl"

def preprocess_input(df):
    df = df.drop(columns=[
        'id', 'mold_name', 'name', 'line', 'emergency_stop', 'count',
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
    df = df.drop(columns=['registration_time'], errors='ignore')

    for col in ['EMS_operation_time', 'mold_code']:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))

    df = df.fillna(df.median(numeric_only=True))
    return df

model = joblib.load(model_path)
test = pd.read_csv(test_path)
test = preprocess_input(test)

call_count = 0

def get_current_data():
    global call_count
    call_count += 1
    
    np.random.seed(int(time.time() * 1000000) % (2**31) + call_count)
    sample_idx = np.random.randint(0, len(test))
    
    sample = test.iloc[sample_idx].copy()
    
    # 모델 예측
    sample_input = sample.drop(labels=['passorfail'], errors='ignore').values.reshape(1, -1)
    prediction = model.predict(sample_input)[0]
    pred_label = "Pass" if prediction == 0 else "Fail"
    
    # 결과 생성
    result = sample.to_dict()
    result['passorfail'] = pred_label
    result['timestamp'] = datetime.datetime.now().isoformat()
    result['debug_info'] = f"call={call_count},idx={sample_idx}"
    
    return result