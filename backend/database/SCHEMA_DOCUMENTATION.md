#  Comprehensive Agentic RAG Database Schema

## Overview
This is a fully normalized, production-ready database schema for the Agentic RAG system that handles ARGO oceanographic data with complete user management, authentication, query tracking, and optimization.

##  Schema Architecture

### **Database Normalization: 3NF (Third Normal Form)**
-  **No redundant data** across tables
-  **Proper foreign key relationships** 
-  **Atomic values** in all columns
-  **Functional dependencies** properly managed

---

##  **Table Structure (8 Core Domains)**

### **1. USER MANAGEMENT DOMAIN**

#### **users** - Main user accounts
`sql
Key Fields: id (UUID), email, username, password_hash
Features: Account types (standard/premium/admin/researcher), usage limits, preferences
Security: Failed login tracking, account locking, API key management
Soft delete: deleted_at for data retention
`

#### **user_tokens** - Authentication tokens
`sql
Purpose: JWT refresh tokens, password reset tokens, email verification
Security: Token hashing, expiration, revocation tracking
Metadata: IP tracking, user agent, device fingerprinting
`

#### **user_otps** - One-time passwords
`sql
Types: Email verification, password reset, 2FA, phone verification
Delivery: Email or SMS with attempt limiting
Security: Auto-expiration, attempt counting, usage tracking
`

#### **user_sessions** - Active user sessions  
`sql
Tracking: Device info, location, activity timestamps
Security: Session tokens, IP validation, automatic expiration
Management: Multiple concurrent sessions per user
`

---

### **2. OCEANOGRAPHIC DATA DOMAIN**

#### **profiles** - Enhanced ARGO profile metadata
`sql
Identification: UUID primary key, float_id, platform_number, cycle
Temporal: Proper timezone handling, generated year/month columns
Geospatial: PostGIS geometry, ocean basin classification
Data Quality: Quality scores, completeness metrics, QC flags
Processing: Status tracking, version control, access counts
Search: Full-text search on keywords, variable availability tracking
`

#### **profile_embeddings** - Vector embeddings for semantic search
`sql
Content Types: metadata, keywords, institution, summary, location, temporal
Vectors: pgvector support (1536 dimensions for OpenAI ada-002)
Quality: Embedding quality scores, similarity thresholds
Versioning: Model name/version tracking for embedding updates
`

#### **measurement_summaries** - Pre-computed statistics
`sql
Variables: temp, psal, pres, oxy, chla, ph, nitrate
Statistics: min/max/mean/median/std/variance for fast queries
Depth Analysis: Surface/deep values, layer-based statistics
Quality Control: QC flags, confidence scores, anomaly detection
Performance: Eliminates need to read parquet files for basic stats
`

---

### **3. QUERY MANAGEMENT DOMAIN**

#### **user_queries** - Complete query lifecycle tracking
`sql
Query Details: Full text, parsed intent, parameters, hash for deduplication
Execution: Status tracking, performance metrics, result summaries
Geographic: Spatial bounds, temporal ranges, depth filters
Results: File paths, visualization links, data volume tracking
User Interaction: Ratings, feedback, bookmarking, sharing
Optimization: Cache hit tracking, SQL query logging
`

#### **user_query_bookmarks** - User query organization
`sql
Organization: Named bookmarks, descriptions, tags, folders
Privacy: Public/private sharing options
User Experience: Quick access to frequently used queries
`

#### **query_cache** - Intelligent caching system
`sql
Performance: Query result caching with TTL management
Metrics: Hit counting, performance tracking, size monitoring
Invalidation: Automatic expiration, manual invalidation support
Optimization: Reduces database load for common queries
`

---

### **4. SYSTEM MONITORING DOMAIN**

#### **system_analytics** - Performance and usage metrics
`sql
Time Series: Hourly/daily buckets for trend analysis
Usage: Active users, query counts, success rates
Performance: Response times, cache hit rates, resource usage
Database: Connection tracking, query performance
Error Tracking: Error rates with detailed breakdowns
`

#### **udit_log** - Comprehensive action tracking
`sql
Security: User action logging, resource access tracking
Changes: Before/after values for data modifications
Context: IP addresses, user agents, API endpoints
Compliance: Full audit trail for regulatory requirements
`

#### **
otifications** - User notification system
`sql
Types: Query completion, system alerts, account notifications
Delivery: In-app, email, SMS, push notifications
Management: Read status, scheduling, expiration
Priority: Low/normal/high/urgent priority levels
`

---

##  **Key Features & Benefits**

### **1. User Management**
-  **Complete authentication** (password + 2FA + API keys)
-  **Account tiers** (standard/premium/admin/researcher)
-  **Usage limits** and quota management
-  **Session management** with device tracking
-  **Security features** (login attempts, account locking)

### **2. Advanced Search Capabilities**
-  **Vector similarity search** using pgvector
-  **Full-text search** on keywords and metadata
-  **Geospatial queries** with PostGIS
-  **Temporal filtering** with optimized indexes
-  **Multi-dimensional filtering** (depth, quality, variables)

### **3. Performance Optimization**
-  **Pre-computed statistics** eliminate parquet file reads
-  **Intelligent caching** reduces repeated computations
-  **Optimized indexes** for all common query patterns
-  **Generated columns** for fast temporal filtering
-  **Partial indexes** for specific use cases

### **4. Data Quality & Governance**
-  **Quality scoring** for profiles and embeddings
-  **Anomaly detection** and flagging
-  **Data lineage** tracking through processing versions
-  **Access tracking** for usage analytics
-  **Audit logging** for compliance

### **5. RAG System Support**
-  **Query intent classification** and parameter extraction
-  **Result provenance** with profile IDs and confidence
-  **Query optimization** tracking and learning
-  **User feedback** integration for system improvement
-  **Visualization support** with chart generation tracking

---

##  **Performance Features**

### **Indexing Strategy**
- **Composite indexes** for common query patterns
- **Partial indexes** for filtered queries  
- **GIN indexes** for array and JSONB operations
- **GIST indexes** for geospatial operations
- **Vector indexes** for similarity search

### **Generated Columns**
- **year/month** extraction for fast temporal filtering
- **depth_range** calculation for quick depth queries
- **full_name** concatenation for user display
- **keywords_tsvector** for optimized text search

### **Automatic Triggers**
- **updated_at** timestamp maintenance
- **Profile access** tracking on query completion
- **Data validation** and constraint enforcement

---

##  **Implementation Plan**

### **Phase 1: Migration** 
1. Backup existing data
2. Create new schema structure
3. Migrate current profiles data
4. Apply essential indexes
5. Verify data integrity

### **Phase 2: User System**
1. Implement user authentication
2. Create default admin user
3. Set up session management
4. Configure OTP system

### **Phase 3: Vector Embeddings**
1. Generate embeddings for existing profiles
2. Set up similarity search
3. Create embedding update pipeline

### **Phase 4: Query System**
1. Implement query tracking
2. Set up caching system
3. Create analytics pipeline

### **Phase 5: Full Optimization**
1. Apply all performance indexes
2. Set up monitoring
3. Implement notification system

---

##  **Security Features**

- **Password hashing** with bcrypt/argon2
- **API key management** with usage tracking
- **Session security** with device fingerprinting
- **Rate limiting** through user quotas
- **Audit logging** for all actions
- **Data validation** with constraints
- **Soft deletes** for data retention
- **Input sanitization** built into schema

---

##  **Scalability Considerations**

- **Partitioning ready** for large datasets
- **Index optimization** for billion+ records  
- **Caching layers** for performance
- **Async processing** support
- **Horizontal scaling** compatible
- **Read replicas** support
- **Connection pooling** ready

This schema provides a solid foundation for a production-grade Agentic RAG system with comprehensive user management, security, performance optimization, and monitoring capabilities.
