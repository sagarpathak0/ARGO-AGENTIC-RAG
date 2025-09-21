-- ===============================================
-- COMPREHENSIVE DATABASE INDEXES AND CONSTRAINTS
-- High-performance indexes for Agentic RAG system
-- ===============================================

-- ===============================================
-- 1. USER MANAGEMENT INDEXES
-- ===============================================

-- Users table indexes
CREATE INDEX idx_users_email ON users (email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users (username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_api_key ON users (api_key) WHERE api_key IS NOT NULL;
CREATE INDEX idx_users_account_type ON users (account_type, is_active);
CREATE INDEX idx_users_created_at ON users (created_at);
CREATE INDEX idx_users_last_login ON users (last_login_at);

-- User tokens indexes
CREATE INDEX idx_user_tokens_user_id ON user_tokens (user_id, token_type);
CREATE INDEX idx_user_tokens_expires_cleanup ON user_tokens (expires_at) WHERE used_at IS NULL AND revoked_at IS NULL;
CREATE INDEX idx_user_tokens_hash ON user_tokens (token_hash);

-- User OTPs indexes
CREATE INDEX idx_user_otps_user_id ON user_otps (user_id, otp_type);
CREATE INDEX idx_user_otps_cleanup ON user_otps (expires_at) WHERE is_used = FALSE;
CREATE INDEX idx_user_otps_code_lookup ON user_otps (otp_code, otp_type) WHERE is_used = FALSE AND expires_at > NOW();

-- User sessions indexes
CREATE INDEX idx_user_sessions_user_id ON user_sessions (user_id, is_active);
CREATE INDEX idx_user_sessions_token ON user_sessions (session_token);
CREATE INDEX idx_user_sessions_cleanup ON user_sessions (expires_at) WHERE is_active = TRUE;
CREATE INDEX idx_user_sessions_activity ON user_sessions (last_activity_at);

-- ===============================================
-- 2. PROFILES TABLE INDEXES (OCEANOGRAPHIC DATA)
-- ===============================================

-- Primary performance indexes for RAG queries
CREATE INDEX idx_profiles_time_location ON profiles (time_coverage_start, latitude, longitude);
CREATE INDEX idx_profiles_year_month ON profiles (year, month);
CREATE INDEX idx_profiles_geom_time ON profiles USING GIST (geom, time_coverage_start);
CREATE INDEX idx_profiles_keywords_gin ON profiles USING GIN (keywords_tsvector);
CREATE INDEX idx_profiles_variables ON profiles USING GIN (variables_available);

-- Geographic and temporal indexes
CREATE INDEX idx_profiles_geom ON profiles USING GIST (geom);
CREATE INDEX idx_profiles_ocean_region ON profiles (ocean_basin, sea_region);
CREATE INDEX idx_profiles_lat_lon ON profiles (latitude, longitude);
CREATE INDEX idx_profiles_time_range ON profiles (time_coverage_start, time_coverage_end);

-- Data quality and processing indexes
CREATE INDEX idx_profiles_quality ON profiles (data_quality_score, completeness_score) WHERE data_quality_score IS NOT NULL;
CREATE INDEX idx_profiles_processing ON profiles (is_processed, is_indexed);
CREATE INDEX idx_profiles_institution ON profiles (institution) WHERE institution IS NOT NULL;
CREATE INDEX idx_profiles_data_source ON profiles (data_source) WHERE data_source IS NOT NULL;

-- Depth and measurement indexes
CREATE INDEX idx_profiles_depth ON profiles (depth_min, depth_max);
CREATE INDEX idx_profiles_depth_range ON profiles (depth_range) WHERE depth_range IS NOT NULL;
CREATE INDEX idx_profiles_measurement_count ON profiles (measurement_count) WHERE measurement_count IS NOT NULL;

-- File and access tracking
CREATE INDEX idx_profiles_file_path ON profiles (file_path);
CREATE INDEX idx_profiles_parquet_path ON profiles (parquet_path);
CREATE INDEX idx_profiles_access ON profiles (access_count, last_accessed_at);

-- Composite indexes for common query patterns
CREATE INDEX idx_profiles_region_time ON profiles (ocean_basin, year, month);
CREATE INDEX idx_profiles_quality_time ON profiles (data_quality_score, time_coverage_start) WHERE data_quality_score > 0.7;
CREATE INDEX idx_profiles_complete_data ON profiles (variables_available, completeness_score) WHERE is_processed = TRUE;

-- ===============================================
-- 3. VECTOR EMBEDDINGS INDEXES
-- ===============================================

-- Vector similarity indexes (pgvector)
CREATE INDEX idx_embeddings_vector_cosine ON profile_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_embeddings_vector_l2 ON profile_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
CREATE INDEX idx_embeddings_vector_ip ON profile_embeddings USING ivfflat (embedding vector_ip_ops) WITH (lists = 100);

-- Content and metadata indexes
CREATE INDEX idx_embeddings_profile_content ON profile_embeddings (profile_id, content_type);
CREATE INDEX idx_embeddings_content_type ON profile_embeddings (content_type, model_name);
CREATE INDEX idx_embeddings_content_hash ON profile_embeddings (content_hash);
CREATE INDEX idx_embeddings_quality ON profile_embeddings (embedding_quality_score) WHERE embedding_quality_score IS NOT NULL;
CREATE INDEX idx_embeddings_updated ON profile_embeddings (updated_at);

-- ===============================================
-- 4. MEASUREMENT SUMMARIES INDEXES
-- ===============================================

-- Variable and profile indexes
CREATE INDEX idx_measurement_summaries_profile_var ON measurement_summaries (profile_id, variable_name);
CREATE INDEX idx_measurement_summaries_variable ON measurement_summaries (variable_name, data_quality);
CREATE INDEX idx_measurement_summaries_quality ON measurement_summaries (data_quality, confidence_score);

-- Statistical analysis indexes
CREATE INDEX idx_measurement_summaries_stats ON measurement_summaries (variable_name, mean_value, std_value);
CREATE INDEX idx_measurement_summaries_depth_stats ON measurement_summaries (surface_value, deep_value) WHERE surface_value IS NOT NULL AND deep_value IS NOT NULL;
CREATE INDEX idx_measurement_summaries_anomaly ON measurement_summaries (is_anomalous, anomaly_score) WHERE is_anomalous = TRUE;

-- Count and validity indexes
CREATE INDEX idx_measurement_summaries_counts ON measurement_summaries (variable_name, valid_count, total_count);

-- ===============================================
-- 5. USER QUERIES INDEXES
-- ===============================================

-- User and session indexes
CREATE INDEX idx_user_queries_user_id ON user_queries (user_id, created_at DESC);
CREATE INDEX idx_user_queries_session ON user_queries (session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_user_queries_status ON user_queries (status, created_at);

-- Query analysis indexes
CREATE INDEX idx_user_queries_type ON user_queries (query_type, status);
CREATE INDEX idx_user_queries_hash ON user_queries (query_hash) WHERE query_hash IS NOT NULL;
CREATE INDEX idx_user_queries_parameters ON user_queries USING GIN (query_parameters);

-- Geographic and temporal query indexes
CREATE INDEX idx_user_queries_geo_bounds ON user_queries USING GIST (geographic_bounds) WHERE geographic_bounds IS NOT NULL;
CREATE INDEX idx_user_queries_time_range ON user_queries (time_range_start, time_range_end) WHERE time_range_start IS NOT NULL;
CREATE INDEX idx_user_queries_depth_range ON user_queries (depth_range_min, depth_range_max) WHERE depth_range_min IS NOT NULL;

-- Performance tracking indexes
CREATE INDEX idx_user_queries_performance ON user_queries (execution_time_ms, result_count) WHERE status = 'completed';
CREATE INDEX idx_user_queries_cache ON user_queries (cache_hit, execution_time_ms);

-- User interaction indexes
CREATE INDEX idx_user_queries_bookmarked ON user_queries (user_id, is_bookmarked) WHERE is_bookmarked = TRUE;
CREATE INDEX idx_user_queries_shared ON user_queries (is_shared, share_token) WHERE is_shared = TRUE;
CREATE INDEX idx_user_queries_rating ON user_queries (user_rating, query_type) WHERE user_rating IS NOT NULL;

-- Variables and results indexes
CREATE INDEX idx_user_queries_variables ON user_queries USING GIN (variables_requested) WHERE variables_requested IS NOT NULL;

-- ===============================================
-- 6. QUERY BOOKMARKS INDEXES
-- ===============================================

CREATE INDEX idx_query_bookmarks_user ON user_query_bookmarks (user_id, created_at DESC);
CREATE INDEX idx_query_bookmarks_query ON user_query_bookmarks (query_id);
CREATE INDEX idx_query_bookmarks_folder ON user_query_bookmarks (user_id, folder_name) WHERE folder_name IS NOT NULL;
CREATE INDEX idx_query_bookmarks_tags ON user_query_bookmarks USING GIN (tags) WHERE tags IS NOT NULL;
CREATE INDEX idx_query_bookmarks_private ON user_query_bookmarks (user_id, is_private);

-- ===============================================
-- 7. QUERY CACHE INDEXES
-- ===============================================

CREATE INDEX idx_query_cache_hash ON query_cache (query_hash);
CREATE INDEX idx_query_cache_key ON query_cache (cache_key);
CREATE INDEX idx_query_cache_expires ON query_cache (expires_at, is_valid);
CREATE INDEX idx_query_cache_performance ON query_cache (hit_count, last_hit_at);
CREATE INDEX idx_query_cache_cleanup ON query_cache (expires_at, is_valid) WHERE is_valid = TRUE;
CREATE INDEX idx_query_cache_size ON query_cache (data_size_bytes, execution_time_ms);

-- ===============================================
-- 8. SYSTEM MONITORING INDEXES
-- ===============================================

-- Analytics indexes
CREATE INDEX idx_system_analytics_time ON system_analytics (recorded_at DESC);
CREATE INDEX idx_system_analytics_hourly ON system_analytics (hour_bucket) WHERE hour_bucket IS NOT NULL;
CREATE INDEX idx_system_analytics_daily ON system_analytics (date_bucket) WHERE date_bucket IS NOT NULL;
CREATE INDEX idx_system_analytics_performance ON system_analytics (avg_response_time_ms, cache_hit_rate);

-- Audit log indexes
CREATE INDEX idx_audit_log_user ON audit_log (user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_audit_log_action ON audit_log (action, resource_type, created_at DESC);
CREATE INDEX idx_audit_log_resource ON audit_log (resource_type, resource_id) WHERE resource_id IS NOT NULL;
CREATE INDEX idx_audit_log_success ON audit_log (success, created_at) WHERE success = FALSE;
CREATE INDEX idx_audit_log_session ON audit_log (session_id) WHERE session_id IS NOT NULL;

-- ===============================================
-- 9. NOTIFICATIONS INDEXES
-- ===============================================

CREATE INDEX idx_notifications_user ON notifications (user_id, created_at DESC);
CREATE INDEX idx_notifications_unread ON notifications (user_id, is_read, created_at DESC) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_type ON notifications (type, created_at DESC);
CREATE INDEX idx_notifications_scheduled ON notifications (scheduled_for) WHERE scheduled_for IS NOT NULL AND sent_at IS NULL;
CREATE INDEX idx_notifications_cleanup ON notifications (expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_notifications_priority ON notifications (priority, created_at DESC) WHERE priority IN ('high', 'urgent');

-- ===============================================
-- 10. FOREIGN KEY CONSTRAINTS
-- ===============================================

-- Already defined in table creation, but ensuring referential integrity
-- Additional constraints for data consistency

-- User queries must have valid geographic bounds
ALTER TABLE user_queries ADD CONSTRAINT chk_valid_geographic_bounds 
    CHECK (geographic_bounds IS NULL OR ST_IsValid(geographic_bounds));

-- Time ranges must be logical
ALTER TABLE user_queries ADD CONSTRAINT chk_valid_time_range 
    CHECK (time_range_end IS NULL OR time_range_end >= time_range_start);

-- Depth ranges must be logical  
ALTER TABLE user_queries ADD CONSTRAINT chk_valid_depth_range 
    CHECK (depth_range_max IS NULL OR depth_range_max >= depth_range_min);

-- Profiles must have valid geometry
ALTER TABLE profiles ADD CONSTRAINT chk_valid_profile_geom 
    CHECK (ST_IsValid(geom) AND ST_GeometryType(geom) = 'ST_Point');

-- Cache expiration must be in future when created
ALTER TABLE query_cache ADD CONSTRAINT chk_cache_expiration 
    CHECK (expires_at > created_at);

-- OTP expiration must be in future when created
ALTER TABLE user_otps ADD CONSTRAINT chk_otp_expiration 
    CHECK (expires_at > created_at);

-- Session expiration must be in future when created
ALTER TABLE user_sessions ADD CONSTRAINT chk_session_expiration 
    CHECK (expires_at > created_at);

-- Token expiration must be in future when created
ALTER TABLE user_tokens ADD CONSTRAINT chk_token_expiration 
    CHECK (expires_at > created_at);

-- ===============================================
-- 11. PARTIAL INDEXES FOR OPTIMIZATION
-- ===============================================

-- Active users only
CREATE INDEX idx_users_active_email ON users (email) WHERE is_active = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_users_active_api ON users (api_key) WHERE is_active = TRUE AND api_key IS NOT NULL;

-- Recent queries for active users
CREATE INDEX idx_recent_user_queries ON user_queries (user_id, created_at DESC) 
    WHERE created_at > NOW() - INTERVAL '30 days' AND status = 'completed';

-- High-quality profiles
CREATE INDEX idx_high_quality_profiles ON profiles (time_coverage_start, geom) 
    WHERE data_quality_score > 0.8 AND is_processed = TRUE;

-- Unread notifications
CREATE INDEX idx_unread_notifications_recent ON notifications (user_id, created_at DESC) 
    WHERE is_read = FALSE AND created_at > NOW() - INTERVAL '7 days';

-- Active sessions
CREATE INDEX idx_active_sessions_recent ON user_sessions (user_id, last_activity_at DESC) 
    WHERE is_active = TRUE AND last_activity_at > NOW() - INTERVAL '24 hours';

-- Failed queries for analysis
CREATE INDEX idx_failed_queries_recent ON user_queries (query_type, created_at DESC, error_code) 
    WHERE status = 'failed' AND created_at > NOW() - INTERVAL '7 days';

-- ===============================================
-- 12. TRIGGERS FOR AUTOMATIC UPDATES
-- ===============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS UTF8
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
UTF8 language 'plpgsql';

-- Apply to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_embeddings_updated_at BEFORE UPDATE ON profile_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update profile access tracking
CREATE OR REPLACE FUNCTION update_profile_access()
RETURNS TRIGGER AS UTF8
BEGIN
    UPDATE profiles 
    SET access_count = access_count + 1,
        last_accessed_at = CURRENT_TIMESTAMP
    WHERE profile_id = ANY(NEW.profile_ids);
    RETURN NEW;
END;
UTF8 language 'plpgsql';

-- Trigger for query completion to update profile access
CREATE TRIGGER update_profile_access_on_query AFTER UPDATE ON user_queries
    FOR EACH ROW WHEN (NEW.status = 'completed' AND OLD.status != 'completed')
    EXECUTE FUNCTION update_profile_access();
