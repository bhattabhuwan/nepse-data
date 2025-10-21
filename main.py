from fastapi import FastAPI
from scraper import scrape_merolagani

app = FastAPI(
    title="NEPSE Live Data API",
    description="Fetches NEPSE stock data from Merolagani and returns it in JSON format.",
    version="1.0.0"
)

@app.get("/nepse", summary="Get NEPSE market data")
def get_nepse_data():
    """
    Scrapes Merolagani market page and returns stock data as JSON.
    """
    result = scrape_merolagani()
    return result
