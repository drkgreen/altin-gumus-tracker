#!/usr/bin/env python3
"""
Metal Price Tracker Bot v2.0
GitHub Actions ile arka planda çalışır ve fiyat verilerini toplar
Yeni özellikler:
- Her gün 07:00-21:00 arası veri toplama
- Gece 02:00'de günlük optimizasyon (en yüksek portföy değeri)
- Hafta sonu dahil 7/24 çalışma
- Geriye dönük optimizasyon desteği
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

def optimize_single_day(records, target_date):
    """Belirli bir günün verilerini optimize eder"""
    # O güne ait optimize edilmemiş kayıtları bul
    day_records = [r for r in records 
                  if r.get("date") == target_date 
                  and not r.get("optimized", False)]
    
    if not day_records:
        return None, 0
    
    # En yüksek portföy değerine sahip kaydı bul
    max_portfolio_value = 0
    peak_record = None
    
    for record in day_records:
        gold_price = record.get("gold_price")
        silver_price = record.get("silver_price")
        
        if gold_price and silver_price:
            portfolio_value = calculate_portfolio_value(gold_price, silver_price)
            
            if portfolio_value > max_portfolio_value:
                max_portfolio_value = portfolio_value
                peak_record = record.copy()
    
    if peak_record:
        # Peak kaydı optimize edilmiş olarak işaretle
        peak_record.update({
            "optimized": True,
            "daily_peak": True,
            "portfolio_value": max_portfolio_value,
            "peak_time": peak_record.get("time", "unknown")
        })
    
    return peak_record, len(day_records)

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
    
    # Tek günü optimize et
    peak_record, original_count = optimize_single_day(records, yesterday)
    
    if not peak_record:
        print(f"❌ {yesterday} tarihine ait optimize edilmemiş veri bulunamadı!")
        return
    
    print(f"📊 {yesterday} tarihine ait {original_count} kayıt bulundu")
    
    # Dünün TÜM kayıtlarını sil ve sadece peak kaydı ekle
    filtered_records = [r for r in records if r.get("date") != yesterday]
    filtered_records.append(peak_record)
    
    # Veriyi güncelle
    price_data["records"] = filtered_records
    price_data["last_optimization"] = datetime.now(timezone.utc).isoformat()
    price_data["optimization_stats"] = {
        "date": yesterday,
        "original_count": original_count,
        "peak_portfolio_value": peak_record["portfolio_value"],
        "peak_time": peak_record.get("time"),
        "removed_count": original_count - 1
    }
    
    # Dosyaya kaydet
    if save_price_history(price_data):
        print(f"✅ Optimizasyon tamamlandı!")
        print(f"   📅 Tarih: {yesterday}")
        print(f"   📊 Peak Portföy: {peak_record['portfolio_value']:.2f} TL")
        print(f"   🕐 Peak Saat: {peak_record.get('time')}")
        print(f"   🗑️ Silinen kayıt: {original_count - 1}")
        print(f"   💾 Toplam kayıt: {len(filtered_records)}")
    else:
        print("❌ Optimizasyon kaydetme başarısız!")

def retroactive_optimization(days_back=7):
    """Geriye dönük optimizasyon yapar"""
    print(f"🔄 Geriye dönük optimizasyon başlatılıyor...")
    print(f"Son {days_back} gün optimize edilecek")
    print(f"Zaman: {datetime.now(timezone.utc).isoformat()}")
    print("-" * 50)
    
    # Mevcut veriyi yükle
    price_data = load_price_history()
    records = price_data.get("records", [])
    
    if not records:
        print("❌ Optimize edilecek veri bulunamadı!")
        return
    
    optimization_results = []
    total_removed = 0
    
    # Son N günü geriye doğru kontrol et
    for i in range(1, days_back + 1):
        target_date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        
        print(f"\n📅 İşleniyor: {target_date}")
        
        # O güne ait optimize edilmemiş kayıtları say
        unoptimized_count = len([r for r in records 
                                if r.get("date") == target_date 
                                and not r.get("optimized", False)])
        
        if unoptimized_count == 0:
            # Zaten optimize edilmiş mi kontrol et
            optimized_exists = any(r for r in records 
                                 if r.get("date") == target_date 
                                 and r.get("optimized", True))
            
            if optimized_exists:
                print(f"   ✅ Zaten optimize edilmiş")
            else:
                print(f"   ⏭️ Veri yok, atlanıyor")
            continue
        
        # O günü optimize et
        peak_record, original_count = optimize_single_day(records, target_date)
        
        if peak_record:
            # O günün TÜM kayıtlarını sil
            records = [r for r in records if r.get("date") != target_date]
            # Sadece peak kaydı ekle
            records.append(peak_record)
            
            removed = original_count - 1
            total_removed += removed
            
            optimization_results.append({
                "date": target_date,
                "original_count": original_count,
                "peak_value": peak_record["portfolio_value"],
                "peak_time": peak_record.get("time"),
                "removed": removed
            })
            
            print(f"   📊 {original_count} kayıt → 1 peak kayıt")
            print(f"   💰 Peak değer: {peak_record['portfolio_value']:.2f} TL")
            print(f"   🕐 Peak saat: {peak_record.get('time')}")
    
    # Veriyi güncelle
    price_data["records"] = records
    price_data["last_retroactive_optimization"] = datetime.now(timezone.utc).isoformat()
    price_data["retroactive_optimization_stats"] = {
        "days_processed": len(optimization_results),
        "total_removed": total_removed,
        "results": optimization_results
    }
    
    # Eski kayıtları temizle
    price_data["records"] = cleanup_old_records(price_data["records"])
    price_data["total_records"] = len(price_data["records"])
    
    # Dosyaya kaydet
    if save_price_history(price_data):
        print("\n" + "=" * 50)
        print("✅ Geriye dönük optimizasyon tamamlandı!")
        print(f"📊 İşlenen gün sayısı: {len(optimization_results)}")
        print(f"🗑️ Toplam silinen kayıt: {total_removed}")
        print(f"💾 Kalan toplam kayıt: {len(price_data['records'])}")
        
        if optimization_results:
            print("\n📈 Optimize edilen günler:")
            for result in optimization_results:
                print(f"   • {result['date']}: {result['original_count']} → 1 kayıt (Peak: {result['peak_value']:.2f} TL)")
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
    parser.add_argument('--retroactive', action='store_true',
                       help='Run retroactive optimization for past days')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to optimize retroactively (default: 7)')
    
    args = parser.parse_args()
    
    if args.retroactive:
        retroactive_optimization(days_back=args.days)
    elif args.optimize:
        optimize_daily_data()
    elif args.collect:
        collect_price_data()
    else:
        # Varsayılan davranış: veri toplama
        collect_price_data()

if __name__ == "__main__":
    main()