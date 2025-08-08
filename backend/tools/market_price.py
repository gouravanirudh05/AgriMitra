# tools/market_price.py
import json
import os
from pathlib import Path
import datetime
from typing import Optional, Dict, Any, Tuple
import logging
from functools import lru_cache

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from rapidfuzz import fuzz, process
from langchain.tools import tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgMarkNetScraper:
    """Scraper for AgMarkNet agricultural market data"""
    
    def __init__(self, data_dir: str = "datasets"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = "https://agmarknet.gov.in/"
        self.search_url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
        
        # HTTP headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Referer': 'https://agmarknet.gov.in/',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive'
        }
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Cache for data
        self._states_data = None
        self._commodities_data = None
        
        # Initialize connection
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session by visiting the main page"""
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            logger.info("Session initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            # Don't raise error, continue with fallback data
            logger.warning("Continuing with fallback data...")
    
    def _load_json_data(self, filename: str) -> Dict:
        """Load JSON data from file"""
        filepath = self.data_dir / filename
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as file:
                    return json.load(file)
            else:
                logger.warning(f"Data file not found: {filepath}")
                return {}
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}
    
    def _save_json_data(self, data: Dict, filename: str):
        """Save data to JSON file"""
        filepath = self.data_dir / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            logger.info(f"Saved data to {filepath}")
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
    
    @property
    def states_data(self) -> Dict:
        """Get states data (lazy loaded)"""
        if self._states_data is None:
            self._states_data = self._load_json_data("states.json")
            if not self._states_data:
                # If no cached data, create basic mapping
                self._states_data = {
                    "12": "Karnataka",
                    "21": "Maharashtra", 
                    "7": "Andhra Pradesh",
                    "29": "Tamil Nadu",
                    "10": "Gujarat"
                }
                self._save_json_data(self._states_data, "states.json")
        return self._states_data
    
    @property 
    def commodities_data(self) -> Dict:
        """Get commodities data (lazy loaded and cached)"""
        if self._commodities_data is None:
            # Try to load from cache first
            cached_file = self.data_dir / "commodities.json"
            if cached_file.exists():
                # Check if cache is recent (within 7 days)
                cache_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(cached_file.stat().st_mtime)
                if cache_age.days < 7:
                    self._commodities_data = self._load_json_data("commodities.json")
                    if self._commodities_data:
                        logger.info("Using cached commodities data")
                        return self._commodities_data
            
            # Fetch fresh data if cache is old or doesn't exist
            logger.info("Fetching fresh commodities data from AgMarkNet...")
            try:
                self._commodities_data = self._fetch_commodities_from_web()
                if self._commodities_data:
                    self._save_json_data(self._commodities_data, "commodities.json")
            except Exception as e:
                logger.error(f"Failed to fetch commodities from web: {e}")
                # Use fallback data
                self._commodities_data = self._get_fallback_commodities()
                logger.warning("Using fallback commodities data")
            
            # If still no data, use fallback
            if not self._commodities_data:
                self._commodities_data = self._get_fallback_commodities()
        
        return self._commodities_data or {}
    
    def _get_fallback_commodities(self) -> Dict:
        """Fallback commodity data when web scraping fails"""
        return {
            "2": ["Wheat", "Gehun"],
            "3": ["Rice", "Chawal", "Paddy"],
            "19": ["Onion", "Pyaz"],
            "25": ["Tomato", "Tamatar"],
            "23": ["Potato", "Aloo"],
            "110": ["Almond", "Badam"],  # Fixed: Added Almond with proper ID
            "46": ["Cotton", "Kapas"],
            "11": ["Sugarcane", "Ganna"],
            "8": ["Arecanut", "Betelnut", "Supari"],
            "15": ["Turmeric", "Haldi"],
            "39": ["Chilli", "Mirchi"],
            "36": ["Groundnut", "Peanut", "Moongfali"],
            "4": ["Jowar", "Sorghum"],
            "5": ["Bajra", "Pearl Millet"],
            "6": ["Maize", "Corn", "Makka"]
        }
    
    def _extract_aliases(self, name: str) -> list:
        """Extract aliases from commodity name like 'Arecanut (Betelnut/Supari)'"""
        if not name:
            return []
            
        name = name.strip()
        aliases = []
        
        # Split on parentheses and slashes - FIXED REGEX
        # First get main name before parentheses
        main_match = re.match(r'^([^(]+)', name)
        if main_match:
            main_name = main_match.group(1).strip()
            if main_name:
                aliases.append(main_name)
        
        # Then get aliases from within parentheses
        paren_content = re.findall(r'\(([^)]+)\)', name)
        for content in paren_content:
            # Split by slash or comma
            sub_aliases = re.split(r'[/,]', content)
            for alias in sub_aliases:
                cleaned = alias.strip()
                if cleaned and cleaned not in aliases:
                    aliases.append(cleaned)
        
        return aliases if aliases else [name.strip()]
    
    def _fetch_commodities_from_web(self) -> Dict:
        """Fetch commodity dropdown options from web"""
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple dropdown selectors - ENHANCED
            dropdown_ids = ['ddlCommodity', 'ctl00_cphBody_ddlCommodity', 'cphBody_ddlCommodity']
            dropdown = None
            
            for dropdown_id in dropdown_ids:
                dropdown = soup.find('select', {'id': dropdown_id})
                if dropdown:
                    logger.info(f"Found dropdown with ID: {dropdown_id}")
                    break
            
            if not dropdown:
                logger.error("Commodity dropdown not found with any known ID")
                return {}
            
            commodities = {}
            for option in dropdown.find_all('option'):
                value = option.get('value', '').strip()
                text = option.get_text(strip=True)
                
                # Skip invalid options
                if not value or not text or value in ['0', ''] or text.lower() in ['select', '--select--']:
                    continue
                    
                aliases = self._extract_aliases(text)
                if aliases:
                    commodities[value] = aliases
            
            logger.info(f"Fetched {len(commodities)} commodities")
            return commodities
            
        except Exception as e:
            logger.error(f"Error fetching commodities: {e}")
            raise  # Re-raise to trigger fallback
    
    @lru_cache(maxsize=100)
    def find_commodity_id(self, query: str, threshold: int = 70) -> Optional[str]:  # LOWERED THRESHOLD
        """Find commodity ID using fuzzy matching - ENHANCED"""
        if not query or not query.strip():
            return None
            
        query = query.strip().lower()
        commodities = self.commodities_data
        
        if not commodities:
            logger.error("No commodities data available")
            return None
        
        logger.info(f"Searching for commodity: '{query}' in {len(commodities)} commodities")
        
        # FIXED: Better search strategy
        # 1. Create search pairs with better handling
        search_pairs = []
        for commodity_id, aliases in commodities.items():
            if not aliases:  # Skip empty aliases
                continue
            for alias in aliases:
                if alias and alias.strip():  # Ensure alias is valid
                    alias_clean = alias.strip().lower()
                    search_pairs.append((alias_clean, commodity_id, alias))
        
        logger.info(f"Created {len(search_pairs)} search pairs")
        
        # 2. Exact match first
        for alias_clean, commodity_id, original_alias in search_pairs:
            if alias_clean == query:
                logger.info(f"Exact match found: '{original_alias}' -> ID {commodity_id}")
                return commodity_id
        
        # 3. Contains match (both ways)
        for alias_clean, commodity_id, original_alias in search_pairs:
            if query in alias_clean or alias_clean in query:
                logger.info(f"Contains match found: '{original_alias}' -> ID {commodity_id}")
                return commodity_id
        
        # 4. Fuzzy matching with better error handling
        try:
            all_aliases = [pair[0] for pair in search_pairs]
            if not all_aliases:
                logger.error("No aliases available for fuzzy matching")
                return None
                
            best_match = process.extractOne(
                query, 
                all_aliases, 
                scorer=fuzz.ratio,
                score_cutoff=threshold
            )
            
            if best_match:
                matched_alias = best_match[0]
                confidence = best_match[1]
                logger.info(f"Fuzzy match found: '{matched_alias}' with confidence {confidence}%")
                
                for alias_clean, commodity_id, original_alias in search_pairs:
                    if alias_clean == matched_alias:
                        logger.info(f"Returning commodity ID: {commodity_id} for '{original_alias}'")
                        return commodity_id
        except Exception as e:
            logger.error(f"Error in fuzzy matching: {e}")
        
        # Show debug info
        similar_matches = process.extract(query, [pair[0] for pair in search_pairs], limit=3) if search_pairs else []
        logger.warning(f"No match found for '{query}'. Similar: {similar_matches}")
        return None
    
    @lru_cache(maxsize=50)
    def find_state_id(self, query: str, threshold: int = 60) -> Optional[str]:
        """Find state ID using fuzzy matching"""
        if not query or not query.strip():
            return None
            
        states = self.states_data
        choices = list(states.values())
        best_match = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)
        
        if best_match and best_match[1] >= threshold:
            for state_id, state_name in states.items():
                if state_name == best_match[0]:
                    return state_id
        
        return None
    
    def get_market_data(self, 
                       commodity: str, 
                       state: str, 
                       start_date: str = None, 
                       end_date: str = None,
                       district: str = None) -> str:
        """
        Fetch market data and return as markdown table
        
        Args:
            commodity: Name of commodity (e.g., "Wheat", "Rice")
            state: Name of state (e.g., "Karnataka", "Maharashtra") 
            start_date: Start date in DD-MM-YYYY format (defaults to 7 days ago)
            end_date: End date in DD-MM-YYYY format (defaults to today)
            district: Optional district filter
        """
        
        # Default date range if not provided - FIXED DATE LOGIC
        today = datetime.datetime.now()
        if not end_date:
            end_dt = today - datetime.timedelta(days=1)  # Yesterday
            end_date = end_dt.strftime("%d-%m-%Y")
        if not start_date:
            start_dt = today - datetime.timedelta(days=8)  # 7 days ago
            start_date = start_dt.strftime("%d-%m-%Y")
        
        # Find commodity and state IDs
        commodity_id = self.find_commodity_id(commodity)
        state_id = self.find_state_id(state)
        
        if not commodity_id:
            # ENHANCED ERROR MESSAGE - show available commodities
            available = []
            for commodity_data in list(self.commodities_data.values())[:10]:
                if commodity_data and commodity_data[0]:
                    available.append(commodity_data[0])
            suggestions = ', '.join(available[:5]) if available else "wheat, rice, cotton, sugarcane, tomato"
            return f"❌ Commodity '{commodity}' not found. Available commodities include: {suggestions}"
        
        if not state_id:
            available_states = list(self.states_data.values())[:5]
            return f"❌ State '{state}' not found. Available states include: {', '.join(available_states)}"
        
        # Get commodity and state names
        commodity_name = self.commodities_data[commodity_id][0]  # First alias
        state_name = self.states_data[state_id]
        
        return self._fetch_agmarknet_data(
            commodity_id=commodity_id,
            state_id=state_id, 
            commodity_name=commodity_name,
            state_name=state_name,
            start_date=start_date,
            end_date=end_date,
            district=district
        )
    
    def _fetch_agmarknet_data(self,
                             commodity_id: str,
                             state_id: str, 
                             commodity_name: str,
                             state_name: str,
                             start_date: str,
                             end_date: str,
                             district: str = None) -> str:
        """Fetch actual market data from AgMarkNet - ENHANCED WITH MULTIPLE ATTEMPTS"""
        
        # Try multiple URL formats
        url_attempts = [
            # Format 1: Original format
            f"{self.search_url}?Tx_Commodity={commodity_id}&Tx_State={state_id}&Tx_District=0&Tx_Market=0&DateFrom={start_date}&DateTo={end_date}&Fr_Date={start_date}&To_Date={end_date}&Tx_Trend=0&Tx_CommodityHead={commodity_name}&Tx_StateHead={state_name}&Tx_DistrictHead=--Select--&Tx_MarketHead=--Select--",
            
            # Format 2: Simplified format
            f"{self.search_url}?Tx_Commodity={commodity_id}&Tx_State={state_id}&DateFrom={start_date}&DateTo={end_date}"
        ]
        
        logger.info(f"Fetching data for {commodity_name} in {state_name} from {start_date} to {end_date}")
        
        for i, url in enumerate(url_attempts):
            try:
                logger.info(f"Attempting URL format {i+1}/{len(url_attempts)}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # ENHANCED TABLE FINDING
                table = None
                table_selectors = [
                    {'id': 'cphBody_GridPriceData'},
                    {'id': 'GridPriceData'},
                    {'class': 'table'},
                    {'id': re.compile(r'.*Grid.*', re.I)},
                    {'id': re.compile(r'.*Price.*', re.I)}
                ]
                
                for selector in table_selectors:
                    table = soup.find('table', selector)
                    if table and len(table.find_all('tr')) > 1:
                        logger.info(f"Found table with selector: {selector}")
                        break
                
                if not table:
                    # Try finding any table with reasonable data
                    all_tables = soup.find_all('table')
                    for t in all_tables:
                        rows = t.find_all('tr')
                        if len(rows) > 1 and len(rows[0].find_all(['th', 'td'])) > 3:
                            table = t
                            logger.info("Found fallback table")
                            break
                
                if not table:
                    if "no record found" in response.text.lower():
                        return f"⚠️ No market data found for **{commodity_name}** in **{state_name}** between {start_date} and {end_date}"
                    else:
                        logger.warning(f"URL format {i+1} failed: No table found")
                        continue
                
                # Parse table data - ENHANCED
                records = []
                rows = table.find_all('tr')
                
                if len(rows) < 2:
                    logger.warning(f"URL format {i+1} failed: No data rows")
                    continue
                
                # Extract headers with better cleaning
                header_row = rows[0]
                headers = []
                for th in header_row.find_all(['th', 'td']):
                    header_text = th.get_text(strip=True).lower()
                    # Clean header text
                    header_text = re.sub(r'[^\w\s]', '', header_text).replace(' ', '_')
                    headers.append(header_text)
                
                # Extract data rows
                for row in rows[1:]:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= len(headers):
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(cols):
                                record[header] = cols[i].get_text(strip=True)
                        if any(record.values()):  # Only add non-empty records
                            records.append(record)
                
                if not records:
                    logger.warning(f"URL format {i+1} failed: No data records")
                    continue
                
                # SUCCESS - format and return data
                df = pd.DataFrame(records)
                
                # Optional district filtering
                if district and 'district_name' in df.columns:
                    original_count = len(df)
                    df = df[df['district_name'].str.lower().str.contains(district.lower(), na=False)]
                    if df.empty:
                        return f"⚠️ No records found for district **{district}** (out of {original_count} total records)"
                    logger.info(f"Filtered {len(df)} records for district {district}")
                
                # Format as markdown
                markdown_table = f"## 📊 Market Prices: {commodity_name} in {state_name}\n\n"
                markdown_table += f"**Date Range:** {start_date} to {end_date}\n"
                markdown_table += f"**Records Found:** {len(df)}\n"
                if district:
                    markdown_table += f"**District Filter:** {district}\n"
                markdown_table += f"\n{df.to_markdown(index=False)}\n"
                
                logger.info(f"Successfully retrieved {len(records)} records")
                return markdown_table
                
            except requests.RequestException as e:
                logger.error(f"URL format {i+1} failed with request error: {e}")
                continue
            except Exception as e:
                logger.error(f"URL format {i+1} failed with error: {e}")
                continue
        
        # If all attempts failed
        return f"❌ Unable to fetch data for **{commodity_name}** in **{state_name}**. All URL formats failed. The service may be temporarily unavailable."
    
    def list_commodities(self, limit: int = 20) -> str:
        """List available commodities"""
        commodities = self.commodities_data
        if not commodities:
            return "❌ No commodities data available"
        
        items = []
        for commodity_id, aliases in list(commodities.items())[:limit]:
            if not aliases:
                continue
            main_name = aliases[0] if aliases else f"ID-{commodity_id}"
            other_names = aliases[1:3] if len(aliases) > 1 else []
            if other_names:
                items.append(f"- **{main_name}** ({', '.join(other_names)})")
            else:
                items.append(f"- **{main_name}**")
        
        result = f"## 🌾 Available Commodities (showing {len(items)} of {len(commodities)})\n\n"
        result += "\n".join(items)
        return result
    
    def list_states(self) -> str:
        """List available states"""
        states = self.states_data
        if not states:
            return "❌ No states data available"
        
        items = [f"- **{state_name}**" for state_name in sorted(states.values())]
        result = f"## 🗺️ Available States ({len(states)} total)\n\n"
        result += "\n".join(items)
        return result


# Global scraper instance
_scraper = None

def get_scraper() -> AgMarkNetScraper:
    """Get or create scraper instance"""
    global _scraper
    if _scraper is None:
        data_dir = os.getenv("AGMARKNET_DATA_DIR", "datasets")
        _scraper = AgMarkNetScraper(data_dir)
    return _scraper


@tool
def get_market_price(query: str) -> str:
    """
    Get agricultural market prices from AgMarkNet for Indian commodities.
    
    Query format examples:
    - "wheat prices in Karnataka"
    - "rice market data in Maharashtra from 01-08-2025 to 07-08-2025" 
    - "tomato prices in Karnataka district Bangalore"
    - "arecanut prices in Karnataka"
    
    Args:
        query: Natural language query specifying commodity, state, optional dates and district
    
    Returns:
        Market price data in markdown table format
    """
    if not query or not query.strip():
        return "Please specify a commodity and state. Example: 'wheat prices in Karnataka'"
    
    try:
        scraper = get_scraper()
        
        # Simple parsing of natural language query
        query_lower = query.lower()
        
        # Extract commodity (first significant word)
        words = query_lower.split()
        commodity = None
        state = None
        district = None
        start_date = None
        end_date = None
        
        # Find "in" keyword to separate commodity and state
        if " in " in query_lower:
            parts = query_lower.split(" in ", 1)
            commodity = parts[0].strip().replace("prices", "").replace("market data", "").replace("price", "").strip()
            location_part = parts[1].strip()
            
            # Check for date patterns (DD-MM-YYYY)
            date_pattern = r'(\d{2}-\d{2}-\d{4})'
            dates = re.findall(date_pattern, location_part)
            if len(dates) >= 2:
                start_date = dates[0]
                end_date = dates[1]
                # Remove dates from location part
                location_part = re.sub(date_pattern, '', location_part).strip()
            elif len(dates) == 1:
                end_date = dates[0]
                location_part = re.sub(date_pattern, '', location_part).strip()
            
            # Check for district
            if "district" in location_part:
                parts = location_part.split("district")
                state = parts[0].strip()
                if len(parts) > 1:
                    district = parts[1].strip()
            else:
                state = location_part.strip()
        else:
            # Fallback parsing
            commodity_keywords = ["wheat", "rice", "tomato", "onion", "potato", "arecanut", "cotton", "sugarcane", "almond", "badam"]  # ADDED ALMOND
            for keyword in commodity_keywords:
                if keyword in query_lower:
                    commodity = keyword
                    break
            
            state_keywords = ["karnataka", "maharashtra", "tamil nadu", "andhra pradesh", "gujarat", "punjab"]
            for keyword in state_keywords:
                if keyword in query_lower:
                    state = keyword
                    break
        
        if not commodity:
            return "❌ Please specify a commodity. Example: 'wheat prices in Karnataka'"
        
        if not state:
            return "❌ Please specify a state. Example: 'wheat prices in Karnataka'"
        
        return scraper.get_market_data(commodity, state, start_date, end_date, district)
        
    except Exception as e:
        logger.error(f"Market price tool error: {e}")
        return f"❌ Error fetching market data: {e}"


@tool  
def list_market_commodities() -> str:
    """List available commodities for market price queries"""
    try:
        scraper = get_scraper()
        return scraper.list_commodities()
    except Exception as e:
        return f"❌ Error listing commodities: {e}"


@tool
def list_market_states() -> str:
    """List available states for market price queries"""
    try:
        scraper = get_scraper()
        return scraper.list_states()
    except Exception as e:
        return f"❌ Error listing states: {e}"


# Export main tool
market_price_tool = get_market_price