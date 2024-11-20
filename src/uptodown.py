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
    # Load configuration
    with open(f'./apps/uptodown/{app_name}.json', 'r') as file:
        config = json.load(file)

    base_url = f"https://{config['name']}.en.uptodown.com/android"
    response = scraper.get(f"{base_url}/versions")
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, "html.parser")
    data_code = soup.find('h1', id='detail-app-name')['data-code']

    page = 1
    while True:
        response = scraper.get(f"{base_url}/apps/{data_code}/versions/{page}")
        response.raise_for_status()
        version_data = response.json().get('data', [])
        
        for entry in version_data:
            if entry["version"] == version:
                version_page = scraper.get(f"{entry['versionURL']}-x")
                version_page.raise_for_status()
                content_size = len(version_page.content)
                logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
                soup = BeautifulSoup(version_page.content, "html.parser")
                data = soup.find('button', id='detail-download-button')
                logging.info(f'{data}')
                return
                download_url = soup.find('button', id='detail-download-button')['data-url']
                return f"https://dw.uptodown.com/dwn/{download_url}"
        
        if all(entry["version"] < version for entry in version_data):
            break
        page += 1

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
