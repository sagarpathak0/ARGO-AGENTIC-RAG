# bulk_ingest_argo.py
"""
Recursively ingest ARGO .nc files into per-profile Parquet and a master metadata CSV.
- Keeps originals untouched.
- Prefers adjusted variables.
- Optional Postgres insertion (set PG_URL).
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

import xarray as xr
import pandas as pd
from tqdm import tqdm

# Optional: PostgreSQL insertion
try:
    from sqlalchemy import create_engine, text
except Exception:
    create_engine = None

# -------- CONFIG defaults --------
DEFAULT_BASE_DIR = r"C:\Users\sagar\OneDrive\desktop\AGRODATA\gadr\data\indian"
OUT_ROOT = Path(DEFAULT_BASE_DIR).parent / "processed_profiles"   # default sibling folder
METADATA_CSV = OUT_ROOT / "profiles_metadata.csv"
PARQUET_DIR = OUT_ROOT / "parquet"
LOG_FILE = OUT_ROOT / "ingest.log"
PG_URL = "postgresql://avnadmin:AVNS_T7GmZnlliHeBAIDQB0r@pg-rabbitanimated-postgres-animate28.i.aivencloud.com:13249/AlgoForge?sslmode=require"   # Aiven PostgreSQL connection

# -------- logging --------
def setup_logging(log_path):
    os.makedirs(log_path.parent, exist_ok=True)
    logging.basicConfig(
        filename=str(log_path), filemode="a",
        format="%(asctime)s %(levelname)s: %(message)s",
        level=logging.INFO
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

# -------- helpers --------
def prefer_var(ds, names):
    for n in names:
        if n in ds.variables:
            return ds[n]
    return None

def create_profiles_table(engine):
    """Create the profiles table if it doesn't exist."""
    # First enable PostGIS extension
    enable_postgis_sql = text("CREATE EXTENSION IF NOT EXISTS postgis;")
    
    create_table_sql = text("""
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
            -- Enhanced fields for AI queries
            institution TEXT,
            data_source TEXT,
            depth_min DOUBLE PRECISION,
            depth_max DOUBLE PRECISION,
            time_coverage_start TIMESTAMP,
            time_coverage_end TIMESTAMP,
            conventions TEXT,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- PostGIS geometry column for advanced spatial queries
            geom GEOMETRY(POINT, 4326),
            -- Constraints
            CONSTRAINT valid_coordinates CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
        );
        
        -- Create indexes for common AI query patterns
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
    """)
    
    try:
        with engine.begin() as conn:
            # Enable PostGIS
            conn.execute(enable_postgis_sql)
            logging.info("PostGIS extension enabled successfully")
            
            # Create table
            conn.execute(create_table_sql)
            logging.info("Profiles table created/verified successfully")
    except Exception as e:
        logging.error("Failed to create profiles table: %s", e)
        raise

def safe_scalar(x):
    try:
        if hasattr(x, "values"):
            val = x.values
        else:
            val = x
        if hasattr(val, "tolist"):
            val = val.tolist()
        return val
    except Exception:
        return None

def make_json_serializable(obj):
    """
    Convert numpy types and other non-JSON-serializable objects to JSON-compatible types.
    """
    import numpy as np
    
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif hasattr(obj, 'item'):  # other numpy scalars
        try:
            return obj.item()
        except (ValueError, TypeError):
            return str(obj)
    else:
        return obj

def process_single_file(nc_path_str, parquet_root_str):
    """
    Process a single NetCDF file - optimized for multiprocessing.
    Returns list of metadata rows for this file.
    """
    import xarray as xr
    import pandas as pd
    import numpy as np
    from pathlib import Path
    import uuid
    import json
    import os
    
    nc_path = Path(nc_path_str)
    parquet_root = Path(parquet_root_str)
    
    try:
        # Open with minimal decoding for speed
        ds = xr.open_dataset(nc_path, decode_times=False, mask_and_scale=False, chunks=None)
        
        # Quick extraction of profiles
        profiles = extract_profiles_from_ds_fast(ds, nc_path)
        
        rows = []
        for prof in profiles:
            pid = prof["profile_id"]
            
            # Extract year/month from path - same logic but optimized
            subfolder = extract_date_from_path(nc_path)
            
            out_dir = parquet_root / subfolder
            os.makedirs(out_dir, exist_ok=True)
            ppath = out_dir / f"profile_{pid}.parquet"
            
            # Write parquet file
            prof["measurements"].to_parquet(ppath, index=False)
            
            # Compute QC summary
            qc_summary = compute_qc_summary(prof["measurements"])
            
            # Extract metadata
            attrs = prof["attrs"]
            
            row = {
                "profile_id": pid,
                "file_name": prof["file_name"],
                "file_path": prof["file_path"],
                "float_id": prof["float_id"],
                "platform_number": prof["platform_number"],
                "cycle_number": prof["cycle_number"],
                "profile_time": prof["profile_time"],
                "latitude": prof["latitude"],
                "longitude": prof["longitude"],
                "parquet_path": str(ppath),
                "qc_summary": json.dumps(qc_summary),
                "attrs": json.dumps(prof["attrs"]),
                "institution": attrs.get("institution", ""),
                "data_source": attrs.get("source", attrs.get("file_source", "")),
                "depth_min": attrs.get("geospatial_vertical_min"),
                "depth_max": attrs.get("geospatial_vertical_max"),
                "time_coverage_start": attrs.get("time_coverage_start"),
                "time_coverage_end": attrs.get("time_coverage_end"),
                "conventions": attrs.get("Conventions", ""),
                "keywords": attrs.get("keywords", "")
            }
            rows.append(row)
        
        ds.close()
        return rows
        
    except Exception as e:
        # Return error info instead of crashing
        return [{"error": str(e), "file_path": str(nc_path)}]

def extract_date_from_path(nc_path):
    """Fast date extraction from file path"""
    path_parts = nc_path.parts
    for i, part in enumerate(path_parts):
        if part.isdigit() and len(part) == 4 and part.startswith(('19', '20')):
            year = part
            if i + 1 < len(path_parts):
                next_part = path_parts[i + 1]
                if next_part.isdigit() and len(next_part) <= 2 and 1 <= int(next_part) <= 12:
                    month = next_part.zfill(2)
                    return f"{year}_{month}"
            return f"{year}_01"
    return "unknown"

def compute_qc_summary(measurements_df):
    """Fast QC summary computation"""
    def qc_frac(series):
        if series is None or series.isnull().all():
            return None
        s = series.astype(str)
        bad = s.str.contains("[48]|9", na=False)
        return float(bad.sum()) / float(len(s)) if len(s) > 0 else 0.0
    
    return {
        "temp_bad_frac": qc_frac(measurements_df.get("temp_qc")),
        "psal_bad_frac": qc_frac(measurements_df.get("psal_qc")),
    }

def extract_profiles_from_ds_fast(ds, nc_path):
    """
    Faster version of profile extraction - minimal processing
    """
    out = []
    
    # Quick variable identification
    lat_v = prefer_var(ds, ["latitude","LATITUDE","lat"])
    lon_v = prefer_var(ds, ["longitude","LONGITUDE","lon"])
    time_v = prefer_var(ds, ["juld","JULD","time"])
    cycle_v = prefer_var(ds, ["cycle_number","CYCLE_NUMBER","cycle"])
    platform_v = prefer_var(ds, ["platform_number","PLATFORM_NUMBER","platform"])
    
    pres_v = prefer_var(ds, ["pres_adjusted","PRES_ADJUSTED","pres"])
    temp_v = prefer_var(ds, ["temp_adjusted","TEMP_ADJUSTED","temp"])
    psal_v = prefer_var(ds, ["psal_adjusted","PSAL_ADJUSTED","psal"])
    pres_qc_v = prefer_var(ds, ["pres_qc","PRES_QC","pres_qc"])
    temp_qc_v = prefer_var(ds, ["temp_qc","TEMP_QC","temp_qc"])
    psal_qc_v = prefer_var(ds, ["psal_qc","PSAL_QC","psal_qc"])

    n_prof = ds.sizes.get("n_prof", 1)

    for prof_idx in range(n_prof):
        profile_id = str(uuid.uuid4())
        
        # Quick scalar extraction
        lat = safe_scalar_fast(lat_v, prof_idx)
        lon = safe_scalar_fast(lon_v, prof_idx)
        prof_time = safe_scalar_fast(time_v, prof_idx)
        cycle = safe_scalar_fast(cycle_v, prof_idx)
        platform = safe_scalar_fast(platform_v, prof_idx)

        # Quick measurements DataFrame
        meas_df = pd.DataFrame({
            "pres": slice_var_fast(pres_v, prof_idx),
            "temp": slice_var_fast(temp_v, prof_idx),
            "psal": slice_var_fast(psal_v, prof_idx),
            "pres_qc": slice_var_fast(pres_qc_v, prof_idx),
            "temp_qc": slice_var_fast(temp_qc_v, prof_idx),
            "psal_qc": slice_var_fast(psal_qc_v, prof_idx),
        })

        rec = {
            "profile_id": profile_id,
            "file_name": os.path.basename(nc_path),
            "file_path": str(nc_path),
            "float_id": str(ds.attrs.get("id") or platform),
            "platform_number": platform,
            "cycle_number": cycle,
            "profile_time": str(prof_time),
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lon) if lon is not None else None,
            "attrs": make_json_serializable(dict(ds.attrs)),
            "measurements": meas_df
        }
        out.append(rec)
    return out

def safe_scalar_fast(var, prof_idx):
    """Fast scalar extraction"""
    if var is None:
        return None
    try:
        if hasattr(var, "values"):
            val = var.values
            if hasattr(val, "ndim") and val.ndim > 0:
                return val[prof_idx] if prof_idx < len(val) else val[0]
            return val
        return var
    except:
        return None

def slice_var_fast(var, prof_idx):
    """Fast variable slicing"""
    if var is None:
        return None
    try:
        arr = var.values
        if arr is None:
            return None
        if hasattr(arr, "ndim") and arr.ndim == 2:
            return pd.Series(arr[prof_idx, :])
        else:
            return pd.Series(arr)
    except:
        return pd.Series(dtype=float)

def extract_profiles_from_ds(ds, nc_path):
    """
    Returns a list of dicts: each dict has metadata and a pandas.DataFrame for measurements.
    Handles n_prof > 1 by iterating over profile index.
    """
    out = []
    # identify variables
    lat_v = prefer_var(ds, ["latitude","LATITUDE","lat"])
    lon_v = prefer_var(ds, ["longitude","LONGITUDE","lon"])
    time_v = prefer_var(ds, ["juld","JULD","time"])
    cycle_v = prefer_var(ds, ["cycle_number","CYCLE_NUMBER","cycle"])
    platform_v = prefer_var(ds, ["platform_number","PLATFORM_NUMBER","platform"])
    # measurements per profile: pres, temp, psal (prefer adjusted)
    pres_v = prefer_var(ds, ["pres_adjusted","PRES_ADJUSTED","pres"])
    temp_v = prefer_var(ds, ["temp_adjusted","TEMP_ADJUSTED","temp"])
    psal_v = prefer_var(ds, ["psal_adjusted","PSAL_ADJUSTED","psal"])
    pres_qc_v = prefer_var(ds, ["pres_qc","PRES_QC","pres_qc"])
    temp_qc_v = prefer_var(ds, ["temp_qc","TEMP_QC","temp_qc"])
    psal_qc_v = prefer_var(ds, ["psal_qc","PSAL_QC","psal_qc"])

    n_prof = ds.sizes.get("n_prof", 1)
    n_levels = ds.sizes.get("n_levels", None)

    for prof_idx in range(n_prof):
        profile_id = str(uuid.uuid4())
        # scalar metadata - some variables may be dimensioned (n_prof,)
        lat = None; lon = None; prof_time = None; cycle = None; platform = None
        try:
            if lat_v is not None:
                lat = safe_scalar(lat_v[prof_idx] if getattr(lat_v, "ndim", 0)>0 else lat_v)
            if lon_v is not None:
                lon = safe_scalar(lon_v[prof_idx] if getattr(lon_v, "ndim", 0)>0 else lon_v)
            if time_v is not None:
                prof_time = safe_scalar(time_v[prof_idx] if getattr(time_v, "ndim", 0)>0 else time_v)
            if cycle_v is not None:
                cycle = safe_scalar(cycle_v[prof_idx] if getattr(cycle_v, "ndim", 0)>0 else cycle_v)
            if platform_v is not None:
                platform = safe_scalar(platform_v[prof_idx] if getattr(platform_v, "ndim", 0)>0 else platform_v)
        except Exception:
            # fallback to attrs
            pass

        # build measurements DF (n_levels x variables). Some DSs store as (n_levels,) for single profile, or (n_prof,n_levels)
        def slice_var(var):
            if var is None:
                return None
            arr = var.values
            # try to extract the level array for this profile
            if arr is None:
                return None
            # if var shape (n_prof, n_levels)
            if getattr(arr, "ndim", 0) == 2:
                # choose row prof_idx
                row = arr[prof_idx, :]
            elif getattr(arr, "ndim", 0) == 1 and n_levels is not None and n_prof>1:
                # ambiguous, try to treat as levels (same for all) — fallback
                row = arr
            else:
                row = arr
            # convert masked arrays to regular numpy arrays
            try:
                return pd.Series(row).replace({None: pd.NA})
            except Exception:
                return pd.Series(row.tolist())
        s_pres = slice_var(pres_v)
        s_temp = slice_var(temp_v)
        s_psal = slice_var(psal_v)
        s_pres_qc = slice_var(pres_qc_v)
        s_temp_qc = slice_var(temp_qc_v)
        s_psal_qc = slice_var(psal_qc_v)

        meas_df = pd.DataFrame({
            "pres": s_pres,
            "temp": s_temp,
            "psal": s_psal,
            "pres_qc": s_pres_qc,
            "temp_qc": s_temp_qc,
            "psal_qc": s_psal_qc,
        })

        rec = {
            "profile_id": profile_id,
            "file_name": os.path.basename(nc_path),
            "file_path": str(nc_path),
            "float_id": str(ds.attrs.get("id") or platform),
            "platform_number": platform,
            "cycle_number": cycle,
            "profile_time": str(prof_time),
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lon) if lon is not None else None,
            "attrs": make_json_serializable(dict(ds.attrs)),
            "measurements": meas_df
        }
        out.append(rec)
    return out

# -------- main ingestion logic --------
def run_ingest(base_dir, out_root, pg_url=None, resume=True, max_workers=None):
    base_dir = Path(base_dir)
    out_root = Path(out_root)
    parquet_root = out_root / "parquet"
    os.makedirs(parquet_root, exist_ok=True)
    setup_logging(out_root / "ingest.log")
    logging.info("Starting FAST ingest: %s", base_dir)

    # Use all CPU cores by default
    if max_workers is None:
        max_workers = min(mp.cpu_count(), 8)  # Cap at 8 to avoid overwhelming system
    
    logging.info("Using %d worker processes", max_workers)

    # prepare metadata CSV (append mode if resume)
    cols = ["profile_id","file_name","file_path","float_id","platform_number","cycle_number",
            "profile_time","latitude","longitude","parquet_path","qc_summary","attrs",
            "institution","data_source","depth_min","depth_max","time_coverage_start",
            "time_coverage_end","conventions","keywords"]
    if resume and METADATA_CSV.exists():
        meta_df = pd.read_csv(METADATA_CSV)
        seen_files = set(meta_df["file_path"].unique())
        logging.info("Existing metadata rows: %d", len(meta_df))
    else:
        meta_df = pd.DataFrame(columns=cols)
        seen_files = set()

    nc_paths = list(base_dir.rglob("*.nc"))
    logging.info("Found %d .nc files", len(nc_paths))

    # Filter out already processed files
    if resume:
        nc_paths = [nc for nc in nc_paths if str(nc) not in seen_files]
        logging.info("Processing %d new files (skipping %d already processed)", 
                    len(nc_paths), len(seen_files))

    # Process files in chunks to avoid memory issues
    CHUNK_SIZE = max_workers * 10  # Process in chunks
    all_new_rows = []
    
    start_time = time.time()
    
    for chunk_start in range(0, len(nc_paths), CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, len(nc_paths))
        chunk_paths = nc_paths[chunk_start:chunk_end]
        
        logging.info("Processing chunk %d-%d of %d files", 
                    chunk_start, chunk_end, len(nc_paths))
        
        # Process chunk in parallel
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files in chunk
            future_to_path = {
                executor.submit(process_single_file, str(nc_path), str(parquet_root)): nc_path 
                for nc_path in chunk_paths
            }
            
            # Collect results with progress bar
            chunk_rows = []
            for future in tqdm(as_completed(future_to_path), 
                             total=len(future_to_path), 
                             desc=f"Chunk {chunk_start//CHUNK_SIZE + 1}"):
                try:
                    file_rows = future.result(timeout=30)  # 30 second timeout per file
                    if file_rows:
                        chunk_rows.extend(file_rows)
                except Exception as e:
                    nc_path = future_to_path[future]
                    logging.error("Failed to process %s: %s", nc_path, e)
        
        # Add chunk results to collection
        all_new_rows.extend(chunk_rows)
        
        # Save progress every chunk
        if chunk_rows:
            chunk_df = pd.DataFrame(chunk_rows, columns=cols)
            meta_df = pd.concat([meta_df, chunk_df], ignore_index=True)
            meta_df.to_csv(METADATA_CSV, index=False)
            
            elapsed = time.time() - start_time
            rate = (chunk_end) / elapsed if elapsed > 0 else 0
            estimated_total = len(nc_paths) / rate if rate > 0 else 0
            
            logging.info("Processed %d/%d files. Rate: %.1f files/sec. ETA: %.1f minutes", 
                        chunk_end, len(nc_paths), rate, (estimated_total - elapsed) / 60)

    # Final save and optional Postgres bulk insert
    if all_new_rows:
        logging.info("Final save of %d total new profiles", len(all_new_rows))
        meta_df.to_csv(METADATA_CSV, index=False)
        
        # Optional bulk Postgres insert
        if pg_url and create_engine:
            try:
                bulk_postgres_insert(all_new_rows, pg_url)
            except Exception as e:
                logging.error("Bulk Postgres insert failed: %s", e)

def bulk_postgres_insert(rows, pg_url):
    """Bulk insert rows into Postgres - much faster than individual inserts"""
    if not create_engine:
        return
        
    engine = create_engine(pg_url, pool_pre_ping=True)
    create_profiles_table(engine)
    
    # Prepare bulk insert data
    insert_data = []
    for row in rows:
        if "error" not in row:  # Skip error rows
            insert_data.append({
                "profile_id": row["profile_id"],
                "float_id": row["float_id"],
                "platform_number": row["platform_number"],
                "cycle_number": row["cycle_number"],
                "profile_time": row["profile_time"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "file_path": row["file_path"],
                "parquet_path": row["parquet_path"],
                "qc_summary": row["qc_summary"],
                "attrs": row["attrs"],
                "institution": row["institution"],
                "data_source": row["data_source"],
                "depth_min": row["depth_min"],
                "depth_max": row["depth_max"],
                "time_coverage_start": row["time_coverage_start"],
                "time_coverage_end": row["time_coverage_end"],
                "conventions": row["conventions"],
                "keywords": row["keywords"],
            })
    
    if insert_data:
        # Bulk insert using pandas - much faster
        df = pd.DataFrame(insert_data)
        df.to_sql('profiles', engine, if_exists='append', index=False, method='multi')
        logging.info("Bulk inserted %d profiles to Postgres", len(insert_data))

# -------- CLI --------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", default=DEFAULT_BASE_DIR, help="Root folder with downloaded .nc files")
    parser.add_argument("--out_root", default=str(OUT_ROOT), help="Where processed files will be stored")
    parser.add_argument("--pg_url", default=PG_URL, help="Optional Postgres URL (SQLAlchemy)")
    parser.add_argument("--no_resume", action="store_true", help="Reprocess everything (ignore existing metadata)")
    parser.add_argument("--max_workers", type=int, default=None, help="Number of parallel workers (default: auto)")
    args = parser.parse_args()

    run_ingest(args.base_dir, args.out_root, pg_url=args.pg_url, resume=not args.no_resume, max_workers=args.max_workers)
