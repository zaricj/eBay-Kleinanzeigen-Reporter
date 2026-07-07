# test_main.py
from typing import Any
import requests
import pandas as pd

# My imports
from converter import convert_to_excel, save_to_file

# Description: Retrieves a list of listings based on search criteria.
"""
Query Parameters:

    - query (string, optional): The search term (e.g., "fahrrad" to search for bicycles).
    - location (string, optional): The location or postal code to narrow the search (e.g., 10178 for Berlin).
    - radius (integer, optional): The search radius in kilometers from the specified location (e.g., 5 for a 5 km radius).
    - min_price (integer, optional): The minimum price in Euros for the listings (e.g., 200 for at least 200 Euros).
    - max_price (integer, optional): The maximum price in Euros for the listings (e.g., 500 for at most 500 Euros).
    - page_count (integer, optional): The number of pages to search or return (e.g., 5 for the first 5 pages, default is 1, max: 20 pages).
    - min_publish_date (datetime, optional): Stop fetching once a page contains listings published before this datetime. Listings older than the threshold are removed from the final results. Format: YYYY-MM-DDTHH:MM:SS (e.g., 2026-05-03T08:00:00). Useful for intraday runs that should only collect new listings.
    
Example Requests:

    GET http://127.0.0.1:8000/inserate?query=fahrrad&location=97720&radius=5&min_price=1000&page_count=1
"""

def get_request(base_url: str, endpoint: str, params: dict[str, Any] | None = None) -> requests.Response:
    final_url: str = f"{base_url.rstrip('/')}/{endpoint.rstrip('/')}"
    response = requests.get(url=final_url,  params=params, timeout=20)
    response.raise_for_status()
    return response
    

def main_test():
    base_url: str = "https://jsonplaceholder.typicode.com"
    endpoint: str = "posts"
    
    # File
    output_dir: str = "./Output/JSON"
    output_file = "mydata.json"
    
    response = get_request(base_url, endpoint, None)
    response_data = response.json()  # Get the data of the get request in JSON format
    
    save_to_file(output_dir, output_file, response_data)
    
    #df: DataFrame = pd.DataFrame(response_data)
    

if __name__ == "__main__":
    main_test()
