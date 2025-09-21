# ultra_fast_ingest_enhanced.py
"""
ENHANCED ULTRA-FAST bulk ingestion for ARGO .nc files with new schema support.
Compatible with the comprehensive agentic RAG database schema.
Target: 214,400 files in 15-30 minutes = ~120-480 files/second
Enhancements:
- Support for new schema columns (quality_score, access_count, year, month, etc.)
- Backward compatibility with existing data
- Enhanced metadata extraction
- Processing version tracking
"""
import os
import glob
import uuid
import json
from pathlib import Path
import argparse
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
from functools import partial
from datetime import datetime

import xarray as xr
import pandas as pd
from tqdm import tqdm
import numpy as np

# Optional: PostgreSQL insertion
try:
    from sqlalchemy import create_engine, text
    HAS_SQLALCHEMY = True
except Exception:
    create_engine = None
    HAS_SQLALCHEMY = False

# -------- CONFIG --------
DEFAULT_BASE_DIR = r"C:\Users\sagar\OneDrive\desktop\AGRODATA\gadr\data\indian"
OUT_ROOT = Path(DEFAULT_BASE_DIR).parent / "processed_profiles"
METADATA_CSV = OUT_ROOT / "profiles_metadata.csv"
PARQUET_DIR = OUT_ROOT / "parquet"
LOG_FILE = OUT_ROOT / "ingest.log"
PG_URL = "postgresql://avnadmin:AVNS_T7GmZnlliHeBAIDQB0r@pg-rabbitanimated-postgres-animate28.i.aivencloud.com:13249/AlgoForge?sslmode=require"

# Enhanced settings
MAX_WORKERS = min(16, mp.cpu_count())
CHUNK_SIZE = 500
SAVE_INTERVAL = 2000
CHECKPOINT_INTERVAL = 5000
PROCESSING_VERSION = "2.0.0"  # Track processing version

def setup_logging(log_path):
    """Setup logging with INFO level for speed"""
    os.makedirs(log_path.parent, exist_ok=True)
    logging.basicConfig(
        filename=str(log_path), filemode="a",
        format="%(asctime)s %(levelname)s: %(message)s",
        level=logging.INFO
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

def create_profiles_table_enhanced(engine):
    """Create the enhanced profiles table matching our new comprehensive schema."""
    enable_extensions_sql = text("""
        CREATE EXTENSION IF NOT EXISTS postgis;
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
    """)
    
    create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS profiles (
            -- Primary identification
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            profile_id TEXT UNIQUE NOT NULL,
            float_id TEXT,
            platform_number TEXT,
            cycle_number NUMERIC,
            
            -- Temporal information
            profile_time TEXT,
            time_coverage_start TIMESTAMP,
            time_coverage_end TIMESTAMP,
            year INTEGER GENERATED ALWAYS AS (EXTRACT(YEAR FROM time_coverage_start)) STORED,
            month INTEGER GENERATED ALWAYS AS (EXTRACT(MONTH FROM time_coverage_start)) STORED,
            
            -- Geospatial information
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            geom GEOMETRY(POINT, 4326),
            ocean_basin TEXT,
            
            -- Data sources and paths
            file_path TEXT,
            parquet_path TEXT,
            institution TEXT,
            data_source TEXT,
            
            -- Metadata and attributes
            qc_summary JSONB DEFAULT '{}',
            attrs JSONB DEFAULT '{}',
            conventions TEXT,
            keywords TEXT,
            keywords_tsvector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', COALESCE(keywords, ''))) STORED,
            
            -- Data characteristics
            depth_min DOUBLE PRECISION,
            depth_max DOUBLE PRECISION,
            depth_range TEXT GENERATED ALWAYS AS (
                CASE 
                    WHEN depth_max IS NULL OR depth_min IS NULL THEN 'unknown'
                    WHEN depth_max <= 100 THEN 'surface'
                    WHEN depth_max <= 1000 THEN 'intermediate'
                    ELSE 'deep'
                END
            ) STORED,
            
            -- Available variables (for quick filtering)
            has_temperature BOOLEAN DEFAULT FALSE,
            has_salinity BOOLEAN DEFAULT FALSE,
            has_pressure BOOLEAN DEFAULT FALSE,
            has_oxygen BOOLEAN DEFAULT FALSE,
            has_chlorophyll BOOLEAN DEFAULT FALSE,
            has_ph BOOLEAN DEFAULT FALSE,
            has_nitrate BOOLEAN DEFAULT FALSE,
            variable_count INTEGER DEFAULT 0,
            
            -- Quality and processing
            quality_score DOUBLE PRECISION DEFAULT 0.5,
            completeness_score DOUBLE PRECISION DEFAULT 0.0,
            qc_flag TEXT DEFAULT 'unknown',
            processing_status TEXT DEFAULT 'raw',
            processing_version TEXT DEFAULT '1.0.0',
            anomaly_flags TEXT[] DEFAULT '{}',
            
            -- Usage tracking
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            popularity_score DOUBLE PRECISION DEFAULT 0.0,
            
            -- Audit fields
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            CONSTRAINT valid_coordinates CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180),
            CONSTRAINT valid_quality_score CHECK (quality_score BETWEEN 0 AND 1),
            CONSTRAINT valid_completeness CHECK (completeness_score BETWEEN 0 AND 1)
        );
        
        -- Essential indexes for performance
        CREATE INDEX IF NOT EXISTS idx_profiles_profile_id ON profiles (profile_id);
        CREATE INDEX IF NOT EXISTS idx_profiles_float_id ON profiles (float_id);
        CREATE INDEX IF NOT EXISTS idx_profiles_platform ON profiles (platform_number);
        CREATE INDEX IF NOT EXISTS idx_profiles_year_month ON profiles (year, month);
        CREATE INDEX IF NOT EXISTS idx_profiles_lat_lon ON profiles (latitude, longitude);
        CREATE INDEX IF NOT EXISTS idx_profiles_geom ON profiles USING GIST (geom);
        CREATE INDEX IF NOT EXISTS idx_profiles_depth_range ON profiles (depth_range);
        CREATE INDEX IF NOT EXISTS idx_profiles_institution ON profiles (institution);
        CREATE INDEX IF NOT EXISTS idx_profiles_keywords_tsvector ON profiles USING GIN (keywords_tsvector);
        CREATE INDEX IF NOT EXISTS idx_profiles_quality_score ON profiles (quality_score DESC);
        CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles (created_at);
        
        -- Partial indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_profiles_high_quality ON profiles (quality_score, created_at) 
            WHERE quality_score > 0.7;
        CREATE INDEX IF NOT EXISTS idx_profiles_recent ON profiles (created_at) 
            WHERE created_at > CURRENT_DATE - INTERVAL '30 days';
        CREATE INDEX IF NOT EXISTS idx_profiles_has_temp ON profiles (float_id, year) 
            WHERE has_temperature = TRUE;
            
        -- Trigger for updated_at
        CREATE OR REPLACE FUNCTION update_profiles_updated_at()
        RETURNS TRIGGER AS helpers\extractor\test_ultra_fast_enhanced.py 
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        helpers\extractor\test_ultra_fast_enhanced.py LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS trigger_profiles_updated_at ON profiles;
        CREATE TRIGGER trigger_profiles_updated_at
            BEFORE UPDATE ON profiles
            FOR EACH ROW
            EXECUTE FUNCTION update_profiles_updated_at();
    """)
    
    try:
        with engine.begin() as conn:
            conn.execute(enable_extensions_sql)
            conn.execute(create_table_sql)
        logging.info("Enhanced profiles table created/verified successfully")
    except Exception as e:
        logging.error("Failed to create enhanced profiles table: %s", e)
        raise

def calculate_data_quality_score(measurements_data):
    """Calculate a quality score based on data completeness and validity."""
    total_points = 0
    valid_points = 0
    
    for var_name, values in measurements_data.items():
        if var_name == 'level':
            continue
        
        total_points += len(values)
        valid_points += sum(1 for v in values if v is not None and v != '' and not (isinstance(v, float) and np.isnan(v)) and not (isinstance(v, str) and v.replace('.', '').replace('-', '').isdigit() and np.isnan(float(v))))
    
    if total_points == 0:
        return 0.0
    
    completeness = valid_points / total_points
    # Simple quality score based on completeness
    # In production, this could include additional checks
    return min(1.0, completeness * 1.2)  # Slight boost for good data

def detect_available_variables(measurements_data):
    """Detect which oceanographic variables are available in the data."""
    variables = {
        'has_temperature': False,
        'has_salinity': False, 
        'has_pressure': False,
        'has_oxygen': False,
        'has_chlorophyll': False,
        'has_ph': False,
        'has_nitrate': False
    }
    
    var_mapping = {
        'temp': 'has_temperature',
        'psal': 'has_salinity',
        'pres': 'has_pressure',
        'oxy': 'has_oxygen',
        'chla': 'has_chlorophyll',
        'ph': 'has_ph',
        'nitrate': 'has_nitrate'
    }
    
    variable_count = 0
    for var_name in measurements_data.keys():
        if var_name.lower() in var_mapping:
            # Check if variable has valid data
            values = measurements_data[var_name]
            if any(v is not None and str(v) != '' and not (isinstance(v, float) and np.isnan(v)) for v in values):
                variables[var_mapping[var_name.lower()]] = True
                variable_count += 1
    
    variables['variable_count'] = variable_count
    return variables

def determine_ocean_basin(lat, lon):
    """Simple ocean basin classification based on coordinates."""
    if lat is None or lon is None:
        return 'unknown'
    
    # Simplified basin classification for Indian Ocean focus
    if 20 <= lon <= 120 and -60 <= lat <= 30:
        return 'indian'
    elif -80 <= lon <= 20 and -60 <= lat <= 70:
        return 'atlantic'
    elif 120 <= lon <= 180 or -180 <= lon <= -80:
        if lat >= 0:
            return 'north_pacific'
        else:
            return 'south_pacific'
    elif lat >= 60:
        return 'arctic'
    elif lat <= -60:
        return 'southern'
    else:
        return 'other'

def bulk_postgres_insert_enhanced(rows, pg_url):
    """Enhanced bulk insert with new schema columns."""
    if not (HAS_SQLALCHEMY and create_engine and pg_url):
        return
    try:
        engine = create_engine(pg_url, pool_pre_ping=True)
        create_profiles_table_enhanced(engine)
        insert_data = []
        
        for row in rows:
            if "error" in row:
                continue
                
            # Calculate quality metrics
            quality_score = row.get('quality_score', 0.5)
            completeness_score = row.get('completeness_score', 0.0)
            
            # Prepare enhanced data
            insert_data.append({
                "profile_id": row.get("profile_id"),
                "float_id": row.get("float_id"),
                "platform_number": row.get("platform_number"),
                "cycle_number": row.get("cycle_number"),
                "profile_time": row.get("profile_time"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "ocean_basin": row.get("ocean_basin", "unknown"),
                "file_path": row.get("file_path"),
                "parquet_path": row.get("parquet_path"),
                "qc_summary": row.get("qc_summary"),
                "attrs": row.get("attrs"),
                "institution": row.get("institution", ""),
                "data_source": row.get("data_source", ""),
                "depth_min": row.get("depth_min"),
                "depth_max": row.get("depth_max"),
                "time_coverage_start": row.get("time_coverage_start"),
                "time_coverage_end": row.get("time_coverage_end"),
                "conventions": row.get("conventions", ""),
                "keywords": row.get("keywords", ""),
                
                # Enhanced fields
                "has_temperature": row.get("has_temperature", False),
                "has_salinity": row.get("has_salinity", False),
                "has_pressure": row.get("has_pressure", False),
                "has_oxygen": row.get("has_oxygen", False),
                "has_chlorophyll": row.get("has_chlorophyll", False),
                "has_ph": row.get("has_ph", False),
                "has_nitrate": row.get("has_nitrate", False),
                "variable_count": row.get("variable_count", 0),
                
                "quality_score": quality_score,
                "completeness_score": completeness_score,
                "qc_flag": row.get("qc_flag", "unknown"),
                "processing_status": "processed",
                "processing_version": PROCESSING_VERSION,
                "anomaly_flags": row.get("anomaly_flags", []),
            })
            
        if insert_data:
            df = pd.DataFrame(insert_data)
            
            # Normalize time fields
            for col in ["time_coverage_start", "time_coverage_end"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Insert data
            df.to_sql('profiles', engine, if_exists='append', index=False, method='multi')
            
            # Update geometry for new rows
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE profiles
                        SET geom = CASE
                          WHEN latitude IS NOT NULL AND longitude IS NOT NULL 
                          THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
                          ELSE geom
                        END
                        WHERE geom IS NULL;
                    """))
            except Exception as e:
                logging.warning("Failed to backfill geom: %s", e)
                
            logging.info("Enhanced bulk inserted %d profiles to Postgres", len(insert_data))
    except Exception as e:
        logging.error("Enhanced bulk Postgres insert failed: %s", e)

def extract_year_month_from_path(nc_path):
    """Ultra-fast year/month extraction from file path"""
    path_parts = Path(nc_path).parts
    year = None
    month = None
    
    for i, part in enumerate(path_parts):
        if part.isdigit() and len(part) == 4 and part.startswith(('19', '20')):
            year = part
            if i + 1 < len(path_parts):
                next_part = path_parts[i + 1]
                if next_part.isdigit() and len(next_part) <= 2:
                    try:
                        month_num = int(next_part)
                        if 1 <= month_num <= 12:
                            month = next_part.zfill(2)
                    except ValueError:
                        pass
            break
    
    if year and month:
        return f"{year}_{month}"
    elif year:
        return f"{year}_01"
    else:
        return "unknown"

def _jsonify_attrs(attrs: dict) -> str:
    """Safely convert xarray ds.attrs to a JSON string."""
    try:
        def convert(v):
            if isinstance(v, (np.floating, np.integer)):
                return v.item()
            if isinstance(v, (np.ndarray,)):
                return v.tolist()
            return v
        safe = {k: convert(v) for k, v in dict(attrs or {}).items()}
        return json.dumps(safe)
    except Exception:
        try:
            return json.dumps({k: str(v) for k, v in dict(attrs or {}).items()})
        except Exception:
            return "{}"

def process_single_file_enhanced(nc_path, parquet_root):
    """
    Enhanced processing of a single NetCDF file with new schema support.
    Extracts enhanced metadata and quality metrics.
    """
    try:
        subfolder = extract_year_month_from_path(nc_path)
        
        with xr.open_dataset(nc_path, decode_times=False, mask_and_scale=False) as ds:
            n_prof = ds.sizes.get("n_prof", 1)
            gattrs = dict(ds.attrs)
            
            # Extract enhanced metadata
            institution = gattrs.get("institution", "")
            data_source = gattrs.get("source", gattrs.get("file_source", ""))
            depth_min = gattrs.get("geospatial_vertical_min")
            depth_max = gattrs.get("geospatial_vertical_max")
            t_start = gattrs.get("time_coverage_start")
            t_end = gattrs.get("time_coverage_end")
            conventions = gattrs.get("Conventions", "")
            keywords = gattrs.get("keywords", "")
            
            profiles_data = []
            
            for prof_idx in range(n_prof):
                profile_id = str(uuid.uuid4())
                
                # Extract coordinates
                lat = lon = prof_time = None
                try:
                    # Latitude
                    for lat_name in ["latitude", "LATITUDE"]:
                        if lat_name in ds.variables:
                            lat_var = ds[lat_name]
                            lat = float(lat_var.values.flat[prof_idx] if lat_var.ndim > 0 else lat_var.values)
                            break
                    
                    # Longitude  
                    for lon_name in ["longitude", "LONGITUDE"]:
                        if lon_name in ds.variables:
                            lon_var = ds[lon_name]
                            lon = float(lon_var.values.flat[prof_idx] if lon_var.ndim > 0 else lon_var.values)
                            break
                    
                    # Time
                    for time_name in ["juld", "time"]:
                        if time_name in ds.variables:
                            time_var = ds[time_name]
                            prof_time = str(time_var.values.flat[prof_idx] if time_var.ndim > 0 else time_var.values)
                            break
                            
                except Exception:
                    pass
                
                # Extract platform info
                platform = cycle = None
                try:
                    if "platform_number" in ds.variables:
                        platform_var = ds["platform_number"]
                        platform = str(platform_var.values.flat[prof_idx] if platform_var.ndim > 0 else platform_var.values)
                    if "cycle_number" in ds.variables:
                        cycle_var = ds["cycle_number"]
                        cycle = float(cycle_var.values.flat[prof_idx] if cycle_var.ndim > 0 else cycle_var.values)
                except Exception:
                    pass
                
                # Enhanced measurements extraction
                n_levels = ds.sizes.get("n_levels", 0)
                measurements_data = {"level": list(range(n_levels))}
                
                # Get all available variables
                for var_name in ["pres", "temp", "psal", "oxy", "chla", "ph", "nitrate", 
                                "PRES", "TEMP", "PSAL", "OXY", "CHLA", "PH", "NITRATE"]:
                    if var_name in ds.variables:
                        try:
                            var = ds[var_name]
                            if var.ndim == 2:
                                values = var.values[prof_idx, :].tolist()
                            else:
                                values = var.values.tolist()
                            measurements_data[var_name.lower()] = values
                        except Exception:
                            measurements_data[var_name.lower()] = [None] * n_levels
                
                measurements_df = pd.DataFrame(measurements_data)
                
                # Create output directory and save parquet
                out_dir = parquet_root / subfolder
                out_dir.mkdir(parents=True, exist_ok=True)
                ppath = out_dir / f"profile_{profile_id}.parquet"
                measurements_df.to_parquet(ppath, index=False)
                
                # Enhanced quality analysis
                quality_score = calculate_data_quality_score(measurements_data)
                completeness_score = len([v for v in measurements_data.values() if v]) / len(measurements_data) if measurements_data else 0
                variable_info = detect_available_variables(measurements_data)
                ocean_basin = determine_ocean_basin(lat, lon)
                
                # Enhanced profile data
                profile_data = {
                    "profile_id": profile_id,
                    "file_name": os.path.basename(nc_path),
                    "file_path": str(nc_path),
                    "float_id": platform or "unknown",
                    "platform_number": platform,
                    "cycle_number": cycle,
                    "profile_time": prof_time,
                    "latitude": lat,
                    "longitude": lon,
                    "ocean_basin": ocean_basin,
                    "parquet_path": str(ppath),
                    "subfolder": subfolder,
                    "qc_summary": json.dumps({"quality_score": quality_score, "completeness": completeness_score}),
                    "attrs": _jsonify_attrs(gattrs),
                    "institution": institution,
                    "data_source": data_source,
                    "depth_min": depth_min,
                    "depth_max": depth_max,
                    "time_coverage_start": t_start,
                    "time_coverage_end": t_end,
                    "conventions": conventions,
                    "keywords": keywords,
                    
                    # Enhanced fields
                    "quality_score": quality_score,
                    "completeness_score": completeness_score,
                    "qc_flag": "good" if quality_score > 0.7 else "questionable" if quality_score > 0.3 else "bad",
                    "anomaly_flags": [],
                    **variable_info
                }
                profiles_data.append(profile_data)
        
        return profiles_data
        
    except Exception as e:
        return [{"error": str(e), "file_path": str(nc_path)}]

def process_chunk_enhanced(file_chunk, parquet_root):
    """Enhanced chunk processing with better error handling."""
    chunk_results = []
    for nc_path in file_chunk:
        try:
            result = process_single_file_enhanced(nc_path, parquet_root)
            chunk_results.extend(result)
        except Exception as e:
            logging.error("Failed to process file %s: %s", nc_path, e)
            chunk_results.append({"error": str(e), "file_path": str(nc_path)})
    return chunk_results

def run_enhanced_bulk_ingest(base_dir=None, max_files=None, resume_from=None):
    """Enhanced main ingestion function with comprehensive schema support."""
    if base_dir is None:
        base_dir = DEFAULT_BASE_DIR
    
    setup_logging(LOG_FILE)
    logging.info("=" * 50)
    logging.info("Starting ENHANCED ULTRA-FAST bulk ingestion")
    logging.info("Processing version: %s", PROCESSING_VERSION)
    logging.info("Base directory: %s", base_dir)
    logging.info("Max workers: %d", MAX_WORKERS)
    logging.info("=" * 50)
    
    # Create output directories
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all NetCDF files
    pattern = os.path.join(base_dir, "**", "*.nc")
    nc_files = glob.glob(pattern, recursive=True)
    
    if max_files:
        nc_files = nc_files[:max_files]
    
    if resume_from:
        # Simple resume functionality
        nc_files = nc_files[resume_from:]
        logging.info("Resuming from file #%d", resume_from)
    
    total_files = len(nc_files)
    logging.info("Found %d NetCDF files to process", total_files)
    
    if total_files == 0:
        logging.warning("No NetCDF files found!")
        return
    
    # Process in chunks with multiprocessing
    start_time = time.time()
    all_profiles = []
    processed_count = 0
    error_count = 0
    
    # Create chunks for processing
    chunks = [nc_files[i:i + CHUNK_SIZE] for i in range(0, len(nc_files), CHUNK_SIZE)]
    
    logging.info("Processing %d chunks with %d workers", len(chunks), MAX_WORKERS)
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all chunks
        process_func = partial(process_chunk_enhanced, parquet_root=PARQUET_DIR)
        future_to_chunk = {executor.submit(process_func, chunk): chunk for chunk in chunks}
        
        # Process results with progress bar
        with tqdm(total=total_files, desc="Processing files", unit="files") as pbar:
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result()
                    
                    # Count successes and errors
                    for result in chunk_results:
                        if "error" in result:
                            error_count += 1
                            logging.error("Error in file %s: %s", result.get("file_path", "unknown"), result["error"])
                        else:
                            processed_count += 1
                            all_profiles.append(result)
                    
                    pbar.update(len(chunk))
                    
                    # Periodic saves and database inserts
                    if len(all_profiles) >= SAVE_INTERVAL:
                        # Save to CSV
                        df = pd.DataFrame(all_profiles)
                        if METADATA_CSV.exists():
                            df.to_csv(METADATA_CSV, mode='a', header=False, index=False)
                        else:
                            df.to_csv(METADATA_CSV, index=False)
                        
                        # Insert to PostgreSQL
                        if PG_URL:
                            bulk_postgres_insert_enhanced(all_profiles, PG_URL)
                        
                        # Clear memory
                        all_profiles = []
                        
                        # Log progress
                        elapsed = time.time() - start_time
                        rate = processed_count / elapsed if elapsed > 0 else 0
                        logging.info("Processed %d files (%.1f files/sec), %d errors", 
                                   processed_count, rate, error_count)
                
                except Exception as e:
                    logging.error("Chunk processing failed: %s", e)
                    error_count += len(chunk)
                    pbar.update(len(chunk))
    
    # Final save of remaining profiles
    if all_profiles:
        df = pd.DataFrame(all_profiles)
        if METADATA_CSV.exists():
            df.to_csv(METADATA_CSV, mode='a', header=False, index=False)
        else:
            df.to_csv(METADATA_CSV, index=False)
        
        if PG_URL:
            bulk_postgres_insert_enhanced(all_profiles, PG_URL)
    
    # Final statistics
    end_time = time.time()
    total_time = end_time - start_time
    success_rate = (processed_count / total_files * 100) if total_files > 0 else 0
    avg_rate = processed_count / total_time if total_time > 0 else 0
    
    logging.info("=" * 50)
    logging.info("ENHANCED INGESTION COMPLETE!")
    logging.info("Total files processed: %d / %d (%.1f%%)", processed_count, total_files, success_rate)
    logging.info("Total errors: %d", error_count)
    logging.info("Total time: %.1f seconds", total_time)
    logging.info("Average rate: %.1f files/second", avg_rate)
    logging.info("Processing version: %s", PROCESSING_VERSION)
    logging.info("Output CSV: %s", METADATA_CSV)
    logging.info("Output Parquet dir: %s", PARQUET_DIR)
    logging.info("=" * 50)
    
    return {
        "processed_count": processed_count,
        "error_count": error_count,
        "total_time": total_time,
        "avg_rate": avg_rate,
        "success_rate": success_rate
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced Ultra-fast ARGO bulk ingestion")
    parser.add_argument("--base-dir", help="Base directory containing NetCDF files")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    parser.add_argument("--resume-from", type=int, help="Resume from file number")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Number of worker processes")
    
    args = parser.parse_args()
    
    if args.workers:
        MAX_WORKERS = min(args.workers, mp.cpu_count())
    
    results = run_enhanced_bulk_ingest(
        base_dir=args.base_dir,
        max_files=args.max_files,
        resume_from=args.resume_from
    )
    
    print(f"\nIngestion completed!")
    print(f"Processed: {results['processed_count']} files")
    print(f"Errors: {results['error_count']} files")
    print(f"Rate: {results['avg_rate']:.1f} files/second")
    print(f"Success rate: {results['success_rate']:.1f}%")
