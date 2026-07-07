import pandas as pd
from pathlib import Path
from pprint import pprint
from rich import print
from typing import Any
import json

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def save_to_file(destination_dir: str, filename: str, data: Any) -> None:
    """Write data to a file format.

    Args:
        filename (str): Name of the file with the suffix (file extension) at the end. Use **.txt** or **.json** for now
        data (Any): Data to write to the specified file format.

    Raises:
        OSError: If filename does not contain a suffix.
    """
    # Params
    buffer: int = 65512
    filepath: Path = Path(destination_dir) / filename
    extension: str = Path(filename).suffix
    ensure_dir(Path(destination_dir))
    
    if not extension:
        raise OSError(f"Filename is missing a suffix (file extension) at the end! You have entered: '{filepath.__str__()}'")
    
    match extension:
        case ".txt":
            with open(file={filepath}, mode="w", buffering=buffer, encoding="utf-8") as f:
                pprint("[bold green]Writing data to file as text file...[bold green]")
                f.write(data)
            pprint(f"Text file saved to: [bold magenta]'{filepath}'[/bold magenta]")
        case ".json":
            with open(file=filepath, mode="w", encoding="utf-8") as f:
                print("[bold green]Writing data to file as json file...[/bold green]")
                json.dump(data, f, indent=4, ensure_ascii=False)
            pprint(f"JSON file saved to: [bold magenta]'{filepath}'[/bold magenta]")
        case _:
            raise ValueError(f"[bold red]Unsupported extension: {extension}[/bold red]")
    

def convert_to_excel(df: pd.DataFrame, excel_output_file: str) -> None:
    sheet_name: str = "Data"
    with pd.ExcelWriter(excel_output_file, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        worksheet = writer.sheets[sheet_name]

        max_row, max_col = df.shape
        column_settings = [{"header": col} for col in df.columns]
        worksheet.add_table(
            0,
            0,
            max_row,
            max_col - 1,
            {
                "columns": column_settings,
                "style": "Table Style Medium 16",
                "name": f"{sheet_name[:30]}",
                "autofilter": True,
            },
        )
        worksheet.set_column(0, max_col - 1, 18)