#!/usr/bin/env python3
"""
Metal Price Tracker Bot v2.0
GitHub Actions ile arka planda çalışır ve fiyat verilerini toplar
Yeni özellikler:
- Her gün 07:00-21:00 arası veri toplama
- Gece 02:00'de günlük optimizasyon (en yüksek portföy değeri)
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

def calculate_portfolio_value(gold_price, silver_price, gold_amount=1, silver_amount=1):
    """Standart portföy değeri hesapla (varsayılan: 1gr altın + 1gr gümüş)"""
    if gold_price is None or silver_price is None:
        return 0
    return (gold_price * gold_amount) + (silver_price * silver_amount)

def optimize_daily_data():
    """Bir önceki günün verilerinden en yüksek portföy değerini sakla, diğerlerini sil"""
    print("🌙 Gece optimizasyonu başlatılıyor...")
    print(f"Zaman: {datetime.now(timezone.utc).isoformat()}")
    
    # Mevcut veriyi yükle
    price_data = load_price_history()
    records = price_data.get("records", [])
    
    if not records:
        print("❌ Optimize edilecek veri bulunamadı!")
        return
    
    # Dünün tarihini hesapla
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Dünün verilerini bul
    yesterday_records = [r for r in records if r.get("date") == yesterday]
    
    if not yesterday_records:
        print(f"❌ {yesterday} tarihine ait veri bulunamadı!")
        return
    
    print(f"📊 {yesterday} tarihine ait {len(yesterday_records)} kayıt bulundu")
    
    # En yüksek portföy değerine sahip kaydı bul
    max_portfolio_value = 0
    peak_record = None
    
    for record in yesterday_records:
        gold_price = record.get("gold_price")
        silver_price = record.get("silver_price")
        
        if gold_price and silver_price:
            portfolio_value = calculate_portfolio_value(gold_price, silver_price)
            
            if portfolio_value > max_portfolio_value:
                max_portfolio_value = portfolio_value
                peak_record = record
    
    if not peak_record:
        print(f"❌ {yesterday} tarihinde geçerli fiyat verisi bulunamadı!")
        return
    
    # Peak kaydı optimize edilmiş olarak işaretle
    peak_record.update({
        "optimized": True,
        "daily_peak": True,
        "portfolio_value": max_portfolio_value,
        "peak_time": peak_record.get("time", "unknown")
    })
    
    # Dünün diğer kayıtlarını sil
    other_records = [r for r in records if r.get("date") != yesterday]
    optimized_records = other_records + [peak_record]
    
    # Veriyi güncelle
    price_data["records"] = optimized_records
    price_data["last_optimization"] = datetime.now(timezone.utc).isoformat()
    price_data["optimization_stats"] = {
        "date": yesterday,
        "original_count": len(yesterday_records),
        "peak_portfolio_value": max_portfolio_value,
        "peak_time": peak_record.get("time"),
        "removed_count": len(yesterday_records) - 1
    }
    
    # Dosyaya kaydet
    if save_price_history(price_data):
        print(f"✅ Optimizasyon tamamlandı!")
        print(f"   📅 Tarih: {yesterday}")
        print(f"   📊 Peak Portföy: {max_portfolio_value:.2f} TL")
        print(f"   🕐 Peak Saat: {peak_record.get('time')}")
        print(f"   🗑️ Silinen kayıt: {len(yesterday_records) - 1}")
        print(f"   💾 Toplam kayıt: {len(optimized_records)}")
    else:
        print("❌ Optimizasyon kaydetme başarısız!")

def collect_price_data():
    """Normal fiyat verisi toplama işlemi"""
    print("📊 Metal Fiyat Takip Botu - Veri Toplama")
    print(f"Zaman: {datetime.now(timezone.utc).isoformat()}")
    
    # Fiyatları çek
    gold_price = get_gold_price()
    silver_price = get_silver_price()
    
    if gold_price is None and silver_price is None:
        print("❌ Hiçbir fiyat alınamadı!")
        return
    
    print(f"✅ Altın: {gold_price} TL" if gold_price else "❌ Altın fiyatı alınamadı")
    print(f"✅ Gümüş: {silver_price} TL" if silver_price else "❌ Gümüş fiyatı alınamadı")
    
    # Portföy değeri hesapla (referans için)
    portfolio_value = calculate_portfolio_value(gold_price, silver_price) if gold_price and silver_price else 0
    
    # Mevcut veriyi yükle
    price_data = load_price_history()
    
    # Yeni kaydı oluştur
    new_record = {
        "timestamp": datetime.now(timezone.utc).timestamp(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "gold_price": gold_price,
        "silver_price": silver_price,
        "portfolio_value": portfolio_value,
        "optimized": False,  # Henüz optimize edilmedi
        "daily_peak": False,  # Peak kontrolü daha sonra yapılacak
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
    price_data["bot_version"] = "2.0.0"
    
    # Dosyaya kaydet
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
        # Varsayılan davranış: veri toplama
        collect_price_data()

if __name__ == "__main__":
    main()