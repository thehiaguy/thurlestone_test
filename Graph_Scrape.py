import requests

# Your hardcoded API key
api_key = "hM4bggzq9uz0AejSnhyETcnGEtNuVxlc6tsVbeiH" 

# The base URL for the EIA API version 2
base_url = "https://api.eia.gov/v2/"

params = {'api_key': api_key}

try:
    # Make the request to the top-level of the API
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    
    data = response.json()
    
    print("--- Top-Level EIA Data Categories ---")
    for route in data['response']['routes']:
        print(f"- ID: {route['id']:<20} Name: {route['name']}")

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")