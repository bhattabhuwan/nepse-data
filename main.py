from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import scrape_merolagani, init_database, save_to_database

# ✅ Create FastAPI app
app = FastAPI(
    title="NEPSE Live Data API",
    description="Fetches NEPSE stock data from Merolagani",
    version="1.0.0"
)

# ✅ Run when API starts
@app.on_event("startup")
def startup_event():
    init_database()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/nepse", summary="Get NEPSE market data")
def get_nepse_data():
    """
    Scrapes Merolagani market page and returns stock data as JSON.
    """
    result = scrape_merolagani()
    return result
