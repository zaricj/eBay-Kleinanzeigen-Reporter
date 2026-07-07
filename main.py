# main.py
from typing import Any
from rich import print
import requests
import pandas as pd
import time

# My imports
from src.converter import convert_to_excel, save_to_file
from src.core import get_kleinanzeigen_results, enrich_listing_data

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
    
Example Basic Requests:

    GET http://127.0.0.1:8000/inserate?query=fahrrad&location=97720&radius=5&min_price=1000&page_count=1
    
Example Detailed Requests:

    GET http://127.0.0.1:8000/inserate/3402414948-208-6136
"""

def get_request(base_url: str, endpoint: str, params: dict[str, Any] | None = None) -> requests.Response:
    final_url: str = f"{base_url.rstrip('/')}/{endpoint.rstrip('/')}"
    response = requests.get(url=final_url,  params=params, timeout=20)
    response.raise_for_status()
    return response

def get_request_detailed(base_url: str, endpoint: str, id: str, params: dict[str, Any] | None = None) -> requests.Response:
    final_url: str = f"{base_url.rstrip('/')}/{endpoint.rstrip('/')}/{id.rstrip('/')}"
    response = requests.get(url=final_url, params=params, timeout=20)
    response.raise_for_status()
    return response

def fetch_all_listings_detailed(results: list[dict[str, Any]], base_url: str, endpoint: str) -> list[dict[str, Any]]:
    detailed_listings: list = []
    
    print(f"Fetching detailed information for [bold green]{len(results)}[/bold green] listings...")
    
    # Fetch the detailed information for every listing
    for index, item in enumerate(results, 1):
        detail_params = {"batch_id": f"batch_{int(time.time())}"}
        
        try:
            detail_response = get_request_detailed(
                base_url,
                endpoint,
                item["detail_id"],
                params=detail_params
            )
            detail_data = detail_response.json()
            detailed_listings.append(detail_data)
        except Exception as e:
            print(f"[bold red]Error fetching detail for {item.get('detail_id')}: {e}[/bold red]")
        
        time.sleep(1.5)
        
        if index > 1:
            print("[yellow]STOPPING, testing only 2 listings! :)[/yellow]")
            break

    return detailed_listings
        
        
def get_apartments(detailed_listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    detailed_apartments: list = []
    
    # Extract the actual data payload safely from memory
    for detail_data in detailed_listings:
        if detail_data.get("success") and "data" in detail_data:
            ad_details = detail_data["data"]
            
            # Check status to filter out old, unhelpful listings
            if ad_details.get("status") in ["sold", "deleted"]:
                continue
            
            # Flatten the specific metadata you care about for your Excel output
            flat_entry = {
                "ID": ad_details.get("id"),
                "Title": ad_details.get("title"),
                "Price (€)": ad_details.get("price", {}).get("amount"),
                "Negotiable": ad_details.get("price", {}).get("negotiable"),
                "Zip": ad_details.get("location", {}).get("zip"),
                "City": ad_details.get("location", {}).get("city"),
                "Seller Type": ad_details.get("seller", {}).get("type"),
                "URL": ad_details.get("url_redirected"),
                # Extracts specific fields from the properties dictionary dynamically
                "Zimmer": ad_details.get("details", {}).get("Zimmer", "N/A"),
                "Wohnfläche": ad_details.get("details", {}).get("Wohnfläche", "N/A"),
                "Description": ad_details.get("description", "")[:200] + "..." 
            }
            detailed_apartments.append(flat_entry)
            
    return detailed_apartments

def main() -> None:

    BASE_URL: str = "http://127.0.0.1:8000"
    ENDPOINT: str = "inserate"
    
    params: dict[str, Any] = {
    "query": "Mietwohnung",
    "location": "Bad Neustadt a.d. Saale - Bayern",
    "radius": 5,
    #"min_price": 1000,
    "page_count": 1,
}
    print(f"Searching for [bold cyan]{params['query']}[/bold cyan] in [bold cyan]{params['location']}[/bold cyan]...")
    
    # Get all listings
    response = get_request(BASE_URL, ENDPOINT, params)
    data = response.json()
    
    # Add the detail_id to every listing
    data = enrich_listing_data(data)
    
    # Params for filename
    location: str = params['location']
    search: str = params['query']
    
    # Save the raw data to file as JSON
    output_dir: str = "./output/JSON"
    output_file: str = f"Kleinanzeigen_{search}_{location.replace(" ", "_")}.json"
    save_to_file(output_dir, output_file, data)
    
    # Get only the results list of the response
    results = get_kleinanzeigen_results(data)
    if not results:
        print("[yellow]No listings found matching criteria.[/yellow]")
        return
    
    # Fetch all detailed responses
    raw_detailed_data = fetch_all_listings_detailed(results, BASE_URL, "inserat")
    save_to_file(output_dir, "Detailed_listings.json", raw_detailed_data)
    
    # Extract and clean the apartment specs
    clean_apartments = get_apartments(raw_detailed_data)
    print(clean_apartments)
    
    # Convert to Pandas DataFrame which can be passed and converted to different file types.
    #df: DataFrame = pd.DataFrame(response.json())


if __name__ == "__main__":
    main()
