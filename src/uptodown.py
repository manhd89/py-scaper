import json
import logging
import cloudscraper 
from bs4 import BeautifulSoup

# Configuration
scraper = cloudscraper.create_scraper()
scraper.headers.update(
    {'User-Agent': 'Mozilla/5.0 (Android 13; Mobile; rv:125.0) Gecko/125.0 Firefox/125.0'}
)
logging.basicConfig(
  level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)

def get_latest_version(app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    url = f"https://{config['name']}.en.uptodown.com/android/versions"

    response = scraper.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")
    version_spans = soup.select('#versions-items-list .version')
    versions = [span.text for span in version_spans]
    highest_version = max(versions)
    logging.info(f"{highest_version}")    
    return highest_version

def get_download_link(version: str, app_name: str) -> str:
    # Load configuration file
    conf_file_path = f'./apps/uptodown/{app_name}.json'
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    # Initial URL for the app's version list
    url = f"https://{config['name']}.en.uptodown.com/android/versions"
    response = scraper.get(url)
    response.raise_for_status()
    logging.info(f"Fetched base URL: {url}")
    
    # Parse the data-code from the main page
    soup = BeautifulSoup(response.content, "html.parser")
    h1_tag = soup.find('h1', id='detail-app-name')
    
    data_code = h1_tag['data-code']
    logging.info(f"App data-code: {data_code}")
    
    # Loop through pages to find the desired version
    page = 1
    while True:
        page_url = f"https://{config['name']}.en.uptodown.com/android/apps/{data_code}/versions/{page}"
        response = scraper.get(page_url)
        response.raise_for_status()
        
        # Parse JSON response to get version data
        try:
            json_data = response.json()
            version_data = json_data['data'] or []
        except Exception as e:
            logging.error(f"Failed to parse JSON from {page_url}: {e}")
            return None
        
        # Search for the specified version in the current page
        for entry in version_data:
            if entry["version"] == version:
                version_url = entry["versionURL"]
                if not version_url:
                    return None
                
                # Fetch the download link from the version URL
                response = scraper.get(version_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                download_button = soup.find('button', id='detail-download-button')
                
                # Construct the full download URL
                data_url = download_button['data-url']
                full_url = f"https://dw.uptodown.com/dwn/{data_url}"
                return full_url
        
        # Check if all versions on the current page are older than the desired version
        all_versions_lower = all(
            entry["version"] < version
            for entry in version_data
        )
        if all_versions_lower:
            break
        
        # Move to the next page
        page += 1
    
    # Return None if no matching version is found
    return None

def download_resource(url: str, name: str) -> str:
    filepath = f"./{name}"

    with scraper.get(url, stream=True) as res:
        res.raise_for_status()

        final_url = res.url  # Get the final URL after any redirects
        total_size = int(res.headers.get('content-length', 0))
        downloaded_size = 0

        with open(filepath, "wb") as file:
            for chunk in res.iter_content(chunk_size=8192):
                file.write(chunk)
                downloaded_size += len(chunk)
                
        logging.info(
            f"URL:{final_url} [{downloaded_size}/{total_size}] -> \"{name}\" [1]"
        )

    return filepath

def download_uptodown(app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
    version = config['version']

    if not version:
        version = get_latest_version(app_name)
    download_link = get_download_link(version, app_name)
    filename = f"{app_name}-v{version}.apk"
    return download_resource(download_link, filename)
