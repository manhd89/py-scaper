import json
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# Configuration
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)

# Create Chrome driver with headless options
def create_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")  # Bypass sandbox mode
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--remote-debugging-port=9222")  # Configure remote debugging
    chrome_options.add_argument("start-maximized")  # Maximize window
    chrome_options.add_argument("disable-infobars")  # Disable infobars
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument(
        f"user-agent=Mozilla/5.0 (Android 13; Mobile; rv:125.0) Gecko/125.0 Firefox/125.0"
    )

    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Click on 'See more' button if necessary
def click_see_more(driver):
    try:
        see_more_button = driver.find_element(By.ID, "button-list-more")
        if see_more_button:
            logging.info("Clicking 'See more' to load more versions.")
            see_more_button.click()
    except NoSuchElementException:
        logging.info("No 'See more' button found, all versions are already loaded.")
        pass

# Get the latest version of the app
def get_latest_version(app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'

    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    url = f"https://{config['name']}.en.uptodown.com/android/versions"
    
    driver = create_chrome_driver()  # Create driver
    driver.get(url)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")  # Parse HTML from Selenium
    driver.quit()

    version_spans = soup.select('#versions-items-list .version')
    
    versions = [span.text.strip() for span in version_spans]
    highest_version = max(versions)
    
    logging.info(f"Highest version found for {app_name}: {highest_version}")
    return highest_version

# Get download link for a specific version
def get_download_link(version: str, app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'

    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
    
    url = f"https://{config['name']}.en.uptodown.com/android/versions"

    driver = create_chrome_driver()  # Create driver
    driver.get(url)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")

    while True:
        divs = soup.find_all("div", {"data-url": True})
        for div in divs:
            version_span = div.find("span", class_="version")
            if version_span and version_span.text.strip() == version:
                dl_url = div["data-url"]
                
                # Navigate to the version-specific download page
                logging.info(f"Found download page for version {version}, navigating to it...")
                driver.get(dl_url)

                # Parse the download page for the actual download link
                soup = BeautifulSoup(driver.page_source, "html.parser")
                download_button = soup.find('button', {'id': 'detail-download-button'})
                if download_button and download_button.get('data-url'):
                    data_url = download_button.get('data-url')
                    full_url = f"https://dw.uptodown.com/dwn/{data_url}"
                    logging.info(f"Found download link: {full_url}")
                    driver.quit()
                    return full_url

        # If the "See more" button is available, click to load more versions
        click_see_more(driver)
        soup = BeautifulSoup(driver.page_source, "html.parser")

    driver.quit()
    return None

# Download APK or XAPK resource from URL with dynamic extension
def download_resource(url: str, name: str) -> str:
    if not url:
        logging.error(f"Download URL is None. Cannot download {name}.")
        return None

    # Extract file extension from the URL
    file_extension = os.path.splitext(url)[1]  # This will return .apk, .xapk, etc.

    # Dynamically adjust the filename with the correct extension
    filepath = f"./{name}{file_extension}"

    # Using Selenium to initiate download or requests could be better, but we're using Selenium here for consistency
    driver = create_chrome_driver()
    driver.get(url)

    with open(filepath, "wb") as file:
        file.write(driver.page_source.encode('utf-8'))

    driver.quit()

    logging.info(f"Downloaded {name} to {filepath}")
    return filepath

# Main function to download app from Uptodown
def download_uptodown(app_name: str) -> str:
    version = "19.33.35"  # Hardcoded version, you can use get_latest_version(app_name) instead
    download_link = get_download_link(version, app_name)
    filename = f"{app_name}-v{version}"
    
    if download_link:
        return download_resource(download_link, filename)
    else:
        logging.error("Failed to retrieve the download link.")
        return None
