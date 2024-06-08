import re
import cloudscraper
import logging
from bs4 import BeautifulSoup

# Keywords to check in the text
criteria = ["APK", "nodpi"]

# Create a scraper with custom browser information
scraper = cloudscraper.create_scraper(
    browser={
        'custom': 'Mozilla/5.0'
    }
)
base_url = "https://www.apkmirror.com"

def get_download_page(org: str,name: str,version: str) -> str:
    url = f"{base_url}/apk/{org}/{name}/{name}-{version.replace('.', '-')}-release/"

    response = scraper.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    rows = soup.find_all('div', class_='table-row headerFont')
    for row in rows:
        row_text = row.get_text()
        if all(criterion in row_text for criterion in criteria):
            sub_url = row.find('a', class_='accent_color')
            if sub_url:
                return base_url + sub_url['href']
    return None

def extract_download_link(page: str) -> str:
    response = scraper.get(page)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    sub_url = soup.find('a', class_='downloadButton')
    if sub_url:
        download_page_url = base_url + sub_url['href']
        response = scraper.get(download_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        sub_url = soup.select_one('a[rel="nofollow"]')
        if sub_url:
            return base_url +  sub_url['href']

    return None

def get_latest_version(name: str,) -> str:
    url = f"{base_url}/uploads/?appcategory={name}"

    response = scraper.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    app_rows = soup.find_all("div", class_="appRow")
    version_pattern = re.compile(r'\d+(\.\d+)*(-[a-zA-Z0-9]+(\.\d+)*)*')

    for row in app_rows:
        version_text = row.find("h5", class_="appRowTitle").a.text.strip()
        if "alpha" not in version_text.lower() and "beta" not in version_text.lower():
            match = version_pattern.search(version_text)
            if match:
                return match.group()

    return None

def download_resource(url: str, name: str) -> str:
    filepath = f"./{name}"

    with scraper.get(url, stream=True) as res:
        res.raise_for_status()

        total_size = int(res.headers.get('content-length', 0))
        downloaded_size = 0

        with open(filepath, "wb") as file:
            for chunk in res.iter_content(chunk_size=8192):
                file.write(chunk)
                downloaded_size += len(chunk)

        logging.info(
            f"URL: {url} [{downloaded_size}/{total_size}] -> {name}"
        )

    return filepath

org = 'x-corp'
name = "twitter'
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
version = get_latest_version(name)        
download_page = get_download_page(org, name, version) 
download_link = extract_download_link(download_page)
filename = f"{name}-v{version}.apk"
download_resource(download_link, filename)
logging.info(f"Downloaded file saved as {filename}")
    
