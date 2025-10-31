#!/usr/bin/env python3
"""
Metal Price Tracker Web App v3.1
Soft Dark Theme - Göz Dostu ve Konforlu Tasarım
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

SECRET_KEY = os.environ.get('SECRET_KEY', 'metal_tracker_secret_key_2024_permanent')
app.secret_key = SECRET_KEY

def load_portfolio_config():
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/portfolio-config.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}
    except Exception:
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}

def verify_password(password):
    config = load_portfolio_config()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == config.get("password_hash", "")

def load_price_history():
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/data/price-history.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"records": []}
    except Exception:
        return {"records": []}

def get_daily_data():
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
                "time": f"{day_data['time']} 📈",
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

# SOFT DARK THEME - GÖZ DOSTU
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker v3.1</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d3f 100%);
            color: #e4e4e7;
            min-height: 100vh;
            padding: 20px;
            line-height: 1.5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto auto auto;
            gap: 20px;
        }
        
        .card {
            background: rgba(45, 45, 63, 0.8);
            border: 1px solid rgba(156, 163, 175, 0.2);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(8px);
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .card:hover {
            border-color: rgba(156, 163, 175, 0.3);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }
        
        /* Header */
        .header {
            grid-column: 1 / -1;
            background: rgba(55, 65, 81, 0.9);
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 24px;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .logo {
            font-size: 24px;
            font-weight: 700;
            color: #f9fafb;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #9ca3af;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .header-actions {
            display: flex;
            gap: 12px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
        }
        
        .btn-primary {
            background: #3b82f6;
            color: white;
        }
        
        .btn-primary:hover {
            background: #2563eb;
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: rgba(107, 114, 128, 0.3);
            color: #e5e7eb;
            border: 1px solid rgba(156, 163, 175, 0.3);
        }
        
        .btn-secondary:hover {
            background: rgba(107, 114, 128, 0.5);
        }
        
        /* Portfolio Card */
        .portfolio {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
            border: 1px solid rgba(59, 130, 246, 0.2);
            text-align: center;
        }
        
        .portfolio-title {
            font-size: 16px;
            color: #9ca3af;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .portfolio-amount {
            font-size: 36px;
            font-weight: 800;
            color: #f9fafb;
            margin-bottom: 24px;
        }
        
        .metals-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        
        .metal {
            background: rgba(75, 85, 99, 0.3);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        
        .metal-name {
            font-size: 14px;
            color: #9ca3af;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        
        .metal-price {
            font-size: 13px;
            color: #d1d5db;
            margin-bottom: 8px;
        }
        
        .metal-value {
            font-size: 20px;
            font-weight: 700;
            color: #f9fafb;
        }
        
        .metal-amount {
            font-size: 12px;
            color: #6b7280;
            margin-top: 6px;
        }
        
        /* Stats Card */
        .stats {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }
        
        .stats-title {
            font-size: 16px;
            color: #9ca3af;
            margin-bottom: 20px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
        }
        
        .stat {
            background: rgba(75, 85, 99, 0.3);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 12px;
            color: #9ca3af;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        
        .stat-value {
            font-size: 16px;
            font-weight: 700;
            color: #10b981;
        }
        
        /* Data Table */
        .data {
            grid-column: 1 / -1;
            background: rgba(55, 65, 81, 0.6);
        }
        
        .data-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .data-title {
            font-size: 18px;
            color: #f9fafb;
            font-weight: 600;
        }
        
        .tabs {
            display: flex;
            gap: 8px;
            background: rgba(75, 85, 99, 0.3);
            border-radius: 8px;
            padding: 4px;
        }
        
        .tab {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            background: transparent;
            color: #9ca3af;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
        }
        
        .tab.active {
            background: #3b82f6;
            color: white;
        }
        
        .table-wrapper {
            background: rgba(75, 85, 99, 0.2);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(156, 163, 175, 0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background: rgba(75, 85, 99, 0.4);
            color: #d1d5db;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            border-bottom: 1px solid rgba(156, 163, 175, 0.2);
        }
        
        td {
            padding: 12px 16px;
            border-bottom: 1px solid rgba(156, 163, 175, 0.1);
            font-size: 14px;
        }
        
        tr:hover {
            background: rgba(75, 85, 99, 0.2);
        }
        
        .time { color: #60a5fa; font-weight: 600; }
        .price { color: #e5e7eb; }
        .portfolio { color: #10b981; font-weight: 600; }
        .change { font-weight: 600; }
        .change.positive { color: #10b981; }
        .change.negative { color: #ef4444; }
        .change.neutral { color: #9ca3af; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
                gap: 16px;
                padding: 0 12px;
            }
            
            .metals-grid { grid-template-columns: 1fr; }
            .data-header { flex-direction: column; gap: 12px; }
            .portfolio-amount { font-size: 28px; }
            th, td { padding: 10px 12px; font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="card header">
            <div class="header-left">
                <div class="logo">📊 Metal Tracker</div>
                <div class="status">
                    <div class="status-dot"></div>
                    <span id="statusText">Online</span>
                </div>
            </div>
            <div class="header-actions">
                <button class="btn btn-primary" onclick="fetchData()" id="refreshBtn">Güncelle</button>
                <button class="btn btn-secondary" onclick="logout()">Çıkış</button>
            </div>
        </div>
        
        <!-- Portfolio -->
        <div class="card portfolio">
            <div class="portfolio-title">Portföy Değeri</div>
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="metals-grid">
                <div class="metal">
                    <div class="metal-name">Altın</div>
                    <div class="metal-price" id="goldPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="goldValue">0,00 ₺</div>
                    <div class="metal-amount" id="goldAmount">0 gr</div>
                </div>
                <div class="metal">
                    <div class="metal-name">Gümüş</div>
                    <div class="metal-price" id="silverPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="silverValue">0,00 ₺</div>
                    <div class="metal-amount" id="silverAmount">0 gr</div>
                </div>
            </div>
        </div>
        
        <!-- Statistics -->
        <div class="card stats">
            <div class="stats-title">Maksimum Değerler</div>
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-label">En Yüksek Altın</div>
                    <div class="stat-value" id="maxGold">0 ₺</div>
                </div>
                <div class="stat">
                    <div class="stat-label">En Yüksek Gümüş</div>
                    <div class="stat-value" id="maxSilver">0 ₺</div>
                </div>
                <div class="stat">
                    <div class="stat-label">En Yüksek Portföy</div>
                    <div class="stat-value" id="maxPortfolio">0 ₺</div>
                </div>
            </div>
        </div>
        
        <!-- Data Table -->
        <div class="card data">
            <div class="data-header">
                <div class="data-title">Fiyat Verileri</div>
                <div class="tabs">
                    <button class="tab active" onclick="switchTab('daily')" id="dailyTab">Günlük</button>
                    <button class="tab" onclick="switchTab('weekly')" id="weeklyTab">Aylık</button>
                </div>
            </div>
            <div class="table-wrapper">
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
                    <tbody id="dataTableBody">
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
            const statusText = document.getElementById('statusText');
            
            try {
                refreshBtn.textContent = 'Güncelleniyor...';
                refreshBtn.disabled = true;
                statusText.textContent = 'Güncelleniyor...';
                
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
                    document.getElementById('goldAmount').textContent = portfolioConfig.gold_amount + ' gr';
                    document.getElementById('silverAmount').textContent = portfolioConfig.silver_amount + ' gr';
                }
                
                if (tableDataRes.success) {
                    tableData = tableDataRes.data;
                    updateTable();
                    updateStatistics();
                }
                
                updatePortfolio();
                statusText.textContent = 'Son güncelleme: ' + new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                
            } catch (error) {
                console.error('Güncelleme hatası:', error);
                statusText.textContent = 'Hata';
            } finally {
                refreshBtn.textContent = 'Güncelle';
                refreshBtn.disabled = false;
            }
        }

        function updateStatistics() {
            if (tableData.statistics && tableData.statistics[currentPeriod]) {
                const stats = tableData.statistics[currentPeriod];
                document.getElementById('maxGold').textContent = formatPrice(stats.max_gold_price);
                document.getElementById('maxSilver').textContent = formatPrice(stats.max_silver_price);
                document.getElementById('maxPortfolio').textContent = formatCurrency(stats.max_portfolio_value);
            }
        }

        function switchTab(period) {
            currentPeriod = period;
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
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
            
            const tbody = document.getElementById('dataTableBody');
            tbody.innerHTML = '';
            
            tableData[currentPeriod].forEach((item) => {
                let portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                const row = document.createElement('tr');
                
                const timeDisplay = item.optimized ? 
                    `<span title="Peak değer (${item.peak_time || 'bilinmiyor'})">${item.time}</span>` : 
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
            document.getElementById('goldValue').textContent = formatCurrency(goldValue);
            document.getElementById('silverValue').textContent = formatCurrency(silverValue);
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
            if (confirm('Çıkış yapmak istediğinize emin misiniz?')) {
                fetch('/logout', {method: 'POST'}).then(() => {
                    window.location.href = '/login';
                });
            }
        }

        // Otomatik güncelleme (5 dakikada bir)
        setInterval(fetchData, 300000);
        window.onload = function() { fetchData(); };
    </script>
</body>
</html>'''

# SOFT LOGIN TEMPLATE
LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker - Giriş</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d3f 100%);
            color: #e4e4e7;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-container {
            background: rgba(45, 45, 63, 0.9);
            border: 1px solid rgba(156, 163, 175, 0.3);
            border-radius: 20px;
            padding: 40px 32px;
            width: 100%;
            max-width: 400px;
            text-align: center;
            backdrop-filter: blur(10px);
            box-shadow: 0 20px 25px rgba(0, 0, 0, 0.2);
        }
        
        .header {
            margin-bottom: 32px;
        }
        
        .logo {
            font-size: 32px;
            font-weight: 700;
            color: #f9fafb;
            margin-bottom: 8px;
        }
        
        .subtitle {
            font-size: 16px;
            color: #9ca3af;
        }
        
        .form-group {
            margin-bottom: 24px;
            text-align: left;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            font-size: 14px;
            color: #d1d5db;
        }
        
        .form-input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid rgba(156, 163, 175, 0.3);
            border-radius: 8px;
            font-size: 16px;
            background: rgba(75, 85, 99, 0.3);
            color: #f9fafb;
            transition: all 0.2s ease;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            background: rgba(75, 85, 99, 0.5);
        }
        
        .form-input::placeholder {
            color: #6b7280;
        }
        
        .login-btn {
            width: 100%;
            padding: 12px 24px;
            background: #3b82f6;
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 16px;
        }
        
        .login-btn:hover {
            background: #2563eb;
            transform: translateY(-1px);
        }
        
        .login-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .error-message {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
            color: #fca5a5;
            font-size: 14px;
            display: none;
        }
        
        .error-message.show {
            display: block;
        }
        
        .info {
            font-size: 12px;
            color: #6b7280;
            margin-top: 16px;
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="header">
            <div class="logo">📊 Metal Tracker</div>
            <div class="subtitle">Güvenli giriş yapın</div>
        </div>
        
        <form onsubmit="handleLogin(event)">
            <div class="form-group">
                <label class="form-label">Şifre</label>
                <input type="password" class="form-input" id="password" placeholder="Şifrenizi girin" required>
            </div>
            
            <div class="error-message" id="errorMessage">
                Hatalı şifre! Lütfen tekrar deneyin.
            </div>
            
            <button type="submit" class="login-btn" id="loginBtn">
                Giriş Yap
            </button>
        </form>
        
        <div class="info">
            Metal Tracker v3.1 - Göz Dostu Tasarım<br>
            Giriş bilgileriniz güvenli şekilde saklanır.
        </div>
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
                    loginBtn.textContent = 'Başarılı!';
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 500);
                } else {
                    errorMessage.classList.add('show');
                    document.getElementById('password').value = '';
                    document.getElementById('password').focus();
                }
            } catch (error) {
                errorMessage.textContent = 'Bağlantı hatası! Lütfen tekrar deneyin.';
                errorMessage.classList.add('show');
            } finally {
                setTimeout(() => {
                    loginBtn.disabled = false;
                    loginBtn.textContent = 'Giriş Yap';
                }, 500);
            }
        }
        
        window.onload = function() {
            document.getElementById('password').focus();
        };
    </script>
</body>
</html>'''

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