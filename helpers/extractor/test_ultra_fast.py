# ultra_fast_ingest.py
"""
ULTRA-FAST bulk ingestion for ARGO .nc files.
Target: 214,400 files in 15-30 minutes = ~120-480 files/second
Optimizations:
- Maximum multiprocessing (use all CPU cores)
- Minimal NetCDF reading (essential metadata only)
- Skip detailed QC analysis
- Bulk operations everywhere
- Smart checkpointing
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

# Ultra-fast settings
MAX_WORKERS = min(16, mp.cpu_count())  # Use more workers
CHUNK_SIZE = 500  # Process larger chunks
SAVE_INTERVAL = 2000  # Save less frequently
CHECKPOINT_INTERVAL = 5000  # Checkpoint every 5000 files

def setup_logging(log_path):
    """Setup logging with INFO level for speed"""
    os.makedirs(log_path.parent, exist_ok=True)
    logging.basicConfig(
        filename=str(log_path), filemode="a",
        format="%(asctime)s %(levelname)s: %(message)s",
        level=logging.INFO
    )
    # Also log to console for visibility
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

def create_profiles_table(engine):
    """Create the profiles table (and PostGIS) if not exists, matching test.py."""
    enable_postgis_sql = text("CREATE EXTENSION IF NOT EXISTS postgis;")
    create_table_sql = text(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            profile_id TEXT PRIMARY KEY,
            float_id TEXT,
            platform_number TEXT,
            cycle_number NUMERIC,
            profile_time TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            file_path TEXT,
            parquet_path TEXT,
            qc_summary JSONB,
            attrs JSONB,
            institution TEXT,
            data_source TEXT,
            depth_min DOUBLE PRECISION,
            depth_max DOUBLE PRECISION,
            time_coverage_start TIMESTAMP,
            time_coverage_end TIMESTAMP,
            conventions TEXT,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            geom GEOMETRY(POINT, 4326),
            CONSTRAINT valid_coordinates CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
        );
        CREATE INDEX IF NOT EXISTS idx_profiles_lat ON profiles (latitude);
        CREATE INDEX IF NOT EXISTS idx_profiles_lon ON profiles (longitude);
        CREATE INDEX IF NOT EXISTS idx_profiles_location ON profiles (latitude, longitude);
        CREATE INDEX IF NOT EXISTS idx_profiles_geom ON profiles USING GIST (geom);
        CREATE INDEX IF NOT EXISTS idx_profiles_time_start ON profiles (time_coverage_start);
        CREATE INDEX IF NOT EXISTS idx_profiles_time_end ON profiles (time_coverage_end);
        CREATE INDEX IF NOT EXISTS idx_profiles_depth_min ON profiles (depth_min);
        CREATE INDEX IF NOT EXISTS idx_profiles_depth_max ON profiles (depth_max);
        CREATE INDEX IF NOT EXISTS idx_profiles_institution ON profiles (institution);
        CREATE INDEX IF NOT EXISTS idx_profiles_float ON profiles (float_id);
        CREATE INDEX IF NOT EXISTS idx_profiles_keywords ON profiles USING GIN (to_tsvector('english', keywords));
        """
    )
    try:
        with engine.begin() as conn:
            conn.execute(enable_postgis_sql)
            conn.execute(create_table_sql)
        logging.info("Profiles table created/verified successfully")
    except Exception as e:
        logging.error("Failed to create profiles table: %s", e)
        raise

def bulk_postgres_insert(rows, pg_url):
    """Bulk insert rows into Postgres; fast path using pandas to_sql like test.py."""
    if not (HAS_SQLALCHEMY and create_engine and pg_url):
        return
    try:
        engine = create_engine(pg_url, pool_pre_ping=True)
        create_profiles_table(engine)
        insert_data = []
        for row in rows:
            if "error" in row:
                continue
            insert_data.append({
                "profile_id": row.get("profile_id"),
                "float_id": row.get("float_id"),
                "platform_number": row.get("platform_number"),
                "cycle_number": row.get("cycle_number"),
                "profile_time": row.get("profile_time"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
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
            })
        if insert_data:
            df = pd.DataFrame(insert_data)
            # Normalize time fields to pandas datetime where possible
            for col in ["time_coverage_start", "time_coverage_end"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            # Use multi-row insert for speed
            df.to_sql('profiles', engine, if_exists='append', index=False, method='multi')
            # Set geom for rows missing it if lat/lon present
            try:
                with engine.begin() as conn:
                    conn.execute(text(
                        """
                        UPDATE profiles
                        SET geom = CASE
                          WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
                          ELSE geom
                        END
                        WHERE geom IS NULL;
                        """
                    ))
            except Exception as e:
                logging.warning("Failed to backfill geom: %s", e)
            logging.info("Bulk inserted %d profiles to Postgres", len(insert_data))
    except Exception as e:
        logging.error("Bulk Postgres insert failed: %s", e)

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
        # Fallback to stringified attrs
        try:
            return json.dumps({k: str(v) for k, v in dict(attrs or {}).items()})
        except Exception:
            return "{}"

def process_single_file_ultra_fast(nc_path, parquet_root):
    """
    Ultra-fast processing of a single NetCDF file.
    Only extracts essential metadata, skips detailed analysis.
    """
    try:
        # Fast subfolder extraction
        subfolder = extract_year_month_from_path(nc_path)
        
        # Minimal NetCDF reading - only essential variables
        with xr.open_dataset(nc_path, decode_times=False, mask_and_scale=False) as ds:
            # Get basic dimensions
            n_prof = ds.sizes.get("n_prof", 1)
            # Pull cheap global attrs for metadata columns (no heavy decoding)
            gattrs = dict(ds.attrs)
            institution = gattrs.get("institution", "")
            data_source = gattrs.get("source", gattrs.get("file_source", ""))
            depth_min = gattrs.get("geospatial_vertical_min")
            depth_max = gattrs.get("geospatial_vertical_max")
            t_start = gattrs.get("time_coverage_start")
            t_end = gattrs.get("time_coverage_end")
            conventions = gattrs.get("Conventions", "")
            keywords = gattrs.get("keywords", "")
            
            # Extract only essential variables (no QC analysis)
            profiles_data = []
            
            for prof_idx in range(n_prof):
                profile_id = str(uuid.uuid4())
                
                # Get coordinates - minimal processing
                lat = lon = prof_time = None
                try:
                    if "latitude" in ds.variables:
                        lat_var = ds["latitude"]
                        lat = float(lat_var.values.flat[prof_idx] if lat_var.ndim > 0 else lat_var.values)
                    elif "LATITUDE" in ds.variables:
                        lat_var = ds["LATITUDE"] 
                        lat = float(lat_var.values.flat[prof_idx] if lat_var.ndim > 0 else lat_var.values)
                        
                    if "longitude" in ds.variables:
                        lon_var = ds["longitude"]
                        lon = float(lon_var.values.flat[prof_idx] if lon_var.ndim > 0 else lon_var.values)
                    elif "LONGITUDE" in ds.variables:
                        lon_var = ds["LONGITUDE"]
                        lon = float(lon_var.values.flat[prof_idx] if lon_var.ndim > 0 else lon_var.values)
                        
                    # Skip time parsing for speed - just store raw
                    if "juld" in ds.variables:
                        time_var = ds["juld"]
                        prof_time = str(time_var.values.flat[prof_idx] if time_var.ndim > 0 else time_var.values)
                    elif "time" in ds.variables:
                        time_var = ds["time"]
                        prof_time = str(time_var.values.flat[prof_idx] if time_var.ndim > 0 else time_var.values)
                        
                except Exception:
                    # Continue with None values if extraction fails
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
                
                # Create minimal measurements DataFrame (no QC analysis for speed)
                n_levels = ds.sizes.get("n_levels", 0)
                measurements_data = {"level": list(range(n_levels))}
                
                # Get pressure, temp, salinity if available (raw values only)
                for var_name in ["pres", "temp", "psal", "PRES", "TEMP", "PSAL"]:
                    if var_name in ds.variables:
                        try:
                            var = ds[var_name]
                            if var.ndim == 2:  # (n_prof, n_levels)
                                values = var.values[prof_idx, :].tolist()
                            else:  # (n_levels,)
                                values = var.values.tolist()
                            measurements_data[var_name.lower()] = values
                        except Exception:
                            measurements_data[var_name.lower()] = [None] * n_levels
                
                measurements_df = pd.DataFrame(measurements_data)
                
                # Create output directory
                out_dir = parquet_root / subfolder
                out_dir.mkdir(parents=True, exist_ok=True)
                
                # Save parquet
                ppath = out_dir / f"profile_{profile_id}.parquet"
                measurements_df.to_parquet(ppath, index=False)
                
                # Minimal metadata (but include cheap attrs for DB usefulness)
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
                    "parquet_path": str(ppath),
                    "subfolder": subfolder,
                    # Keep QC lightweight; detailed QC skipped
                    "qc_summary": "{}",
                    "attrs": _jsonify_attrs(gattrs),
                    "institution": institution,
                    "data_source": data_source,
                    "depth_min": depth_min,
                    "depth_max": depth_max,
                    "time_coverage_start": t_start,
                    "time_coverage_end": t_end,
                    "conventions": conventions,
                    "keywords": keywords
                }
                profiles_data.append(profile_data)
        
        return profiles_data
        
    except Exception as e:
        # Return error info instead of crashing
        return [{"error": str(e), "file_path": str(nc_path)}]

def process_chunk(file_chunk, parquet_root):
    """Process a chunk of files"""
    results = []
    for nc_path in file_chunk:
        result = process_single_file_ultra_fast(nc_path, parquet_root)
        results.extend(result)
    return results

def run_ultra_fast_ingest(base_dir, out_root, pg_url=None, resume=True):
    """Ultra-fast ingestion with maximum multiprocessing"""
    base_dir = Path(base_dir)
    out_root = Path(out_root)
    parquet_root = out_root / "parquet"
    
    # Setup
    parquet_root.mkdir(parents=True, exist_ok=True)
    setup_logging(out_root / "ingest.log")
    
    # Load existing progress
    metadata_csv = out_root / "profiles_metadata.csv"
    checkpoint_file = out_root / "processing_checkpoint.txt"
    
    cols = ["profile_id","file_name","file_path","float_id","platform_number","cycle_number",
            "profile_time","latitude","longitude","parquet_path","qc_summary","attrs",
            "institution","data_source","depth_min","depth_max","time_coverage_start",
            "time_coverage_end","conventions","keywords","subfolder"]
    
    processed_files = set()
    if resume and metadata_csv.exists():
        try:
            existing_df = pd.read_csv(metadata_csv)
            processed_files = set(existing_df["file_path"].unique())
            logging.info(f"Found {len(processed_files)} already processed files")
        except Exception as e:
            logging.warning(f"Could not load existing metadata: {e}")
    
    # Get all files
    all_files = list(base_dir.rglob("*.nc"))
    remaining_files = [f for f in all_files if str(f) not in processed_files]
    
    total_files = len(all_files)
    remaining_count = len(remaining_files)
    
    logging.info(f"Total files: {total_files}")
    logging.info(f"Already processed: {total_files - remaining_count}")
    logging.info(f"Remaining to process: {remaining_count}")
    logging.info(f"Using {MAX_WORKERS} workers with chunk size {CHUNK_SIZE}")
    
    if remaining_count == 0:
        logging.info("All files already processed!")
        return
    
    # Split into chunks for multiprocessing
    file_chunks = [remaining_files[i:i + CHUNK_SIZE] for i in range(0, len(remaining_files), CHUNK_SIZE)]
    
    # Process with maximum multiprocessing
    all_results = []
    processed_count = total_files - remaining_count
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all chunks
        future_to_chunk = {
            executor.submit(process_chunk, chunk, parquet_root): chunk 
            for chunk in file_chunks
        }
        
        # Process results as they complete
        with tqdm(total=len(file_chunks), desc="Processing chunks") as pbar:
            for future in as_completed(future_to_chunk):
                try:
                    chunk_results = future.result()
                    all_results.extend(chunk_results)
                    
                    chunk = future_to_chunk[future]
                    processed_count += len(chunk)
                    
                    # Save progress periodically
                    if len(all_results) >= SAVE_INTERVAL:
                        save_progress(all_results, metadata_csv, cols, processed_count, pg_url)
                        all_results.clear()
                    
                    # Update progress
                    elapsed = time.time() - start_time
                    rate = processed_count / elapsed if elapsed > 0 else 0
                    pbar.set_postfix({
                        'processed': processed_count,
                        'rate': f'{rate:.1f} files/sec',
                        'eta': f'{(total_files - processed_count) / rate / 60:.1f}min' if rate > 0 else 'N/A'
                    })
                    
                except Exception as e:
                    logging.error(f"Chunk failed: {e}")
                
                pbar.update(1)
    
    # Save final results
    if all_results:
        save_progress(all_results, metadata_csv, cols, processed_count, pg_url)
    
    elapsed = time.time() - start_time
    logging.info(f"Processing completed in {elapsed/60:.1f} minutes")
    logging.info(f"Average rate: {processed_count/elapsed:.1f} files/second")

def save_progress(results, metadata_csv, cols, processed_count, pg_url=None):
    """Save progress to CSV"""
    try:
        # Filter out error results
        valid_results = [r for r in results if "error" not in r]
        error_results = [r for r in results if "error" in r]
        
        if error_results:
            logging.warning(f"Skipped {len(error_results)} files due to errors")
        
        if valid_results:
            # Convert to DataFrame
            new_df = pd.DataFrame(valid_results)
            
            # Append to existing CSV
            if metadata_csv.exists():
                existing_df = pd.read_csv(metadata_csv)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = new_df
            
            # Save
            combined_df.to_csv(metadata_csv, index=False)
            logging.info(f"Saved progress: {len(valid_results)} new profiles, total processed: {processed_count}")
            # Optional DB insert for just-saved rows
            if pg_url:
                bulk_postgres_insert(valid_results, pg_url)
            
    except Exception as e:
        logging.error(f"Failed to save progress: {e}")

def backfill_db_from_csv(out_root, pg_url):
    """Push all rows from existing metadata CSV to Postgres (idempotent if empty table)."""
    if not (HAS_SQLALCHEMY and create_engine and pg_url):
        logging.error("SQLAlchemy not available or PG URL missing; cannot backfill DB")
        return
    out_root = Path(out_root)
    metadata_csv = out_root / "profiles_metadata.csv"
    if not metadata_csv.exists():
        logging.error("No metadata CSV found at %s", metadata_csv)
        return
    try:
        df = pd.read_csv(metadata_csv)
        # Normalize/ensure columns exist
        cols = [
            "profile_id","float_id","platform_number","cycle_number","profile_time",
            "latitude","longitude","file_path","parquet_path","qc_summary","attrs",
            "institution","data_source","depth_min","depth_max","time_coverage_start",
            "time_coverage_end","conventions","keywords"
        ]
        for c in cols:
            if c not in df.columns:
                df[c] = None
        df = df[cols]
        # Cast time-like columns
        for col in ["time_coverage_start","time_coverage_end"]:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        engine = create_engine(pg_url, pool_pre_ping=True)
        create_profiles_table(engine)

        # Use a staging table then upsert into main table
        stage = 'profiles_stage'
        with engine.begin() as conn:
            # Drop/create stage
            conn.execute(text(f"DROP TABLE IF EXISTS {stage};"))
            df.head(0).to_sql(stage, engine, if_exists='replace', index=False)
            # Bulk load stage
            df.to_sql(stage, engine, if_exists='append', index=False, method='multi')
            # Upsert from stage
            upsert_sql = text(
                """
                INSERT INTO profiles (
                    profile_id,float_id,platform_number,cycle_number,profile_time,
                    latitude,longitude,file_path,parquet_path,qc_summary,attrs,
                    institution,data_source,depth_min,depth_max,time_coverage_start,
                    time_coverage_end,conventions,keywords
                )
                SELECT 
                    profile_id,float_id,platform_number,cycle_number,profile_time,
                    latitude,longitude,file_path,parquet_path,qc_summary,attrs,
                    institution,data_source,depth_min,depth_max,time_coverage_start,
                    time_coverage_end,conventions,keywords
                FROM profiles_stage
                ON CONFLICT (profile_id) DO UPDATE SET
                    float_id = EXCLUDED.float_id,
                    platform_number = EXCLUDED.platform_number,
                    cycle_number = EXCLUDED.cycle_number,
                    profile_time = EXCLUDED.profile_time,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    file_path = EXCLUDED.file_path,
                    parquet_path = EXCLUDED.parquet_path,
                    qc_summary = EXCLUDED.qc_summary,
                    attrs = EXCLUDED.attrs,
                    institution = EXCLUDED.institution,
                    data_source = EXCLUDED.data_source,
                    depth_min = EXCLUDED.depth_min,
                    depth_max = EXCLUDED.depth_max,
                    time_coverage_start = EXCLUDED.time_coverage_start,
                    time_coverage_end = EXCLUDED.time_coverage_end,
                    conventions = EXCLUDED.conventions,
                    keywords = EXCLUDED.keywords;
                """
            )
            conn.execute(upsert_sql)
            # Backfill geom where possible
            conn.execute(text(
                """
                UPDATE profiles
                SET geom = CASE
                  WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
                  ELSE geom
                END
                WHERE geom IS NULL;
                """
            ))
            # Drop stage
            conn.execute(text(f"DROP TABLE IF EXISTS {stage};"))
        logging.info("Backfill/Upsert completed for %d rows", len(df))
    except Exception as e:
        logging.error("Backfill failed: %s", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ultra-fast ARGO ingestion")
    parser.add_argument("--base_dir", default=DEFAULT_BASE_DIR, help="Root folder with .nc files")
    parser.add_argument("--out_root", default=str(OUT_ROOT), help="Output folder")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Number of worker processes")
    parser.add_argument("--chunk_size", type=int, default=CHUNK_SIZE, help="Files per chunk")
    parser.add_argument("--no_resume", action="store_true", help="Start fresh")
    parser.add_argument("--pg_url", default=PG_URL, help="Optional Postgres URL (SQLAlchemy)")
    parser.add_argument("--backfill_db", action="store_true", help="Push existing CSV metadata to DB and exit")

    args = parser.parse_args()

    # Update global settings
    MAX_WORKERS = args.workers
    CHUNK_SIZE = args.chunk_size

    if args.backfill_db:
        setup_logging(Path(args.out_root) / "ingest.log")
        logging.info("Starting DB backfill from CSV -> Postgres")
        backfill_db_from_csv(args.out_root, args.pg_url)
    else:
        print(f"🚀 Ultra-fast ingestion starting...")
        print(f"📁 Input: {args.base_dir}")
        print(f"📁 Output: {args.out_root}")
        print(f"⚡ Workers: {MAX_WORKERS}")
        print(f"📦 Chunk size: {CHUNK_SIZE}")
        print(f"🔄 Resume: {not args.no_resume}")

        run_ultra_fast_ingest(args.base_dir, args.out_root, pg_url=args.pg_url, resume=not args.no_resume)