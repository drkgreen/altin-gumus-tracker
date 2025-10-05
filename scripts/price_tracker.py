#!/usr/bin/env python3
"""
Metal Price Tracker Bot v2.0
GitHub Actions ile arka planda çalışır ve fiyat verilerini toplar
Yeni özellikler:
- Her gün 07:00-21:00 arası veri toplama
- Her gün 22:00'de günlük optimizasyon (en yüksek portföy değeri)
- Hafta sonu dahil 7/24 çalışma
"""

import json
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import os
import argparse

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
        
        price_element = soup.find('span', {
            'data-socket-key': '5-gumus',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            price_text = price_element.get_text(strip=True)
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

def calculate_portfolio_value(gold_price, silver_price, gold_amount=1, silver_amount=1):
    """Standart portföy değeri hesapla (varsayılan: 1gr altın + 1gr gümüş)"""
    if gold_price is None or silver_price is None:
        return 0
    return (gold_price * gold_amount) + (silver_price * silver_amount)

def optimize_daily_data():
    """Bugünün verilerinden en yüksek portföy değerini sakla, diğerlerini sil"""
    print("🌙 Günlük optimizasyon başlatılıyor...")
    print(f"Zaman: {datetime.now(timezone.utc).isoformat()}")
    
    price_data = load_price_history()
    records = price_data.get("records", [])
    
    if not records:
        print("❌ Optimize edilecek veri bulunamadı!")
        return
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    today_records = [r for r in records 
                    if r.get("date") == today 
                    and not r.get("optimized", False)]
    
    if not today_records:
        print(f"❌ {today} tarihine ait optimize edilmemiş veri bulunamadı!")
        return
    
    print(f"📊 {today} tarihine ait {len(today_records)} kayıt bulundu")
    
    max_portfolio_value = 0
    peak_record = None
    
    for record in today_records:
        gold_price = record.get("gold_price")
        silver_price = record.get("silver_price")
        
        if gold_price and silver_price:
            portfolio_value = calculate_portfolio_value(gold_price, silver_price)
            
            if portfolio_value > max_portfolio_value:
                max_portfolio_value = portfolio_value
                peak_record = record.copy()
    
    if not peak_record:
        print(f"❌ {today} tarihinde geçerli fiyat verisi bulunamadı!")
        return
    
    peak_record.update({
        "optimized": True,
        "daily_peak": True,
        "portfolio_value": max_portfolio_value,
        "peak_time": peak_record.get("time", "unknown")
    })
    
    filtered_records = [r for r in records if r.get("optimized", False) == True]
    filtered_records.append(peak_record)
    
    price_data["records"] = filtered_records
    price_data["last_optimization"] = datetime.now(timezone.utc).isoformat()
    price_data["optimization_stats"] = {
        "date": today,
        "original_count": len(today_records),
        "peak_portfolio_value": max_portfolio_value,
        "peak_time": peak_record.get("time"),
        "removed_count": len(records) - len(filtered_records)
    }
    
    if save_price_history(price_data):
        print(f"✅ Optimizasyon tamamlandı!")
        print(f"   📅 Tarih: {today}")
        print(f"   📊 Peak Portföy: {max_portfolio_value:.2f} TL")
        print(f"   🕐 Peak Saat: {peak_record.get('time')}")
        print(f"   🗑️ Silinen kayıt: {len(records) - len(filtered_records)}")
        print(f"   💾 Toplam kayıt: {len(filtered_records)}")
    else:
        print("❌ Optimizasyon kaydetme başarısız!")

def collect_price_data():
    """Normal fiyat verisi toplama işlemi"""
    print("📊 Metal Fiyat Takip Botu - Veri Toplama")
    print(f"Zaman: {datetime.now(timezone.utc).isoformat()}")
    
    gold_price = get_gold_price()
    silver_price = get_silver_price()
    
    if gold_price is None and silver_price is None:
        print("❌ Hiçbir fiyat alınamadı!")
        return
    
    print(f"✅ Altın: {gold_price} TL" if gold_price else "❌ Altın fiyatı alınamadı")
    print(f"✅ Gümüş: {silver_price} TL" if silver_price else "❌ Gümüş fiyatı alınamadı")
    
    portfolio_value = calculate_portfolio_value(gold_price, silver_price) if gold_price and silver_price else 0
    
    price_data = load_price_history()
    
    new_record = {
        "timestamp": datetime.now(timezone.utc).timestamp(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "gold_price": gold_price,
        "silver_price": silver_price,
        "portfolio_value": portfolio_value,
        "optimized": False,
        "daily_peak": False,
        "success": {
            "gold": gold_price is not None,
            "silver": silver_price is not None
        }
    }
    
    price_data["records"].append(new_record)
    price_data["last_update"] = datetime.now(timezone.utc).isoformat()
    price_data["total_records"] = len(price_data["records"])
    price_data["bot_version"] = "2.0.0"
    
    if save_price_history(price_data):
        print(f"✅ Veri kaydedildi. Toplam kayıt: {len(price_data['records'])}")
        if portfolio_value > 0:
            print(f"💰 Portföy Değeri: {portfolio_value:.2f} TL (1gr altın + 1gr gümüş)")
    else:
        print("❌ Veri kaydetme başarısız!")

def main():
    parser = argparse.ArgumentParser(description='Metal Price Tracker Bot v2.0')
    parser.add_argument('--optimize', action='store_true', 
                       help='Optimize daily data (remove all but peak portfolio value)')
    parser.add_argument('--collect', action='store_true', 
                       help='Collect current price data')
    
    args = parser.parse_args()
    
    if args.optimize:
        optimize_daily_data()
    elif args.collect:
        collect_price_data()
    else:
        collect_price_data()

if __name__ == "__main__":
    main()