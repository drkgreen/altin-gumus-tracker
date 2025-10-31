#!/usr/bin/env python3
"""
Metal Price Tracker Web App v3.0
Neon Cyberpunk Dashboard Theme
BÖLÜM 1: Backend Fonksiyonlar ve Veri İşleme
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
                "time": f"{day_data['time']} ⚡",
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
    """Maksimum değerleri hesapla"""
    try:
        config = load_portfolio_config()
        
        if data_type == 'daily':
            data = get_daily_data()
        elif data_type == 'weekly':
            data = get_weekly_optimized_data()
        else:
            daily_data = get_daily_data()
            weekly_data = get_weekly_optimized_data()
            data = daily_data + weekly_data
        
        if not data:
            return {"max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0}
        
        max_gold = max(item["gold_price"] for item in data)
        max_silver = max(item["silver_price"] for item in data)
        
        gold_amount = config.get("gold_amount", 0)
        silver_amount = config.get("silver_amount", 0)
        
        max_portfolio = 0
        if gold_amount > 0 or silver_amount > 0:
            portfolio_values = [
                (gold_amount * item["gold_price"]) + (silver_amount * item["silver_price"])
                for item in data
            ]
            max_portfolio = max(portfolio_values) if portfolio_values else 0
        
        return {
            "max_gold_price": max_gold,
            "max_silver_price": max_silver,
            "max_portfolio_value": max_portfolio
        }
        
    except Exception:
        return {"max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0}

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
# BÖLÜM 2: HTML TEMPLATES VE CSS - NEON CYBERPUNK THEME

# NEON CYBERPUNK ANA SAYFA TEMPLATE
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Metal Tracker v3.0</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Orbitron', monospace;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
            position: relative;
        }
        
        /* Animated background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 25% 25%, #ff00ff20 0%, transparent 50%),
                radial-gradient(circle at 75% 75%, #00ffff20 0%, transparent 50%),
                linear-gradient(45deg, #1a0033 0%, #000 50%, #003333 100%);
            z-index: -1;
            animation: backgroundShift 10s ease-in-out infinite alternate;
        }
        
        @keyframes backgroundShift {
            0% { transform: translateX(-10px) translateY(-10px); }
            100% { transform: translateX(10px) translateY(10px); }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto auto auto;
            gap: 20px;
        }
        
        .neon-card {
            background: rgba(10, 10, 20, 0.8);
            border: 2px solid #00ffff;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 
                0 0 20px rgba(0, 255, 255, 0.3),
                inset 0 0 20px rgba(0, 255, 255, 0.05);
            position: relative;
            transition: all 0.3s ease;
        }
        
        .neon-card:hover {
            box-shadow: 
                0 0 30px rgba(0, 255, 255, 0.5),
                inset 0 0 30px rgba(0, 255, 255, 0.1);
            transform: translateY(-2px);
        }
        
        .neon-card::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(45deg, #00ffff, #ff00ff, #ffff00, #00ffff);
            border-radius: 15px;
            z-index: -1;
            animation: borderGlow 3s linear infinite;
        }
        
        @keyframes borderGlow {
            0% { background-position: 0% 50%; }
            100% { background-position: 100% 50%; }
        }
        
        /* Header full width */
        .header-card {
            grid-column: 1 / -1;
            background: rgba(20, 20, 40, 0.9);
            border: 2px solid #ff00ff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 25px;
        }
        
        .header-card::before {
            background: linear-gradient(45deg, #ff00ff, #00ffff, #ff00ff);
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo {
            font-size: 24px;
            font-weight: 900;
            color: #ff00ff;
            text-shadow: 0 0 10px #ff00ff;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00ff00;
            box-shadow: 0 0 10px #00ff00;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .update-time {
            font-size: 14px;
            color: #00ffff;
            text-shadow: 0 0 5px #00ffff;
        }
        
        .header-actions {
            display: flex;
            gap: 10px;
        }
        
        .cyber-btn {
            padding: 8px 16px;
            background: linear-gradient(45deg, #ff00ff, #00ffff);
            border: none;
            border-radius: 8px;
            color: #000;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            font-size: 12px;
        }
        
        .cyber-btn:hover {
            box-shadow: 0 0 15px rgba(255, 0, 255, 0.7);
            transform: scale(1.05);
        }
        
        /* Portfolio Summary */
        .portfolio-card {
            background: rgba(20, 0, 40, 0.8);
            border: 2px solid #ffff00;
            text-align: center;
        }
        
        .portfolio-card::before {
            background: linear-gradient(45deg, #ffff00, #ff00ff, #ffff00);
        }
        
        .portfolio-title {
            font-size: 18px;
            color: #ffff00;
            margin-bottom: 10px;
            text-shadow: 0 0 10px #ffff00;
        }
        
        .portfolio-amount {
            font-size: 32px;
            font-weight: 900;
            color: #00ff00;
            text-shadow: 0 0 15px #00ff00;
            margin-bottom: 20px;
        }
        
        .metal-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .metal-info {
            background: rgba(0, 20, 20, 0.6);
            border: 1px solid #00ffff;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        
        .metal-name {
            font-size: 14px;
            color: #00ffff;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        
        .metal-price {
            font-size: 12px;
            color: #ffffff;
            margin-bottom: 5px;
        }
        
        .metal-value {
            font-size: 18px;
            font-weight: 700;
            color: #ffff00;
            text-shadow: 0 0 8px #ffff00;
        }
        
        .metal-amount {
            font-size: 10px;
            color: #888;
            margin-top: 5px;
        }
        
        /* Statistics Card */
        .stats-card {
            background: rgba(0, 20, 0, 0.8);
            border: 2px solid #00ff00;
        }
        
        .stats-card::before {
            background: linear-gradient(45deg, #00ff00, #ffff00, #00ff00);
        }
        
        .stats-title {
            font-size: 16px;
            color: #00ff00;
            margin-bottom: 15px;
            text-align: center;
            text-shadow: 0 0 10px #00ff00;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 10px;
        }
        
        .stat-item {
            background: rgba(0, 40, 0, 0.6);
            border: 1px solid #00ff00;
            border-radius: 8px;
            padding: 10px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 10px;
            color: #88ff88;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        
        .stat-value {
            font-size: 14px;
            font-weight: 700;
            color: #00ff00;
            text-shadow: 0 0 8px #00ff00;
        }
        
        /* Data Table Card - Full width */
        .data-card {
            grid-column: 1 / -1;
            background: rgba(40, 0, 40, 0.8);
            border: 2px solid #ff00ff;
        }
        
        .data-card::before {
            background: linear-gradient(45deg, #ff00ff, #ffff00, #ff00ff);
        }
        
        .data-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .data-title {
            font-size: 18px;
            color: #ff00ff;
            text-shadow: 0 0 10px #ff00ff;
        }
        
        .tab-buttons {
            display: flex;
            gap: 5px;
        }
        
        .tab-btn {
            padding: 8px 15px;
            background: rgba(40, 0, 40, 0.8);
            border: 1px solid #ff00ff;
            border-radius: 5px;
            color: #ff00ff;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .tab-btn.active {
            background: #ff00ff;
            color: #000;
            box-shadow: 0 0 15px #ff00ff;
        }
        
        .data-table {
            background: rgba(0, 0, 20, 0.8);
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #00ffff;
        }
        
        .data-table table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .data-table th {
            background: rgba(0, 40, 40, 0.8);
            color: #00ffff;
            padding: 12px 8px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 1px solid #00ffff;
        }
        
        .data-table td {
            padding: 10px 8px;
            border-bottom: 1px solid rgba(0, 255, 255, 0.2);
            font-size: 11px;
        }
        
        .data-table tr:hover {
            background: rgba(0, 255, 255, 0.1);
        }
        
        .data-table .time { color: #ffff00; font-weight: 700; }
        .data-table .price { color: #00ffff; }
        .data-table .portfolio { color: #00ff00; font-weight: 700; }
        .data-table .change { font-weight: 700; }
        .change.positive { color: #00ff00; }
        .change.negative { color: #ff0000; }
        .change.neutral { color: #888; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
                gap: 15px;
                padding: 0 10px;
            }
            
            .metal-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr; }
            .data-header { flex-direction: column; gap: 10px; }
            .portfolio-amount { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="neon-card header-card">
            <div class="header-left">
                <div class="logo">⚡ METAL TRACKER v3.0</div>
                <div class="status-indicator"></div>
                <div class="update-time" id="updateTime">SYSTEM ONLINE</div>
            </div>
            <div class="header-actions">
                <button class="cyber-btn" onclick="fetchData()" id="refreshBtn">SYNC</button>
                <button class="cyber-btn" onclick="logout()">EXIT</button>
            </div>
        </div>
        
        <!-- Portfolio Summary -->
        <div class="neon-card portfolio-card">
            <div class="portfolio-title">PORTFOLIO VALUE</div>
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="metal-grid">
                <div class="metal-info">
                    <div class="metal-name">GOLD</div>
                    <div class="metal-price" id="goldPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="goldValue">0,00 ₺</div>
                    <div class="metal-amount" id="goldAmount">0 gr</div>
                </div>
                <div class="metal-info">
                    <div class="metal-name">SILVER</div>
                    <div class="metal-price" id="silverPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="silverValue">0,00 ₺</div>
                    <div class="metal-amount" id="silverAmount">0 gr</div>
                </div>
            </div>
        </div>
        
        <!-- Statistics -->
        <div class="neon-card stats-card">
            <div class="stats-title">⚡ MAX VALUES</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">MAX GOLD</div>
                    <div class="stat-value" id="maxGold">0 ₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">MAX SILVER</div>
                    <div class="stat-value" id="maxSilver">0 ₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">MAX PORTFOLIO</div>
                    <div class="stat-value" id="maxPortfolio">0 ₺</div>
                </div>
            </div>
        </div>
        
        <!-- Data Table -->
        <div class="neon-card data-card">
            <div class="data-header">
                <div class="data-title">⚡ PRICE DATA STREAM</div>
                <div class="tab-buttons">
                    <button class="tab-btn active" onclick="switchTab('daily')" id="dailyTab">DAILY</button>
                    <button class="tab-btn" onclick="switchTab('weekly')" id="weeklyTab">MONTHLY</button>
                </div>
            </div>
            <div class="data-table">
                <table>
                    <thead>
                        <tr>
                            <th id="timeHeader">TIME</th>
                            <th>GOLD</th>
                            <th>SILVER</th>
                            <th>PORTFOLIO</th>
                            <th>CHANGE</th>
                        </tr>
                    </thead>
                    <tbody id="dataTableBody">
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

        async function fetchData() {
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                refreshBtn.textContent = 'SYNCING...';
                refreshBtn.style.transform = 'scale(0.9)';
                
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
                    document.getElementById('goldPrice').textContent = goldData.price;
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                    document.getElementById('silverPrice').textContent = silverData.price;
                }
                
                if (configData.success) {
                    portfolioConfig = configData.config;
# BÖLÜM 3: FLASK ROUTES VE ANA PROGRAM

# FLASK ROUTES
@app.route('/')
def index():
    """Ana sayfa - authentication kontrolü ile"""
    if not is_authenticated():
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE)

@app.route('/login')
def login():
    """Login sayfası - zaten giriş yapılmışsa ana sayfaya yönlendir"""
    if is_authenticated():
        return redirect(url_for('index'))
    return LOGIN_TEMPLATE

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login API endpoint - şifre doğrulama ve session oluşturma"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if verify_password(password):
            # Kalıcı session oluştur
            session.permanent = True
            session['authenticated'] = True
            
            # Response oluştur ve auth cookie ekle
            response = make_response(jsonify({'success': True}))
            response = set_auth_cookie(response)
            
            return response
        else:
            return jsonify({'success': False, 'error': 'Invalid password'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logout', methods=['POST'])
def logout():
    """Logout API endpoint - session ve cookie temizleme"""
    session.clear()
    response = make_response(jsonify({'success': True}))
    # Auth cookie'sini sil
    response.set_cookie('auth_token', '', expires=0)
    return response

@app.route('/api/gold-price')
def api_gold_price():
    """Altın fiyatı API endpoint"""
    try:
        price = get_gold_price()
        return jsonify({'success': bool(price), 'price': price or ''})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/silver-price')
def api_silver_price():
    """Gümüş fiyatı API endpoint"""
    try:
        price = get_silver_price()
        return jsonify({'success': bool(price), 'price': price or ''})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/table-data')
def api_table_data():
    """Tablo verisi API endpoint"""
    try:
        data = get_table_data()
        return jsonify({'success': bool(data), 'data': data or {}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/portfolio-config')
def api_portfolio_config():
    """Portföy konfigürasyonu API endpoint"""
    try:
        config = load_portfolio_config()
        # Güvenlik: şifreyi döndürme
        config.pop('password_hash', None)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ANA PROGRAM
if __name__ == '__main__':
    """Ana program - Flask uygulamasını başlat"""
    
    # Session kalıcılığı için önemli ayarlar
    app.permanent_session_lifetime = timedelta(days=365)
    
    # Port ayarı (Heroku uyumlu)
    port = int(os.environ.get('PORT', 5000))
    
    # Uygulamayı başlat
    print("🚀 Metal Tracker v3.0 - Cyberpunk Edition Starting...")
    print(f"⚡ Server running on port: {port}")
    print("🔒 Secure session system: ACTIVE")
    print("🌐 Ready for connections...")
    
    app.run(
        host='0.0.0.0',    # Tüm network interface'lerde dinle
        port=port,         # Port numarası
        debug=False        # Production için debug=False
    )