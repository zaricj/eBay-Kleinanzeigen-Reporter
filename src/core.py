import time
from typing import Any

import requests
from rich import print


def get_request(base_url: str, endpoint: str, params: dict[str, Any] | None = None, session: requests.Session | None = None) -> requests.Response:
    client = session or requests
    final_url: str = f"{base_url.rstrip('/')}/{endpoint.rstrip('/')}"
    response = client.get(url=final_url,  params=params, timeout=20)
    response.raise_for_status()
    return response


def get_request_detailed(base_url: str, endpoint: str, id: str, params: dict[str, Any] | None = None, session: requests.Session | None = None) -> requests.Response:
    client = session or requests
    final_url: str = f"{base_url.rstrip('/')}/{endpoint.rstrip('/')}/{id.rstrip('/')}"
    response = client.get(url=final_url, params=params, timeout=20)
    response.raise_for_status()
    return response


def fetch_all_listings_detailed(results: list[dict[str, Any]], base_url: str, endpoint: str, max_listings: int | None = None) -> list[dict[str, Any]]:
    detailed_listings: list = []
    
    print(f"Fetching detailed information for [bold green]{len(results)}[/bold green] listings...")
    
    with requests.Session() as session:
        # Fetch the detailed information for every listing
        for index, item in enumerate(results, 1):
            detail_params = {"batch_id": f"batch_{int(time.time())}"}
        
            try:
                detail_response = get_request_detailed(
                    base_url,
                    endpoint,
                    item["detail_id"],
                    params=detail_params,
                    session=session
                )
                detail_data = detail_response.json()
                detailed_listings.append(detail_data)
            except Exception as e:
                print(f"[bold red]Error fetching detail for {item.get('detail_id')}: {e}.[/bold red]")

            # Sleep to avoid rate limiting
            time.sleep(1.5)

            if max_listings is not None and index == max_listings:
                print(f"[bold yellow]Stopping fetching further listing, because max listings signals was set to {max_listings}.[/bold yellow]")
                break

    return detailed_listings


def get_kleinanzeigen_results(data: dict) -> list[dict[str, Any]]:
    """Returns a list of dictionaries of the 'results' key from the API response. Safely returns empty list on failure."""
    try:
        return data["results"]
    except KeyError:
        print("[bold red]KeyError: 'results' field not found in response payload.[/bold red]")
        return []


def enrich_listing_data(data: dict[str, Any]) -> dict[str, Any]:
    """Adds a 'detail_id' key to original listing from the API response.\n
    The key is the **kleinanzeigen full URL segment** (e.g. 3405045537-203-6136) which is the **recommended** way to search and scrape the listings details"""

    for item in data.get("results", []):
        item["detail_id"] = item["url"].rsplit("/", 1)[-1]

    return data
