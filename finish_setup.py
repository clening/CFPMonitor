import os
from dotenv import load_dotenv
from setup import init_sheet, install_hook

load_dotenv()
sheet_id = os.getenv("GOOGLE_SHEET_ID")
print(f"Sheet ID is: {repr(sheet_id)}")
init_sheet(sheet_id, os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH"))
print("Sheet initialized")
install_hook()
print("Hook installed")
