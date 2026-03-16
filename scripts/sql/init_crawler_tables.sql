-- NOTE:
-- 현재는 백엔드(Spring Boot)가 공용 DB 스키마를 생성/관리하므로
-- 크롤러 전용 init SQL 실행을 비활성화한다.
-- (향후 DB 분리 시, 그때 별도 마이그레이션으로 복구/재작성)

DO $$
BEGIN
    RAISE EXCEPTION
        'disabled script: scripts/sql/init_crawler_tables.sql (schema is managed by backend)';
END
$$;
