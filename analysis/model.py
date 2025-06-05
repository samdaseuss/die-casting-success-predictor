from sklearn.base import BaseEstimator, TransformerMixin
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
from sklearn.metrics import recall_score, classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import matplotlib.pyplot as plt


class CustomCleaner(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        X = X.copy()
        X = X.drop(columns=['mold_name', 'name', 'line',
                            'emergency_stop', 'count', 'tryshot_signal',
                            'upper_mold_temp3', 'lower_mold_temp3',
                            'molten_volume', 'time', 'date', 'heating_furnace'],
                   errors='ignore')  # test셋에 없는 컬럼 있어도 대비
        X = X[~X['working'].isna()]
        X['registration_time'] = pd.to_datetime(X['registration_time'])
        X['EMS_operation_time'] = X['EMS_operation_time'].astype('object')
        X['mold_code'] = X['mold_code'].astype('object')
        X = X[~((X['molten_temp'] == 0) |
                (X['low_section_speed'] >= 60000) |
                (X['production_cycletime'] == 0) |
                (X['upper_mold_temp1'] >= 1449) |
                (X['sleeve_temperature'] >= 1449) |
                (X['physical_strength'] >= 60000) |
                (X['Coolant_temperature'] >= 1449) |
                (X['upper_mold_temp2'] >= 4000))]
        X['hour'] = X['registration_time'].dt.hour
        X = X.drop(columns=['registration_time']) 
        return X.reset_index(drop=True)
    

df = pd.read_csv('./data/train.csv')
X = df.drop(columns=['passorfail','id'])
y = df['passorfail']

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
cleaner = CustomCleaner()

train_set = X_train.copy()
train_set['passorfail'] = y_train
train_set_clean = cleaner.fit_transform(train_set)
y_train = train_set_clean['passorfail']
X_train = train_set_clean.drop(columns=['passorfail'])

val_set = X_val.copy()
val_set['passorfail'] = y_val
val_set_clean = cleaner.transform(val_set)
y_val = val_set_clean['passorfail']
X_val = val_set_clean.drop(columns=['passorfail'])


num_features = X_train.select_dtypes(include=['float64', 'int64']).columns.tolist()
cat_features = X_train.select_dtypes(include=['object']).columns.tolist()

numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])
categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('encoder', OneHotEncoder(handle_unknown='ignore'))
])
preprocessor = ColumnTransformer([
    ('num', numeric_transformer, num_features),
    ('cat', categorical_transformer, cat_features)
])


models = {
    'LogisticRegression': LogisticRegression(),
    'DecisionTree': DecisionTreeClassifier(),
    'RandomForest': RandomForestClassifier(),
    'XGBoost': XGBClassifier()
}
model_results = {}

for name, model in models.items():
    print(f"\n🔧 모델: {name}")
    
    pipeline = ImbPipeline([
        ('preprocessor', preprocessor),
        ('smote', SMOTE(random_state=42)),
        ('model', model)
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_val)

    recall = recall_score(y_val, y_pred)
    model_results[name] = {
        'recall_score': recall,
        'model': pipeline
    }

    print("📌 Params: default")
    print("📊 Classification Report:")
    print(classification_report(y_val, y_pred, digits=4))
    cm = confusion_matrix(y_val, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot(cmap='Blues')
    plt.title(f'Confusion Matrix: {name}')
    plt.show()

best_model_name = max(model_results, key=lambda name: model_results[name]['f1_score'])
final_model = model_results[best_model_name]['model']

#test로 정답지 확인
total = pd.read_csv('./data/casting.csv', encoding='cp949',index_col=0)
test = pd.read_csv('./data/test.csv')


X_test = cleaner.transform(test)
y_true = total.loc[X_test['id'], 'passorfail'].values
y_pred = final_model.predict(X_test)

print(confusion_matrix(y_true, y_pred))
print(classification_report(y_true, y_pred))


