#!/usr/bin/env python3
"""
Metal Price Tracker Web App v2.0
Dark Blue Glassmorphism Theme - Düzeltilmiş Tam Sürüm
"""
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for, make_response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime, timezone, timedelta
import hashlib
import secrets

app = Flask(__name__)
CORS(app)

# Secret key sabit olsun
SECRET_KEY = os.environ.get('SECRET_KEY', 'metal_tracker_secret_key_2024_permanent')
app.secret_key = SECRET_KEY

def load_portfolio_config():
    """GitHub'dan portföy ayarlarını ve hash'lenmiş şifreyi yükler"""
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/portfolio-config.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}
    except Exception:
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}

def verify_password(password):
    """Şifreyi hash'leyip GitHub'daki hash ile karşılaştırır"""
    config = load_portfolio_config()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == config.get("password_hash", "")

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

def get_daily_data():
    """Son 2 günün tüm verilerini getir"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        now = datetime.now(timezone.utc)
        daily_data = []
        
        for day_offset in range(2):
            target_date = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            day_records = [r for r in records 
                          if r.get("date") == target_date 
                          and r.get("gold_price") 
                          and r.get("silver_price")
                          and not r.get("optimized", False)]
            
            if day_records:
                sorted_day_records = sorted(day_records, key=lambda x: x.get("timestamp", 0), reverse=True)
                
                for i, record in enumerate(sorted_day_records):
                    timestamp = record.get("timestamp", 0)
                    local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
                    
                    if day_offset == 0:
                        time_label = local_time.strftime("%H:%M")
                    else:
                        time_label = local_time.strftime("%d.%m %H:%M")
                    
                    change_percent = 0
                    if i < len(sorted_day_records) - 1:
                        prev_record = sorted_day_records[i + 1]
                        if prev_record and prev_record.get("gold_price"):
                            price_diff = record["gold_price"] - prev_record["gold_price"]
                            change_percent = (price_diff / prev_record["gold_price"]) * 100
                    
                    daily_data.append({
                        "time": time_label,
                        "gold_price": record["gold_price"],
                        "silver_price": record["silver_price"],
                        "change_percent": change_percent,
                        "optimized": False
                    })
        
        return daily_data
        
    except Exception:
        return []

def get_weekly_optimized_data():
    """Son 30 günün optimize edilmiş verilerini getir"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        optimized_records = [
            r for r in records 
            if r.get("optimized") == True and r.get("daily_peak") == True
        ]
        
        weekly_data = []
        weekly_temp = []
        now = datetime.now(timezone.utc)
        
        for i in range(29, -1, -1):
            target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            
            day_record = next(
                (r for r in optimized_records if r.get("date") == target_date), 
                None
            )
            
            if day_record:
                day_name = (now - timedelta(days=i)).strftime("%d.%m")
                weekly_temp.append({
                    "time": day_name,
                    "gold_price": day_record["gold_price"],
                    "silver_price": day_record["silver_price"],
                    "date_offset": i,
                    "peak_time": day_record.get("peak_time", "unknown"),
                    "portfolio_value": day_record.get("portfolio_value", 0)
                })
        
        for i, day_data in enumerate(weekly_temp):
            change_percent = 0
            
            if i > 0:
                prev_day = weekly_temp[i-1]
                if prev_day["gold_price"] > 0:
                    price_diff = day_data["gold_price"] - prev_day["gold_price"]
                    change_percent = (price_diff / prev_day["gold_price"]) * 100
            
            weekly_data.append({
                "time": f"{day_data['time']} 📊",
                "gold_price": day_data["gold_price"],
                "silver_price": day_data["silver_price"],
                "change_percent": change_percent,
                "optimized": True,
                "peak_time": day_data["peak_time"],
                "portfolio_value": day_data["portfolio_value"]
            })
        
        weekly_data.reverse()
        return weekly_data
        
    except Exception:
        return []

def calculate_statistics(data_type='all'):
    """Maksimum değerleri hesapla - tarih ve peak bilgileri ile"""
    try:
        config = load_portfolio_config()
        history = load_price_history()
        records = history.get("records", [])
        
        if data_type == 'daily':
            data = get_daily_data()
            # Eğer günlük veri yoksa haftalık verilerden son 3 günü al
            if not data:
                weekly_data = get_weekly_optimized_data()
                data = weekly_data[:3] if weekly_data else []
        elif data_type == 'weekly':
            data = get_weekly_optimized_data()
        else:
            daily_data = get_daily_data()
            weekly_data = get_weekly_optimized_data()
            data = daily_data + weekly_data
        
        if not data:
            return {
                "max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0,
                "max_gold_date": "", "max_silver_date": "", "max_portfolio_date": "",
                "peak_info": "Veri bulunamadı"
            }
        
        # En yüksek değerleri bul
        max_gold = max(item["gold_price"] for item in data)
        max_silver = max(item["silver_price"] for item in data)
        
        gold_amount = config.get("gold_amount", 0)
        silver_amount = config.get("silver_amount", 0)
        
        # Portföy değerleri hesapla
        portfolio_data = []
        for item in data:
            portfolio_value = (gold_amount * item["gold_price"]) + (silver_amount * item["silver_price"])
            portfolio_data.append({
                "value": portfolio_value,
                "time": item.get("time", ""),
                "optimized": item.get("optimized", False),
                "peak_time": item.get("peak_time", "")
            })
        
        max_portfolio = max(portfolio_data, key=lambda x: x["value"])["value"] if portfolio_data else 0
        
        # Tarih bilgilerini bul
        max_gold_date = ""
        max_silver_date = ""
        max_portfolio_date = ""
        peak_info = ""
        
        now = datetime.now(timezone.utc)
        turkey_time = now + timedelta(hours=3)
        day_name = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][turkey_time.weekday()]
        current_date_str = f"{turkey_time.strftime('%d.%m.%Y')} {day_name}"
        
        if data_type == 'daily':
            # Günlük veri varsa bugünün peak değerini kontrol et
            daily_data = get_daily_data()
            if daily_data:
                # Günlük veri mevcut
                today = now.strftime("%Y-%m-%d")
                today_peak = next(
                    (r for r in records 
                     if r.get("date") == today 
                     and r.get("optimized") == True 
                     and r.get("daily_peak") == True), 
                    None
                )
                
                if today_peak:
                    max_gold_date = current_date_str
                    max_silver_date = current_date_str  
                    max_portfolio_date = current_date_str
                    peak_time = today_peak.get("peak_time", "bilinmiyor")
                    peak_info = f"Bugünün peak değeri: {peak_time}"
                else:
                    max_gold_date = current_date_str
                    max_silver_date = current_date_str
                    max_portfolio_date = current_date_str
                    peak_info = "Güncel veriler"
            else:
                # Günlük veri yok, haftalık verilerden son günleri kullan
                max_gold_date = "Son günler"
                max_silver_date = "Son günler"
                max_portfolio_date = "Son günler"
                peak_info = "Günlük veri silinmiş, haftalık peak değerler gösteriliyor"
        
        elif data_type == 'weekly':
            # Haftalık veriler için en yüksek değerlerin tarihlerini bul
            for i in range(30):
                check_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                day_peak = next(
                    (r for r in records 
                     if r.get("date") == check_date 
                     and r.get("optimized") == True 
                     and r.get("daily_peak") == True), 
                    None
                )
                
                if day_peak:
                    if day_peak["gold_price"] == max_gold and not max_gold_date:
                        date_obj = now - timedelta(days=i) + timedelta(hours=3)
                        day_name = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][date_obj.weekday()]
                        max_gold_date = f"{date_obj.strftime('%d.%m.%Y')} {day_name}"
                    
                    if day_peak["silver_price"] == max_silver and not max_silver_date:
                        date_obj = now - timedelta(days=i) + timedelta(hours=3)
                        day_name = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][date_obj.weekday()]
                        max_silver_date = f"{date_obj.strftime('%d.%m.%Y')} {day_name}"
                    
                    portfolio_val = (gold_amount * day_peak["gold_price"]) + (silver_amount * day_peak["silver_price"])
                    if abs(portfolio_val - max_portfolio) < 0.01 and not max_portfolio_date:
                        date_obj = now - timedelta(days=i) + timedelta(hours=3)
                        day_name = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][date_obj.weekday()]
                        max_portfolio_date = f"{date_obj.strftime('%d.%m.%Y')} {day_name}"
            
            peak_info = "Son 30 günün peak değerleri"
        
        return {
            "max_gold_price": max_gold,
            "max_silver_price": max_silver,
            "max_portfolio_value": max_portfolio,
            "max_gold_date": max_gold_date,
            "max_silver_date": max_silver_date,
            "max_portfolio_date": max_portfolio_date,
            "peak_info": peak_info
        }
        
    except Exception as e:
        return {
            "max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0,
            "max_gold_date": "", "max_silver_date": "", "max_portfolio_date": "",
            "peak_info": f"Hata: {str(e)}"
        }

def get_table_data():
    """Tablo verilerini getir"""
    try:
        daily_data = get_daily_data()
        weekly_data = get_weekly_optimized_data()
        
        daily_stats = calculate_statistics('daily')
        weekly_stats = calculate_statistics('weekly')
        
        return {
            "daily": daily_data,
            "weekly": weekly_data,
            "statistics": {"daily": daily_stats, "weekly": weekly_stats}
        }
        
    except Exception:
        return {
            "daily": [], 
            "weekly": [], 
            "statistics": {
                "daily": {"max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0},
                "weekly": {"max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0}
            }
        }

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

def is_authenticated():
    """Kullanıcının doğrulanıp doğrulanmadığını kontrol et"""
    if session.get('authenticated'):
        return True
    
    auth_token = request.cookies.get('auth_token')
    if auth_token:
        expected_token = hashlib.sha256(f"{SECRET_KEY}_authenticated".encode()).hexdigest()
        if auth_token == expected_token:
            session.permanent = True
            session['authenticated'] = True
            return True
    
    return False

def set_auth_cookie(response):
    """Doğrulama cookie'si ekle"""
    auth_token = hashlib.sha256(f"{SECRET_KEY}_authenticated".encode()).hexdigest()
    expires = datetime.now() + timedelta(days=365)
    response.set_cookie(
        'auth_token', 
        auth_token,
        expires=expires,
        httponly=True,
        secure=False,
        samesite='Lax'
    )
    return response

# HTML TEMPLATE
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1d3a 25%, #0f172a 50%, #1e293b 75%, #0f0f23 100%);
            min-height: 100vh; padding: 15px; color: #e2e8f0; overflow-x: hidden;
        }
        
        body::before {
            content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at 20% 80%, rgba(30, 58, 138, 0.2) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
                        radial-gradient(circle at 40% 40%, rgba(29, 78, 216, 0.1) 0%, transparent 50%);
            pointer-events: none; z-index: -1;
        }
        
        .container { max-width: 460px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
        
        .glass-card {
            background: rgba(15, 23, 42, 0.4);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        
        .header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 14px 18px;
        }
        
        .header-left { display: flex; align-items: center; gap: 10px; }
        .logo { font-size: 17px; font-weight: 800; color: #60a5fa; }
        .version { 
            font-size: 10px; color: rgba(96, 165, 250, 0.7); 
            background: rgba(59, 130, 246, 0.15); 
            padding: 2px 6px; border-radius: 6px; 
        }
        .update-time { font-size: 13px; color: #cbd5e1; }
        
        .actions { display: flex; gap: 8px; }
        .action-btn {
            width: 38px; height: 38px; border-radius: 10px;
            background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(96, 165, 250, 0.3);
            color: #60a5fa; font-size: 16px; cursor: pointer;
            transition: all 0.2s ease; display: flex; align-items: center; justify-content: center;
        }
        .action-btn:hover { 
            background: rgba(59, 130, 246, 0.3); 
            border-color: rgba(96, 165, 250, 0.5);
            transform: translateY(-1px);
        }
        
        .portfolio-summary {
            background: linear-gradient(135deg, rgba(29, 78, 216, 0.3) 0%, rgba(59, 130, 246, 0.2) 100%);
            border: 1px solid rgba(96, 165, 250, 0.3);
            border-radius: 18px; padding: 20px; color: white; text-align: center;
            backdrop-filter: blur(25px);
            box-shadow: 0 8px 32px rgba(29, 78, 216, 0.3);
        }
        
        .portfolio-amount { font-size: 36px; font-weight: 900; margin-bottom: 16px; color: #60a5fa; }
        
        .portfolio-metals { display: flex; gap: 8px; margin-top: 16px; }
        .metal-item {
            flex: 1; 
            background: rgba(15, 23, 42, 0.6); 
            border: 1px solid rgba(59, 130, 246, 0.25);
            border-radius: 14px; padding: 14px; min-height: 120px;
            backdrop-filter: blur(15px);
        }
        
        .metal-name { font-size: 15px; font-weight: 700; margin-bottom: 8px; color: #60a5fa; }
        .metal-price { font-size: 13px; color: #cbd5e1; margin-bottom: 6px; }
        .metal-value { font-size: 20px; font-weight: 800; color: #e2e8f0; }
        .metal-amount { font-size: 11px; color: #94a3b8; margin-top: 6px; }
        
        .statistics-section { padding: 16px; }
        .statistics-title {
            font-size: 16px; font-weight: 800; color: #fbbf24;
            margin-bottom: 12px; text-align: center;
        }
        
        .statistics-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
        .stat-item {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 10px; padding: 10px 6px; text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .stat-label { font-size: 9px; color: #94a3b8; margin-bottom: 4px; line-height: 1.1; }
        .stat-value { font-size: 13px; font-weight: 800; color: #fbbf24; margin-bottom: 2px; }
        .stat-date { font-size: 8px; color: #60a5fa; line-height: 1.1; }
        
        .peak-info {
            background: rgba(29, 78, 216, 0.15);
            border: 1px solid rgba(96, 165, 250, 0.25);
            border-radius: 8px; padding: 8px; margin-top: 10px;
            text-align: center; font-size: 10px; color: #60a5fa;
        }
        
        .price-history { padding: 14px; }
        .history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .history-title { font-size: 16px; font-weight: 800; color: #e2e8f0; }
        
        .period-tabs {
            display: flex; gap: 4px;
            background: rgba(15, 23, 42, 0.6); border-radius: 8px; padding: 3px;
        }
        .period-tab {
            padding: 6px 12px; border: none; border-radius: 5px;
            background: transparent; color: #94a3b8;
            font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.2s;
        }
        .period-tab.active { 
            background: rgba(59, 130, 246, 0.3); 
            color: #60a5fa; 
            border: 1px solid rgba(96, 165, 250, 0.4);
        }
        
        .price-table {
            overflow-x: auto; border-radius: 10px; 
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(59, 130, 246, 0.2);
            backdrop-filter: blur(15px);
        }
        
        .price-table table { width: 100%; border-collapse: collapse; }
        .price-table th {
            background: rgba(29, 78, 216, 0.2); padding: 10px 6px; text-align: left;
            font-weight: 700; color: #60a5fa; font-size: 12px;
            border-bottom: 1px solid rgba(59, 130, 246, 0.3);
        }
        .price-table td {
            padding: 10px 6px; border-bottom: 1px solid rgba(59, 130, 246, 0.1);
            font-size: 12px; color: #cbd5e1;
        }
        .price-table tr:hover { background: rgba(59, 130, 246, 0.05); }
        
        .price-table .time { font-weight: 700; color: #60a5fa; }
        .price-table .price { font-weight: 600; color: #e2e8f0; }
        .price-table .portfolio { font-weight: 800; color: #fbbf24; }
        .price-table .change { font-weight: 600; }
        .change.positive { color: #34d399; }
        .change.negative { color: #f87171; }
        .change.neutral { color: #94a3b8; }
        
        @media (max-width: 400px) {
            .container { padding: 0 5px; }
            .portfolio-metals { flex-direction: column; gap: 10px; }
            .history-header { flex-direction: column; gap: 8px; }
            .statistics-grid { grid-template-columns: 1fr; gap: 6px; }
            .stat-item { padding: 8px 6px; }
            .stat-label { font-size: 8px; }
            .stat-value { font-size: 12px; }
            .stat-date { font-size: 7px; }
            .peak-info { font-size: 9px; padding: 6px; }
            .price-table th, .price-table td { padding: 8px 4px; font-size: 11px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="glass-card header">
            <div class="header-left">
                <div>
                    <div class="logo">Metal Tracker</div>
                    <div class="version">v2.0</div>
                </div>
                <div class="update-time" id="headerTime">--:--</div>
            </div>
            <div class="actions">
                <button class="action-btn" onclick="fetchPrice()" id="refreshBtn">⟳</button>
                <button class="action-btn" onclick="logout()" title="Çıkış">🚪</button>
            </div>
        </div>
        
        <div class="glass-card portfolio-summary">
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="portfolio-metals">
                <div class="metal-item">
                    <div class="metal-name">Altın</div>
                    <div class="metal-price" id="goldCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="goldPortfolioValue">0,00 ₺</div>
                    <div class="metal-amount" id="goldAmount">0 gr</div>
                </div>
                <div class="metal-item">
                    <div class="metal-name">Gümüş</div>
                    <div class="metal-price" id="silverCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="silverPortfolioValue">0,00 ₺</div>
                    <div class="metal-amount" id="silverAmount">0 gr</div>
                </div>
            </div>
        </div>
        
        <div class="glass-card statistics-section">
            <div class="statistics-title">📊 Maksimum Değerler</div>
            <div class="statistics-grid">
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Altın Fiyatı</div>
                    <div class="stat-value" id="maxGoldPrice">0 ₺</div>
                    <div class="stat-date" id="maxGoldDate"></div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Gümüş Fiyatı</div>
                    <div class="stat-value" id="maxSilverPrice">0 ₺</div>
                    <div class="stat-date" id="maxSilverDate"></div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Portföy Tutarı</div>
                    <div class="stat-value" id="maxPortfolioValue">0 ₺</div>
                    <div class="stat-date" id="maxPortfolioDate"></div>
                </div>
            </div>
        </div>
        
        <div class="glass-card price-history">
            <div class="history-header">
                <div class="history-title">Fiyat Geçmişi</div>
                <div class="period-tabs">
                    <button class="period-tab active" onclick="switchPeriod('daily')" id="dailyTab">Günlük</button>
                    <button class="period-tab" onclick="switchPeriod('weekly')" id="weeklyTab">Aylık</button>
                </div>
            </div>
            <div class="price-table">
                <table>
                    <thead>
                        <tr>
                            <th id="timeHeader">Saat</th>
                            <th>Altın</th>
                            <th>Gümüş</th>
                            <th>Portföy</th>
                            <th>Değişim</th>
                        </tr>
                    </thead>
                    <tbody id="priceTableBody">
                        <!-- Dynamic content -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let currentGoldPrice = 0;
        let currentSilverPrice = 0;
        let tableData = {};
        let currentPeriod = 'daily';
        let portfolioConfig = {};

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                
                const [goldRes, silverRes, tableRes, configRes] = await Promise.all([
                    fetch('/api/gold-price'), fetch('/api/silver-price'),
                    fetch('/api/table-data'), fetch('/api/portfolio-config')
                ]);
                
                const goldData = await goldRes.json();
                const silverData = await silverRes.json();
                const tableDataRes = await tableRes.json();
                const configData = await configRes.json();
                
                if (goldData.success) {
                    let cleanPrice = goldData.price.replace(/[^\\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                    document.getElementById('goldCurrentPrice').textContent = goldData.price;
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                    document.getElementById('silverCurrentPrice').textContent = silverData.price;
                }
                
                if (configData.success) {
                    portfolioConfig = configData.config;
                    document.getElementById('goldAmount').textContent = portfolioConfig.gold_amount + ' gr';
                    document.getElementById('silverAmount').textContent = portfolioConfig.silver_amount + ' gr';
                }
                
                if (tableDataRes.success) {
                    tableData = tableDataRes.data;
                    updateTable();
                    updateStatistics();
                }
                
                document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                updatePortfolio();
                
            } catch (error) {
                console.error('Fetch error:', error);
            } finally {
                setTimeout(() => refreshBtn.style.transform = 'rotate(0deg)', 500);
            }
        }

        function updateStatistics() {
            if (tableData.statistics && tableData.statistics[currentPeriod]) {
                const stats = tableData.statistics[currentPeriod];
                
                // Fiyat değerlerini güncelle
                document.getElementById('maxGoldPrice').textContent = formatPrice(stats.max_gold_price);
                document.getElementById('maxSilverPrice').textContent = formatPrice(stats.max_silver_price);
                document.getElementById('maxPortfolioValue').textContent = formatCurrency(stats.max_portfolio_value);
                
                // Tarih bilgilerini güncelle
                document.getElementById('maxGoldDate').textContent = stats.max_gold_date || '';
                document.getElementById('maxSilverDate').textContent = stats.max_silver_date || '';
                document.getElementById('maxPortfolioDate').textContent = stats.max_portfolio_date || '';
                
                // Başlığı güncelle
                const periodText = currentPeriod === 'daily' ? 'Günlük' : 'Aylık';
                document.querySelector('.statistics-title').textContent = `📊 ${periodText} Maksimum Değerler`;
            }
        }

        function switchPeriod(period) {
            currentPeriod = period;
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            const timeHeader = document.getElementById('timeHeader');
            timeHeader.textContent = period === 'daily' ? 'Saat' : 'Tarih';
            
            updateTable();
            updateStatistics();
        }

        function updateTable() {
            const goldAmount = portfolioConfig.gold_amount || 0;
            const silverAmount = portfolioConfig.silver_amount || 0;
            
            if (!tableData[currentPeriod]) return;
            
            const tbody = document.getElementById('priceTableBody');
            tbody.innerHTML = '';
            
            tableData[currentPeriod].forEach((item) => {
                let portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                const row = document.createElement('tr');
                
                const timeDisplay = item.optimized ? 
                    `<span title="Günün peak değeri (${item.peak_time || 'bilinmiyor'})">${item.time}</span>` : 
                    item.time;
                
                row.innerHTML = `
                    <td class="time">${timeDisplay}</td>
                    <td class="price">${formatPrice(item.gold_price)}</td>
                    <td class="price">${formatPrice(item.silver_price)}</td>
                    <td class="portfolio">${portfolioValue > 0 ? formatCurrency(portfolioValue) : '-'}</td>
                    <td class="change ${getChangeClass(item.change_percent)}">${formatChange(item.change_percent)}</td>
                `;
                tbody.appendChild(row);
            });
        }

        function getChangeClass(changePercent) {
            if (changePercent > 0) return 'positive';
            if (changePercent < 0) return 'negative';
            return 'neutral';
        }

        function formatChange(changePercent) {
            if (changePercent === 0) return '0.00%';
            const sign = changePercent > 0 ? '+' : '';
            return `${sign}${changePercent.toFixed(2)}%`;
        }

        function updatePortfolio() {
            const goldAmount = portfolioConfig.gold_amount || 0;
            const silverAmount = portfolioConfig.silver_amount || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
            document.getElementById('goldPortfolioValue').textContent = formatCurrency(goldValue);
            document.getElementById('silverPortfolioValue').textContent = formatCurrency(silverValue);
        }

        function formatCurrency(amount) {
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount) + '₺';
        }

        function formatPrice(price) {
            if (!price) return '0,00₺';
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(price) + '₺';
        }

        function logout() {
            if (confirm('Oturumu kapatmak istediğinize emin misiniz?')) {
                fetch('/logout', {method: 'POST'}).then(() => {
                    window.location.href = '/login';
                });
            }
        }

        window.onload = function() {
            fetchPrice();
        };
    </script>
</body>
</html>'''

# LOGIN TEMPLATE
LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker - Giriş</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1d3a 25%, #0f172a 50%, #1e293b 75%, #0f0f23 100%);
            color: #e2e8f0; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;
        }
        
        body::before {
            content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at 20% 80%, rgba(30, 58, 138, 0.3) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(59, 130, 246, 0.2) 0%, transparent 50%);
            pointer-events: none; z-index: -1;
        }
        
        .login-container {
            background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(25px);
            border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 20px;
            padding: 35px 25px; width: 100%; max-width: 380px; text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        
        .logo {
            font-size: 22px; font-weight: 900; color: #60a5fa; margin-bottom: 6px;
            display: flex; align-items: center; justify-content: center; gap: 8px;
        }
        .logo-icon { font-size: 26px; }
        
        .subtitle { font-size: 13px; color: #94a3b8; margin-bottom: 28px; }
        
        .form-group { margin-bottom: 20px; text-align: left; }
        .form-label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 13px; color: #cbd5e1; }
        
        .form-input {
            width: 100%; padding: 14px; border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 10px; font-size: 15px; background: rgba(15, 23, 42, 0.6);
            color: #e2e8f0; transition: all 0.3s ease; backdrop-filter: blur(10px);
        }
        .form-input:focus {
            outline: none; border-color: #60a5fa; background: rgba(15, 23, 42, 0.8);
            box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
        }
        .form-input::placeholder { color: #64748b; }
        
        .login-btn {
            width: 100%; padding: 14px; background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
            border: none; border-radius: 10px; color: white; font-size: 15px; font-weight: 700;
            cursor: pointer; transition: all 0.3s ease; margin-bottom: 14px;
        }
        .login-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); }
        .login-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        
        .error-message {
            background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4);
            border-radius: 8px; padding: 10px; margin-bottom: 14px; color: #fca5a5;
            font-size: 13px; display: none;
        }
        .error-message.show { display: block; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <span class="logo-icon">📊</span>
            <span>Metal Tracker</span>
        </div>
        <div class="subtitle">Güvenli giriş yapın</div>
        
        <form onsubmit="handleLogin(event)">
            <div class="form-group">
                <label class="form-label">Şifre</label>
                <input type="password" class="form-input" id="password" placeholder="Şifrenizi girin" required>
            </div>
            
            <div class="error-message" id="errorMessage">Hatalı şifre! Lütfen tekrar deneyin.</div>
            
            <button type="submit" class="login-btn" id="loginBtn">Giriş Yap</button>
        </form>
    </div>

    <script>
        async function handleLogin(event) {
            event.preventDefault();
            
            const password = document.getElementById('password').value;
            const errorMessage = document.getElementById('errorMessage');
            const loginBtn = document.getElementById('loginBtn');
            
            errorMessage.classList.remove('show');
            loginBtn.disabled = true;
            loginBtn.textContent = 'Giriş yapılıyor...';
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ password: password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.href = '/';
                } else {
                    errorMessage.classList.add('show');
                    document.getElementById('password').value = '';
                    document.getElementById('password').focus();
                }
            } catch (error) {
                errorMessage.textContent = 'Bağlantı hatası! Lütfen tekrar deneyin.';
                errorMessage.classList.add('show');
            } finally {
                loginBtn.disabled = false;
                loginBtn.textContent = 'Giriş Yap';
            }
        }
        
        window.onload = function() {
            document.getElementById('password').focus();
        };
    </script>
</body>
</html>'''

# FLASK ROUTES
@app.route('/')
def index():
    if not is_authenticated():
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE)

@app.route('/login')
def login():
    if is_authenticated():
        return redirect(url_for('index'))
    return LOGIN_TEMPLATE

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if verify_password(password):
            session.permanent = True
            session['authenticated'] = True
            
            response = make_response(jsonify({'success': True}))
            response = set_auth_cookie(response)
            
            return response
        else:
            return jsonify({'success': False, 'error': 'Invalid password'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    response = make_response(jsonify({'success': True}))
    response.set_cookie('auth_token', '', expires=0)
    return response

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

@app.route('/api/portfolio-config')
def api_portfolio_config():
    try:
        config = load_portfolio_config()
        config.pop('password_hash', None)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.permanent_session_lifetime = timedelta(days=365)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)