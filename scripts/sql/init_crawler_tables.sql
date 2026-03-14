CREATE TABLE IF NOT EXISTS marathon_event (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    event_date DATE NOT NULL,
    region VARCHAR(50) NOT NULL,
    distances VARCHAR[] NOT NULL DEFAULT '{}'::VARCHAR[],
    reg_start_date TIMESTAMPTZ NOT NULL,
    reg_end_date TIMESTAMPTZ,
    is_major BOOLEAN NOT NULL DEFAULT FALSE,
    link_url TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    source_name VARCHAR(100),
    source_url TEXT,
    crawled_at_kst TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_marathon_event_dedup
    ON marathon_event (title, event_date, region, link_url);

CREATE INDEX IF NOT EXISTS idx_marathon_event_event_date
    ON marathon_event (event_date);

CREATE INDEX IF NOT EXISTS idx_marathon_event_status
    ON marathon_event (status);

CREATE TABLE IF NOT EXISTS raw_crawled_data (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    parsed_status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_crawled_data_source_created_at
    ON raw_crawled_data (source, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_crawled_data_parsed_status
    ON raw_crawled_data (parsed_status);

CREATE TABLE IF NOT EXISTS marathon_event_watch (
    id BIGSERIAL PRIMARY KEY,
    watch_key VARCHAR(255) NOT NULL UNIQUE,
    base_title VARCHAR(255) NOT NULL,
    sample_title VARCHAR(255) NOT NULL,
    last_event_date DATE NOT NULL,
    expected_event_date DATE NOT NULL,
    detected_event_date DATE,
    status VARCHAR(20) NOT NULL,
    source_name VARCHAR(100),
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marathon_event_watch_status
    ON marathon_event_watch (status);

CREATE INDEX IF NOT EXISTS idx_marathon_event_watch_expected_event_date
    ON marathon_event_watch (expected_event_date);

CREATE TABLE IF NOT EXISTS marathon_event_watch_seed (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    event_date DATE NOT NULL,
    source_name VARCHAR(100),
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_marathon_event_watch_seed_dedup
    ON marathon_event_watch_seed (title, event_date, COALESCE(source_name, ''), COALESCE(source_url, ''));
