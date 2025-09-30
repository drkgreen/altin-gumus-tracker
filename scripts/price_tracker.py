#!/usr/bin/env python3
"""
Metal Price Tracker Bot v2.0
Yeni özellikler:
- 07:00-22:00 arası veri toplama
- 02:00'da günlük temizleme ve max değer saklama
- Haftalık arşiv sistemi
"""

import json
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import os
import sys
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

def load_daily_records():
    """Günlük kayıtları yükler"""
    try:
        with open('data/daily-records.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        current_date = get_turkey_date()  # TR tarihini kullan
        return {
            "current_date": current_date,
            "records": [],
            "last_update": None
        }
    except Exception as e:
        print(f"Günlük kayıt okuma hatası: {e}")
        return {"current_date": "", "records": [], "last_update": None}

def save_daily_records(data):
    """Günlük kayıtları dosyaya kaydeder"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/daily-records.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Günlük kayıt kaydetme hatası: {e}")
        return False

def load_weekly_archive():
    """Haftalık arşivi yükler"""
    try:
        with open('data/weekly-archive.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "archive": [],
            "last_cleanup": None,
            "total_days": 0
        }
    except Exception as e:
        print(f"Haftalık arşiv okuma hatası: {e}")
        return {"archive": [], "last_cleanup": None, "total_days": 0}

def save_weekly_archive(data):
    """Haftalık arşivi dosyaya kaydeder"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/weekly-archive.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Haftalık arşiv kaydetme hatası: {e}")
        return False

def get_turkey_time():
    """Türkiye saati döndürür (UTC+3)"""
    return datetime.now(timezone.utc) + timedelta(hours=3)

def get_turkey_date():
    """Türkiye tarihini döndürür (UTC+3)"""
    return get_turkey_time().strftime("%Y-%m-%d")

def collect_prices():
    """Anlık fiyat toplama modu"""
    turkey_time = get_turkey_time()
    utc_time = datetime.now(timezone.utc)
    
    print("📊 Fiyat Toplama Modu")
    print(f"⏰ UTC Zaman: {utc_time.strftime('%H:%M:%S')}")
    print(f"🇹🇷 TR Zaman: {turkey_time.strftime('%H:%M:%S')}")
    
    # Fiyatları çek
    gold_price = get_gold_price()
    silver_price = get_silver_price()
    
    if gold_price is None and silver_price is None:
        print("❌ Hiçbir fiyat alınamadı!")
        return False
    
    print(f"✅ Altın: {gold_price} TL" if gold_price else "❌ Altın fiyatı alınamadı")
    print(f"✅ Gümüş: {silver_price} TL" if silver_price else "❌ Gümüş fiyatı alınamadı")
    
    # Günlük kayıtları yükle
    daily_data = load_daily_records()
    current_date = get_turkey_date()  # Türkiye tarihini kullan
    
    # Tarih değişti mi kontrol et (Türkiye saatine göre)
    if daily_data["current_date"] != current_date:
        print(f"📅 Yeni gün başladı (TR): {current_date}")
        daily_data = {
            "current_date": current_date,
            "records": [],
            "last_update": None
        }
    
    # Yeni kaydı oluştur (UTC timestamp, TR time string)
    new_record = {
        "timestamp": utc_time.timestamp(),  # UTC timestamp
        "time": turkey_time.strftime("%H:%M:%S"),  # TR saat
        "turkey_date": current_date,  # TR tarih
        "gold_price": gold_price,
        "silver_price": silver_price,
        "success": {
            "gold": gold_price is not None,
            "silver": silver_price is not None
        }
    }
    
    # Kayıtları güncelle
    daily_data["records"].append(new_record)
    daily_data["last_update"] = utc_time.isoformat()
    
    # Dosyaya kaydet
    if save_daily_records(daily_data):
        print(f"✅ Günlük veri kaydedildi. Toplam kayıt: {len(daily_data['records'])}")
        return True
    else:
        print("❌ Günlük veri kaydetme başarısız!")
        return False

def cleanup_and_archive():
    """Günlük temizleme ve arşivleme modu"""
    turkey_time = get_turkey_time()
    utc_time = datetime.now(timezone.utc)
    
    print("🧹 Temizleme ve Arşivleme Modu")
    print(f"⏰ UTC Zaman: {utc_time.strftime('%H:%M:%S')}")
    print(f"🇹🇷 TR Zaman: {turkey_time.strftime('%H:%M:%S')}")
    
    # Dünün tarihini hesapla (Türkiye saatine göre)
    yesterday_turkey = (turkey_time - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"📅 İşlenecek tarih (TR): {yesterday_turkey}")
    
    # Günlük kayıtları yükle
    daily_data = load_daily_records()
    
    # Eğer işlenecek tarih mevcut tarih ise (dünün verisi)
    if daily_data["current_date"] == yesterday_turkey and daily_data["records"]:
        print(f"📊 {len(daily_data['records'])} adet kayıt bulundu")
        
        # Max değerleri bul
        valid_records = [r for r in daily_data["records"] 
                        if r.get("gold_price") and r.get("silver_price")]
        
        if not valid_records:
            print("❌ Geçerli veri bulunamadı!")
            return False
        
        # En yüksek fiyatları bul
        max_gold_record = max(valid_records, key=lambda x: x["gold_price"])
        max_silver_record = max(valid_records, key=lambda x: x["silver_price"])
        
        max_gold_price = max_gold_record["gold_price"]
        max_silver_price = max_silver_record["silver_price"]
        max_gold_time = max_gold_record["time"]  # Zaten TR saati
        max_silver_time = max_silver_record["time"]  # Zaten TR saati
        
        print(f"🏆 Max Altın: {max_gold_price} TL (TR {max_gold_time})")
        print(f"🏆 Max Gümüş: {max_silver_price} TL (TR {max_silver_time})")
        
        # Haftalık arşivi yükle
        weekly_data = load_weekly_archive()
        
        # Yeni arşiv kaydı oluştur
        archive_record = {
            "date": yesterday_turkey,  # TR tarih
            "max_gold_price": max_gold_price,
            "max_silver_price": max_silver_price,
            "max_gold_time": max_gold_time,  # TR saat
            "max_silver_time": max_silver_time,  # TR saat
            "total_records": len(daily_data["records"]),
            "archived_at": utc_time.isoformat(),  # UTC timestamp
            "archived_at_turkey": turkey_time.isoformat()  # TR timestamp
        }
        
        # Arşive ekle
        weekly_data["archive"].append(archive_record)
        
        # 30 günden eski arşiv kayıtlarını sil (TR tarihine göre)
        cutoff_date = (turkey_time - timedelta(days=30)).strftime("%Y-%m-%d")
        old_count = len(weekly_data["archive"])
        weekly_data["archive"] = [
            record for record in weekly_data["archive"]
            if record["date"] > cutoff_date
        ]
        removed_count = old_count - len(weekly_data["archive"])
        
        if removed_count > 0:
            print(f"🗑️ {removed_count} eski kayıt silindi (30 gün öncesi)")
        
        # Meta bilgileri güncelle
        weekly_data["last_cleanup"] = utc_time.isoformat()
        weekly_data["last_cleanup_turkey"] = turkey_time.isoformat()
        weekly_data["total_days"] = len(weekly_data["archive"])
        
        # Haftalık arşivi kaydet
        if save_weekly_archive(weekly_data):
            print(f"✅ Haftalık arşiv güncellendi. Toplam gün: {weekly_data['total_days']}")
        else:
            print("❌ Haftalık arşiv kaydetme başarısız!")
            return False
        
        # Günlük kayıtları temizle (yeni gün için hazırla)
        new_date = get_turkey_date()  # Bugünün TR tarihi
        daily_data = {
            "current_date": new_date,
            "records": [],
            "last_update": None
        }
        
        if save_daily_records(daily_data):
            print(f"✅ Günlük kayıtlar temizlendi. Yeni gün (TR): {new_date}")
            return True
        else:
            print("❌ Günlük kayıt temizleme başarısız!")
            return False
    
    else:
        print(f"ℹ️ İşlenecek veri bulunamadı")
        print(f"   Beklenen tarih: {yesterday_turkey}")
        print(f"   Mevcut tarih: {daily_data.get('current_date')}")
        print(f"   Kayıt sayısı: {len(daily_data.get('records', []))}")
        return True

def main():
    parser = argparse.ArgumentParser(description='Metal Price Tracker v2.0')
    parser.add_argument('--mode', choices=['collect', 'cleanup'], required=True,
                      help='Çalışma modu: collect (fiyat toplama) veya cleanup (temizleme)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 Metal Fiyat Takipçisi v2.0")
    print("=" * 60)
    
    if args.mode == 'collect':
        success = collect_prices()
    elif args.mode == 'cleanup':
        success = cleanup_and_archive()
    else:
        print("❌ Geçersiz mod!")
        sys.exit(1)
    
    if success:
        print("✅ İşlem başarıyla tamamlandı!")
        sys.exit(0)
    else:
        print("❌ İşlem başarısız!")
        sys.exit(1)

if __name__ == "__main__":
    main()