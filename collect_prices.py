import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

def get_gold_price():
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '6-gram-altin',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            clean_price = price_text.replace('.', '').replace(',', '.')
            return float(clean_price)
            
        return None
        
    except Exception as e:
        print(f"Gold price error: {e}")
        return None

def get_silver_price():
    try:
        url = "https://m.doviz.com/altin/vakifbank/gumus"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '5-gumus',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            clean_price = price_text.replace(',', '.')
            return float(clean_price)
            
        return None
        
    except Exception as e:
        print(f"Silver price error: {e}")
        return None

def load_data():
    if os.path.exists('data/prices.json'):
        try:
            with open('data/prices.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"prices": [], "last_updated": None}

def save_data(data):
    os.makedirs('data', exist_ok=True)
    with open('data/prices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("Collecting metal prices...")
    
    gold_price = get_gold_price()
    silver_price = get_silver_price()
    
    if gold_price is None and silver_price is None:
        print("No prices collected!")
        return
    
    data = load_data()
    
    now = datetime.now(timezone.utc)
    price_entry = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "gold_price": gold_price,
        "silver_price": silver_price
    }
    
    data["prices"].append(price_entry)
    data["last_updated"] = now.isoformat()
    
    # Keep last 720 hours (30 days)
    if len(data["prices"]) > 720:
        data["prices"] = data["prices"][-720:]
    
    save_data(data)
    
    print(f"Saved: Gold={gold_price}, Silver={silver_price}")
    print(f"Time: {now.strftime('%Y-%m-%d %H:%M UTC')}")

if __name__ == "__main__":
    main()