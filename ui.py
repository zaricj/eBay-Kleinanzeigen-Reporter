from typing import Any
import json
from pathlib import Path
import time
from datetime import datetime
import requests
import pandas as pd
from nicegui import ui, run

# Configure Dark Mode globally
ui.dark_mode(True)

# Global tracking flags for cancellation operations
abort_requested = False
is_running = False

def get_request(base_url: str, endpoint: str, params: dict[str, Any] | None = None, session: requests.Session | None = None) -> requests.Response:
    client = session or requests
    final_url: str = f"{base_url.rstrip('/')}/{endpoint.rstrip('/')}"
    response = client.get(url=final_url, params=params, timeout=20)
    response.raise_for_status()
    return response


def get_request_detailed(base_url: str, endpoint: str, id: str, params: dict[str, Any] | None = None, session: requests.Session | None = None) -> requests.Response:
    client = session or requests
    final_url: str = f"{base_url.rstrip('/')}/{endpoint.rstrip('/')}/{id.rstrip('/')}"
    response = client.get(url=final_url, params=params, timeout=20)
    response.raise_for_status()
    return response


def fetch_all_listings_detailed(results: list[dict[str, Any]], base_url: str, endpoint: str, max_listings: int | None = None, log_callback=print) -> list[dict[str, Any]]:
    global abort_requested
    detailed_listings: list = []
    log_callback(f"Fetching detailed information for {len(results)} listings...")
    
    with requests.Session() as session:
        for index, item in enumerate(results, 1):
            # Check the stop flag at the start of every loop iteration
            if abort_requested:
                log_callback("[WARNING] Abort signal caught! Stopping processing loops immediately.")
                break
                
            detail_params = {"batch_id": f"batch_{int(time.time())}"}
            try:
                detail_response = get_request_detailed(
                    base_url, endpoint, item["detail_id"], params=detail_params, session=session
                )
                detail_data = detail_response.json()
                detailed_listings.append(detail_data)
                log_callback(f"Successfully fetched detail for item {index}.")
            except Exception as e:
                log_callback(f"Error fetching detail for {item.get('detail_id')}: {e}.")

            # Dynamic incremental sleeping that reacts immediately to abort actions
            for _ in range(15):
                if abort_requested:
                    break
                time.sleep(0.1)

            if max_listings is not None and index >= max_listings:
                log_callback(f"Stopping fetching further listings; maximum set to {max_listings}.")
                break

    return detailed_listings


def get_kleinanzeigen_results(data: dict, log_callback=print) -> list[dict[str, Any]]:
    try:
        return data["results"]
    except KeyError:
        log_callback("KeyError: 'results' field not found in response payload.")
        return []


def enrich_listing_data(data: dict[str, Any]) -> dict[str, Any]:
    for item in data.get("results", []):
        if "url" in item:
            item["detail_id"] = item["url"].rsplit("/", 1)[-1]
    return data


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_to_file(destination_dir: str, filename: str, data: Any, log_callback=print) -> None:
    buffer: int = 65512
    filepath: Path = Path(destination_dir) / filename
    extension: str = Path(filename).suffix
    ensure_dir(Path(destination_dir))
    
    if not extension:
        raise OSError(f"Filename missing extension! Entered: '{filepath.__str__()}'")
    
    match extension:
        case ".txt":
            with open(file=filepath, mode="w", buffering=buffer, encoding="utf-8") as f:
                f.write(data)
            log_callback(f"Text file saved to: '{filepath.__str__()}'")
        case ".json":
            with open(file=filepath, mode="w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            log_callback(f"JSON file saved to: '{filepath.__str__()}'")
        case _:
            raise ValueError(f"Unsupported extension: {extension}")


def flatten_listings_data(detailed_listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened_records: list = []
    
    for detail_data in detailed_listings:
        if detail_data.get("success") and "data" in detail_data:
            ad_details = detail_data["data"]
            
            if ad_details.get("status") in ["sold", "deleted"]:
                continue
                
            flat_entry = {
                "ID": ad_details.get("id"),
                "Title": ad_details.get("title"),
                "Price (€)": ad_details.get("price", {}).get("amount"),
                "Negotiable": ad_details.get("price", {}).get("negotiable"),
                "Zip": ad_details.get("location", {}).get("zip"),
                "City": ad_details.get("location", {}).get("city"),
                "Seller Type": ad_details.get("seller", {}).get("type"),
                "URL": ad_details.get("url_redirected"),
            }
            
            category_details = ad_details.get("details", {})
            for key, val in category_details.items():
                flat_entry[key] = val
                
            desc = ad_details.get("description", "")
            flat_entry["Description"] = desc[:100] + "..." if len(desc) > 100 else desc
            
            flattened_records.append(flat_entry)
            
    return flattened_records


def convert_to_excel(df: pd.DataFrame, excel_output_file: str) -> None:
    sheet_name: str = "Data"
    with pd.ExcelWriter(excel_output_file, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        worksheet = writer.sheets[sheet_name]
        max_row, max_col = df.shape
        column_settings = [{"header": col} for col in df.columns]
        worksheet.add_table(
            0, 0, max_row, max_col - 1,
            {
                "columns": column_settings,
                "style": "Table Style Medium 16",
                "name": f"{sheet_name[:30]}",
                "autofilter": True,
            },
        )
        worksheet.set_column(0, max_col - 1, 18)


# --- NICEGUI UI MANAGEMENT ---

def log_to_ui(message: str):
    current_time = time.strftime("%H:%M:%S")
    formatted_msg = f"[{current_time}] {message}"
    print(formatted_msg)
    log_viewer.push(formatted_msg)


def request_abort():
    global abort_requested
    abort_requested = True
    log_to_ui("[USER ACTION] Abort requested. Gracefully wrapping up current items...")
    ui.notify("Aborting scraper pipeline...", type='warning')


async def run_scraper():
    global abort_requested, is_running
    abort_requested = False
    is_running = True
    
    # Toggle interface run buttons visibility state 
    run_btn.set_visibility(False)
    abort_btn.set_visibility(True)
    
    log_viewer.clear()
    log_to_ui("Starting scraping routine...")
    
    base_url = base_url_input.value
    endpoint = endpoint_input.value
    
    params: dict[str, Any] = {}
    if query_input.value:
        params["query"] = query_input.value
    if location_input.value:
        params["location"] = location_input.value
    if radius_input.value is not None:
        params["radius"] = int(radius_input.value)
    if min_price_input.value is not None:
        params["min_price"] = int(min_price_input.value)
    if max_price_input.value is not None:
        params["max_price"] = int(max_price_input.value)
    if page_count_input.value is not None:
        params["page_count"] = min(int(page_count_input.value), 20)
        
    if publish_date_input.value:
        try:
            datetime.fromisoformat(publish_date_input.value)
            params["min_publish_date"] = publish_date_input.value
        except ValueError:
            log_to_ui("Error: Format of 'Min Publish Date' is invalid. Use YYYY-MM-DDTHH:MM:SS.")
            ui.notify("Invalid date-time parameter format", type='negative')
            is_running = False
            run_btn.set_visibility(True)
            abort_btn.set_visibility(False)
            return

    max_listings = int(max_listings_input.value) if max_listings_input.value else None
    
    try:
        response = await run.io_bound(get_request, base_url, endpoint, params)
        data = enrich_listing_data(response.json())
        
        if save_json_checkbox.value:
            output_dir = "./output/JSON"
            clean_query = params.get('query', 'search')
            clean_loc = str(params.get('location', 'any')).replace(" ", "_").replace(".", "")
            await run.io_bound(save_to_file, output_dir, f"Kleinanzeigen_{clean_query}_{clean_loc}.json", data, log_to_ui)
        
        results = get_kleinanzeigen_results(data, log_to_ui)
        if not results:
            log_to_ui("No base items found matching criteria.")
            table_view.rows = []
            return
            
        # Call long-running network task
        raw_detailed_data = await run.io_bound(
            fetch_all_listings_detailed, results, base_url, "inserat", max_listings, log_to_ui
        )
        
        # Save whatever items were successfully fetched before truncation or normal exit
        if save_json_checkbox.value and raw_detailed_data:
            await run.io_bound(save_to_file, output_dir, f"Detailed_Kleinanzeigen_{clean_query}_{clean_loc}.json", raw_detailed_data, log_to_ui)
        
        log_to_ui("Processing metadata structures for retrieved data subsets...")
        flat_data = flatten_listings_data(raw_detailed_data)
        
        if flat_data:
            all_keys = []
            for item in flat_data:
                for k in item.keys():
                    if k not in all_keys:
                        all_keys.append(k)

            table_view.columns = []
            for key in all_keys:
                col_config = {
                    'name': key,
                    'label': key,
                    'field': key,
                    'required': True,
                    'align': 'left',
                    'sortable': True,
                }
                if key == "URL":
                    col_config['style'] = 'max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'
                elif key == "Description":
                    col_config['style'] = 'max-width: 250px; white-space: normal; line-height: 1.4;'
                elif key in ["Title", "Zimmer", "Wohnfläche", "Haustyp"]:
                    col_config['style'] = 'min-width: 110px; font-weight: 500;'
                else:
                    col_config['style'] = 'min-width: 90px;'
                table_view.columns.append(col_config)
                
            table_view.rows = flat_data
            
            if abort_requested:
                log_to_ui(f"Pipeline Interrupted! Rendered {len(flat_data)} partially collected records safely.")
                ui.notify(f"Run stopped. Loaded {len(flat_data)} items.", type='warning')
            else:
                log_to_ui(f"Successfully loaded all {len(flat_data)} items into view!")
                ui.notify("Scraping completed successfully!", type='positive')
        else:
            table_view.rows = []
            log_to_ui("No valid data elements retrieved.")
            
    except Exception as e:
        log_to_ui(f"An error occurred during execution: {e}")
    finally:
        is_running = False
        run_btn.set_visibility(True)
        abort_btn.set_visibility(False)


async def manual_export_excel():
    if not table_view.rows:
        ui.notify("No current table data found to export!", type='warning')
        return
        
    try:
        log_to_ui("Compiling and processing visible dataset records into spreadsheet sheets...")
        df = pd.DataFrame(table_view.rows)
        excel_dir = "./output/Excel"
        ensure_dir(Path(excel_dir))
        
        filename = f"Export_{int(time.time())}.xlsx"
        full_path = f"{excel_dir}/{filename}"
        
        await run.io_bound(convert_to_excel, df, full_path)
        log_to_ui(f"Excel dataset compiled successfully! Saved to: {full_path}")
        ui.notify("Excel file exported successfully!", type='positive')
    except Exception as ex:
        log_to_ui(f"Excel build task execution error: {ex}")
        ui.notify("Export failed", type='negative')


# --- MODERN FULL-WIDTH DASHBOARD LAYOUT DESIGN ---

ui.add_css('''
    .custom-dashboard-table .q-table th {
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        color: #a78bfa !important;
        background-color: #18181b !important;
        padding: 12px 16px !important;
        border-bottom: 2px solid #27272a !important;
    }
    .custom-dashboard-table .q-table td {
        padding: 14px 16px !important;
        font-size: 0.85rem !important;
        border-bottom: 1px solid #27272a !important;
    }
    .custom-dashboard-table .q-table tbody tr:nth-child(even) {
        background-color: #141416 !important;
    }
    .custom-dashboard-table .q-table tbody tr:hover {
        background-color: #242427 !important;
        transition: background-color 0.2s ease;
    }
    .url-link-btn {
        color: #3b82f6;
        text-decoration: none;
        font-weight: 500;
    }
    .url-link-btn:hover {
        text-decoration: underline;
        color: #60a5fa;
    }
''')

with ui.column().classes('w-full px-6 py-4 gap-6 bg-zinc-950 min-h-screen text-zinc-100'):
    with ui.row().classes('w-full items-center justify-between border-b border-zinc-800 pb-4'):
        with ui.column().classes('gap-1'):
            ui.label('eBay Kleinanzeigen Scraping Hub').classes('text-2xl font-bold text-white tracking-wide')
            ui.label('Dynamic Multi-Category Live Analyzer Engine').classes('text-sm text-zinc-400')
        with ui.row().classes('items-center gap-2 bg-zinc-900 border border-zinc-800 px-4 py-2 rounded-xl shadow-inner'):
            ui.icon('settings', size='sm').classes('text-zinc-400')
            save_json_checkbox = ui.checkbox('Save Raw Data JSON to Disk', value=False).classes('text-xs font-semibold text-zinc-300')

    with ui.grid(columns='1fr 1fr').classes('w-full gap-6 items-stretch'):
        
        with ui.column().classes('gap-4 w-full h-full justify-between'):
            with ui.column().classes('w-full gap-4'):
                with ui.card().classes('w-full bg-zinc-900 border border-zinc-800 shadow-2xl p-5 rounded-xl gap-4'):
                    ui.label('API Routing Configuration').classes('text-xs font-bold text-red-400 uppercase tracking-wider')
                    with ui.grid(columns=2).classes('w-full gap-4'):
                        base_url_input = ui.input(label='Base URL', value='http://127.0.0.1:8000').classes('w-full')
                        endpoint_input = ui.input(label='Endpoint', value='inserate').classes('w-full')

                with ui.card().classes('w-full bg-zinc-900 border border-zinc-800 shadow-2xl p-5 rounded-xl gap-4'):
                    ui.label('Query parameters targeting matrix').classes('text-xs font-bold text-red-400 uppercase tracking-wider')
                    
                    with ui.grid(columns=2).classes('w-full gap-4'):
                        query_input = ui.input(label='Query Keyword', value='Mietwohnung').classes('w-full')
                        location_input = ui.input(label='Target Location / Zip', value='Bad Neustadt a.d. Saale - Bayern').classes('w-full')
                    
                    with ui.grid(columns=3).classes('w-full gap-4 mt-1'):
                        radius_input = ui.number(label='Radius (km)', value=5, min=5, format='%d').classes('w-full')
                        min_price_input = ui.number(label='Min Price (€)', value=None, min=1, format='%d', placeholder="0€").classes('w-full')
                        max_price_input = ui.number(label='Max Price (€)', value=None, min=1, format='%d', placeholder="0€").classes('w-full')

                    with ui.grid(columns=3).classes('w-full gap-4 mt-1'):
                        page_count_input = ui.number(label='Pages (Max 20)', value=1, min=1, max=20, format='%d').classes('w-full')
                        max_listings_input = ui.number(label='Max Target Items', value=0, min=0, max=25, format='%d').classes('w-full')
                        publish_date_input = ui.date_input(label='Min Publish Date', value="", placeholder='YYYY-MM-DD HH:MM:SS').classes('w-full')
            
            # Interactive Executions Action Containers
            with ui.row().classes('w-full mt-2'):
                run_btn = ui.button('Scrape Data', on_click=run_scraper, icon='bolt', color="coral").classes('w-full py-4 text-md font-bold bg-blue-600 hover:bg-blue-500 rounded-xl text-white shadow-xl transition-all tracking-wider uppercase')
                abort_btn = ui.button('Abort Task', on_click=request_abort, icon='block', color="red").classes('w-full py-4 text-md font-bold bg-red-600 hover:bg-red-500 rounded-xl text-white shadow-xl transition-all tracking-wider uppercase')
                abort_btn.set_visibility(False) # Keep hidden until processing routine triggers

        with ui.card().classes('w-full bg-zinc-900 border border-zinc-800 shadow-2xl p-5 rounded-xl flex flex-col justify-between'):
            ui.label('Live Pipeline Log').classes('text-xs font-bold text-purple-400 mb-2 uppercase tracking-wider')
            log_viewer = ui.log().classes('w-full flex-grow h-[390px] rounded-lg bg-black border border-zinc-950 p-3 text-xs font-mono text-emerald-400 shadow-inner')

    with ui.card().classes('w-full bg-zinc-900 border border-zinc-800 shadow-2xl p-5 mt-2 rounded-xl'):
        with ui.row().classes('w-full items-center justify-between mb-4'):
            with ui.column().classes('gap-0'):
                ui.label('Extracted Category Metrics Payload View').classes('text-md font-semibold text-purple-400 uppercase tracking-wider')
                ui.label('Live parsed listing values with responsive active path navigation anchors').classes('text-xs text-zinc-400')
            ui.button('Export to Excel', on_click=manual_export_excel, icon='download', color="green").classes('bg-purple-700 hover:bg-purple-600 font-bold px-5 py-2 text-white rounded-xl shadow-lg transition-all text-xs tracking-wider uppercase')

        with ui.element('div').classes('w-full overflow-x-auto border border-zinc-800 rounded-xl bg-zinc-950 shadow-inner'):
            table_view = ui.table(
                columns=[],
                rows=[],
                row_key='ID'
            ).classes('w-full text-zinc-300 min-w-full custom-dashboard-table')
            
            table_view.props('dark flat square dense wrap-cells binary-state-sort')
            
            table_view.add_slot('body-cell-URL', '''
                <q-td :props="props">
                    <a :href="props.value" target="_blank" class="url-link-btn">
                        <q-icon name="open_in_new" size="xs" class="q-mr-xs"></q-icon>Open Listing
                    </a>
                </q-td>
            ''')
            
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Kleinanzeigen Scraper Platform", reload=True)