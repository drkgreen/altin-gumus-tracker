#!/usr/bin/env python3
"""
Metal Price Tracker Bot
GitHub Actions ile arka planda çalışır ve fiyat verilerini toplar
"""

import json
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import os

def get_gold_price():
    """Yapı Kredi altın fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Spesifik elementi ara
        price_element = soup.find('span', {
            'data-socket-key': '6-gram-altin',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            # Fiyatı float'a çevir
            clean_price = price_text.replace('.', '').replace(',', '.')
            return float(clean_price)
        
        return None
        
    except Exception as e:
        print(f"Altın fiyatı çekme hatası: {e}")
        return None

def get_silver_price():
    """Vakıfbank gümüş fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/vakifbank/gumus"
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Spesifik elementi ara
        price_element = soup.find('span', {
            'data-socket-key': '5-gumus',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            # Fiyatı float'a çevir
            clean_price = price_text.replace('.', '').replace(',', '.')
            return float(clean_price)
        
        return None
        
    except Exception as e:
        print(f"Gümüş fiyatı çekme hatası: {e}")
        return None

def load_price_history():
    """Mevcut fiyat geçmişini yükler"""
    try:
        with open('data/price-history.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"records": []}
    except Exception as e:
        print(f"Dosya okuma hatası: {e}")
        return {"records": []}

def save_price_history(data):
    """Fiyat geçmişini dosyaya kaydeder"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/price-history.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Dosya kaydetme hatası: {e}")
        return False

def cleanup_old_records(records, max_days=30):
    """30 günden eski kayıtları siler"""
    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time.timestamp() - (max_days * 24 * 60 * 60)
    
    return [
        record for record in records 
        if record.get('timestamp', 0) > cutoff_time
    ]

def main():
    print("Metal Fiyat Takip Botu Başlatılıyor...")
    print(f"Zaman: {datetime.now(timezone.utc).isoformat()}")
    
    # Fiyatları çek
    gold_price = get_gold_price()
    silver_price = get_silver_price()
    
    if gold_price is None and silver_price is None:
        print("❌ Hiçbir fiyat alınamadı!")
        return
    
    print(f"✅ Altın: {gold_price} TL" if gold_price else "❌ Altın fiyatı alınamadı")
    print(f"✅ Gümüş: {silver_price} TL" if silver_price else "❌ Gümüş fiyatı alınamadı")
    
    # Mevcut veriyi yükle
    price_data = load_price_history()
    
    # Yeni kaydı oluştur
    new_record = {
        "timestamp": datetime.now(timezone.utc).timestamp(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "gold_price": gold_price,
        "silver_price": silver_price,
        "success": {
            "gold": gold_price is not None,
            "silver": silver_price is not None
        }
    }
    
    # Kayıtları güncelle
    price_data["records"].append(new_record)
    
    # Eski kayıtları temizle (30 günden eski)
    price_data["records"] = cleanup_old_records(price_data["records"])
    
    # Meta bilgileri güncelle
    price_data["last_update"] = datetime.now(timezone.utc).isoformat()
    price_data["total_records"] = len(price_data["records"])
    price_data["bot_version"] = "1.0.0"
    
    # Dosyaya kaydet
    if save_price_history(price_data):
        print(f"✅ Veri kaydedildi. Toplam kayıt: {len(price_data['records'])}")
    else:
        print("❌ Veri kaydetme başarısız!")

if __name__ == "__main__":
    main()