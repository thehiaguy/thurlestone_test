# =============================================================================
#
#  EIA Coal Price Scraper
#  ----------------------
#  This script scrapes historical coal price data from a dynamic graph on
#  the EIA website. It works by first extracting the graph's isolated URL
#  without a browser, then using a stealthy automated browser to navigate
#  directly to that URL, click the necessary tab, and extract the data
#  from the chart's JavaScript object in memory.
#
#  Required Libraries:
#  - pandas
#  - curl_cffi
#  - selenium
#  - webdriver-manager
#  - selenium-stealth
#
#  To install all dependencies, run:
#  pip install pandas "curl_cffi>=0.6.0" selenium webdriver-manager selenium-stealth
#
#  To run the script:
#  python scrape_eia.py
#
# =============================================================================

import pandas as pd
from datetime import datetime
import json
import time
import re
import sys  # Used to exit the script cleanly on failure

# Stage 1: Infiltration using a non-browser client
try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("Error: curl_cffi library not found. Please run 'pip install curl_cffi'.")
    sys.exit(1)

# Stage 2: Extraction using a stealth browser
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium_stealth import stealth
except ImportError:
    print("Error: A required Selenium library is not found. Please run 'pip install selenium webdriver-manager selenium-stealth'.")
    sys.exit(1)


# --- Configuration ---
MAIN_PAGE_URL = "https://www.eia.gov/coal/markets/includes/archive2.php"
BASE_URL = "https://www.eia.gov/coal/markets/includes/"
OUTPUT_FILENAME = "eia_coal_prices.csv"


def stage1_infiltrate_and_get_iframe_url():
    """
    Uses a non-browser HTTP client to fetch the main page's raw HTML and
    extract the iframe source URL, avoiding anti-browser scripts.
    """
    try:
        print("[Stage 1] Infiltrating main page to acquire iframe URL...")
        response = cffi_requests.get(
            MAIN_PAGE_URL,
            impersonate="chrome120",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        response.raise_for_status()
        html_content = response.text

        match = re.search(r'<iframe[^>]*src="([^"]+)"', html_content)
        if not match:
            raise Exception("Could not find iframe 'src' URL in the page's HTML.")
        
        iframe_relative_url = match.group(1)
        iframe_src_url = BASE_URL + iframe_relative_url.lstrip('./')
        
        print(f"[Stage 1] Success. Isolated iframe URL: {iframe_src_url}")
        return iframe_src_url

    except Exception as e:
        print(f"\n[Stage 1] FAILED. Could not acquire the iframe URL. Error: {e}")
        return None


def stage2_extract_data_from_iframe(iframe_url):
    """
    Launches a stealthy browser, navigates directly to the isolated iframe,
    clicks the tab, and extracts data from the chart's JavaScript object.
    """
    print("\n[Stage 2] Launching stealth browser to navigate directly to the iframe.")
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Initialize driver here so it can be closed in the finally block
    driver = None
    try:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )

        stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

        print(f"[Stage 2] Navigating to isolated graph application...")
        driver.get(iframe_url)
        
        print("[Stage 2] Waiting for the 'Prices' tab to be clickable...")
        prices_tab_locator = (By.XPATH, "//a[@href='#tabs-prices-1']")
        prices_tab_element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(prices_tab_locator))
        prices_tab_element.click()
        print("[Stage 2] Tab clicked successfully.")
        
        print("[Stage 2] Waiting for graph data to render...")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'highcharts-series-g')))
        time.sleep(2)  # Allow all data series to fully render

        print("[Stage 2] Executing JavaScript to extract data from chart memory...")
        js_script = """
        const chart = Highcharts.charts.find(c => c);
        return chart ? chart.series.map(s => ({ name: s.name, data: s.options.data })) : null;
        """
        extracted_data = driver.execute_script(js_script)
        
        if not extracted_data:
            raise Exception("Could not extract data from Highcharts object.")
            
        print("\n>>> MISSION ACCOMPLISHED. Data has been extracted. <<<")
        return extracted_data

    except Exception as e:
        if driver:
            driver.save_screenshot('extraction_error.png')
        print(f"\n[Stage 2] FAILED. An error occurred during the extraction phase: {e}")
        print("A screenshot 'extraction_error.png' has been saved for debugging.")
        return None
    finally:
        if driver:
            print("\nClosing browser...")
            driver.quit()


def process_and_save_data(data):
    """
    Processes the extracted data into a pandas DataFrame and saves it to a CSV file.
    """
    if not data:
        print("\nNo data to process. Aborting.")
        return

    print("\nProcessing extracted data...")
    all_data_points = []
    for series in data:
        series_name = series.get('name')
        for point in series.get('data', []):
            timestamp_ms, value = point[0], point[1]
            if timestamp_ms is not None and value is not None:
                date = datetime.fromtimestamp(timestamp_ms / 1000)
                all_data_points.append({'Series': series_name, 'Date': date.strftime('%Y-%m-%d'), 'Value': value})

    df = pd.DataFrame(all_data_points)
    df.to_csv(OUTPUT_FILENAME, index=False)

    print(f"\nSuccessfully processed {len(df)} data points.")
    print(f"Data saved to '{OUTPUT_FILENAME}'")
    
    print("\n--- Data Preview ---")
    print(df.head())


if __name__ == "__main__":
    # Main execution block
    iframe_url = stage1_infiltrate_and_get_iframe_url()
    
    if iframe_url:
        final_data = stage2_extract_data_from_iframe(iframe_url)
        process_and_save_data(final_data)
    else:
        print("\nScript terminated due to failure in Stage 1.")