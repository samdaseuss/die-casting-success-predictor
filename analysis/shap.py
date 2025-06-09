import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler, RobustScaler
from sklearn.compose import ColumnTransformer
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, recall_score, f1_score, roc_auc_score
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from scipy import stats
import optuna
from optuna.samplers import TPESampler
import shap
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 데이터 로드 및 기본 전처리
df = pd.read_csv('./data/train.csv')
df3 = df.copy()
df3 = df3.drop(columns=['id', 'mold_name', 'name', 'line',
                        'emergency_stop', 'count', 'tryshot_signal',
                        'upper_mold_temp3', 'lower_mold_temp3',
                        'time', 'date', 'heating_furnace'], errors='ignore')
# molten_volume는 제거하지 않음

df3 = df3[~df3['working'].isna()]
df3['registration_time'] = pd.to_datetime(df3['registration_time'], errors='coerce')
df3['EMS_operation_time'] = df3['EMS_operation_time'].astype('object')
df3['mold_code'] = df3['mold_code'].astype('object')

X = df3.drop('passorfail', axis=1)
y = df3['passorfail']

# 특성 분리
numeric_features = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()

print(f"Original dataset size: {len(X)}")
print(f"Class distribution: {y.value_counts().to_dict()}")


##################################
#     이상치 제거를 위한 특성 정의
########################################


def apply_zscore_outlier_removal(X, y, threshold=3):
    """Z-Score를 사용한 이상치 제거"""
    print("Applying Z-Score outlier detection...")
    X_numeric = X[numeric_features].fillna(X[numeric_features].median())
    z_scores = np.abs(stats.zscore(X_numeric, nan_policy='omit'))
    outliers = (z_scores > threshold).any(axis=1)
    
    outlier_count = np.sum(outliers)
    print(f"Detected {outlier_count} outliers ({outlier_count/len(X)*100:.2f}%)")
    
    X_clean = X[~outliers].reset_index(drop=True)
    y_clean = y[~outliers].reset_index(drop=True)
    
    print(f"Final dataset size: {len(X_clean)}")
    return X_clean, y_clean, outlier_count

def apply_preprocessing_outlier_removal(X, y):
    """전처리 기반 이상치 제거"""
    print("Applying preprocessing-based outlier removal...")
    # 원본 데이터에서 전처리 기반 이상치 제거 조건 적용
    mask = ~((X['molten_temp'] == 0) | 
             (X['low_section_speed'] >= 60000) | 
             (X['production_cycletime'] == 0) | 
             (X['upper_mold_temp1'] >= 1449) | 
             (X['sleeve_temperature'] >= 1449) | 
             (X['physical_strength'] >= 60000) | 
             (X['Coolant_temperature'] >= 1449) | 
             (X['upper_mold_temp2'] >= 4000) |
             (X['molten_volume'] >= 1449))  ### molten_volume는 제거하지 않음
    
    outlier_count = len(X) - np.sum(mask)
    print(f"Detected {outlier_count} outliers ({outlier_count/len(X)*100:.2f}%)")
    
    X_clean = X[mask].reset_index(drop=True)
    y_clean = y[mask].reset_index(drop=True)
    
    print(f"Final dataset size: {len(X_clean)}")
    return X_clean, y_clean, outlier_count

def create_preprocessor(use_robust_scaler=False):
    """전처리기 생성"""
    scaler = RobustScaler() if use_robust_scaler else StandardScaler()
    
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', scaler)
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    return ColumnTransformer(transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features)
    ])

###############################
#   SMOTE 파이프라인 생성
##################################
def create_smote_pipeline(model, use_robust_scaler=False, smote_k_neighbors=5):
    """SMOTE 파이프라인 생성"""
    preprocessor = create_preprocessor(use_robust_scaler)
    return ImbPipeline([
        ('preprocessor', preprocessor),
        ('smote', SMOTE(random_state=42, k_neighbors=smote_k_neighbors)),
        ('classifier', model)
    ])


def objective_xgb(trial, X_train, y_train):
    """XGBoost 최적화"""
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.05, 0.3),
        'n_estimators': trial.suggest_int('n_estimators', 100, 300),
        'subsample': trial.suggest_float('subsample', 0.7, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.7, 1.0),
        'random_state': 42,
        'eval_metric': 'logloss'
    }
    
    use_robust = trial.suggest_categorical('use_robust_scaler', [True, False])
    min_class_size = min(y_train.value_counts())
    max_k = min(10, min_class_size - 1) if min_class_size > 1 else 1
    k_neighbors = trial.suggest_int('smote_k_neighbors', 1, max(1, max_k))
    
    model = XGBClassifier(**params)
    pipeline = create_smote_pipeline(model, use_robust, k_neighbors)
    
    try:
        scores = cross_val_score(pipeline, X_train, y_train, cv=3, scoring='recall', n_jobs=-1)
        return scores.mean()
    except:
        return 0.0

def objective_lgb(trial, X_train, y_train):
    """LightGBM 최적화"""
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.05, 0.3),
        'n_estimators': trial.suggest_int('n_estimators', 100, 300),
        'num_leaves': trial.suggest_int('num_leaves', 20, 150),
        'subsample': trial.suggest_float('subsample', 0.7, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.7, 1.0),
        'random_state': 42,
        'verbose': -1
    }
    
    use_robust = trial.suggest_categorical('use_robust_scaler', [True, False])
    min_class_size = min(y_train.value_counts())
    max_k = min(10, min_class_size - 1) if min_class_size > 1 else 1
    k_neighbors = trial.suggest_int('smote_k_neighbors', 1, max(1, max_k))
    
    model = LGBMClassifier(**params)
    pipeline = create_smote_pipeline(model, use_robust, k_neighbors)
    
    try:
        scores = cross_val_score(pipeline, X_train, y_train, cv=3, scoring='recall', n_jobs=-1)
        return scores.mean()
    except:
        return 0.0


##################################
#     SHAP 분석 함수 추가
######################################
def analyze_feature_importance_with_shap(pipeline, X_sample, feature_names=None, model_name="Model"):
    """SHAP을 사용한 특성 중요도 분석"""
    print(f"\nAnalyzing feature importance for {model_name} using SHAP...")
    
    # 파이프라인에서 전처리된 데이터 추출
    X_transformed = pipeline.named_steps['preprocessor'].transform(X_sample)
    model = pipeline.named_steps['classifier']
    
    # 특성 이름 생성
    if feature_names is None:
        # Numeric features
        num_feature_names = numeric_features.copy()
        # Categorical features (One-hot encoded)
        cat_feature_names = []
        if categorical_features:
            cat_transformer = pipeline.named_steps['preprocessor'].named_transformers_['cat']
            encoder = cat_transformer.named_steps['encoder']
            cat_feature_names = encoder.get_feature_names_out(categorical_features).tolist()
        
        feature_names = num_feature_names + cat_feature_names
    
    try:
        # Try different explainer types based on availability
        explainer = None
        shap_values = None
        
        # Method 1: Try Tree explainer (for tree-based models)
        try:
            if hasattr(shap, 'TreeExplainer'):
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_transformed)
        except:
            pass
        
        # Method 2: Try Explainer (general purpose)
        if explainer is None:
            try:
                if hasattr(shap, 'Explainer'):
                    explainer = shap.Explainer(model, X_transformed[:100])  # Use sample as background
                    shap_values = explainer(X_transformed)
                    if hasattr(shap_values, 'values'):
                        shap_values = shap_values.values
            except:
                pass
        
        # Method 3: Use built-in feature importance as fallback
        if explainer is None or shap_values is None:
            print(f"SHAP analysis not available, using built-in feature importance for {model_name}")
            if hasattr(model, 'feature_importances_'):
                importance_scores = model.feature_importances_
                # Create fake SHAP values for visualization compatibility
                shap_values = np.tile(importance_scores, (X_transformed.shape[0], 1))
            else:
                return None
        
        # Handle binary classification output
        if isinstance(shap_values, list) and len(shap_values) == 2:
            shap_values = shap_values[1]  # Positive class
        elif len(shap_values.shape) == 3 and shap_values.shape[2] == 2:
            shap_values = shap_values[:, :, 1]  # Positive class
        
        return {
            'shap_values': shap_values,
            'feature_names': feature_names,
            'X_transformed': X_transformed,
            'explainer': explainer
        }
        
    except Exception as e:
        print(f"Error in SHAP analysis: {e}")
        # Fallback to feature importance
        try:
            if hasattr(model, 'feature_importances_'):
                importance_scores = model.feature_importances_
                shap_values = np.tile(importance_scores, (X_transformed.shape[0], 1))
                print(f"Using feature_importances_ as fallback for {model_name}")
                return {
                    'shap_values': shap_values,
                    'feature_names': feature_names,
                    'X_transformed': X_transformed,
                    'explainer': None
                }
        except:
            pass
        return None

def plot_shap_importance(shap_results, model_name, top_n=20):
    """SHAP 특성 중요도 시각화"""
    if shap_results is None:
        return
    
    shap_values = shap_results['shap_values']
    feature_names = shap_results['feature_names']
    X_transformed = shap_results['X_transformed']
    explainer = shap_results['explainer']
    
    plt.figure(figsize=(15, 12))
    
    # Calculate mean absolute SHAP values
    mean_shap = np.abs(shap_values).mean(0)
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': mean_shap
    }).sort_values('importance', ascending=False).head(top_n)
    
    # 1. Try SHAP summary plot (bar)
    plt.subplot(2, 2, 1)
    try:
        if explainer is not None:
            shap.summary_plot(shap_values, X_transformed, feature_names=feature_names, 
                             max_display=top_n, show=False, plot_type="bar")
            plt.title(f'{model_name} - SHAP Feature Importance')
        else:
            raise Exception("No explainer available")
    except:
        # Fallback to manual bar plot
        plt.barh(range(len(feature_importance)), feature_importance['importance'])
        plt.yticks(range(len(feature_importance)), feature_importance['feature'])
        plt.xlabel('Feature Importance')
        plt.title(f'{model_name} - Feature Importance (Bar)')
        plt.gca().invert_yaxis()
    
    # 2. Try SHAP summary plot (scatter)
    plt.subplot(2, 2, 2)
    try:
        if explainer is not None:
            shap.summary_plot(shap_values, X_transformed, feature_names=feature_names, 
                             max_display=top_n, show=False)
            plt.title(f'{model_name} - SHAP Summary Plot')
        else:
            raise Exception("No explainer available")
    except:
        # Fallback to correlation plot
        top_features_idx = feature_importance.head(15).index
        correlation_data = []
        for idx in top_features_idx:
            feature_idx = feature_names.index(feature_importance.loc[idx, 'feature'])
            correlation_data.append({
                'feature': feature_importance.loc[idx, 'feature'],
                'mean_value': X_transformed[:, feature_idx].mean(),
                'importance': feature_importance.loc[idx, 'importance']
            })
        
        corr_df = pd.DataFrame(correlation_data)
        plt.scatter(corr_df['mean_value'], corr_df['importance'], alpha=0.7)
        plt.xlabel('Mean Feature Value')
        plt.ylabel('Feature Importance')
        plt.title(f'{model_name} - Feature Value vs Importance')
        
        # Add labels for top features
        for i, row in corr_df.head(5).iterrows():
            plt.annotate(row['feature'][:15], (row['mean_value'], row['importance']), 
                        fontsize=8, alpha=0.7)
    
    # 3. Mean absolute SHAP values
    plt.subplot(2, 2, 3)
    plt.barh(range(len(feature_importance)), feature_importance['importance'])
    plt.yticks(range(len(feature_importance)), feature_importance['feature'])
    plt.xlabel('Mean |SHAP value|')
    plt.title(f'{model_name} - Top {top_n} Features by Mean |SHAP|')
    plt.gca().invert_yaxis()
    
    # 4. Feature importance comparison (if multiple models)
    plt.subplot(2, 2, 4)
    plt.text(0.5, 0.5, f'{model_name}\nTop Features:\n' + 
             '\n'.join([f"{row['feature']}: {row['importance']:.4f}" 
                       for _, row in feature_importance.head(10).iterrows()]),
             ha='center', va='center', transform=plt.gca().transAxes, fontsize=10)
    plt.axis('off')
    plt.title('Top 10 Features Summary')
    
    plt.tight_layout()
    plt.show()
    
    return feature_importance


##################################
#     모델 최적화 및 평가 함수 (SHAP 추가)
######################################
def optimize_and_evaluate(model_name, X_train, y_train, X_val, y_val, n_trials=15):
    """모델 최적화 및 평가 (SHAP 분석 포함)"""
    print(f"\nOptimizing {model_name}...")
    
    study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
    
    if model_name == 'XGBoost':
        study.optimize(lambda trial: objective_xgb(trial, X_train, y_train), n_trials=n_trials)
    else:  # LightGBM
        study.optimize(lambda trial: objective_lgb(trial, X_train, y_train), n_trials=n_trials)
    
    # 최적 모델로 평가
    best_params = study.best_params.copy()
    use_robust = best_params.pop('use_robust_scaler', False)
    k_neighbors = best_params.pop('smote_k_neighbors', 5)
    
    if model_name == 'XGBoost':
        model = XGBClassifier(**best_params)
    else:
        model = LGBMClassifier(**best_params)
    
    pipeline = create_smote_pipeline(model, use_robust, k_neighbors)
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_val)
    y_proba = pipeline.predict_proba(X_val)[:, 1]
    
    results = {
        'cv_recall': study.best_value,
        'accuracy': accuracy_score(y_val, y_pred),
        'recall': recall_score(y_val, y_pred),
        'f1_score': f1_score(y_val, y_pred),
        'auc': roc_auc_score(y_val, y_proba),
        'pipeline': pipeline  # 파이프라인 저장
    }
    
    print(f"CV Recall: {results['cv_recall']:.4f}")
    print(f"Val Recall: {results['recall']:.4f}")
    print(f"Val F1: {results['f1_score']:.4f}")
    print(f"Val AUC: {results['auc']:.4f}")
    
    # SHAP 분석 (샘플 데이터 사용)
    sample_size = min(1000, len(X_val))  # SHAP 계산 속도를 위해 샘플 사용
    X_sample = X_val.sample(n=sample_size, random_state=42)
    
    shap_results = analyze_feature_importance_with_shap(pipeline, X_sample, model_name=model_name)
    if shap_results:
        feature_importance = plot_shap_importance(shap_results, model_name)
        results['feature_importance'] = feature_importance
        results['shap_results'] = shap_results
    
    return results

# 메인 실행
print("Starting ML Pipeline with SHAP Analysis...")

# 3가지 이상치 처리 방법 비교
outlier_methods = {
    'none': None,
    'z_score': 'z_score',
    'preprocessing': 'preprocessing'
}

comparison_results = []
all_shap_results = {}  # SHAP 결과 저장

for method_name, method in outlier_methods.items():
    print(f"\n{'='*50}")
    print(f"Testing with {method_name.upper()} outlier detection")
    print(f"{'='*50}")
    
    # 이상치 처리
    if method_name == 'none':
        X_processed, y_processed, outlier_count = X, y, 0
    elif method_name == 'z_score':
        X_processed, y_processed, outlier_count = apply_zscore_outlier_removal(X, y)
    elif method_name == 'preprocessing':
        X_processed, y_processed, outlier_count = apply_preprocessing_outlier_removal(X, y)
    
    # 데이터 분리
    X_train, X_val, y_train, y_val = train_test_split(
        X_processed, y_processed, test_size=0.2, random_state=42, stratify=y_processed
    )
    
    print(f"Training set class distribution: {y_train.value_counts(normalize=True).round(3).to_dict()}")
    
    # 모델 최적화 및 평가
    for model_name in ['XGBoost', 'LightGBM']:
        try:
            results = optimize_and_evaluate(model_name, X_train, y_train, X_val, y_val)
            
            comparison_results.append({
                'Outlier_Method': method_name,
                'Model': model_name,
                'Data_Size': len(X_processed),
                'Outliers_Removed': outlier_count,
                'CV_Recall': results['cv_recall'],
                'Val_Recall': results['recall'],
                'Val_F1': results['f1_score'],
                'Val_AUC': results['auc'],
                'Val_Accuracy': results['accuracy']
            })
            
            # SHAP 결과 저장
            if 'shap_results' in results:
                all_shap_results[f"{method_name}_{model_name}"] = results['shap_results']
            
        except Exception as e:
            print(f"Error with {model_name}: {e}")
            continue

# 최종 결과 요약
print("\n" + "="*80)
print("FINAL COMPARISON RESULTS")
print("="*80)

results_df = pd.DataFrame(comparison_results)
if not results_df.empty:
    print(results_df.round(4))
    
    # 최고 성능 모델 찾기
    best_model_idx = results_df['Val_Recall'].idxmax()
    best_model = results_df.iloc[best_model_idx]
    
    print(f"\nBest Model Configuration:")
    print(f"Method: {best_model['Outlier_Method']}")
    print(f"Model: {best_model['Model']}")
    print(f"Validation Recall: {best_model['Val_Recall']:.4f}")
    print(f"Validation F1: {best_model['Val_F1']:.4f}")
    print(f"Validation AUC: {best_model['Val_AUC']:.4f}")

# SHAP 결과 종합 시각화
if all_shap_results:
    print("\n" + "="*50)
    print("FEATURE IMPORTANCE COMPARISON ACROSS ALL MODELS")
    print("="*50)
    
    # 모든 모델의 특성 중요도를 하나의 DataFrame으로 합치기
    importance_comparison = pd.DataFrame()
    
    for model_key, shap_result in all_shap_results.items():
        if shap_result:
            shap_values = shap_result['shap_values']
            feature_names = shap_result['feature_names']
            
            mean_shap = np.abs(shap_values).mean(0)
            temp_df = pd.DataFrame({
                'feature': feature_names,
                f'{model_key}_importance': mean_shap
            })
            
            if importance_comparison.empty:
                importance_comparison = temp_df
            else:
                importance_comparison = pd.merge(importance_comparison, temp_df, on='feature', how='outer')
    
    # 특성 중요도 비교 시각화
    if not importance_comparison.empty:
        importance_comparison = importance_comparison.fillna(0)
        
        # 평균 중요도 계산
        importance_cols = [col for col in importance_comparison.columns if col != 'feature']
        importance_comparison['mean_importance'] = importance_comparison[importance_cols].mean(axis=1)
        
        # 상위 15개 특성만 선택
        top_features = importance_comparison.nlargest(15, 'mean_importance')
        
        plt.figure(figsize=(15, 10))
        
        # 히트맵으로 모든 모델의 특성 중요도 비교
        plt.subplot(2, 1, 1)
        heatmap_data = top_features.set_index('feature')[importance_cols]
        sns.heatmap(heatmap_data.T, annot=True, fmt='.3f', cmap='viridis')
        plt.title('Feature Importance Comparison Across All Models (Top 15 Features)')
        plt.xlabel('Features')
        plt.ylabel('Models')
        
        # 평균 특성 중요도 바 차트
        plt.subplot(2, 1, 2)
        plt.barh(range(len(top_features)), top_features['mean_importance'])
        plt.yticks(range(len(top_features)), top_features['feature'])
        plt.xlabel('Mean Importance Score')
        plt.title('Average Feature Importance Across All Models')
        plt.gca().invert_yaxis()
        
        plt.tight_layout()
        plt.show()
        
        print("\nTop 10 Most Important Features (Average across all models):")
        for i, (_, row) in enumerate(top_features.head(10).iterrows(), 1):
            print(f"{i:2d}. {row['feature']}: {row['mean_importance']:.4f}")