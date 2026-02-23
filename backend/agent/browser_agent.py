import os
import pandas as pd
from pathlib import Path

class BrowserAgent:
    def resolve_data(self, placeholder):
        """
        Resolves placeholders like <DataFileName.ColumnName_RowNumber>
        Example: <Pump_modal.Username_1>
        """
        if not (placeholder.startswith("<") and placeholder.endswith(">")):
            return placeholder
        
        print(f"📊 BrowserAgent: Resolving data for {placeholder}...")
        if not placeholder or not isinstance(placeholder, str):
            return ""
            
        if not (placeholder.startswith("<") and placeholder.endswith(">")):
            return str(placeholder)
            
        content = placeholder[1:-1].strip()
        try:
            if content == "Sensitive Data" or content == "data" or not content:
                return "" # Don't type anything if it's still a generic placeholder
                
            if "." not in content:
                # Default case if only file name is provided
                return str(placeholder)
            
            file_part, detail_part = content.split(".", 1)
            if "_" not in detail_part:
                return str(placeholder)
                
            column_name, row_idx_str = detail_part.rsplit("_", 1)
            try:
                # Row index in placeholder (e.g. _2) refers to Excel row number.
                # Assuming Row 1 is header, Row 2 is first data row (iloc[0]).
                row_idx = int(row_idx_str) - 2
                if row_idx < 0:
                    print(f"   ⚠️ Invalid row index {row_idx_str}. Data starts from _2.")
                    return str(placeholder)
            except ValueError:
                return str(placeholder)

            # Use absolute path for more reliability across environments
            data_dir = Path(os.getcwd()) / "backend" / "data"
            if not data_dir.exists():
                print(f"   ⚠️ Data directory not found: {data_dir.absolute()}")
                return str(placeholder)

            # Try different extensions
            for ext in [".csv", ".xlsx", ".xls", ".json"]:
                file_path = data_dir / f"{file_part}{ext}"
                if file_path.exists():
                    print(f"   🔍 Checking file: {file_path.absolute()}")
                    val = self._read_from_file(file_path, column_name, row_idx)
                    if val is not None:
                        print(f"   ✅ Resolved to: {val}")
                        return str(val)
                    else:
                        print(f"   ⚠️ Value not found in {file_part}{ext} (Col: {column_name}, Row: {row_idx+1})")
            
            print(f"   ⚠️ Data resolution failed for {placeholder}")
            return str(placeholder)
        except Exception as e:
            print(f"Error resolving data for {placeholder}: {e}")
            return str(placeholder)

    def _read_from_file(self, file_path, column, row):
        try:
            ext = file_path.suffix.lower()
            if ext == ".csv":
                df = pd.read_csv(file_path)
            elif ext in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path)
            elif ext == ".json":
                df = pd.read_json(file_path)
            else:
                return None
                
            # Case-insensitive column search
            matched_col = next((c for c in df.columns if c.lower() == column.lower()), None)
            
            if matched_col:
                if 0 <= row < len(df):
                    val = df.iloc[row][matched_col]
                    return str(val) if pd.notna(val) else ""
                else:
                    print(f"   ❌ Row index {row+1} out of bounds (Total rows: {len(df)})")
            else:
                print(f"   ❌ Column '{column}' not found. Available columns: {list(df.columns)}")
        except Exception as e:
            print(f"   ❌ Error reading file {file_path}: {e}")
        return None

browser_agent = BrowserAgent()
