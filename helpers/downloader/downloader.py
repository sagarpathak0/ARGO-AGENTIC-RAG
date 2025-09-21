import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_file(file_url, save_path):
    """Downloads a single file from a URL and saves it to a path."""
    try:
        print(f"Downloading: {file_url}")
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Saved: {save_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {file_url}: {e}")
        return False

def get_links(url):
    """Fetches and parses a directory listing, returning a list of links."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [urljoin(url, a.get('href')) for a in soup.find_all('a')]
        return links
    except requests.exceptions.RequestException as e:
        print(f"Error fetching directory: {e}")
        return []

def main():
    base_url = "https://www.ncei.noaa.gov/data/oceans/argo/gadr/data/indian/"
    base_save_dir = "indian_ocean_data"
    
    # 🚀 INCREASED PARALLEL THREADS FOR FASTER DOWNLOADING
    # Optimal range: 20-50 threads depending on your internet connection
    num_threads = 30  # Increased from 10 to 30 (3x faster!)
    
    # Optional: Even more aggressive for high-speed connections
    # num_threads = 50  # Uncomment for maximum speed (if you have very fast internet)
    
    print(f"🚀 Starting downloads with {num_threads} parallel threads...")
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        
        # A queue to hold directories to process
        dirs_to_process = [base_url]
        
        while dirs_to_process:
            current_dir_url = dirs_to_process.pop(0)
            
            # Create a local path for the current directory
            dir_path_name = current_dir_url.replace(base_url, "").strip('/')
            current_save_dir = os.path.join(base_save_dir, dir_path_name)
            os.makedirs(current_save_dir, exist_ok=True)
            
            links = get_links(current_dir_url)
            
            for link in links:
                if link.endswith('/'):
                    # Found a subdirectory, add it to the queue for processing
                    if link != current_dir_url and link != urljoin(current_dir_url, '../'):
                        dirs_to_process.append(link)
                elif link.endswith('.nc'):
                    # Found an NC file, submit a download job to the thread pool
                    file_name = os.path.basename(link)
                    save_path = os.path.join(current_save_dir, file_name)
                    
                    if not os.path.exists(save_path):
                        future = executor.submit(download_file, link, save_path)
                        futures.append(future)
                    else:
                        print(f"Skipping existing file: {save_path}")

        # Wait for all download jobs to complete and check for results
        for future in as_completed(futures):
            future.result()
            
    print("All downloads have been processed.")

if __name__ == "__main__":
    main()



# import requests
# import os
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin
# from concurrent.futures import ThreadPoolExecutor, as_completed

# # Define the download_file and get_links functions from the previous response here
# def download_file(file_url, save_path):
#     """Downloads a single file from a URL and saves it to a path."""
#     try:
#         print(f"Downloading: {file_url}")
#         with requests.get(file_url, stream=True) as r:
#             r.raise_for_status()
#             with open(save_path, 'wb') as f:
#                 for chunk in r.iter_content(chunk_size=8192):
#                     f.write(chunk)
#         print(f"Saved: {save_path}")
#         return True
#     except requests.exceptions.RequestException as e:
#         print(f"Error downloading {file_url}: {e}")
#         return False

# def get_links(url):
#     """Fetches and parses a directory listing, returning a list of links."""
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, 'html.parser')
#         links = [urljoin(url, a.get('href')) for a in soup.find_all('a')]
#         return links
#     except requests.exceptions.RequestException as e:
#         print(f"Error fetching directory: {e}")
#         return []

# def main():
#     base_url = "https://www.ncei.noaa.gov/data/oceans/argo/gadr/data/indian/"
#     base_save_dir = "indian_ocean_data"
    
#     num_threads = 10
    
#     with ThreadPoolExecutor(max_workers=num_threads) as executor:
#         futures = []
#         dirs_to_process = [base_url]
        
#         # Keep track of directories already processed to avoid infinite loops
#         processed_dirs = set()
        
#         while dirs_to_process:
#             current_dir_url = dirs_to_process.pop(0)
            
#             # Skip if this directory has already been processed
#             if current_dir_url in processed_dirs:
#                 continue
#             processed_dirs.add(current_dir_url)
            
#             # Extract the year from the URL path
#             try:
#                 year_part = current_dir_url.rstrip('/').split('/')[-1]
#                 year = int(year_part)
#                 # Filter logic: only process folders that are 2004 or older
#                 if year < 2006:
#                     print(f"Skipping directory {year_part} as it's after 2006.")
#                     continue
#             except (ValueError, IndexError):
#                 # This will catch the base URL or other non-year directories
#                 pass

#             dir_path_name = current_dir_url.replace(base_url, "").strip('/')
#             current_save_dir = os.path.join(base_save_dir, dir_path_name)
#             os.makedirs(current_save_dir, exist_ok=True)
            
#             links = get_links(current_dir_url)
            
#             for link in links:
#                 if link.endswith('/'):
#                     if link != current_dir_url and link != urljoin(current_dir_url, '../'):
#                         dirs_to_process.append(link)
#                 elif link.endswith('.nc'):
#                     file_name = os.path.basename(link)
#                     save_path = os.path.join(current_save_dir, file_name)
                    
#                     if not os.path.exists(save_path):
#                         future = executor.submit(download_file, link, save_path)
#                         futures.append(future)
#                     else:
#                         print(f"Skipping existing file: {save_path}")
        
#         for future in as_completed(futures):
#             future.result()
            
#     print("All downloads have been processed.")

# if __name__ == "__main__":
#     main()


# import requests
# import os
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin
# from concurrent.futures import ThreadPoolExecutor, as_completed

# # Define the download_file and get_links functions from the previous response here
# def download_file(file_url, save_path):
#     """Downloads a single file from a URL and saves it to a path."""
#     try:
#         print(f"Downloading: {file_url}")
#         with requests.get(file_url, stream=True) as r:
#             r.raise_for_status()
#             with open(save_path, 'wb') as f:
#                 for chunk in r.iter_content(chunk_size=8192):
#                     f.write(chunk)
#         print(f"Saved: {save_path}")
#         return True
#     except requests.exceptions.RequestException as e:
#         print(f"Error downloading {file_url}: {e}")
#         return False

# def get_links(url):
#     """Fetches and parses a directory listing, returning a list of links."""
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, 'html.parser')
#         links = [urljoin(url, a.get('href')) for a in soup.find_all('a')]
#         return links
#     except requests.exceptions.RequestException as e:
#         print(f"Error fetching directory: {e}")
#         return []

# def main():
#     base_url = "https://www.ncei.noaa.gov/data/oceans/argo/gadr/data/indian/"
#     base_save_dir = "indian_ocean_data"
    
#     num_threads = 10
    
#     with ThreadPoolExecutor(max_workers=num_threads) as executor:
#         futures = []
#         dirs_to_process = [base_url]
        
#         # Keep track of directories already processed to avoid infinite loops
#         processed_dirs = set()
        
#         while dirs_to_process:
#             current_dir_url = dirs_to_process.pop(0)
            
#             if current_dir_url in processed_dirs:
#                 continue
#             processed_dirs.add(current_dir_url)
            
#             # Extract the year from the URL path
#             try:
#                 year_part = current_dir_url.rstrip('/').split('/')[-1]
#                 year = int(year_part)
                
#                 # --- NEW FILTERING LOGIC ---
#                 # Only process folders from 2005 to 2020 (inclusive)
#                 if not (2005 <= year <= 2020):
#                     print(f"Skipping directory {year_part} as it's outside the 2005-2020 range.")
#                     continue
#                 # --- END OF NEW LOGIC ---
                
#             except (ValueError, IndexError):
#                 # This will catch the base URL or other non-year directories
#                 pass

#             dir_path_name = current_dir_url.replace(base_url, "").strip('/')
#             current_save_dir = os.path.join(base_save_dir, dir_path_name)
#             os.makedirs(current_save_dir, exist_ok=True)
            
#             links = get_links(current_dir_url)
            
#             for link in links:
#                 if link.endswith('/'):
#                     if link != current_dir_url and link != urljoin(current_dir_url, '../'):
#                         dirs_to_process.append(link)
#                 elif link.endswith('.nc'):
#                     file_name = os.path.basename(link)
#                     save_path = os.path.join(current_save_dir, file_name)
                    
#                     if not os.path.exists(save_path):
#                         future = executor.submit(download_file, link, save_path)
#                         futures.append(future)
#                     else:
#                         print(f"Skipping existing file: {save_path}")
        
#         for future in as_completed(futures):
#             future.result()
            
#     print("All downloads have been processed.")

# if __name__ == "__main__":
#     main()


import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_file(file_url, save_path):
    """Downloads a single file from a URL and saves it to a path."""
    try:
        print(f"Downloading: {file_url}")
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Saved: {save_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {file_url}: {e}")
        return False

def get_links(url):
    """Fetches and parses a directory listing, returning a list of links."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [urljoin(url, a.get('href')) for a in soup.find_all('a')]
        return links
    except requests.exceptions.RequestException as e:
        print(f"Error fetching directory: {e}")
        return []

def main():
    base_url = "https://www.ncei.noaa.gov/data/oceans/argo/gadr/data/indian/"
    base_save_dir = "indian_ocean_data"
    
    # Use a thread pool to handle concurrent downloads
    # The number of threads can be adjusted for your network speed
    num_threads = 10
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        
        # A queue to hold directories to process
        # Only start with the 2005 folder and its subdirectories
        dirs_to_process = [base_url + "2007/"]
        
        while dirs_to_process:
            current_dir_url = dirs_to_process.pop(0)
            
            # Create a local path for the current directory
            dir_path_name = current_dir_url.replace(base_url, "").strip('/')
            current_save_dir = os.path.join(base_save_dir, dir_path_name)
            os.makedirs(current_save_dir, exist_ok=True)
            
            links = get_links(current_dir_url)
            
            for link in links:
                if link.endswith('/'):
                    # Found a subdirectory, add it to the queue for processing
                    if link != current_dir_url and link != urljoin(current_dir_url, '../'):
                        dirs_to_process.append(link)
                elif link.endswith('.nc'):
                    # Found an NC file, submit a download job to the thread pool
                    file_name = os.path.basename(link)
                    save_path = os.path.join(current_save_dir, file_name)
                    
                    if not os.path.exists(save_path):
                        future = executor.submit(download_file, link, save_path)
                        futures.append(future)
                    else:
                        print(f"Skipping existing file: {save_path}")

        # Wait for all download jobs to complete and check for results
        for future in as_completed(futures):
            future.result()
            
    print("All downloads have been processed.")

if __name__ == "__main__":
    main()


# import requests
# import os
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin
# from concurrent.futures import ThreadPoolExecutor, as_completed

# def download_file(file_url, save_path):
#     """Downloads a single file from a URL and saves it to a path."""
#     try:
#         print(f"Downloading: {file_url}")
#         with requests.get(file_url, stream=True) as r:
#             r.raise_for_status()
#             with open(save_path, 'wb') as f:
#                 for chunk in r.iter_content(chunk_size=8192):
#                     f.write(chunk)
#         print(f"Saved: {save_path}")
#         return True
#     except requests.exceptions.RequestException as e:
#         print(f"Error downloading {file_url}: {e}")
#         return False

# def get_links(url):
#     """Fetches and parses a directory listing, returning a list of links."""
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, 'html.parser')
#         links = [urljoin(url, a.get('href')) for a in soup.find_all('a')]
#         return links
#     except requests.exceptions.RequestException as e:
#         print(f"Error fetching directory: {e}")
#         return []

# def main():
#     base_url = "https://www.ncei.noaa.gov/data/oceans/argo/gadr/data/indian/"
#     base_save_dir = "indian_ocean_data"
    
#     num_threads = 10
    
#     with ThreadPoolExecutor(max_workers=num_threads) as executor:
#         futures = []
        
#         # A queue to hold directories to process
#         dirs_to_process = [base_url]
#         processed_dirs = set()
        
#         while dirs_to_process:
#             current_dir_url = dirs_to_process.pop(0)
            
#             if current_dir_url in processed_dirs:
#                 continue
#             processed_dirs.add(current_dir_url)
            
#             # Extract the year from the URL path
#             try:
#                 year_part = current_dir_url.rstrip('/').split('/')[-1]
#                 year = int(year_part)
                
#                 # --- NEW FILTERING LOGIC ---
#                 # Only process folders from 2006 to 2020 (inclusive)
#                 if not (2006 <= year <= 2020):
#                     print(f"Skipping directory {year_part} as it's outside the 2006-2020 range.")
#                     continue
#                 # --- END OF NEW LOGIC ---
                
#             except (ValueError, IndexError):
#                 # This will catch the base URL or other non-year directories
#                 pass

#             dir_path_name = current_dir_url.replace(base_url, "").strip('/')
#             current_save_dir = os.path.join(base_save_dir, dir_path_name)
#             os.makedirs(current_save_dir, exist_ok=True)
            
#             links = get_links(current_dir_url)
            
#             for link in links:
#                 if link.endswith('/'):
#                     if link != current_dir_url and link != urljoin(current_dir_url, '../'):
#                         dirs_to_process.append(link)
#                 elif link.endswith('.nc'):
#                     file_name = os.path.basename(link)
#                     save_path = os.path.join(current_save_dir, file_name)
                    
#                     if not os.path.exists(save_path):
#                         future = executor.submit(download_file, link, save_path)
#                         futures.append(future)
#                     else:
#                         print(f"Skipping existing file: {save_path}")
        
#         for future in as_completed(futures):
#             future.result()
            
#     print("All downloads have been processed.")

# if __name__ == "__main__":
#     main()