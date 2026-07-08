# main.py
import time
from typing import Any

import pandas as pd
from rich import print

# My imports
from src.converter import convert_to_excel, save_to_file
from src.core import (
    enrich_listing_data,
    fetch_all_listings_detailed,
    get_kleinanzeigen_results,
    get_request,
)

def get_apartments(detailed_listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    detailed_apartments: list = []
    
    # Extract the actual data payload safely from memory
    for detail_data in detailed_listings:
        if detail_data.get("success") and "data" in detail_data:
            ad_details = detail_data["data"]
            
            # Check status to filter out sold and deleted listings
            if ad_details.get("status") in ["sold", "deleted"]:
                continue
            
            # Flatten the metadata specifically for apartment searches
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
    
    # Add the detail_id (full url segment) to every listing
    data = enrich_listing_data(data)
    
    # Params for filename
    location: str = params['location']
    search: str = params['query']
    
    # Save the raw data to file as JSON
    output_dir: str = "./output/JSON"
    output_file: str = f"Kleinanzeigen_{search}_{location.replace(" ", "_")}.json"
    save_to_file(output_dir, output_file, data)
    
    # Get only the results list of the response
    results: list[dict[str, Any]] = get_kleinanzeigen_results(data)
    if not results:
        print("[yellow]No listings found matching criteria.[/yellow]")
        return
    
    # Fetch all detailed responses
    raw_detailed_data: list[dict[str, Any]] = fetch_all_listings_detailed(results, BASE_URL, "inserat", 2)
    save_to_file(output_dir, "Detailed_listings.json", raw_detailed_data)
    
    # Extract and clean the apartment specs
    clean_apartments = get_apartments(raw_detailed_data)
    print(clean_apartments)
    
    # Convert to Pandas DataFrame which can be passed and converted to different file types.
    #df: DataFrame = pd.DataFrame(response.json())


if __name__ == "__main__":
    main()
