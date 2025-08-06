import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel
import pymupdf4llm

# -------------------- Helper Classes -------------------- #

class IMDDataHandler:
    def __init__(self, filepath):
        if filepath.endswith(".csv"):
            self.df = pd.read_csv(filepath)
        else:
            self.df = pd.read_excel(filepath)

    def get_imd_code(self, district):
        match = self.df[self.df['District'].str.lower() == district.lower()]
        if not match.empty:
            return match.iloc[0]['IMD Code']
        raise ValueError(f"District '{district}' not found in the data.")


class IMDPDFDownloader:
    def __init__(self, save_dir="downloads"):
        self.base_url = "https://imdagrimet.gov.in/accessData.php?path=Files/District%20AAS%20Bulletin/English%20Bulletin/"
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def get_cached_path(self, imd_code, date_str):
        return self.save_dir / f"{imd_code}_{date_str}_E.pdf"

    def download_pdf(self, imd_code, date_str):
        local_path = self.get_cached_path(imd_code, date_str)
        if local_path.exists():
            print(f"[Cache] Using cached PDF: {local_path}")
            return local_path

        filename = f"{imd_code}_{date_str}_E.pdf"
        url = f"{self.base_url}/{filename}"

        try:
            response = requests.get(url)
            if b"file not found" in response.content.lower() or len(response.content.strip()) < 100:
                print(f"PDF not found at {url}")
                return None
            if response.status_code == 200:
                local_path.write_bytes(response.content)
                print(f"[Download] PDF saved to: {local_path}")
                return local_path
        except requests.RequestException as e:
            print(f"Request failed: {e}")
        return None

    def try_latest_pdf(self, imd_code, max_days=5):
        today = datetime.today()
        for delta in range(max_days):
            date = today - timedelta(days=delta)
            date_str = date.strftime("%Y-%m-%d")
            pdf_path = self.download_pdf(imd_code, date_str)
            if pdf_path:
                return pdf_path
        raise FileNotFoundError(f"No PDF found for IMDCode {imd_code} in the last {max_days} days.")


class IMDPDFProcessor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extract_markdown(self):
        return pymupdf4llm.to_markdown(str(self.pdf_path))


# -------------------- LangChain Tool -------------------- #

class WeatherInput(BaseModel):
    district: str


class GetWeatherTool(BaseTool):
    name = "get_weather"
    description = "Returns the weather markdown report for a given Indian district."

    args_schema: Type[BaseModel] = WeatherInput

    def __init__(self, imd_codes_file: str = "../../../datasets/IMDCodes.csv", **kwargs):
        super().__init__(**kwargs)
        self.data_handler = IMDDataHandler(imd_codes_file)
        self.downloader = IMDPDFDownloader()

    def _run(self, district: str) -> str:
        try:
            imd_code = self.data_handler.get_imd_code(district)
            pdf_path = self.downloader.try_latest_pdf(imd_code)
            processor = IMDPDFProcessor(pdf_path)
            return processor.extract_markdown()
        except Exception as e:
            return f"Error: {e}"

    def _arun(self, district: str) -> str:
        raise NotImplementedError("Async not implemented for this tool.")

