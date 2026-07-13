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
    flatten_listings_data,
)



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
    save_to_file(output_dir, f"Detailed_Kleinanzeigen_{search}_{location}.json", raw_detailed_data)
    
    # Extract and clean the listings data
    flat_data = flatten_listings_data(raw_detailed_data)
    print(flat_data)

    # Convert to Pandas DataFrame which can be passed and converted to different file types.
    #df: DataFrame = pd.DataFrame(response.json())


if __name__ == "__main__":
    main()
