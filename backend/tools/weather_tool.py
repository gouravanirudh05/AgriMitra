# tools/weather_tool.py
import os
from pathlib import Path
from datetime import datetime, timedelta
import requests
import pandas as pd
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

from langchain.tools import tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IMDDataHandler:
    """Handles IMD district codes and mapping"""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"IMD codes file not found at {filepath}")
        
        # Load data based on file extension
        try:
            if self.filepath.suffix.lower() == ".csv":
                self.df = pd.read_csv(self.filepath)
            elif self.filepath.suffix.lower() in [".xlsx", ".xls"]:
                self.df = pd.read_excel(self.filepath)
            else:
                raise ValueError(f"Unsupported file format: {self.filepath.suffix}")
            
            # Validate required columns
            required_columns = ['District', 'IMD Code']
            missing_cols = [col for col in required_columns if col not in self.df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
                
            # Clean and prepare data
            self.df['District'] = self.df['District'].str.strip()
            self.df['IMD Code'] = self.df['IMD Code'].astype(str).str.strip()
            
            logger.info(f"Loaded {len(self.df)} districts from IMD codes file")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load IMD codes file: {e}")
    
    @lru_cache(maxsize=128)
    def get_imd_code(self, district: str) -> str:
        """Get IMD code for a district with fuzzy matching"""
        district = district.strip()
        
        # Exact match (case-insensitive)
        exact_match = self.df[self.df['District'].str.lower() == district.lower()]
        if not exact_match.empty:
            return exact_match.iloc[0]['IMD Code']
        
        # Partial match
        partial_match = self.df[self.df['District'].str.lower().str.contains(district.lower(), na=False)]
        if not partial_match.empty:
            logger.warning(f"Using partial match for '{district}': {partial_match.iloc[0]['District']}")
            return partial_match.iloc[0]['IMD Code']
        
        # If no match found, provide suggestions
        similar = self.df[self.df['District'].str.lower().str.startswith(district.lower()[:3])]
        suggestions = similar['District'].head(5).tolist() if not similar.empty else []
        
        error_msg = f"District '{district}' not found in IMD data."
        if suggestions:
            error_msg += f" Similar districts: {', '.join(suggestions)}"
        
        raise ValueError(error_msg)
    
    def list_available_districts(self, state: Optional[str] = None) -> list:
        """List all available districts, optionally filtered by state"""
        districts = self.df['District'].tolist()
        if state:
            # Assuming there's a State column, otherwise return all
            if 'State' in self.df.columns:
                districts = self.df[self.df['State'].str.lower() == state.lower()]['District'].tolist()
        return sorted(districts)


class IMDPDFDownloader:
    """Downloads IMD weather bulletins"""
    
    def __init__(self, save_dir: str = "downloads", timeout: int = 30):
        self.base_url = (
            "https://imdagrimet.gov.in/accessData.php?"
            "path=Files/District%20AAS%20Bulletin/English%20Bulletin"
        )
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_cached_path(self, imd_code: str, date_str: str) -> Path:
        """Get the local path for cached PDF"""
        return self.save_dir / f"{imd_code}_{date_str}_E.pdf"
    
    def is_valid_pdf(self, content: bytes) -> bool:
        """Check if content is a valid PDF"""
        return (
            len(content) > 200 and 
            content.startswith(b'%PDF') and
            b'%%EOF' in content
        )
    
    def download_pdf(self, imd_code: str, date_str: str, force_download: bool = False) -> Optional[Path]:
        """Download PDF for specific IMD code and date"""
        local_path = self.get_cached_path(imd_code, date_str)
        
        # Return cached file if exists and valid (unless forced)
        if local_path.exists() and not force_download:
            if local_path.stat().st_size > 200:  # Basic size check
                logger.info(f"Using cached file: {local_path}")
                return local_path
            else:
                logger.warning(f"Cached file seems invalid, re-downloading: {local_path}")
                local_path.unlink()  # Remove invalid cached file
        
        filename = f"{imd_code}_{date_str}_E.pdf"
        url = f"{self.base_url}/{filename}"
        
        try:
            logger.info(f"Downloading: {url}")
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                content = response.content
                if self.is_valid_pdf(content):
                    local_path.write_bytes(content)
                    logger.info(f"Successfully downloaded: {local_path}")
                    return local_path
                else:
                    logger.warning(f"Downloaded content is not a valid PDF for {filename}")
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                
        except requests.RequestException as e:
            logger.error(f"Download failed for {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
        
        return None
    
    def try_latest_pdf(self, imd_code: str, max_days: int = 7) -> Optional[Path]:
        """Try to download the most recent available PDF"""
        today = datetime.today()
        
        for delta in range(max_days):
            date = today - timedelta(days=delta)
            date_str = date.strftime("%Y-%m-%d")
            
            logger.info(f"Trying date: {date_str} for IMD code: {imd_code}")
            pdf_path = self.download_pdf(imd_code, date_str)
            
            if pdf_path:
                logger.info(f"Found bulletin for {date_str}")
                return pdf_path
        
        logger.warning(f"No bulletin found for IMD code {imd_code} in the last {max_days} days")
        return None
    
    def cleanup_old_files(self, days_to_keep: int = 30):
        """Remove old cached files"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0
        
        for pdf_file in self.save_dir.glob("*.pdf"):
            if pdf_file.stat().st_mtime < cutoff_date.timestamp():
                pdf_file.unlink()
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old cached files")


class IMDPDFProcessor:
    """Processes IMD PDF bulletins and extracts content"""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def extract_markdown(self) -> str:
        """Extract content as markdown from PDF"""
        try:
            import pymupdf4llm
        except ImportError as e:
            raise RuntimeError(
                "pymupdf4llm is required to extract PDF content. "
                "Install it with: pip install pymupdf4llm"
            ) from e
        
        try:
            logger.info(f"Extracting content from: {self.pdf_path}")
            markdown_content = pymupdf4llm.to_markdown(str(self.pdf_path))
            
            if not markdown_content.strip():
                raise ValueError("Extracted content is empty")
            
            # Add metadata header
            file_info = f"# Weather Bulletin\n"
            file_info += f"**Source:** {self.pdf_path.name}\n"
            file_info += f"**Extracted on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            return file_info + markdown_content
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract content from PDF: {e}") from e
    
    def extract_text(self) -> str:
        """Extract plain text from PDF (fallback method)"""
        try:
            import PyPDF2
        except ImportError as e:
            raise RuntimeError(
                "PyPDF2 is required for text extraction fallback. "
                "Install it with: pip install PyPDF2"
            ) from e
        
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from PDF: {e}") from e


class WeatherToolManager:
    """Main manager class for weather tool operations"""
    
    def __init__(self):
        self.imd_codes_path = os.getenv("IMD_CODES_FILE", "datasets/IMDCodes.csv")
        self.download_dir = os.getenv("WEATHER_DOWNLOAD_DIR", "downloads/weather")
        self.cache_days = int(os.getenv("WEATHER_CACHE_DAYS", "30"))
        
        self._handler = None
        self._downloader = None
    
    @property
    def handler(self) -> IMDDataHandler:
        """Lazy load IMD data handler"""
        if self._handler is None:
            self._handler = IMDDataHandler(self.imd_codes_path)
        return self._handler
    
    @property
    def downloader(self) -> IMDPDFDownloader:
        """Lazy load PDF downloader"""
        if self._downloader is None:
            self._downloader = IMDPDFDownloader(self.download_dir)
        return self._downloader
    
    def get_weather_bulletin(self, district: str, max_days: int = 7) -> str:
        """Get weather bulletin for a district"""
        try:
            # Get IMD code for district
            imd_code = self.handler.get_imd_code(district)
            logger.info(f"Found IMD code {imd_code} for district '{district}'")
            
            # Download latest PDF
            pdf_path = self.downloader.try_latest_pdf(imd_code, max_days)
            if not pdf_path:
                # Provide helpful information about available districts
                suggestions = self.handler.list_available_districts()[:10]
                return (
                    f"No recent IMD bulletin found for district '{district}' "
                    f"(IMD Code: {imd_code}) in the last {max_days} days.\n\n"
                    f"Available districts include: {', '.join(suggestions[:5])}..."
                )
            
            # Process PDF and extract content
            processor = IMDPDFProcessor(pdf_path)
            content = processor.extract_markdown()
            
            # Clean up old files periodically
            if datetime.now().hour == 0:  # Run cleanup once a day at midnight
                self.downloader.cleanup_old_files(self.cache_days)
            
            return content
            
        except ValueError as e:
            # District not found or similar issues
            return f"District Error: {e}"
        except Exception as e:
            logger.error(f"Weather tool error for district '{district}': {e}")
            return f"Weather Tool Error: Unable to fetch weather bulletin for '{district}'. {e}"


# Global manager instance
_weather_manager = WeatherToolManager()


@tool
def get_weather(district: str) -> str:
    """
    Fetch the latest weather bulletin for an Indian district from IMD (Indian Meteorological Department).
    
    Args:
        district: Name of the Indian district (e.g., "Bangalore Urban", "Mumbai", "Delhi")
    
    Returns:
        Weather bulletin content in markdown format, or error message if not found.
    
    Examples:
        - get_weather("Bangalore Urban")
        - get_weather("Mumbai") 
        - get_weather("New Delhi")
    """
    if not district or not district.strip():
        return "Please provide a valid district name. Example: 'Bangalore Urban' or 'Mumbai'"
    
    return _weather_manager.get_weather_bulletin(district.strip())


@tool
def list_weather_districts(state: str = None) -> str:
    """
    List available districts for weather bulletins, optionally filtered by state.
    
    Args:
        state: Optional state name to filter districts
        
    Returns:
        List of available districts
    """
    try:
        districts = _weather_manager.handler.list_available_districts(state)
        if state:
            return f"Available districts in {state}: {', '.join(districts)}"
        else:
            return f"Total {len(districts)} districts available. First 20: {', '.join(districts[:20])}"
    except Exception as e:
        return f"Error listing districts: {e}"


# Export the tools
weather_tool = get_weather
weather_districts_tool = list_weather_districts