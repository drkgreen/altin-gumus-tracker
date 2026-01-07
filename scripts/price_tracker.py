#!/usr/bin/env python3
"""
Metal Price Tracker Bot v3.0
- Çalışma sıklığı: Her 15 dakikada bir (07:00-00:59 TR) - */15 cron formatı
- Anlık optimizasyon: Her veri eklemede peak güncelleme
- Gece temizlik: Eski ham verileri silme (02:00 TR)
- 3 seviye: Ham veri / Günlük peak / Aylık peak
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
    """Standart portföy değeri hesapla"""
    if gold_price is None or silver_price is None:
        return 0
    return (gold_price * gold_amount) + (silver_price * silver_amount)

def find_daily_peak(records, target_date):
    """Belirli bir günün en yüksek portföy değerine sahip kaydını bulur"""
    day_records = [r for r in records 
                   if r.get("date") == target_date 
                   and r.get("gold_price") 
                   and r.get("silver_price")]
    
    if not day_records:
        return None
    
    max_portfolio = 0
    peak_record = None
    
    for record in day_records:
        portfolio_value = record.get("portfolio_value", 0)
        if portfolio_value == 0:
            # Portfolio hesaplanmamışsa hesapla
            portfolio_value = calculate_portfolio_value(
                record.get("gold_price"),
                record.get("silver_price")
            )
        
        if portfolio_value > max_portfolio:
            max_portfolio = portfolio_value
            peak_record = record
    
    return peak_record

def find_monthly_peak(records, target_month):
    """Belirli bir ayın günlük peak'lerinden en yüksek olanını bulur"""
    daily_peaks = [r for r in records 
                   if r.get("date", "").startswith(target_month)
                   and r.get("daily_peak") == True]
    
    if not daily_peaks:
        return None
    
    max_portfolio = 0
    peak_record = None
    
    for record in daily_peaks:
        portfolio_value = record.get("portfolio_value", 0)
        
        if portfolio_value > max_portfolio:
            max_portfolio = portfolio_value
            peak_record = record
    
    return peak_record

def optimize_realtime(price_data):
    """Her yeni veri eklendiğinde çalışır - Peak'leri günceller"""
    records = price_data.get("records", [])
    
    if not records:
        return price_data
    
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    current_month = now.strftime("%Y-%m")
    
    # 1. GÜNLÜK PEAK GÜNCELLEME
    # Bugünün tüm daily_peak flag'lerini sıfırla
    for record in records:
        if record.get("date") == today:
            record["daily_peak"] = False
    
    # Bugünün en yüksek portföy değerini bul
    daily_peak = find_daily_peak(records, today)
    
    if daily_peak:
        # Peak kaydını işaretle
        for record in records:
            if (record.get("timestamp") == daily_peak.get("timestamp") and 
                record.get("date") == today):
                record["daily_peak"] = True
                print(f"✅ Günlük peak güncellendi: {record['time']} - {record['portfolio_value']:.2f} TL")
                break
    
    # 2. AYLIK PEAK GÜNCELLEME
    # Bu ayın tüm monthly_peak flag'lerini sıfırla
    for record in records:
        if record.get("date", "").startswith(current_month):
            record["monthly_peak"] = False
    
    # Bu ayın günlük peak'lerinden en yüksek olanını bul
    monthly_peak = find_monthly_peak(records, current_month)
    
    if monthly_peak:
        # Peak kaydını işaretle
        for record in records:
            if (record.get("timestamp") == monthly_peak.get("timestamp") and 
                record.get("date") == monthly_peak.get("date")):
                record["monthly_peak"] = True
                print(f"✅ Aylık peak güncellendi: {record['date']} {record['time']} - {record['portfolio_value']:.2f} TL")
                break
    
    price_data["records"] = records
    price_data["last_optimization"] = now.isoformat()
    
    return price_data

def cleanup_old_raw_data():
    """Gece 02:00'da çalışır - Dünün ve daha eski günlerin ham verilerini siler"""
    print("🌙 Gece temizliği başlatılıyor...")
    
    price_data = load_price_history()
    records = price_data.get("records", [])
    
    if not records:
        print("❌ Temizlenecek veri bulunamadı!")
        return
    
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    
    initial_count = len(records)
    cleaned_records = []
    removed_count = 0
    
    for record in records:
        record_date = record.get("date")
        
        # Bugünse DOKUNMA
        if record_date == today:
            cleaned_records.append(record)
            continue
        
        # Dün veya daha eski
        if record_date < today:
            # Peak ise KORU
            if record.get("daily_peak") or record.get("monthly_peak"):
                cleaned_records.append(record)
            else:
                # Ham veri SİL
                removed_count += 1
        else:
            # Gelecek tarih (olmamalı ama)
            cleaned_records.append(record)
    
    # Veriyi güncelle
    price_data["records"] = cleaned_records
    price_data["last_cleanup"] = now.isoformat()
    price_data["cleanup_stats"] = {
        "date": today,
        "initial_count": initial_count,
        "final_count": len(cleaned_records),
        "removed_count": removed_count
    }
    
    # Dosyaya kaydet
    if save_price_history(price_data):
        print(f"✅ Temizlik tamamlandı!")
        print(f"   📊 Başlangıç kayıt: {initial_count}")
        print(f"   🗑️ Silinen kayıt: {removed_count}")
        print(f"   💾 Kalan kayıt: {len(cleaned_records)}")
    else:
        print("❌ Temizlik kaydetme başarısız!")

def collect_price_data():
    """Normal fiyat verisi toplama işlemi + Anlık optimizasyon"""
    print("📊 Metal Fiyat Takip Botu v3.0 - Veri Toplama")
    print(f"⏱️  Çalışma Sıklığı: Her 15 dakikada bir (*/15 cron)")
    print(f"🕐 Çalışma Saatleri: 07:00-00:59 TR")
    print(f"⏰ Zaman: {datetime.now(timezone.utc).isoformat()}")
    
    # Fiyatları çek
    gold_price = get_gold_price()
    silver_price = get_silver_price()
    
    if gold_price is None and silver_price is None:
        print("❌ Hiçbir fiyat alınamadı!")
        return
    
    print(f"✅ Altın: {gold_price} TL" if gold_price else "❌ Altın fiyatı alınamadı")
    print(f"✅ Gümüş: {silver_price} TL" if silver_price else "❌ Gümüş fiyatı alınamadı")
    
    # Portföy değeri hesapla
    portfolio_value = calculate_portfolio_value(gold_price, silver_price) if gold_price and silver_price else 0
    
    # Mevcut veriyi yükle
    price_data = load_price_history()
    
    now = datetime.now(timezone.utc)
    
    # Basitleştirilmiş kayıt - Gereksiz alanlar kaldırıldı
    new_record = {
        "timestamp": int(now.timestamp()),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "gold_price": gold_price,
        "silver_price": silver_price,
        "portfolio_value": portfolio_value,
        "daily_peak": False,
        "monthly_peak": False
    }
    
    # Kayıtları güncelle
    price_data["records"].append(new_record)
    
    # ANINDA OPTİMİZASYON YAP
    print("\n⚡ Anlık optimizasyon başlatılıyor...")
    price_data = optimize_realtime(price_data)
    
    # Meta bilgileri güncelle
    price_data["last_update"] = now.isoformat()
    price_data["total_records"] = len(price_data["records"])
    price_data["bot_version"] = "3.0.0"
    price_data["format_version"] = "simplified"
    price_data["cron_format"] = "*/15 4-21 * * * (Garantili 15 dakikalık periyot)"
    
    # Dosyaya kaydet
    if save_price_history(price_data):
        print(f"\n✅ Veri kaydedildi. Toplam kayıt: {len(price_data['records'])}")
        print(f"📦 Format: Basitleştirilmiş (gereksiz alanlar kaldırıldı)")
        if portfolio_value > 0:
            print(f"💰 Portföy Değeri: {portfolio_value:.2f} TL (1gr altın + 1gr gümüş)")
        print(f"🔄 Bir sonraki çalışma: 15 dakika sonra (*/15 cron)")
    else:
        print("\n❌ Veri kaydetme başarısız!")

def main():
    parser = argparse.ArgumentParser(description='Metal Price Tracker Bot v3.0')
    parser.add_argument('--collect', action='store_true', 
                       help='Collect current price data + realtime optimization (Her 15 dakika - */15 cron)')
    parser.add_argument('--cleanup', action='store_true', 
                       help='Clean old raw data (keep only peaks) - Gece 02:00')
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_old_raw_data()
    elif args.collect:
        collect_price_data()
    else:
        # Varsayılan davranış: veri toplama
        collect_price_data()

if __name__ == "__main__":
    main()