-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 기본 데이터베이스 설정
\c diecasting_db;

-- 테이블은 애플리케이션에서 생성하므로 여기서는 확장만 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb;