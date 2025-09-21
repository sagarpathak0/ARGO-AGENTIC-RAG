-- ===============================================
-- COMPREHENSIVE AGENTIC RAG DATABASE SCHEMA
-- Normalized design with user management and full RAG support
-- ===============================================

-- ===============================================
-- 1. USER MANAGEMENT TABLES
-- ===============================================

-- Users table (main user records)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- bcrypt/argon2 hash
    
    -- User profile
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(201) GENERATED ALWAYS AS (CONCAT(first_name, ' ', last_name)) STORED,
    avatar_url TEXT,
    bio TEXT,
    
    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    account_type VARCHAR(20) DEFAULT 'standard' CHECK (account_type IN ('standard', 'premium', 'admin', 'researcher')),
    
    -- Usage limits (for different tiers)
    daily_query_limit INTEGER DEFAULT 100,
    monthly_query_limit INTEGER DEFAULT 3000,
    max_concurrent_queries INTEGER DEFAULT 3,
    
    -- Preferences
    preferred_timezone VARCHAR(50) DEFAULT 'UTC',
    preferred_language VARCHAR(10) DEFAULT 'en',
    notification_settings JSONB DEFAULT '{}',
    ui_preferences JSONB DEFAULT '{}',
    
    -- Security
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip INET,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    -- API access
    api_key VARCHAR(64) UNIQUE,
    api_key_created_at TIMESTAMP WITH TIME ZONE,
    api_key_last_used TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE, -- soft delete
    
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_username CHECK (username ~* '^[a-zA-Z0-9_-]+$' AND LENGTH(username) >= 3)
);

-- User authentication tokens (JWT, refresh tokens, etc.)
CREATE TABLE user_tokens (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    token_type VARCHAR(20) NOT NULL CHECK (token_type IN ('refresh', 'reset_password', 'verify_email', 'api_session')),
    token_hash VARCHAR(255) NOT NULL,
    
    -- Token metadata
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    -- Security context
    created_ip INET,
    user_agent TEXT,
    device_fingerprint VARCHAR(255),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(token_hash)
);

-- OTP (One-Time Password) management
CREATE TABLE user_otps (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- OTP details
    otp_code VARCHAR(10) NOT NULL,
    otp_type VARCHAR(20) NOT NULL CHECK (otp_type IN ('email_verification', 'password_reset', 'login_2fa', 'phone_verification')),
    
    -- Delivery method
    delivery_method VARCHAR(10) NOT NULL CHECK (delivery_method IN ('email', 'sms')),
    delivery_address VARCHAR(255) NOT NULL, -- email or phone
    
    -- Status and security
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP WITH TIME ZONE,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    
    -- Timing
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_otp_length CHECK (LENGTH(otp_code) BETWEEN 4 AND 10)
);

-- User sessions (for tracking active sessions)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session details
    session_token VARCHAR(255) UNIQUE NOT NULL,
    device_info JSONB DEFAULT '{}',
    location_info JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Security
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================
-- 2. ENHANCED PROFILES TABLE (OCEANOGRAPHIC DATA)
-- ===============================================

CREATE TABLE profiles (
    -- Primary identification
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    float_id VARCHAR(50) NOT NULL,
    platform_number VARCHAR(50),
    cycle_number INTEGER,
    
    -- Temporal data (properly indexed)
    profile_time TIMESTAMP WITH TIME ZONE,
    time_coverage_start TIMESTAMP WITH TIME ZONE NOT NULL,
    time_coverage_end TIMESTAMP WITH TIME ZONE,
    year INTEGER GENERATED ALWAYS AS (EXTRACT(YEAR FROM time_coverage_start)) STORED,
    month INTEGER GENERATED ALWAYS AS (EXTRACT(MONTH FROM time_coverage_start)) STORED,
    day_of_year INTEGER GENERATED ALWAYS AS (EXTRACT(DOY FROM time_coverage_start)) STORED,
    
    -- Geospatial data (PostGIS optimized)
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    geom GEOMETRY(POINT, 4326) NOT NULL,
    
    -- Ocean region classification
    ocean_basin VARCHAR(20) CHECK (ocean_basin IN ('Atlantic', 'Pacific', 'Indian', 'Arctic', 'Southern')),
    sea_region VARCHAR(100), -- More specific region
    
    -- Depth information
    depth_min DOUBLE PRECISION CHECK (depth_min >= 0),
    depth_max DOUBLE PRECISION CHECK (depth_max >= depth_min),
    depth_range DOUBLE PRECISION GENERATED ALWAYS AS (depth_max - depth_min) STORED,
    pressure_range DOUBLE PRECISION,
    
    -- File references
    file_path TEXT NOT NULL,
    parquet_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    checksum VARCHAR(64), -- for data integrity
    
    -- Metadata for RAG
    institution TEXT,
    data_source TEXT,
    project_name TEXT,
    instrument_type TEXT,
    conventions TEXT,
    keywords TEXT,
    keywords_tsvector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', COALESCE(keywords, ''))) STORED,
    
    -- QC and attributes (enhanced JSONB)
    qc_summary JSONB DEFAULT '{}',
    attrs JSONB DEFAULT '{}',
    measurement_count INTEGER, -- number of depth measurements
    variables_available TEXT[], -- ['temp', 'psal', 'pres', 'oxy']
    
    -- Data quality metrics
    data_quality_score REAL CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    completeness_score REAL CHECK (completeness_score >= 0 AND completeness_score <= 1),
    qc_flags JSONB DEFAULT '{}',
    
    -- Processing status
    is_processed BOOLEAN DEFAULT FALSE,
    is_indexed BOOLEAN DEFAULT FALSE,
    processing_notes TEXT,
    processing_version VARCHAR(20),
    
    -- Usage tracking
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_coordinates CHECK (
        latitude IS NOT NULL AND longitude IS NOT NULL AND
        latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180
    ),
    CONSTRAINT valid_time_range CHECK (
        time_coverage_end IS NULL OR time_coverage_end >= time_coverage_start
    )
);

-- ===============================================
-- 3. VECTOR EMBEDDINGS TABLE
-- ===============================================
CREATE TABLE profile_embeddings (
    id SERIAL PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    
    -- Embedding types and content
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('metadata', 'keywords', 'institution', 'summary', 'location', 'temporal')),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL, -- for detecting changes
    
    -- Vector embeddings (pgvector)
    embedding VECTOR(1536), -- OpenAI ada-002 dimensions
    model_name VARCHAR(50) DEFAULT 'text-embedding-ada-002',
    model_version VARCHAR(20),
    
    -- Quality metrics
    embedding_quality_score REAL,
    similarity_threshold REAL DEFAULT 0.8,
    
    -- Processing metadata
    processing_time_ms INTEGER,
    token_count INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(profile_id, content_type)
);

-- ===============================================
-- 4. MEASUREMENT SUMMARIES TABLE
-- ===============================================
CREATE TABLE measurement_summaries (
    id SERIAL PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    
    -- Variable information
    variable_name VARCHAR(20) NOT NULL CHECK (variable_name IN ('temp', 'psal', 'pres', 'oxy', 'chla', 'ph', 'nitrate')),
    variable_units VARCHAR(20),
    
    -- Statistical summaries
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    mean_value DOUBLE PRECISION,
    median_value DOUBLE PRECISION,
    std_value DOUBLE PRECISION,
    variance_value DOUBLE PRECISION,
    
    -- Count statistics
    valid_count INTEGER,
    total_count INTEGER,
    missing_count INTEGER,
    outlier_count INTEGER,
    
    -- Depth-based stats
    surface_value DOUBLE PRECISION, -- value at shallowest depth
    deep_value DOUBLE PRECISION,    -- value at deepest depth
    max_gradient DOUBLE PRECISION,  -- maximum vertical gradient
    
    -- Depth layers (for oceanographic analysis)
    surface_layer_stats JSONB DEFAULT '{}',   -- 0-200m
    thermocline_stats JSONB DEFAULT '{}',     -- 200-1000m
    deep_layer_stats JSONB DEFAULT '{}',      -- >1000m
    
    -- QC information
    qc_flags JSONB DEFAULT '{}',
    data_quality VARCHAR(20) CHECK (data_quality IN ('excellent', 'good', 'acceptable', 'questionable', 'bad', 'missing')),
    confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Anomaly detection
    is_anomalous BOOLEAN DEFAULT FALSE,
    anomaly_score REAL,
    anomaly_reasons TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(profile_id, variable_name)
);

-- ===============================================
-- 5. USER QUERY MANAGEMENT
-- ===============================================

-- User queries (history and tracking)
CREATE TABLE user_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    
    -- Query details
    query_text TEXT NOT NULL,
    query_type VARCHAR(30) NOT NULL CHECK (query_type IN (
        'count', 'analysis', 'visualization', 'comparison', 'summary', 
        'statistical', 'temporal', 'spatial', 'quality_check', 'export'
    )),
    query_intent VARCHAR(100), -- parsed intent
    query_parameters JSONB DEFAULT '{}',
    query_hash VARCHAR(64) UNIQUE, -- for deduplication
    
    -- Geographic and temporal filters
    geographic_bounds GEOMETRY,
    time_range_start TIMESTAMP WITH TIME ZONE,
    time_range_end TIMESTAMP WITH TIME ZONE,
    depth_range_min DOUBLE PRECISION,
    depth_range_max DOUBLE PRECISION,
    variables_requested TEXT[],
    
    -- Execution details
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout')),
    execution_time_ms INTEGER,
    result_count INTEGER,
    profiles_analyzed INTEGER,
    data_volume_mb DOUBLE PRECISION,
    
    -- Results
    result_summary JSONB DEFAULT '{}',
    result_data_path TEXT, -- path to result files
    visualization_paths TEXT[], -- paths to generated charts
    
    -- Performance and optimization
    cache_hit BOOLEAN DEFAULT FALSE,
    optimization_notes TEXT,
    sql_query_used TEXT,
    
    -- User interaction
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    is_bookmarked BOOLEAN DEFAULT FALSE,
    is_shared BOOLEAN DEFAULT FALSE,
    share_token VARCHAR(64),
    
    -- System metadata
    api_version VARCHAR(10),
    client_info JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error handling
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER DEFAULT 0
);

-- User query favorites/bookmarks
CREATE TABLE user_query_bookmarks (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_id UUID NOT NULL REFERENCES user_queries(id) ON DELETE CASCADE,
    
    -- Bookmark details
    bookmark_name VARCHAR(255),
    bookmark_description TEXT,
    tags TEXT[],
    
    -- Organization
    folder_name VARCHAR(100),
    is_private BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, query_id)
);

-- ===============================================
-- 6. QUERY CACHE AND OPTIMIZATION
-- ===============================================

CREATE TABLE query_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    query_parameters JSONB DEFAULT '{}',
    
    -- Cache metadata
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_version VARCHAR(10) DEFAULT '1.0',
    
    -- Results
    result_count INTEGER,
    result_data JSONB,
    result_summary JSONB DEFAULT '{}',
    profile_ids UUID[],
    
    -- Performance tracking
    execution_time_ms INTEGER,
    data_size_bytes BIGINT,
    
    -- Cache management
    hit_count INTEGER DEFAULT 1,
    last_hit_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    
    -- Invalidation
    is_valid BOOLEAN DEFAULT TRUE,
    invalidated_at TIMESTAMP WITH TIME ZONE,
    invalidation_reason TEXT
);

-- ===============================================
-- 7. SYSTEM MONITORING AND AUDIT
-- ===============================================

-- System usage analytics
CREATE TABLE system_analytics (
    id SERIAL PRIMARY KEY,
    
    -- Time dimension
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    hour_bucket TIMESTAMP WITH TIME ZONE,
    date_bucket DATE,
    
    -- Usage metrics
    active_users_count INTEGER,
    total_queries_count INTEGER,
    successful_queries_count INTEGER,
    failed_queries_count INTEGER,
    
    -- Performance metrics
    avg_response_time_ms DOUBLE PRECISION,
    p95_response_time_ms DOUBLE PRECISION,
    cache_hit_rate DOUBLE PRECISION,
    
    -- Resource usage
    cpu_usage_percent DOUBLE PRECISION,
    memory_usage_mb DOUBLE PRECISION,
    disk_usage_gb DOUBLE PRECISION,
    
    -- Database metrics
    db_connections_active INTEGER,
    db_query_time_ms DOUBLE PRECISION,
    
    -- Error tracking
    error_rate DOUBLE PRECISION,
    error_breakdown JSONB DEFAULT '{}'
);

-- Audit log for important actions
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    
    -- Who and when
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    
    -- What happened
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255),
    
    -- Details
    old_values JSONB,
    new_values JSONB,
    changes_summary TEXT,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    api_endpoint TEXT,
    request_id UUID,
    
    -- Result
    success BOOLEAN,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================
-- 8. NOTIFICATION SYSTEM
-- ===============================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification content
    type VARCHAR(30) NOT NULL CHECK (type IN ('query_complete', 'system_alert', 'account', 'feature_update', 'maintenance')),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Rich content
    data JSONB DEFAULT '{}',
    action_url TEXT,
    action_text VARCHAR(100),
    
    -- Delivery
    delivery_method VARCHAR(20) CHECK (delivery_method IN ('in_app', 'email', 'sms', 'push')),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- Scheduling
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Priority and expiration
    priority VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
