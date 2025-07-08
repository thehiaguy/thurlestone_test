# File: scrape.py

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime

def scrape_sxcoal_inventory():
    """
    Scrapes the sxcoal.com website to find the latest coal inventory report
    and extracts key inventory figures.
    
    Returns:
        pandas.DataFrame: A DataFrame containing the extracted inventory data,
                          or an empty DataFrame if an error occurs.
    """
    
    # The initial search URL for "coal inventory"
    search_url = "https://www.sxcoal.com/news/search?search=%E7%85%A4%E7%82%AD%E5%BA%93%E5%AD%98"
    base_url = "https://www.sxcoal.com"
    
    # Headers to mimic a browser, which is crucial for many websites
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
    }

    try:
        # --- Step 1 & 2: Go to search page and find the latest article link ---
        print(f"Accessing search results page: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status() # Raises an exception for bad status codes (like 404, 500)

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the first link in the main news list, which should be the latest report
        # The 'newsList' class contains the relevant search results
        latest_article_link = soup.select_one('.newsList li a')
        
        if not latest_article_link:
            print("Error: Could not find the latest article link on the search page.")
            return pd.DataFrame()

        article_url = base_url + latest_article_link['href']
        print(f"Found latest article. Scraping: {article_url}")

        # --- Step 3: Scrape the article text ---
        article_response = requests.get(article_url, headers=headers, timeout=15)
        article_response.raise_for_status()
        
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        
        # The main content is in a div with the class 'article-content'. 
        # Getting its text strips out all HTML tags.
        article_text = article_soup.find('div', class_='view-content').get_text()

        # --- Step 4: Extract the numbers using regular expressions ---
        print("\nExtracting data from article text...")
        
        keywords = {
            "北方港（不包括黄骅港）煤炭库存": "Northern Ports (excluding Huanghua)",
            "京唐港煤炭库存": "Jingtang Port",
            "曹妃甸港煤炭库存": "Caofeidian Port"
        }
        
        results = {}

        for keyword_cn, keyword_en in keywords.items():
            # The regex looks for the keyword, followed by optional characters (为, :, ：), 
            # and then captures the number (including decimals).
            # "(\d+\.?\d*)" is the group that captures the number.
            pattern = re.compile(f"{re.escape(keyword_cn)}[为是:：\\s]*(\\d+\\.?\\d*)")
            match = pattern.search(article_text)
            
            if match:
                # The result is in the first captured group
                value = float(match.group(1))
                results[keyword_en] = value
                print(f"  - Found '{keyword_en}': {value} 万吨")
            else:
                results[keyword_en] = "Not found"
                print(f"  - Could not find '{keyword_en}'")

        if not any(val != "Not found" for val in results.values()):
             print("\nCould not extract any data. The article format may have changed.")
             return pd.DataFrame()

        # Format results into a pandas DataFrame for clean display
        df = pd.DataFrame.from_dict(results, orient='index', columns=['Inventory (in 10,000 tons)'])
        df.index.name = "Port"
        
        # Add a timestamp to know when the data was scraped
        df['Scrape Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return df

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the web request: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return pd.DataFrame()


# --- Run the scraper ---
if __name__ == "__main__":
    inventory_data = scrape_sxcoal_inventory()
    
    if not inventory_data.empty:
        print("\n--- Scraping Complete ---")
        print(inventory_data)