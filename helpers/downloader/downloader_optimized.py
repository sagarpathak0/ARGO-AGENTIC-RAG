import requests
import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tqdm import tqdm
from datetime import datetime

class SmartResumeTracker:
    def __init__(self, base_save_dir):
        self.base_save_dir = base_save_dir
        self.progress_file = os.path.join(base_save_dir, ".download_progress.json")
        self.directory_cache_file = os.path.join(base_save_dir, ".directory_cache.json")
        self.completed_dirs = set()
        self.last_processing_dir = None
        self.directory_cache = {}
        self.load_progress()
        self.load_directory_cache()
        
    def load_progress(self):
        """Load previous download progress"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    self.completed_dirs = set(data.get('completed_dirs', []))
                    self.last_processing_dir = data.get('last_processing_dir', None)
                    print(f"📋 Resuming from progress: {len(self.completed_dirs)} directories completed")
                    if self.last_processing_dir:
                        print(f"🔄 Last processing: {self.last_processing_dir}")
            except Exception as e:
                print(f"⚠️ Could not load progress file: {e}")
                self.completed_dirs = set()
                self.last_processing_dir = None
    
    def load_directory_cache(self):
        """Load cached directory structure to skip discovery"""
        if os.path.exists(self.directory_cache_file):
            try:
                with open(self.directory_cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.directory_cache = cache_data.get('directories', {})
                    cache_time = cache_data.get('cached_at', '')
                    print(f"📁 Loaded directory cache: {len(self.directory_cache)} directories (cached: {cache_time})")
            except Exception as e:
                print(f"⚠️ Could not load directory cache: {e}")
                self.directory_cache = {}
    
    def save_directory_cache(self, directories):
        """Save directory structure for faster future startups"""
        try:
            os.makedirs(self.base_save_dir, exist_ok=True)
            cache_data = {
                'directories': {str(k): v for k, v in directories.items()},
                'cached_at': datetime.now().isoformat(),
                'total_directories': len(directories)
            }
            with open(self.directory_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"💾 Saved directory cache: {len(directories)} directories")
        except Exception as e:
            print(f"⚠️ Could not save directory cache: {e}")
    
    def get_cached_directories(self):
        """Get cached directory structure if available"""
        if self.directory_cache:
            # Convert back to list of tuples
            return [(k, v) for k, v in self.directory_cache.items()]
        return None
    
    def save_progress(self):
        """Save current download progress"""
        try:
            os.makedirs(self.base_save_dir, exist_ok=True)
            progress_data = {
                'completed_dirs': list(self.completed_dirs),
                'last_processing_dir': self.last_processing_dir,
                'last_updated': datetime.now().isoformat(),
                'total_completed_dirs': len(self.completed_dirs)
            }
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save progress: {e}")
    
    def is_directory_completed(self, dir_path):
        """Check if a directory has been fully processed"""
        return dir_path in self.completed_dirs
    
    def mark_directory_completed(self, dir_path):
        """Mark a directory as fully processed"""
        self.completed_dirs.add(dir_path)
        self.last_processing_dir = dir_path
        self.save_progress()
        print(f"✅ Completed directory: {dir_path}")
    
    def set_processing_directory(self, dir_path):
        """Mark a directory as currently being processed"""
        self.last_processing_dir = dir_path
        self.save_progress()
    
    def should_skip_directory(self, dir_path):
        """Determine if we should skip this directory based on resume logic"""
        # If we have a last processing directory, skip everything before it
        if self.last_processing_dir and dir_path < self.last_processing_dir:
            return True
        
        # Skip if already completed
        return self.is_directory_completed(dir_path)

def download_file(file_url, save_path):
    """Downloads a single file from a URL and saves it to a path with optimized settings."""
    try:
        # 🚀 OPTIMIZED REQUEST SETTINGS FOR FASTER DOWNLOADS
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'ArgoDownloader/2.0 (Research Purpose)',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': '*/*'
        })
        
        # 🔥 ENHANCED CONNECTION POOLING
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            pool_connections=50,
            pool_maxsize=100,
            max_retries=2
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        with session.get(file_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            
            with open(save_path, 'wb') as f:
                # 🚀 INCREASED CHUNK SIZE FOR BETTER BANDWIDTH UTILIZATION (512KB)
                for chunk in r.iter_content(chunk_size=524288):
                    if chunk:
                        f.write(chunk)
        
        file_size = os.path.getsize(save_path) / (1024 * 1024)  # MB
        return True, file_size
        
    except requests.exceptions.RequestException as e:
        return False, 0

def get_links_fast(url):
    """ULTRA-FAST directory listing with optimized session"""
    try:
        # Use global session for connection reuse
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'ArgoDownloader/2.0 (Research Purpose)',
            'Connection': 'keep-alive',
            'Accept': 'text/html',
            'Cache-Control': 'no-cache'
        })
        
        # Faster timeout for directory listings
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [urljoin(url, a.get('href')) for a in soup.find_all('a')]
        return links
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching directory {url}: {e}")
        return []

def scan_directory_parallel(directory_url_list, max_workers=20):
    """PARALLEL directory scanning for ultra-fast discovery"""
    print(f"🚀 Parallel scanning {len(directory_url_list)} directories with {max_workers} workers...")
    
    all_results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as scanner_executor:
        # Submit all directory scan jobs
        future_to_url = {
            scanner_executor.submit(get_links_fast, url): url 
            for url in directory_url_list
        }
        
        # Collect results with progress bar
        with tqdm(total=len(future_to_url), desc="🔍 Directory Scanning", unit="dirs") as scan_pbar:
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    links = future.result()
                    all_results[url] = links
                    scan_pbar.update(1)
                except Exception as e:
                    print(f"❌ Failed to scan {url}: {e}")
                    all_results[url] = []
                    scan_pbar.update(1)
    
    return all_results

def main():
    base_url = "https://www.ncei.noaa.gov/data/oceans/argo/gadr/data/indian/"
    base_save_dir = "indian_ocean_data"
    
    # 🚀 NETWORK SATURATION SETTINGS
    print("🔥 Choose your download intensity:")
    print("1. Conservative (500 threads) - Your proven setup")
    print("2. Aggressive (750 threads) - Push network harder")
    print("3. Maximum (1000 threads) - Target full bandwidth")
    print("4. BEAST MODE (1500 threads) - MAXIMUM POWER!")
    
    choice = input("Enter choice (1-4) [default: 1]: ").strip()
    
    thread_configs = {
        '1': 500,
        '2': 750,
        '3': 1000,
        '4': 1500
    }
    
    num_threads = thread_configs.get(choice, 500)
    
    print(f"🚀 Starting smart resume downloads with {num_threads} parallel threads...")
    print(f"📁 Saving to: {base_save_dir}")
    
    # Initialize smart resume tracker
    resume_tracker = SmartResumeTracker(base_save_dir)
    
    start_time = time.time()
    downloaded_files = 0
    skipped_files = 0
    skipped_dirs = 0
    total_size_mb = 0
    
    # PHASE 1: LIGHTNING-FAST RESUME WITHOUT DIRECTORY SCANNING
    print("⚡ LIGHTNING-FAST RESUME MODE...")
    
    # Check if we have cached directories
    cached_directories = resume_tracker.get_cached_directories()
    
    if cached_directories:
        print(f"🚀 Using cached directory structure: {len(cached_directories)} directories")
        all_directories = cached_directories
        
        # ULTRA-FAST RESUME: Skip directly to resume point
        if resume_tracker.last_processing_dir:
            print(f"⚡ INSTANT RESUME from: {resume_tracker.last_processing_dir}")
            # Filter directories to only those at or after resume point
            resume_index = None
            for i, (dir_path, _) in enumerate(all_directories):
                if dir_path == resume_tracker.last_processing_dir:
                    resume_index = i
                    break
            
            if resume_index is not None:
                all_directories = all_directories[resume_index:]
                print(f"🚀 SKIPPED {resume_index} completed directories - INSTANT START!")
            else:
                print(f"⚠️ Resume point not found in cache, starting from beginning")
        
        discovery_time = 0
    else:
        print("🔍 No cache found, performing ONE-TIME directory discovery...")
        
        # Step 1: Discover all directories in parallel batches (ONLY FIRST TIME)
        all_directories = []
        dirs_to_scan = [base_url]
        discovery_start = time.time()
        
        while dirs_to_scan:
            print(f"🔍 Batch scanning {len(dirs_to_scan)} directories...")
            
            # Parallel scan this batch of directories
            scan_results = scan_directory_parallel(dirs_to_scan, max_workers=50)  # More workers
            
            new_dirs_to_scan = []
            
            for dir_url, links in scan_results.items():
                dir_path_name = dir_url.replace(base_url, "").strip('/')
                all_directories.append((dir_path_name, dir_url))
                
                # Find subdirectories for next batch
                for link in links:
                    if link.endswith('/'):
                        if link != dir_url and link != urljoin(dir_url, '../'):
                            new_dirs_to_scan.append(link)
            
            dirs_to_scan = new_dirs_to_scan
            print(f"📂 Found {len(all_directories)} directories so far...")
        
        discovery_time = time.time() - discovery_start
        print(f"⚡ Directory discovery completed in {discovery_time:.1f} seconds!")
        
        # Save to cache for INSTANT future startups
        directory_dict = {path: url for path, url in all_directories}
        resume_tracker.save_directory_cache(directory_dict)
    
    print(f"📂 Processing {len(all_directories)} directories")
    
    # PHASE 2: INSTANT DOWNLOAD WITHOUT SCANNING
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        
        # Sort directories to ensure consistent processing order
        all_directories.sort(key=lambda x: x[0])  # Sort by directory path
        
        print(f"🚀 LAUNCHING {num_threads} DOWNLOAD THREADS...")
        
        for dir_path_name, current_dir_url in all_directories:
            # 🚀 ULTRA-FAST RESUME: Skip completed directories instantly
            if resume_tracker.is_directory_completed(dir_path_name):
                print(f"⏭️ SKIPPING completed: {dir_path_name}")
                skipped_dirs += 1
                continue
            
            # Mark this directory as being processed
            resume_tracker.set_processing_directory(dir_path_name)
            
            current_save_dir = os.path.join(base_save_dir, dir_path_name)
            os.makedirs(current_save_dir, exist_ok=True)
            
            print(f"📂 Processing: {dir_path_name or 'root'}")
            
            # FAST file discovery - only scan when needed
            links = get_links_fast(current_dir_url)
            
            # Process ALL .nc files in this directory instantly
            directory_files = []
            for link in links:
                if link.endswith('.nc'):
                    file_name = os.path.basename(link)
                    save_path = os.path.join(current_save_dir, file_name)
                    
                    if not os.path.exists(save_path):
                        # Submit download immediately - no waiting!
                        future = executor.submit(download_file, file_url=link, save_path=save_path)
                        futures.append((future, dir_path_name, file_name))
                    else:
                        # Count existing file
                        existing_size = os.path.getsize(save_path) / (1024 * 1024)
                        total_size_mb += existing_size
                        skipped_files += 1
                    
                    directory_files.append(file_name)
            
            # Quick check if directory is complete
            existing_files = [f for f in os.listdir(current_save_dir) if f.endswith('.nc')] if os.path.exists(current_save_dir) else []
            
            if len(existing_files) >= len(directory_files) and len(directory_files) > 0:
                # Directory is complete!
                resume_tracker.mark_directory_completed(dir_path_name)
                print(f"✅ Directory COMPLETE: {dir_path_name} ({len(existing_files)} files)")
            elif len(directory_files) > 0:
                files_to_download = len(directory_files) - len(existing_files)
                print(f"📥 Directory ACTIVE: {dir_path_name} (downloading {files_to_download} files)")
        
        # PHASE 3: MONITOR DOWNLOADS WITH BLAZING SPEED
        if futures:
            print(f"\n🔥 MONITORING {len(futures)} DOWNLOADS...")
            
            with tqdm(
                total=len(futures), 
                desc="🚀 BEAST MODE DOWNLOADING", 
                unit="files",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}"
            ) as pbar:
                
                completed_dirs_this_session = set()
                
                for future, dir_name, file_name in as_completed(futures):
                    try:
                        success, file_size = future.result()
                        if success:
                            downloaded_files += 1
                            total_size_mb += file_size
                            
                            # Quick directory completion check
                            if dir_name not in completed_dirs_this_session:
                                save_dir = os.path.join(base_save_dir, dir_name)
                                if os.path.exists(save_dir):
                                    current_files = len([f for f in os.listdir(save_dir) if f.endswith('.nc')])
                                    # Simple heuristic: if we have a reasonable number of files, mark complete
                                    if current_files >= 1000:  # Most directories have 2000+ files
                                        resume_tracker.mark_directory_completed(dir_name)
                                        completed_dirs_this_session.add(dir_name)
                        
                        # Calculate REAL-TIME performance
                        current_time = time.time() - start_time
                        if current_time > 0:
                            files_per_sec = (downloaded_files + skipped_files) / current_time
                            mb_per_second = total_size_mb / current_time
                            mbps = mb_per_second * 8
                            
                            pbar.set_postfix({
                                'Speed': f'{files_per_sec:.0f}/s',
                                'BW': f'{mbps:.0f}Mbps',
                                'Dirs': len(completed_dirs_this_session)
                            })
                        
                        pbar.update(1)
                        
                    except Exception as e:
                        pbar.update(1)
        else:
            print("🎉 ALL FILES ALREADY DOWNLOADED!")
            
            current_save_dir = os.path.join(base_save_dir, dir_path_name)
            os.makedirs(current_save_dir, exist_ok=True)
            
            print(f"📂 Processing: {dir_path_name or 'root'}")
            links = get_links_fast(current_dir_url)
            
            # Collect all .nc files in this directory
            nc_files_in_dir = []
            for link in links:
                if link.endswith('.nc'):
                    file_name = os.path.basename(link)
                    save_path = os.path.join(current_save_dir, file_name)
                    nc_files_in_dir.append((link, save_path, file_name))
            
            # Check existing files and queue downloads
            files_to_download = []
            existing_files_count = 0
            
            for file_url, save_path, file_name in nc_files_in_dir:
                if os.path.exists(save_path):
                    # File already exists
                    existing_size = os.path.getsize(save_path) / (1024 * 1024)
                    total_size_mb += existing_size
                    existing_files_count += 1
                    skipped_files += 1
                else:
                    # File needs to be downloaded
                    files_to_download.append((file_url, save_path))
            
            # Status report for this directory
            total_files_in_dir = len(nc_files_in_dir)
            
            if existing_files_count == total_files_in_dir and total_files_in_dir > 0:
                # Directory is complete
                resume_tracker.mark_directory_completed(dir_path_name)
                print(f"✅ Directory COMPLETE: {dir_path_name} ({existing_files_count} files)")
            elif existing_files_count > 0:
                print(f"🔄 Directory PARTIAL: {dir_path_name} ({existing_files_count}/{total_files_in_dir} files exist)")
            else:
                print(f"📥 Directory NEW: {dir_path_name} ({total_files_in_dir} files to download)")
            
            # Submit download jobs for missing files
            if files_to_download:
                for file_url, save_path in files_to_download:
                    future = executor.submit(download_file, file_url, save_path)
                    futures.append((future, dir_path_name, len(files_to_download), total_files_in_dir))
            elif total_files_in_dir > 0:
                # Directory was already complete, mark it
                resume_tracker.mark_directory_completed(dir_path_name)
        
        # Phase 3: Monitor downloads with enhanced progress tracking
        if futures:
            print(f"\n📥 Downloading {len(futures)} missing files with {num_threads} threads...")
            
            with tqdm(
                total=len(futures), 
                desc="🚀 Smart Resume Download", 
                unit="files",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}"
            ) as pbar:
                
                completed_dirs_this_session = set()
                
                for future, dir_name, files_in_dir, total_files_expected in as_completed(futures):
                    try:
                        success, file_size = future.result()
                        if success:
                            downloaded_files += 1
                            total_size_mb += file_size
                            
                            # Check if this directory is now complete
                            if dir_name not in completed_dirs_this_session:
                                save_dir = os.path.join(base_save_dir, dir_name)
                                if os.path.exists(save_dir):
                                    current_files = len([f for f in os.listdir(save_dir) if f.endswith('.nc')])
                                    
                                    if current_files >= total_files_expected:
                                        resume_tracker.mark_directory_completed(dir_name)
                                        completed_dirs_this_session.add(dir_name)
                        
                        # Calculate real-time network utilization
                        current_time = time.time() - start_time
                        if current_time > 0:
                            files_per_sec = (downloaded_files + skipped_files) / current_time
                            mb_per_second = total_size_mb / current_time
                            mbps = mb_per_second * 8  # Convert to Mbps
                            
                            pbar.set_postfix({
                                'Speed': f'{files_per_sec:.1f}/s',
                                'BW': f'{mbps:.1f}Mbps',
                                'Dirs': len(completed_dirs_this_session)
                            })
                        
                        pbar.update(1)
                        
                    except Exception as e:
                        pbar.update(1)
        else:
            print("🎉 ALL FILES ALREADY DOWNLOADED!")
    
    # Enhanced final statistics
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "🚀"*70)
    print("🎉 SMART RESUME DOWNLOAD COMPLETED!")
    print("🚀"*70)
    print(f"📊 New files downloaded: {downloaded_files}")
    print(f"⏭️ Files skipped (existing): {skipped_files}")
    print(f"📁 Directories skipped: {skipped_dirs}")
    print(f"💾 Total data processed: {total_size_mb:.1f} MB ({total_size_mb/1024:.2f} GB)")
    print(f"⏱️ Total time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"🚀 Threads used: {num_threads}")
    
    if duration > 0 and (downloaded_files + skipped_files) > 0:
        total_files = downloaded_files + skipped_files
        files_per_second = total_files / duration
        mb_per_second = total_size_mb / duration
        mbps_utilized = mb_per_second * 8
        network_utilization = (mbps_utilized / 100) * 100
        
        print(f"📈 Processing speed: {files_per_second:.1f} files/second")
        print(f"🌐 Data speed: {mb_per_second:.1f} MB/second")
        print(f"📡 Bandwidth used: {mbps_utilized:.1f} Mbps")
        print(f"📊 Network utilization: {network_utilization:.1f}% of 100 Mbps")
        
        if mbps_utilized >= 70:
            print("🔥 EXCELLENT! High bandwidth utilization!")
        elif mbps_utilized >= 50:
            print("📈 Good bandwidth usage - consider more threads!")
        else:
            print("⚠️ Low bandwidth usage - try increasing threads!")
    
    print(f"📁 Data saved to: {os.path.abspath(base_save_dir)}")
    print(f"📋 Progress saved to: {resume_tracker.progress_file}")
    print("🚀"*70)

if __name__ == "__main__":
    main()