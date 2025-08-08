import json
from rapidfuzz import fuzz, process
import datetime
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
from rapidfuzz import fuzz, process
from langchain.tools import tool
import os
from datetime import date
global_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Referer': 'https://agmarknet.gov.in/',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive'
        }

  
def load_data(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

def find_closest_crop_id(query, crop_dict, threshold=90):
    query = query.strip().lower()

    # Flatten alias list
    alias_to_id = []
    for crop_id, aliases in crop_dict.items():
        for alias in aliases:
            alias_lower = alias.lower()
            alias_to_id.append((alias_lower, crop_id))
            if alias_lower == query:
                # Exact match shortcut
                return crop_id

    # All unique aliases
    all_aliases = [alias for alias, _ in alias_to_id]

    # Fuzzy match
    best_match = process.extractOne(query, all_aliases, scorer=fuzz.ratio)

    if best_match and best_match[1] >= threshold:
        matched_alias = best_match[0]
        for alias, crop_id in alias_to_id:
            if alias == matched_alias:
                return crop_id

    return None

def find_closest_state_id(query, crop_dict, threshold=50):
    choices = list(crop_dict.values())
    best_match = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)

    if best_match and best_match[1] >= threshold:
        for key, value in crop_dict.items():
            if value == best_match[0]:
                return key
    return None

# Load the JSON from file
# crop_data = load_data("commodities.json")


# Example usage
# query = "wheet"
# result = find_closest_crop_id(query, crop_data)
# print(f"Closest ID for '{query}': {result}")
def extract_aliases(name):
    """
    Extracts aliases from a name like 'Arecanut (Betelnut/Supari)' → ['Arecanut', 'Betelnut', 'Supari']
    """
    name = name.strip()
    aliases = []

    # Split on parentheses and slashes
    # E.g., 'Arecanut (Betelnut/Supari)' → ['Arecanut ', 'Betelnut', 'Supari']
    parts = re.split(r'[()/]', name)
    for part in parts:
        sub_parts = part.split('/')
        for alias in sub_parts:
            cleaned = alias.strip()
            if cleaned:
                aliases.append(cleaned)
    return aliases

def get_dropdown_options(session, url, dropdown_id):
    """
    Fetches dropdown options from a web page and returns a mapping of ID to list of aliases.
    {
        '1': ['Arecanut', 'Betelnut', 'Supari'],
        '2': ['Wheat'],
        ...
    }
    """
    try:
        response = session.get(url,headers=global_headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        dropdown = soup.find('select', {'id': dropdown_id})
        if not dropdown:
            print(f"Dropdown with ID '{dropdown_id}' not found.")
            return {}

        options = {}
        for option in dropdown.find_all('option'):
            value = option.get('value')
            text = option.text.strip()
            if value and text and value != "0":
                aliases = extract_aliases(text)
                options[value] = aliases
        return options

    except requests.exceptions.RequestException as e:
        print(f"Error fetching dropdown options from {url} for {dropdown_id}: {e}")
        return {}
    except Exception as e:
        print(f"Error parsing dropdown options for {dropdown_id}: {e}")
        return {}  
def get_agmarknet_data(session, commodity_id, state_id, commodity_name, state_name, start_dt, end_dt, district_name=None):
    """
    Fetches market data from Agmarknet.gov.in and returns a markdown-formatted table.
    
    Args:
        session (requests.Session): The session object to maintain cookies.
        commodity_id (str): The numeric ID of the commodity (e.g., "1").
        state_id (str): The numeric ID of the state (e.g., "12").
        commodity_name (str): Name of the commodity (e.g., "Wheat").
        state_name (str): Name of the state (e.g., "Madhya Pradesh").
        start_dt (str): Start date in DD-MM-YYYY format.
        end_dt (str): End date in DD-MM-YYYY format.
        district_name (str, optional): If provided, filters data for this district only.

    Returns:
        str: Markdown table as a string.
    """

    

    AGMARKNET_DATA_BASE_URL = "https://agmarknet.gov.in/SearchCmmMkt.aspx?"
    payload = (
        f"Tx_Commodity={commodity_id}&Tx_State={state_id}&Tx_District=0&Tx_Market=0"
        f"&DateFrom={start_dt}&DateTo={end_dt}&Fr_Date={start_dt}&To_Date={end_dt}"
        f"&Tx_Trend=0&Tx_CommodityHead={commodity_name}&Tx_StateHead={state_name}"
        "&Tx_DistrictHead=--Select--&Tx_MarketHead=--Select--"
    )
    AGMARKNET_DATA_ENDPOINT = AGMARKNET_DATA_BASE_URL + payload

    print(f"Fetching Agmarknet data for CommId: {commodity_id}, StateId: {state_id}, Dates: {start_dt} to {end_dt}")

    records = []

    try:
        get_response = session.get(AGMARKNET_DATA_ENDPOINT,headers=global_headers,  timeout=30)
        get_response.raise_for_status()

        soup = BeautifulSoup(get_response.text, 'html.parser')
        table = soup.find('table', {'id': 'cphBody_GridPriceData'})

        if table:
            rows = table.find_all('tr')
            headers = [th.text.strip().replace(' ', '_').lower() for th in rows[0].find_all('th')]

            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) >= len(headers):
                    record = {headers[i]: cols[i].text.strip() for i in range(len(headers))}
                    record["scraped_at"] = datetime.datetime.now().isoformat()
                    records.append(record)
                else:
                    print(f"Skipping row due to column mismatch: {row}")

        else:
            if "No Record Found" in get_response.text:
                print("No records found for the given filters.")
            else:
                print("Data table not found on the page.")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return "### ❌ Request failed. Please check the network or input parameters."
    except Exception as e:
        print(f"Error parsing data: {e}")
        return "### ❌ Error while parsing data."

    # Convert to DataFrame
    df = pd.DataFrame(records)

    if df.empty:
        return "### ⚠️ No data available for the given query."

    # Optional: Filter by district name
    if district_name:
        df = df[df['district_name'].str.lower() == district_name.lower()]
        if df.empty:
            return f"### ⚠️ No records found for district: `{district_name}`"

    # Return Markdown table
    markdown_table = df.to_markdown(index=False)
    return markdown_table



def log_request_and_response(response):
    req = response.request

    print("\n===== HTTP REQUEST =====")
    print(f"{req.method} {req.url}")
    print("Headers:")
    for k, v in req.headers.items():
        print(f"  {k}: {v}")
    if req.body:
        print(f"Body:\n{req.body}")

    print("\n===== HTTP RESPONSE =====")
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for k, v in response.headers.items():
        print(f"  {k}: {v}")
    print("\nBody (first 500 chars):")
    print(response.text[:500])
    print("=========================\n")

# session = requests.Session()
# r = session.get("https://agmarknet.gov.in/")
# # log_request_and_response(r)
# crop_data = (get_dropdown_options(session,"https://agmarknet.gov.in/","ddlCommodity"))


# markdown_result = get_agmarknet_data(
#     session=session,
#     commodity_id=find_closest_crop_id("Arecanut",crop_data),
#     state_id=find_closest_state_id("Karnataka",states),
#     commodity_name=crop_data[find_closest_crop_id("Arecanut",crop_data)],
#     state_name=states[find_closest_state_id("Karnataka",states)],
#     start_dt="01-08-2025",
#     end_dt="07-08-2025",
#     # district_name="Koppa"  # Optional
# )
# Get the folder where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build absolute path to states.json
states_path = os.path.join(BASE_DIR, "../../datasets/agrimarket/states.json")

# Normalize the path
states_path = os.path.normpath(states_path)
states = load_data(states_path)

@tool("get_market_price", return_direct=True)
def get_market_price(state: str, commodity: str, start_date: str, end_date: str, district: str = None) -> str:
    """
    Fetches market price data for a given state, commodity, and date range from Agmarknet.

    Args:
        state (str): Name of the state (e.g., "Karnataka").
        commodity (str): Name of the commodity (e.g., "Arecanut").
        start_date (str): Start date in DD-MM-YYYY format.
        end_date (str): End date in DD-MM-YYYY format.
        district (str, optional): District name. Defaults to None.

    Returns:
        str: Markdown-formatted table of market prices.
    """
    # Start session
    session = requests.Session()
    r = session.get("https://agmarknet.gov.in/")
    # start_date = date.strftime(date.today(), "%d-%m-%Y")
    # end_date = date.strftime(date.today(), "%d-%m-%Y")
    
    # Get dropdown data
    crop_data = get_dropdown_options(session, "https://agmarknet.gov.in/", "ddlCommodity")
    
    # Find IDs
    commodity_id = find_closest_crop_id(commodity, crop_data)
    state_id = find_closest_state_id(state, states)
    # Prepare kwargs for query
    kwargs = dict(
        session=session,
        commodity_id=commodity_id,
        state_id=state_id,
        commodity_name=crop_data[commodity_id],
        state_name=states[state_id],
        start_dt=start_date,
        end_dt=end_date
    )
    if district:
        kwargs["district_name"] = district
    
    # Fetch data
    markdown_result = get_agmarknet_data(**kwargs)
    return markdown_result

@tool  
def list_market_commodities() -> str:
    """List available commodities for market price queries"""
    try:
        session = requests.Session()
        r = session.get("https://agmarknet.gov.in/")
        return get_dropdown_options(session, "https://agmarknet.gov.in/", "ddlCommodity")
    except Exception as e:
        return f"❌ Error listing commodities: {e}"


@tool
def list_market_states() -> str:
    """List available states for market price queries"""
    try:
        return states
    except Exception as e:
        return f"❌ Error listing states: {e}"
