#!/usr/bin/env python3
"""
Metal Price Tracker Web App v3.0
Flask web uygulaması - 3 sekme: Saatlik / Günlük / Aylık
"""
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
CORS(app)

def load_price_history():
    """GitHub'dan fiyat geçmişini yükler"""
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/data/price-history.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"records": []}
    except Exception:
        return {"records": []}

def get_hourly_data():
    """Sadece bugünün tüm verilerini getir (07:00-21:00, 30dk aralıklarla)"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        hourly_data = []
        
        # Sadece bugünün verilerini al (optimize edilmemiş)
        today_records = [r for r in records 
                        if r.get("date") == today 
                        and r.get("gold_price") 
                        and r.get("silver_price")
                        and not r.get("optimized", False)]
        
        if today_records:
            sorted_records = sorted(today_records, key=lambda x: x.get("timestamp", 0), reverse=True)
            
            for i, record in enumerate(sorted_records):
                timestamp = record.get("timestamp", 0)
                local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
                
                time_label = local_time.strftime("%H:%M")
                
                # Değişim hesaplama (bir önceki kayıt ile karşılaştır)
                change_percent = 0
                if i < len(sorted_records) - 1:
                    prev_record = sorted_records[i + 1]
                    if prev_record and prev_record.get("gold_price"):
                        price_diff = record["gold_price"] - prev_record["gold_price"]
                        change_percent = (price_diff / prev_record["gold_price"]) * 100
                
                hourly_data.append({
                    "time": time_label,
                    "gold_price": record["gold_price"],
                    "silver_price": record["silver_price"],
                    "change_percent": change_percent,
                    "optimized": False
                })
        
        return hourly_data
        
    except Exception:
        return []

def get_daily_optimized_data():
    """Son 7 günün optimize edilmiş verilerini getir (günlük peak değerler)"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        # daily_peak: true olan kayıtları bul
        daily_peaks = [
            r for r in records 
            if r.get("daily_peak") == True
        ]
        
        daily_data = []
        daily_temp = []
        now = datetime.now(timezone.utc)
        
        # Son 7 günü topla (eskiden yeniye)
        for i in range(6, -1, -1):
            target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            
            # O günün peak kaydını bul
            day_record = next(
                (r for r in daily_peaks if r.get("date") == target_date), 
                None
            )
            
            if day_record:
                day_name = (now - timedelta(days=i)).strftime("%d.%m")
                daily_temp.append({
                    "time": day_name,
                    "gold_price": day_record["gold_price"],
                    "silver_price": day_record["silver_price"],
                    "peak_time": day_record.get("peak_time", "unknown"),
                    "portfolio_value": day_record.get("portfolio_value", 0)
                })
        
        # Değişim hesaplama
        for i, day_data in enumerate(daily_temp):
            change_percent = 0
            
            if i > 0:
                prev_day = daily_temp[i-1]
                if prev_day["gold_price"] > 0:
                    price_diff = day_data["gold_price"] - prev_day["gold_price"]
                    change_percent = (price_diff / prev_day["gold_price"]) * 100
            
            daily_data.append({
                "time": f"{day_data['time']} 📊",
                "gold_price": day_data["gold_price"],
                "silver_price": day_data["silver_price"],
                "change_percent": change_percent,
                "optimized": True,
                "peak_time": day_data["peak_time"],
                "portfolio_value": day_data["portfolio_value"]
            })
        
        # En son kayıt en başta olsun (yeniden eskiye)
        daily_data.reverse()
        
        return daily_data
        
    except Exception:
        return []

def get_monthly_optimized_data():
    """Son 12 ayın optimize edilmiş verilerini getir (aylık peak değerler)"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        # monthly_peak: true olan kayıtları bul
        monthly_peaks = [
            r for r in records 
            if r.get("monthly_peak") == True
        ]
        
        monthly_data = []
        monthly_temp = []
        now = datetime.now(timezone.utc)
        
        # Son 12 ayı topla (eskiden yeniye)
        for i in range(11, -1, -1):
            target_month = (now - timedelta(days=i*30)).strftime("%Y-%m")
            
            # O ayın peak kaydını bul
            month_record = next(
                (r for r in monthly_peaks 
                 if r.get("date", "").startswith(target_month)), 
                None
            )
            
            if month_record:
                # Ay ismi: "Ocak", "Şubat" vs.
                month_date = datetime.strptime(month_record["date"], "%Y-%m-%d")
                month_names = {
                    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
                    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
                    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
                }
                month_label = f"{month_names[month_date.month]} {month_date.year}"
                
                monthly_temp.append({
                    "time": month_label,
                    "gold_price": month_record["gold_price"],
                    "silver_price": month_record["silver_price"],
                    "peak_time": month_record.get("peak_time", "unknown"),
                    "peak_date": month_record.get("date", "unknown"),
                    "portfolio_value": month_record.get("portfolio_value", 0)
                })
        
        # Değişim hesaplama
        for i, month_data in enumerate(monthly_temp):
            change_percent = 0
            
            if i > 0:
                prev_month = monthly_temp[i-1]
                if prev_month["gold_price"] > 0:
                    price_diff = month_data["gold_price"] - prev_month["gold_price"]
                    change_percent = (price_diff / prev_month["gold_price"]) * 100
            
            monthly_data.append({
                "time": f"{month_data['time']} 🏆",
                "gold_price": month_data["gold_price"],
                "silver_price": month_data["silver_price"],
                "change_percent": change_percent,
                "optimized": True,
                "peak_time": month_data["peak_time"],
                "peak_date": month_data["peak_date"],
                "portfolio_value": month_data["portfolio_value"]
            })
        
        # En son kayıt en başta olsun (yeniden eskiye)
        monthly_data.reverse()
        
        return monthly_data
        
    except Exception:
        return []

def get_table_data():
    """Saatlik, günlük ve aylık veriler için farklı kaynak kullan"""
    try:
        hourly_data = get_hourly_data()
        daily_data = get_daily_optimized_data()
        monthly_data = get_monthly_optimized_data()
        
        return {
            "hourly": hourly_data,
            "daily": daily_data,
            "monthly": monthly_data
        }
        
    except Exception:
        return {"hourly": [], "daily": [], "monthly": []}

def get_gold_price():
    """Yapı Kredi altın fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '6-gram-altin',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
        return None
        
    except Exception as e:
        raise Exception(f"Gold price error: {str(e)}")

def get_silver_price():
    """Vakıfbank gümüş fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/vakifbank/gumus"
        headers = {'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '5-gumus',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
        return None
        
    except Exception as e:
        raise Exception(f"Silver price error: {str(e)}")

# HTML TEMPLATE - Bölüm 2'de devam edecek
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker v3.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #667eea 100%);
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 480px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding: 0 2px; }
        
        .header {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 16px 20px; border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .logo { font-size: 18px; font-weight: 700; color: white; }
        .version { font-size: 11px; color: rgba(255, 255, 255, 0.6); background: rgba(255, 255, 255, 0.1); padding: 2px 8px; border-radius: 8px; }
        .update-time { font-size: 14px; color: rgba(255, 255, 255, 0.8); }
        .actions { display: flex; gap: 10px; }
        .action-btn {
            width: 44px; height: 44px; border-radius: 12px;
            background: rgba(255, 255, 255, 0.2); border: none;
            color: white; font-size: 18px; cursor: pointer;
            transition: all 0.3s ease; display: flex; align-items: center; justify-content: center;
        }
        .action-btn:hover { background: rgba(255, 255, 255, 0.3); }
        
        .portfolio-summary {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            border-radius: 24px; padding: 24px 20px; color: white;
            box-shadow: 0 15px 35px rgba(238, 90, 36, 0.4);
            display: none; text-align: center;
        }
        .portfolio-amount { font-size: 42px; font-weight: 900; margin-bottom: 20px; }
        .portfolio-metals {
            display: flex; justify-content: center; gap: 6px;
            margin: 20px 10px 0 10px;
        }
        .metal-item {
            flex: 1; 
            background: rgba(255, 255, 255, 0.15); 
            border-radius: 16px; 
            padding: 16px;
            backdrop-filter: blur(10px); 
            border: 1px solid rgba(255, 255, 255, 0.2);
            min-height: 140px;
        }
        .metal-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
        .metal-name { font-size: 16px; font-weight: 600; }
        .metal-price { font-size: 15px; opacity: 0.8; margin-bottom: 8px; }
        .metal-value { font-size: 22px; font-weight: 700; }
        
        .price-history {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 16px 4px; border: 1px solid rgba(255, 255, 255, 0.3);
            display: none; margin: 0 -10px; width: calc(100% + 20px);
        }
        .history-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
            padding: 0 16px;
        }
        .history-title { font-size: 18px; font-weight: 700; color: #2c3e50; }
        .period-tabs {
            display: flex; gap: 6px;
            background: #f8f9fa; border-radius: 10px; padding: 4px;
        }
        .period-tab {
            padding: 8px 12px; border: none; border-radius: 6px;
            background: transparent; color: #6c757d;
            font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .period-tab.active { background: white; color: #2c3e50; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        
        .price-table {
            overflow-x: auto; border-radius: 12px; background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 0 8px;
        }
        .price-table table {
            width: 100%; border-collapse: collapse;
        }
        .price-table th {
            background: #f8f9fa; padding: 12px 8px; text-align: left;
            font-weight: 600; color: #495057; font-size: 13px;
            border-bottom: 2px solid #e9ecef; white-space: nowrap;
        }
        .price-table td {
            padding: 12px 8px; border-bottom: 1px solid #f1f3f4;
            font-size: 13px; color: #495057; white-space: nowrap;
        }
        .price-table tr:hover {
            background: #f8f9fa;
        }
        .price-table .time { font-weight: 600; color: #2c3e50; }
        .price-table .price { font-weight: 600; }
        .price-table .portfolio { font-weight: 700; color: #e67e22; }
        .price-table .change {
            font-weight: 600; font-size: 13px;
        }
        .change.positive { color: #27ae60; }
        .change.negative { color: #e74c3c; }
        .change.neutral { color: #95a5a6; }
        
        .peak-row {
            background-color: #fff8e7 !important;
            border-left: 2px solid #f39c12;
            animation: peakPulse 3s ease-in-out infinite;
        }
        
        @keyframes peakPulse {
            0%, 100% { background-color: #fff8e7; }
            50% { background-color: #ffeaa7; }
        }
        
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(12px);
            z-index: 1000; display: none; align-items: center; justify-content: center; padding: 20px;
        }
        .modal-content {
            background: white; border-radius: 24px; padding: 28px;
            width: 100%; max-width: 350px; position: relative;
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .modal-title { font-size: 22px; font-weight: 800; color: #2c3e50; }
        .close-btn {
            width: 36px; height: 36px; border-radius: 10px; background: #f8f9fa;
            border: none; font-size: 18px; cursor: pointer; display: flex;
            align-items: center; justify-content: center;
        }
        .input-group { margin-bottom: 22px; }
        .input-label { display: block; margin-bottom: 10px; font-weight: 700; color: #2c3e50; font-size: 15px; }
        .input-field {
            width: 100%; padding: 16px; border: 2px solid #e9ecef;
            border-radius: 14px; font-size: 17px; background: #f8f9fa; font-weight: 600;
        }
        .input-field:focus { outline: none; border-color: #667eea; background: white; }
        .modal-actions { display: flex; gap: 14px; justify-content: flex-end; }
        .btn {
            padding: 14px 24px; border-radius: 12px; font-weight: 700;
            cursor: pointer; border: none; font-size: 15px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #e9ecef; color: #6c757d; }
        
        @media (max-width: 400px) {
            .container { max-width: 100%; padding: 0 1px; }
            .history-header { flex-direction: column; gap: 12px; }
            .portfolio-metals { flex-direction: column; gap: 12px; }
            .metal-name { font-size: 17px; }
            .metal-price { font-size: 16px; }
            .metal-value { font-size: 24px; }
            .metal-item { padding: 20px; min-height: 130px; }
            .price-table th, .price-table td { padding: 10px 6px; font-size: 12px; }
            .price-history { padding: 12px 2px; margin: 0 -5px; width: calc(100% + 10px); }
            .price-table { margin: 0 4px; }
            .history-header { padding: 0 8px; }
            .period-tabs { flex-wrap: wrap; }
            .period-tab { font-size: 11px; padding: 6px 10px; }
        }
    </style>
</head>
'''

# API Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/gold-price')
def api_gold_price():
    try:
        price = get_gold_price()
        return jsonify({'success': bool(price), 'price': price or ''})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/silver-price')
def api_silver_price():
    try:
        price = get_silver_price()
        return jsonify({'success': bool(price), 'price': price or ''})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/table-data')
def api_table_data():
    try:
        data = get_table_data()
        return jsonify({'success': bool(data), 'data': data or {}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)