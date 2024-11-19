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
    if not h1_tag or 'data-code' not in h1_tag.attrs:
        logging.error("Failed to find `data-code` in the app's main page.")
        return None
    
    data_code = h1_tag['data-code']
    logging.info(f"App data-code: {data_code}")
    
    # Loop through pages to find the desired version
    page = 1
    while True:
        page_url = f"https://{config['name']}.en.uptodown.com/android/apps/{data_code}/versions/{page}"
        response = scraper.get(page_url)
        response.raise_for_status()
        logging.info(f"Fetching page: {page_url}")
        
        # Parse JSON response to get version data
        try:
            json_data = response.json()
            version_data = json_data.get('data', [])
        except Exception as e:
            logging.error(f"Failed to parse JSON from {page_url}: {e}")
            return None
        
        # Search for the specified version in the current page
        for entry in version_data:
            if entry.get("version") == version:
                version_url = entry.get("versionURL")
                if not version_url:
                    logging.error(f"No version URL found for version {version}.")
                    return None
                
                # Fetch the download link from the version URL
                response = scraper.get(version_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                download_button = soup.find('button', id='detail-download-button')
                
                if not download_button or 'data-url' not in download_button.attrs:
                    logging.error(f"No download button found for version {version}.")
                    return None
                
                # Construct the full download URL
                data_url = download_button['data-url']
                full_url = f"https://dw.uptodown.com/dwn/{data_url}"
                logging.info(f"Download link found: {full_url}")
                return full_url
        
        # Check if all versions on the current page are older than the desired version
        all_versions_lower = all(
            entry.get("version") < version
            for entry in version_data
        )
        if all_versions_lower:
            logging.info("No newer versions available. Stopping search.")
            break
        
        # Move to the next page
        page += 1
    
    # Return None if no matching version is found
    logging.info(f"No matching version ({version}) found for {app_name}.")
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
    #version = get_latest_version(app_name)
    version = "2023.02.02-release"
    download_link = get_download_link(version, app_name)
    filename = f"{app_name}-v{version}.apk"
    return download_resource(download_link, filename)
