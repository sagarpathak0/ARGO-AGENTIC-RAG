-- User Authentication Schema
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255),
    user_tier VARCHAR(50) DEFAULT 'standard' CHECK (user_tier IN ('standard', 'premium', 'admin', 'researcher')),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    google_id VARCHAR(255) UNIQUE,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    daily_query_count INTEGER DEFAULT 0,
    total_queries INTEGER DEFAULT 0,
    last_query_reset DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    key_name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    permissions TEXT[],
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 1000,
    last_used TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, key_name)
);

CREATE TABLE IF NOT EXISTS otp_tokens (
    token_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    otp_code VARCHAR(10) NOT NULL,
    token_type VARCHAR(50) NOT NULL CHECK (token_type IN ('email_verification', 'password_reset', 'login_2fa')),
    is_used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    attempts INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    jti VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_hash VARCHAR(255),
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS user_tier_limits (
    tier VARCHAR(50) PRIMARY KEY,
    queries_per_day INTEGER NOT NULL,
    queries_per_hour INTEGER NOT NULL,
    queries_per_minute INTEGER NOT NULL,
    max_api_keys INTEGER NOT NULL,
    features TEXT[] NOT NULL
);

INSERT INTO user_tier_limits (tier, queries_per_day, queries_per_hour, queries_per_minute, max_api_keys, features)
VALUES 
    ('standard', 100, 20, 5, 1, ARRAY['basic_search', 'basic_rag']),
    ('premium', 1000, 100, 15, 3, ARRAY['basic_search', 'basic_rag', 'advanced_search', 'export_data']),
    ('researcher', 5000, 500, 30, 5, ARRAY['basic_search', 'basic_rag', 'advanced_search', 'export_data', 'bulk_access', 'analytics']),
    ('admin', -1, -1, -1, -1, ARRAY['all_features'])
ON CONFLICT (tier) DO NOTHING;
