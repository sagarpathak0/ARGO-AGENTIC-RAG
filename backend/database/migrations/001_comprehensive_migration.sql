-- ===============================================
-- MIGRATION SCRIPT: Current Schema  Comprehensive Schema
-- Safe migration with data preservation
-- ===============================================

-- Set transaction isolation level
BEGIN;

-- ===============================================
-- STEP 1: CREATE NEW USER MANAGEMENT TABLES
-- ===============================================

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(201) GENERATED ALWAYS AS (CONCAT(first_name, ' ', last_name)) STORED,
    avatar_url TEXT,
    bio TEXT,
    
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    account_type VARCHAR(20) DEFAULT 'standard' CHECK (account_type IN ('standard', 'premium', 'admin', 'researcher')),
    
    daily_query_limit INTEGER DEFAULT 100,
    monthly_query_limit INTEGER DEFAULT 3000,
    max_concurrent_queries INTEGER DEFAULT 3,
    
    preferred_timezone VARCHAR(50) DEFAULT 'UTC',
    preferred_language VARCHAR(10) DEFAULT 'en',
    notification_settings JSONB DEFAULT '{}',
    ui_preferences JSONB DEFAULT '{}',
    
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip INET,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    api_key VARCHAR(64) UNIQUE,
    api_key_created_at TIMESTAMP WITH TIME ZONE,
    api_key_last_used TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_username CHECK (username ~* '^[a-zA-Z0-9_-]+$' AND LENGTH(username) >= 3)
);

-- Create supporting tables
CREATE TABLE user_tokens (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_type VARCHAR(20) NOT NULL CHECK (token_type IN ('refresh', 'reset_password', 'verify_email', 'api_session')),
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_ip INET,
    user_agent TEXT,
    device_fingerprint VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(token_hash)
);

CREATE TABLE user_otps (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_code VARCHAR(10) NOT NULL,
    otp_type VARCHAR(20) NOT NULL CHECK (otp_type IN ('email_verification', 'password_reset', 'login_2fa', 'phone_verification')),
    delivery_method VARCHAR(10) NOT NULL CHECK (delivery_method IN ('email', 'sms')),
    delivery_address VARCHAR(255) NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP WITH TIME ZONE,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_otp_length CHECK (LENGTH(otp_code) BETWEEN 4 AND 10)
);

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    device_info JSONB DEFAULT '{}',
    location_info JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================
-- STEP 2: BACKUP EXISTING PROFILES TABLE
-- ===============================================

-- Create backup of current profiles table
CREATE TABLE profiles_backup AS SELECT * FROM profiles;

-- ===============================================
-- STEP 3: RENAME CURRENT PROFILES TO PROFILES_OLD
-- ===============================================

ALTER TABLE profiles RENAME TO profiles_old;

-- ===============================================
-- STEP 4: CREATE NEW ENHANCED PROFILES TABLE
-- ===============================================

CREATE TABLE profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    float_id VARCHAR(50) NOT NULL,
    platform_number VARCHAR(50),
    cycle_number INTEGER,
    
    profile_time TIMESTAMP WITH TIME ZONE,
    time_coverage_start TIMESTAMP WITH TIME ZONE NOT NULL,
    time_coverage_end TIMESTAMP WITH TIME ZONE,
    year INTEGER GENERATED ALWAYS AS (EXTRACT(YEAR FROM time_coverage_start)) STORED,
    month INTEGER GENERATED ALWAYS AS (EXTRACT(MONTH FROM time_coverage_start)) STORED,
    day_of_year INTEGER GENERATED ALWAYS AS (EXTRACT(DOY FROM time_coverage_start)) STORED,
    
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    geom GEOMETRY(POINT, 4326) NOT NULL,
    
    ocean_basin VARCHAR(20) CHECK (ocean_basin IN ('Atlantic', 'Pacific', 'Indian', 'Arctic', 'Southern')),
    sea_region VARCHAR(100),
    
    depth_min DOUBLE PRECISION CHECK (depth_min >= 0),
    depth_max DOUBLE PRECISION CHECK (depth_max >= depth_min),
    depth_range DOUBLE PRECISION GENERATED ALWAYS AS (depth_max - depth_min) STORED,
    pressure_range DOUBLE PRECISION,
    
    file_path TEXT NOT NULL,
    parquet_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    checksum VARCHAR(64),
    
    institution TEXT,
    data_source TEXT,
    project_name TEXT,
    instrument_type TEXT,
    conventions TEXT,
    keywords TEXT,
    keywords_tsvector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', COALESCE(keywords, ''))) STORED,
    
    qc_summary JSONB DEFAULT '{}',
    attrs JSONB DEFAULT '{}',
    measurement_count INTEGER,
    variables_available TEXT[],
    
    data_quality_score REAL CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    completeness_score REAL CHECK (completeness_score >= 0 AND completeness_score <= 1),
    qc_flags JSONB DEFAULT '{}',
    
    is_processed BOOLEAN DEFAULT FALSE,
    is_indexed BOOLEAN DEFAULT FALSE,
    processing_notes TEXT,
    processing_version VARCHAR(20),
    
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_coordinates CHECK (
        latitude IS NOT NULL AND longitude IS NOT NULL AND
        latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180
    ),
    CONSTRAINT valid_time_range CHECK (
        time_coverage_end IS NULL OR time_coverage_end >= time_coverage_start
    )
);

-- ===============================================
-- STEP 5: MIGRATE DATA FROM OLD TO NEW PROFILES TABLE
-- ===============================================

INSERT INTO profiles (
    profile_id,
    float_id,
    platform_number,
    cycle_number,
    profile_time,
    time_coverage_start,
    time_coverage_end,
    latitude,
    longitude,
    geom,
    depth_min,
    depth_max,
    file_path,
    parquet_path,
    institution,
    data_source,
    conventions,
    keywords,
    qc_summary,
    attrs,
    created_at,
    
    -- Set default values for new fields
    ocean_basin,
    data_quality_score,
    is_processed,
    access_count
)
SELECT 
    profile_id::UUID,
    float_id,
    platform_number,
    cycle_number::INTEGER,
    profile_time::TIMESTAMP WITH TIME ZONE,
    time_coverage_start,
    time_coverage_end,
    latitude,
    longitude,
    geom,
    depth_min,
    depth_max,
    file_path,
    parquet_path,
    institution,
    data_source,
    conventions,
    keywords,
    qc_summary,
    attrs,
    COALESCE(created_at, CURRENT_TIMESTAMP),
    
    -- Determine ocean basin based on coordinates
    CASE 
        WHEN longitude BETWEEN 20 AND 147 AND latitude BETWEEN -66 AND 25 THEN 'Indian'
        WHEN longitude BETWEEN -180 AND -70 OR longitude BETWEEN 147 AND 180 THEN 'Pacific'
        WHEN longitude BETWEEN -70 AND 20 THEN 'Atlantic'
        WHEN latitude > 66 THEN 'Arctic'
        WHEN latitude < -60 THEN 'Southern'
        ELSE NULL
    END,
    
    -- Set default quality score
    0.8,
    
    -- Mark as processed if has parquet file
    CASE WHEN parquet_path IS NOT NULL THEN TRUE ELSE FALSE END,
    
    -- Initialize access count
    0
FROM profiles_old
WHERE latitude IS NOT NULL 
    AND longitude IS NOT NULL 
    AND time_coverage_start IS NOT NULL;

-- ===============================================
-- STEP 6: CREATE ADDITIONAL TABLES
-- ===============================================

-- Vector embeddings table
CREATE TABLE profile_embeddings (
    id SERIAL PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('metadata', 'keywords', 'institution', 'summary', 'location', 'temporal')),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding VECTOR(1536),
    model_name VARCHAR(50) DEFAULT 'text-embedding-ada-002',
    model_version VARCHAR(20),
    embedding_quality_score REAL,
    similarity_threshold REAL DEFAULT 0.8,
    processing_time_ms INTEGER,
    token_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, content_type)
);

-- Measurement summaries table
CREATE TABLE measurement_summaries (
    id SERIAL PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    variable_name VARCHAR(20) NOT NULL CHECK (variable_name IN ('temp', 'psal', 'pres', 'oxy', 'chla', 'ph', 'nitrate')),
    variable_units VARCHAR(20),
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    mean_value DOUBLE PRECISION,
    median_value DOUBLE PRECISION,
    std_value DOUBLE PRECISION,
    variance_value DOUBLE PRECISION,
    valid_count INTEGER,
    total_count INTEGER,
    missing_count INTEGER,
    outlier_count INTEGER,
    surface_value DOUBLE PRECISION,
    deep_value DOUBLE PRECISION,
    max_gradient DOUBLE PRECISION,
    surface_layer_stats JSONB DEFAULT '{}',
    thermocline_stats JSONB DEFAULT '{}',
    deep_layer_stats JSONB DEFAULT '{}',
    qc_flags JSONB DEFAULT '{}',
    data_quality VARCHAR(20) CHECK (data_quality IN ('excellent', 'good', 'acceptable', 'questionable', 'bad', 'missing')),
    confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    is_anomalous BOOLEAN DEFAULT FALSE,
    anomaly_score REAL,
    anomaly_reasons TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, variable_name)
);

-- User queries table
CREATE TABLE user_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    query_type VARCHAR(30) NOT NULL CHECK (query_type IN (
        'count', 'analysis', 'visualization', 'comparison', 'summary', 
        'statistical', 'temporal', 'spatial', 'quality_check', 'export'
    )),
    query_intent VARCHAR(100),
    query_parameters JSONB DEFAULT '{}',
    query_hash VARCHAR(64) UNIQUE,
    geographic_bounds GEOMETRY,
    time_range_start TIMESTAMP WITH TIME ZONE,
    time_range_end TIMESTAMP WITH TIME ZONE,
    depth_range_min DOUBLE PRECISION,
    depth_range_max DOUBLE PRECISION,
    variables_requested TEXT[],
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout')),
    execution_time_ms INTEGER,
    result_count INTEGER,
    profiles_analyzed INTEGER,
    data_volume_mb DOUBLE PRECISION,
    result_summary JSONB DEFAULT '{}',
    result_data_path TEXT,
    visualization_paths TEXT[],
    cache_hit BOOLEAN DEFAULT FALSE,
    optimization_notes TEXT,
    sql_query_used TEXT,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    is_bookmarked BOOLEAN DEFAULT FALSE,
    is_shared BOOLEAN DEFAULT FALSE,
    share_token VARCHAR(64),
    api_version VARCHAR(10),
    client_info JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER DEFAULT 0
);

-- Query bookmarks
CREATE TABLE user_query_bookmarks (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_id UUID NOT NULL REFERENCES user_queries(id) ON DELETE CASCADE,
    bookmark_name VARCHAR(255),
    bookmark_description TEXT,
    tags TEXT[],
    folder_name VARCHAR(100),
    is_private BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, query_id)
);

-- Query cache
CREATE TABLE query_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    query_parameters JSONB DEFAULT '{}',
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_version VARCHAR(10) DEFAULT '1.0',
    result_count INTEGER,
    result_data JSONB,
    result_summary JSONB DEFAULT '{}',
    profile_ids UUID[],
    execution_time_ms INTEGER,
    data_size_bytes BIGINT,
    hit_count INTEGER DEFAULT 1,
    last_hit_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    is_valid BOOLEAN DEFAULT TRUE,
    invalidated_at TIMESTAMP WITH TIME ZONE,
    invalidation_reason TEXT
);

-- System analytics
CREATE TABLE system_analytics (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    hour_bucket TIMESTAMP WITH TIME ZONE,
    date_bucket DATE,
    active_users_count INTEGER,
    total_queries_count INTEGER,
    successful_queries_count INTEGER,
    failed_queries_count INTEGER,
    avg_response_time_ms DOUBLE PRECISION,
    p95_response_time_ms DOUBLE PRECISION,
    cache_hit_rate DOUBLE PRECISION,
    cpu_usage_percent DOUBLE PRECISION,
    memory_usage_mb DOUBLE PRECISION,
    disk_usage_gb DOUBLE PRECISION,
    db_connections_active INTEGER,
    db_query_time_ms DOUBLE PRECISION,
    error_rate DOUBLE PRECISION,
    error_breakdown JSONB DEFAULT '{}'
);

-- Audit log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    changes_summary TEXT,
    ip_address INET,
    user_agent TEXT,
    api_endpoint TEXT,
    request_id UUID,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(30) NOT NULL CHECK (type IN ('query_complete', 'system_alert', 'account', 'feature_update', 'maintenance')),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    action_url TEXT,
    action_text VARCHAR(100),
    delivery_method VARCHAR(20) CHECK (delivery_method IN ('in_app', 'email', 'sms', 'push')),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    priority VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================
-- STEP 7: CREATE ESSENTIAL INDEXES
-- ===============================================

-- Users indexes
CREATE INDEX idx_users_email ON users (email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users (username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_api_key ON users (api_key) WHERE api_key IS NOT NULL;

-- Profiles indexes (essential for performance)
CREATE INDEX idx_profiles_time_location ON profiles (time_coverage_start, latitude, longitude);
CREATE INDEX idx_profiles_geom ON profiles USING GIST (geom);
CREATE INDEX idx_profiles_year_month ON profiles (year, month);
CREATE INDEX idx_profiles_keywords_gin ON profiles USING GIN (keywords_tsvector);

-- Vector embeddings indexes
CREATE INDEX idx_embeddings_profile_content ON profile_embeddings (profile_id, content_type);

-- User queries indexes
CREATE INDEX idx_user_queries_user_id ON user_queries (user_id, created_at DESC);
CREATE INDEX idx_user_queries_status ON user_queries (status, created_at);

-- ===============================================
-- STEP 8: VERIFICATION AND CLEANUP
-- ===============================================

-- Verify data migration
DO UTF8
DECLARE
    old_count INTEGER;
    new_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO old_count FROM profiles_old;
    SELECT COUNT(*) INTO new_count FROM profiles;
    
    RAISE NOTICE 'Migration verification:';
    RAISE NOTICE 'Old profiles count: %', old_count;
    RAISE NOTICE 'New profiles count: %', new_count;
    
    IF new_count < old_count * 0.95 THEN
        RAISE EXCEPTION 'Migration failed: too many records lost. Expected at least 95%% migration rate.';
    END IF;
    
    RAISE NOTICE 'Migration successful: %.2f%% of records migrated', (new_count::FLOAT / old_count * 100);
END UTF8;

-- Commit the transaction
COMMIT;

-- ===============================================
-- POST-MIGRATION NOTES
-- ===============================================
/*
1. The profiles_old table contains the original data as backup
2. The profiles_backup table contains a complete backup before migration
3. Run additional index creation from indexes_constraints.sql for full optimization
4. Consider dropping old tables after thorough testing:
   -- DROP TABLE profiles_old;
   -- DROP TABLE profiles_backup;
5. Create a default admin user for initial access
*/

-- Create default admin user (optional)
-- INSERT INTO users (email, username, password_hash, account_type, is_verified)
-- VALUES ('admin@oceandata.com', 'admin', '', 'admin', TRUE);
