#!/usr/bin/env python3
# scripts/collect_prices.py
import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import time

class PriceCollector:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data')
        
        # Data klasörünü oluştur
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.prices_file = os.path.join(self.data_dir, 'prices.json')
        self.daily_file = os.path.join(self.data_dir, 'daily_stats.json')
        
    def get_gold_price(self):
        """Yapı Kredi altın fiyatını çeker"""
        try:
            url = "https://m.doviz.com/altin/yapikredi/gram-altin"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0',
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
                # "4.797,82" -> 4797.82
                clean_price = price_text.replace('.', '').replace(',', '.')
                return float(clean_price)
                
            return None
            
        except Exception as e:
            print(f"Altın fiyatı alınamadı: {e}")
            return None

    def get_silver_price(self):
        """Vakıfbank gümüş fiyatını çeker"""
        try:
            url = "https://m.doviz.com/altin/vakifbank/gumus"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0',
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
                # "54,43" -> 54.43
                clean_price = price_text.replace(',', '.')
                return float(clean_price)
                
            return None
            
        except Exception as e:
            print(f"Gümüş fiyatı alınamadı: {e}")
            return None

    def load_existing_data(self):
        """Mevcut veriyi yükle"""
        try:
            if os.path.exists(self.prices_file):
                with open(self.prices_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"prices": [], "last_updated": None}
        except Exception as e:
            print(f"Mevcut veri yüklenemedi: {e}")
            return {"prices": [], "last_updated": None}

    def save_data(self, data):
        """Veriyi kaydet"""
        try:
            with open(self.prices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Veriler kaydedildi: {self.prices_file}")
        except Exception as e:
            print(f"Veri kaydedilemedi: {e}")

    def collect_and_save(self):
        """Fiyatları topla ve kaydet"""
        print("Fiyat toplama başlıyor...")
        
        # Fiyatları çek
        gold_price = self.get_gold_price()
        silver_price = self.get_silver_price()
        
        if gold_price is None and silver_price is None:
            print("Hiçbir fiyat alınamadı!")
            return False
            
        # Mevcut veriyi yükle
        data = self.load_existing_data()
        
        # Yeni veri noktası
        now = datetime.now(timezone.utc)
        price_entry = {
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "hour": now.hour,
            "gold_price": gold_price,
            "silver_price": silver_price,
            "success": {
                "gold": gold_price is not None,
                "silver": silver_price is not None
            }
        }
        
        # Listeye ekle
        data["prices"].append(price_entry)
        data["last_updated"] = now.isoformat()
        
        # Son 30 günlük veriyi tut (30 * 24 = 720 saat)
        if len(data["prices"]) > 720:
            data["prices"] = data["prices"][-720:]
            
        # Kaydet
        self.save_data(data)
        
        print(f"Başarıyla kaydedildi:")
        print(f"  Altın: {gold_price} TL" if gold_price else "  Altın: HATA")
        print(f"  Gümüş: {silver_price} TL" if silver_price else "  Gümüş: HATA")
        print(f"  Zaman: {now.strftime('%Y-%m-%d %H:%M UTC')}")
        
        return True

    def generate_daily_stats(self):
        """Günlük istatistikler oluştur"""
        try:
            data = self.load_existing_data()
            if not data["prices"]:
                return
                
            # Tarihe göre grupla
            daily_stats = {}
            
            for price_entry in data["prices"]:
                date = price_entry["date"]
                
                if date not in daily_stats:
                    daily_stats[date] = {
                        "date": date,
                        "gold": {"prices": [], "avg": 0, "min": 0, "max": 0},
                        "silver": {"prices": [], "avg": 0, "min": 0, "max": 0},
                        "count": 0
                    }
                
                if price_entry["gold_price"]:
                    daily_stats[date]["gold"]["prices"].append(price_entry["gold_price"])
                
                if price_entry["silver_price"]:
                    daily_stats[date]["silver"]["prices"].append(price_entry["silver_price"])
                    
                daily_stats[date]["count"] += 1
            
            # İstatistikleri hesapla
            for date, stats in daily_stats.items():
                if stats["gold"]["prices"]:
                    prices = stats["gold"]["prices"]
                    stats["gold"]["avg"] = sum(prices) / len(prices)
                    stats["gold"]["min"] = min(prices)
                    stats["gold"]["max"] = max(prices)
                    
                if stats["silver"]["prices"]:
                    prices = stats["silver"]["prices"]
                    stats["silver"]["avg"] = sum(prices) / len(prices)
                    stats["silver"]["min"] = min(prices)
                    stats["silver"]["max"] = max(prices)
                
                # Fiyat listesini temizle (boyutu küçültmek için)
                stats["gold"].pop("prices", None)
                stats["silver"].pop("prices", None)
            
            # Kaydet
            with open(self.daily_file, 'w', encoding='utf-8') as f:
                json.dump(daily_stats, f, ensure_ascii=False, indent=2)
                
            print(f"Günlük istatistikler oluşturuldu: {len(daily_stats)} gün")
            
        except Exception as e:
            print(f"İstatistik oluşturulamadı: {e}")

if __name__ == "__main__":
    collector = PriceCollector()
    
    # Fiyatları topla
    success = collector.collect_and_save()
    
    if success:
        # İstatistikleri güncelle
        collector.generate_daily_stats()
        print("İşlem tamamlandı!")
    else:
        print("İşlem başarısız!")
        exit(1)