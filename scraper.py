import requests
from bs4 import BeautifulSoup
import datetime
import re

def safe_convert_float(value):
    """Safely convert text to float, handling commas and percentage signs"""
    if not value or not value.strip():
        return 0.0
    try:
        # Remove commas, percentage signs, and any extra spaces
        cleaned = value.replace(',', '').replace('%', '').replace('$', '').strip()
        return float(cleaned) if cleaned else 0.0
    except:
        return 0.0

def safe_convert_int(value):
    """Safely convert text to integer, handling commas"""
    if not value or not value.strip():
        return 0
    try:
        cleaned = value.replace(',', '').strip()
        return int(cleaned) if cleaned else 0
    except:
        return 0

def get_company_details(symbol):
    """
    Get company name and sector from individual stock page with better parsing
    """
    try:
        url = f"https://merolagani.com/CompanyDetail.aspx?symbol={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        company_name = ""
        sector = ""
        
        # Method 1: Get company name from page title
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text()
            # Title format: "ACLBSL | Aarambha Chautari Laghubitta Bittiya Sanstha Limited | Merolagani"
            if '|' in title_text:
                parts = title_text.split('|')
                if len(parts) >= 2:
                    company_name = parts[1].strip()
        
        # Method 2: Look for company name in specific elements
        if not company_name:
            company_elements = soup.find_all(['h1', 'h2', 'h3'], string=re.compile(symbol, re.I))
            for elem in company_elements:
                if symbol.upper() in elem.get_text().upper():
                    company_name = elem.get_text().replace(symbol, '').strip(' |')
                    break
        
        # Method 3: Get sector information
        # Look for sector in table rows
        sector_labels = soup.find_all(['td', 'th'], string=re.compile(r'Sector|Industry', re.I))
        for label in sector_labels:
            if label.find_next_sibling():
                sector_text = label.find_next_sibling().get_text(strip=True)
                if sector_text and sector_text not in ['Sector', 'Industry']:
                    sector = sector_text
                    break
        
        # If sector not found in tables, try other elements
        if not sector:
            sector_elements = soup.find_all(string=re.compile(r'Sector:', re.I))
            for elem in sector_elements:
                parent = elem.parent
                if parent:
                    sector_text = parent.get_text().replace('Sector:', '').strip()
                    if sector_text and sector_text not in ['Sector', 'Industry']:
                        sector = sector_text
                        break
        
        return {
            'companyName': company_name if company_name else symbol,
            'sector': sector
        }
        
    except Exception as e:
        print(f"  Could not fetch details for {symbol}: {e}")
        return {
            'companyName': symbol,
            'sector': ''
        }

def scrape_merolagani():
    """
    Scrapes NEPSE data from Merolagani with proper company details
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }

        url = "https://merolagani.com/LatestMarket.aspx"
        print("Fetching data from Merolagani...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        print("Parsing HTML...")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the main trading table
        table = soup.find('table', class_='table table-striped table-bordered table-hover')
        
        if not table:
            table = soup.find('table', id='ctl00_ContentPlaceHolder1_LatestMarket1_gvLatestMarket')
        
        if not table:
            # Try alternative approach
            tables = soup.find_all('table')
            for tbl in tables:
                if len(tbl.find_all('tr')) > 10:
                    table = tbl
                    break

        if not table:
            return {
                "date": datetime.date.today().isoformat(),
                "marketStatus": "Open",
                "data": []
            }

        # Parse data rows
        data = []
        rows = table.find_all('tr')[1:]  # Skip header row

        print(f"Found {len(rows)} rows to process")

        for i, tr in enumerate(rows):
            cells = tr.find_all('td')
            if len(cells) < 8:
                continue

            try:
                # Extract symbol
                symbol_tag = cells[0].find('a')
                symbol = symbol_tag.get_text(strip=True) if symbol_tag else cells[0].get_text(strip=True)
                
                if not symbol or symbol in ['Symbol', '']:
                    continue

                # Get company details for each stock
                print(f"  Fetching details for {symbol} ({i+1}/{len(rows)})")

                
                # company_details = get_company_details(symbol)

                company_details = {'companyName': symbol, 'sector': ''}

                company_name = symbol_tag.get('title', '').strip() if symbol_tag else symbol
                
                # Map table cells to stock data
                stock = {
                    "symbol": symbol,
                    "companyName": company_name,
                    "sector": company_details['sector'],
                    "ltp": safe_convert_float(cells[1].get_text()),
                    "percentChange": safe_convert_float(cells[2].get_text()),
                    "open": safe_convert_float(cells[3].get_text()) if len(cells) > 3 else 0.0,
                    "high": safe_convert_float(cells[4].get_text()) if len(cells) > 4 else 0.0,
                    "low": safe_convert_float(cells[5].get_text()) if len(cells) > 5 else 0.0,
                    "volume": safe_convert_int(cells[6].get_text()) if len(cells) > 6 else 0,
                    "previousClose": safe_convert_float(cells[7].get_text()) if len(cells) > 7 else 0.0,
                }

                # Calculate change
                if len(cells) > 8:
                    stock["change"] = safe_convert_float(cells[8].get_text())
                else:
                    stock["change"] = stock["ltp"] - stock["previousClose"]

                # Calculate turnover
                stock["turnover"] = stock["ltp"] * stock["volume"] if stock["volume"] > 0 else 0.0

                data.append(stock)

            except Exception as row_error:
                print(f"Error processing row {i}: {row_error}")
                continue

        print(f" Extracted {len(data)} stocks successfully")

        return {
            "date": datetime.date.today().isoformat(),
            "marketStatus": "Open",
            "data": data
        }

    except Exception as e:
        print(f" Error: {e}")
        return {
            "date": datetime.date.today().isoformat(),
            "marketStatus": "Open",
            "data": []
        }

def scrape_merolagani_fast():
    """
    Faster version that only gets details for first few stocks
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        url = "https://merolagani.com/LatestMarket.aspx"
        print("Fetching data from Merolagani (fast mode)...")
        response = requests.get(url, headers=headers, timeout=2)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find table
        table = soup.find('table', class_='table table-striped table-bordered table-hover')
        if not table:
            return {"date": datetime.date.today().isoformat(), "marketStatus": "Open", "data": []}

        data = []
        rows = table.find_all('tr')[1:]

        # Get details only for first 3 stocks to save time
        sample_symbols = []
        for i, tr in enumerate(rows[:3]):
            cells = tr.find_all('td')
            if len(cells) >= 8:
                symbol_tag = cells[0].find('a')
                symbol = symbol_tag.get_text(strip=True) if symbol_tag else cells[0].get_text(strip=True)
                if symbol and symbol not in ['Symbol', '']:
                    sample_symbols.append(symbol)

        # Pre-fetch details for sample symbols
        company_details_map = {}
        for symbol in sample_symbols:
            company_details_map[symbol] = get_company_details(symbol)

        # Process all rows
        for i, tr in enumerate(rows):
            cells = tr.find_all('td')
            if len(cells) < 8:
                continue

            symbol_tag = cells[0].find('a')
            symbol = symbol_tag.get_text(strip=True) if symbol_tag else cells[0].get_text(strip=True)
            
            if not symbol or symbol in ['Symbol', '']:
                continue

            # Use pre-fetched details or symbol as fallback
            if symbol in company_details_map:
                details = company_details_map[symbol]
            else:
                details = {'companyName': symbol, 'sector': ''}

            stock = {
                "symbol": symbol,
                "companyName": company_name,
                "sector": details['sector'],
                "ltp": safe_convert_float(cells[1].get_text()),
                "percentChange": safe_convert_float(cells[2].get_text()),
                "open": safe_convert_float(cells[3].get_text()) if len(cells) > 3 else 0.0,
                "high": safe_convert_float(cells[4].get_text()) if len(cells) > 4 else 0.0,
                "low": safe_convert_float(cells[5].get_text()) if len(cells) > 5 else 0.0,
                "volume": safe_convert_int(cells[6].get_text()) if len(cells) > 6 else 0,
                "previousClose": safe_convert_float(cells[7].get_text()) if len(cells) > 7 else 0.0,
                "change": safe_convert_float(cells[8].get_text()) if len(cells) > 8 else 0.0,
                "turnover": 0.0
            }

            # Calculate turnover
            stock["turnover"] = stock["ltp"] * stock["volume"] if stock["volume"] > 0 else 0.0

            data.append(stock)

        print(f"✅ Extracted {len(data)} stocks (fast mode)")
        return {
            "date": datetime.date.today().isoformat(),
            "marketStatus": "Open",
            "data": data
        }

    except Exception as e:
        print(f" Error in fast mode: {e}")
        return {"date": datetime.date.today().isoformat(), "marketStatus": "Open", "data": []}

if __name__ == "__main__":
    # Test the scraper
    print("=== Testing Merolagani Scraper ===")
    
    # Use fast mode for testing
    result = scrape_merolagani_fast()
    
    print(f"Extracted {len(result['data'])} stocks")
    if result['data']:
        print("\nFirst stock sample:")
        for key, value in result['data'][0].items():
            print(f"  {key}: {value}")