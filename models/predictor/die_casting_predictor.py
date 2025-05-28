import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.impute import SimpleImputer
import warnings
warnings.filterwarnings('ignore')

class DiecastingQualityPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        self.target_column = 'passorfail'
        
    def load_and_preprocess_data(self, data_path=None, df=None):
        
        print("📊 데이터 로딩 및 전처리 시작...")
        
        if df is not None:
            self.df = df.copy()
        else:
            # CSV 파일에서 데이터 로딩
            self.df = pd.read_csv(data_path)
        
        print(f"원본 데이터 크기: {self.df.shape}")
        print(f"결측값 개수:\\n{self.df.isnull().sum()}")
        
        # 1. 기본 정보 출력
        print("\\n📋 데이터 기본 정보:")
        print(self.df.info())
        
        # 2. 타겟 변수 확인
        print(f"\\n🎯 타겟 변수 분포:")
        print(self.df[self.target_column].value_counts())
        
        # 3. 전처리 단계
        self.df_processed = self._preprocess_features()
        
        return self.df_processed
    
    def _preprocess_features(self):
        """
        피처 전처리 수행
        """
        df = self.df.copy()
        
        # 1. 날짜/시간 피처 처리
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['day_of_week'] = df['date'].dt.dayofweek
            df['month'] = df['date'].dt.month
            df['day'] = df['date'].dt.day
        
        if 'time' in df.columns:
            # 시간을 분 단위로 변환
            df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
            df['hour'] = df['time'].dt.hour
            df['minute'] = df['time'].dt.minute
        
        # 2. 카테고리 변수 인코딩
        categorical_columns = ['line', 'name', 'mold_name', 'mold_code', 'heating_furnace']
        
        for col in categorical_columns:
            if col in df.columns:
                # 결측값을 'Unknown'으로 채움
                df[col] = df[col].fillna('Unknown')
                
                # 라벨 인코딩
                le = LabelEncoder()
                df[f'{col}_encoded'] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
        
        # 3. 수치형 변수 결측값 처리
        numeric_columns = [
            'molten_temp', 'facility_operation_cycleTime', 'production_cycletime',
            'low_section_speed', 'high_section_speed', 'molten_volume', 'cast_pressure',
            'biscuit_thickness', 'upper_mold_temp1', 'upper_mold_temp2', 'upper_mold_temp3',
            'lower_mold_temp1', 'lower_mold_temp2', 'lower_mold_temp3', 'sleeve_temperature',
            'physical_strength', 'Coolant_temperature', 'EMS_operation_time'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                # 중앙값으로 결측값 채움
                df[col] = df[col].fillna(df[col].median())
        
        # 4. 피처 엔지니어링
        df = self._feature_engineering(df)
        
        # 5. 불필요한 컬럼 제거
        columns_to_drop = ['id', 'date', 'time', 'registration_time'] + categorical_columns
        columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        df = df.drop(columns=columns_to_drop, errors='ignore')
        
        return df
    
    def _feature_engineering(self, df):
        """
        피처 엔지니어링 - 새로운 피처 생성
        """
        # 온도 관련 피처
        temp_cols = ['upper_mold_temp1', 'upper_mold_temp2', 'upper_mold_temp3',
                     'lower_mold_temp1', 'lower_mold_temp2', 'lower_mold_temp3']
        
        existing_temp_cols = [col for col in temp_cols if col in df.columns]
        if existing_temp_cols:
            df['avg_mold_temp'] = df[existing_temp_cols].mean(axis=1)
            df['temp_variation'] = df[existing_temp_cols].std(axis=1)
        
        # 속도 관련 피처
        if 'low_section_speed' in df.columns and 'high_section_speed' in df.columns:
            df['speed_ratio'] = df['high_section_speed'] / (df['low_section_speed'] + 1e-8)
            df['speed_diff'] = df['high_section_speed'] - df['low_section_speed']
        
        # 온도 차이 피처
        if 'molten_temp' in df.columns and 'avg_mold_temp' in df.columns:
            df['temp_diff_molten_mold'] = df['molten_temp'] - df['avg_mold_temp']
        
        # 압력-부피 관련 피처
        if 'cast_pressure' in df.columns and 'molten_volume' in df.columns:
            df['pressure_volume_ratio'] = df['cast_pressure'] / (df['molten_volume'] + 1e-8)
        
        return df
    
    def train_models(self):
        """
        여러 모델을 훈련하고 최적 모델 선택
        """
        print("\\n🤖 모델 훈련 시작...")
        
        # 피처와 타겟 분리
        X = self.df_processed.drop(columns=[self.target_column])
        y = self.df_processed[self.target_column]
        
        # Pass/Fail을 1/0으로 변환
        y = (y == 'Pass').astype(int)
        
        self.feature_columns = X.columns.tolist()
        
        # 훈련/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # 피처 스케일링
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # 여러 모델 정의
        models = {
            'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
            'GradientBoosting': GradientBoostingClassifier(random_state=42),
            'ExtraTrees': ExtraTreesClassifier(n_estimators=100, random_state=42),
            'LogisticRegression': LogisticRegression(random_state=42, max_iter=1000),
            'SVM': SVC(probability=True, random_state=42)
        }
        
        # 모델 성능 비교
        model_scores = {}
        
        for name, model in models.items():
            print(f"\\n🔍 {name} 모델 훈련 중...")
            
            if name in ['LogisticRegression', 'SVM']:
                model.fit(X_train_scaled, y_train)
                y_pred = model.predict(X_test_scaled)
                y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            else:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                y_pred_proba = model.predict_proba(X_test)[:, 1]
            
            accuracy = accuracy_score(y_test, y_pred)
            auc_score = roc_auc_score(y_test, y_pred_proba)
            
            model_scores[name] = {
                'model': model,
                'accuracy': accuracy,
                'auc': auc_score,
                'predictions': y_pred,
                'probabilities': y_pred_proba
            }
            
            print(f"   정확도: {accuracy:.4f}")
            print(f"   AUC: {auc_score:.4f}")
        
        # 최적 모델 선택 (AUC 기준)
        best_model_name = max(model_scores.keys(), key=lambda x: model_scores[x]['auc'])
        self.model = model_scores[best_model_name]['model']
        self.best_model_name = best_model_name
        
        print(f"\\n🏆 최적 모델: {best_model_name}")
        print(f"   정확도: {model_scores[best_model_name]['accuracy']:.4f}")
        print(f"   AUC: {model_scores[best_model_name]['auc']:.4f}")
        
        # 상세 평가 리포트
        self._detailed_evaluation(y_test, model_scores[best_model_name])
        
        # 피처 중요도 출력
        self._feature_importance()
        
        return model_scores
    
    def _detailed_evaluation(self, y_test, best_model_info):
        """
        상세 모델 평가
        """
        print("\\n📊 상세 평가 리포트:")
        print("="*50)
        print(classification_report(y_test, best_model_info['predictions'], target_names=['Fail', 'Pass']))
        
        # 혼동 행렬
        cm = confusion_matrix(y_test, best_model_info['predictions'])
        print("\\n혼동 행렬:")
        print(cm)
        
    def _feature_importance(self):
        """
        피처 중요도 출력
        """
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            print("\\n🔍 피처 중요도 (상위 10개):")
            print("="*40)
            for idx, row in feature_importance.head(10).iterrows():
                print(f"{row['feature']:<25}: {row['importance']:.4f}")
    
    def predict_individual_samples(self, df=None):

        print("\\n🎯 개별 샘플 예측 시작...")
        
        if df is None:
            df = self.df_processed
        
        X = df[self.feature_columns]
        
        # 스케일링 (필요한 경우)
        if self.best_model_name in ['LogisticRegression', 'SVM']:
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            probabilities = self.model.predict_proba(X_scaled)[:, 1]
        else:
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)[:, 1]
        
        # 결과 정리
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            result = {
                'Index': i,
                'Prediction': 'Pass' if pred == 1 else 'Fail',
                'Confidence': prob if pred == 1 else 1-prob,
                'Probability_Pass': prob,
                'Probability_Fail': 1-prob
            }
            results.append(result)
        
        results_df = pd.DataFrame(results)
        
        # 실제값과 비교 (있는 경우)
        if self.target_column in df.columns:
            actual = df[self.target_column].values
            results_df['Actual'] = actual
            results_df['Correct'] = (results_df['Prediction'] == actual)
            accuracy = results_df['Correct'].mean()
            print(f"\\n전체 정확도: {accuracy:.4f}")
        
        return results_df
    
    def predict_individual_samples_one_by_one(self, df=None):
        
        if df is None:
            df = self.df_processed
        
        X = df[self.feature_columns]
        
        if self.best_model_name in ['LogisticRegression', 'SVM']:
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            probabilities = self.model.predict_proba(X_scaled)[:, 1]
        else:
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)[:, 1]
        
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            result = {
                'Index': i,
                'Prediction': 'Pass' if pred == 1 else 'Fail',
                'Confidence': prob if pred == 1 else 1-prob,
                'Probability_Pass': prob,
                'Probability_Fail': 1-prob
            }
            results.append(result)
        
        results_df = pd.DataFrame(results)
        
        if self.target_column in df.columns:
            actual = df[self.target_column].values
            results_df['Actual'] = actual
            results_df['Correct'] = (results_df['Prediction'] == actual)
            accuracy = results_df['Correct'].mean()
            print(f"\\n전체 정확도: {accuracy:.4f}")
        
        return results_df
    
    def print_prediction_summary(self, results_df):

        print("\\n📋 예측 결과 요약:")
        print("="*50)
        
        total_samples = len(results_df)
        pass_predictions = (results_df['Prediction'] == 'Pass').sum()
        fail_predictions = (results_df['Prediction'] == 'Fail').sum()
        
        print(f"전체 샘플 수: {total_samples}")
        print(f"Pass 예측: {pass_predictions} ({pass_predictions/total_samples*100:.1f}%)")
        print(f"Fail 예측: {fail_predictions} ({fail_predictions/total_samples*100:.1f}%)")
        
        # 높은 확신도 예측
        high_confidence = results_df[results_df['Confidence'] > 0.8]
        print(f"\\n높은 확신도(>80%) 예측: {len(high_confidence)}개")
        
        # 낮은 확신도 예측 (주의 필요)
        low_confidence = results_df[results_df['Confidence'] < 0.6]
        print(f"낮은 확신도(<60%) 예측: {len(low_confidence)}개 (재검토 필요)")
        
        if 'Actual' in results_df.columns:
            correct_predictions = results_df['Correct'].sum()
            print(f"\\n정확한 예측: {correct_predictions}/{total_samples} ({correct_predictions/total_samples*100:.1f}%)")
        
        # 샘플 예측 결과 출력 (처음 20개)
        print("\\n🔍 개별 예측 결과 (처음 20개):")
        print("-"*80)
        for idx, row in results_df.head(20).iterrows():
            status = "✅" if row.get('Correct', True) else "❌"
            actual_str = f" (실제: {row['Actual']})" if 'Actual' in row else ""
            print(f"{status} 샘플 {row['Index']:3d}: {row['Prediction']:4s} "
                  f"(확신도: {row['Confidence']:.3f}){actual_str}")

def main():
    """
    메인 실행 함수
    """
    def create_sample_data():
        np.random.seed(42)
        n_samples = 1000
        
        data = {
            'id': range(1, n_samples + 1),
            'line': np.random.choice(['Line_A', 'Line_B', 'Line_C'], n_samples),
            'name': np.random.choice(['Product_1', 'Product_2', 'Product_3'], n_samples),
            'mold_name': np.random.choice(['Mold_X', 'Mold_Y', 'Mold_Z'], n_samples),
            'time': [f"{np.random.randint(8, 18):02d}:{np.random.randint(0, 60):02d}:{np.random.randint(0, 60):02d}" for _ in range(n_samples)],
            'date': pd.date_range('2024-01-01', periods=n_samples, freq='H'),
            'count': np.random.randint(1, 100, n_samples),
            'working': np.random.choice([0, 1], n_samples),
            'emergency_stop': np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),
            'molten_temp': np.random.normal(700, 20, n_samples),
            'facility_operation_cycleTime': np.random.normal(25, 5, n_samples),
            'production_cycletime': np.random.normal(30, 5, n_samples),
            'low_section_speed': np.random.normal(25, 5, n_samples),
            'high_section_speed': np.random.normal(100, 15, n_samples),
            'molten_volume': np.random.normal(150, 20, n_samples),
            'cast_pressure': np.random.normal(60, 10, n_samples),
            'biscuit_thickness': np.random.normal(12, 2, n_samples),
            'upper_mold_temp1': np.random.normal(200, 15, n_samples),
            'upper_mold_temp2': np.random.normal(200, 15, n_samples),
            'upper_mold_temp3': np.random.normal(200, 15, n_samples),
            'lower_mold_temp1': np.random.normal(200, 15, n_samples),
            'lower_mold_temp2': np.random.normal(200, 15, n_samples),
            'lower_mold_temp3': np.random.normal(200, 15, n_samples),
            'sleeve_temperature': np.random.normal(230, 20, n_samples),
            'physical_strength': np.random.normal(300, 30, n_samples),
            'Coolant_temperature': np.random.normal(25, 3, n_samples),
            'EMS_operation_time': np.random.exponential(2, n_samples),
            'registration_time': pd.date_range('2024-01-01', periods=n_samples, freq='H'),
            'tryshot_signal': np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
            'mold_code': np.random.choice(['MC001', 'MC002', 'MC003'], n_samples),
            'heating_furnace': np.random.choice(['HF_A', 'HF_B'], n_samples)
        }
        
        pass_prob = (
            (data['molten_temp'] > 680) * 0.3 +
            (data['cast_pressure'] > 55) * 0.3 +
            (data['physical_strength'] > 280) * 0.2 +
            (data['emergency_stop'] == 0) * 0.2 +
            np.random.normal(0, 0.1, n_samples)
        )
        
        data['passorfail'] = ['Pass' if p > 0.5 else 'Fail' for p in pass_prob]
        
        return pd.DataFrame(data)
    
    print("🏭 다이캐스팅 품질 예측 모델 개발")
    print("=" * 50)
    
    # 1. 데이터 로딩 (예시 데이터 사용)
    # 실제 사용시: df = pd.read_csv('your_data.csv')
    df = create_sample_data()
    print(f"샘플 데이터 생성 완료: {df.shape}")
    
    # 2. 모델 인스턴스 생성
    predictor = DiecastingQualityPredictor()
    
    # 3. 데이터 전처리
    processed_df = predictor.load_and_preprocess_data(df=df)
    
    # 4. 모델 훈련
    model_scores = predictor.train_models()
    
    # 5. 개별 샘플 예측
    prediction_results = predictor.predict_individual_samples()
    
    # 6. 결과 요약 출력
    # predictor.print_prediction_summary(prediction_results)
    
    return predictor, prediction_results


if __name__ == "__main__":
    predictor, results = main()