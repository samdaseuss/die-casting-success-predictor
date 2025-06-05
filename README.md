# 🏭 제조 공정 예측 시스템
test
간단한 Streamlit 기반 제조 공정 데이터 입력 및 확인 시스템입니다.

## 🚀 실행 방법

### 로컬 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run streamlit_app.py
```

### Streamlit Cloud 배포
1. GitHub에 이 프로젝트를 푸시
2. [Streamlit Cloud](https://share.streamlit.io/)에 접속
3. GitHub 리포지토리 연결
4. `streamlit_app.py` 파일 선택
5. 배포 완료!

## 📊 기능

- **공정 파라미터 입력**: 16개의 제조 공정 파라미터 입력
- **실시간 데이터 확인**: 입력된 데이터를 실시간으로 확인
- **데이터 다운로드**: JSON 형태로 데이터 다운로드
- **통계 정보**: 입력 데이터의 기본 통계 정보 제공

## 🔧 파라미터 목록

1. **온도 파라미터**
   - 용융 온도 (molten_temp)
   - 상부 금형 온도 1-3 (upper_mold_temp1-3)
   - 하부 금형 온도 1-3 (lower_mold_temp1-3)
   - 슬리브 온도 (sleeve_temperature)
   - 냉각수 온도 (Coolant_temperature)

2. **공정 파라미터**
   - 생산 사이클 시간 (production_cycletime)
   - 저속/고속 구간 속도 (low/high_section_speed)
   - 주조 압력 (cast_pressure)
   - 비스킷 두께 (biscuit_thickness)
   - 물리적 강도 (physical_strength)
   - 품질 판정 (passorfail)

## 📁 프로젝트 구조
```
manufacturing-prediction-app/
├── streamlit_app.py      # 메인 애플리케이션
├── requirements.txt      # 의존성 패키지
├── README.md            # 프로젝트 문서
├── .gitignore          # Git 제외 파일
└── .streamlit/
    └── config.toml     # Streamlit 설정
```
