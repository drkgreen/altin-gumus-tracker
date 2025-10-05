#!/usr/bin/env python3
"""
Metal Price Tracker Web App v2.0 - Modern Mobile Design
"""
from flask import Flask, jsonify, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
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
    """Son 7 günün optimize edilmiş verilerini getir"""
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
        
        for i in range(6, -1, -1):
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
                "time": day_data['time'],
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

def get_table_data():
    """Günlük ve haftalık veriler"""
    try:
        daily_data = get_daily_data()
        weekly_data = get_weekly_optimized_data()
        
        return {
            "daily": daily_data,
            "weekly": weekly_data
        }
        
    except Exception:
        return {"daily": [], "weekly": []}

def get_gold_price():
    """Yapı Kredi altın fiyatı"""
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
    """Vakıfbank gümüş fiyatı"""
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

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0f172a">
    <title>Metal Tracker 📱</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
            min-height: 100vh;
            padding-bottom: 80px;
            color: #fff;
            overflow-x: hidden;
        }
        
        /* Sticky Header */
        .header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 16px 20px;
        }
        
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .logo-text {
            font-size: 20px;
            font-weight: 800;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .refresh-btn {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            border: none;
            font-size: 24px;
            cursor: pointer;
            transition: transform 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(251, 191, 36, 0.3);
        }
        
        .refresh-btn:active {
            transform: scale(0.95);
        }
        
        .refresh-btn.spinning {
            animation: spin 1s ease-in-out;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .update-time {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.6);
            text-align: center;
        }
        
        /* Main Content */
        .container {
            padding: 0 16px;
            max-width: 500px;
            margin: 0 auto;
        }
        
        /* Price Cards */
        .price-cards {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 20px 0;
        }
        
        .price-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px 16px;
            position: relative;
            overflow: hidden;
        }
        
        .price-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #fbbf24, #f59e0b);
        }
        
        .price-card.silver::before {
            background: linear-gradient(90deg, #94a3b8, #64748b);
        }
        
        .price-label {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 8px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .price-value {
            font-size: 28px;
            font-weight: 900;
            margin-bottom: 4px;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .silver .price-value {
            background: linear-gradient(135deg, #cbd5e1, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .price-unit {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.5);
        }
        
        /* Portfolio Card */
        .portfolio-card {
            background: linear-gradient(135deg, #7c3aed, #a855f7);
            border-radius: 24px;
            padding: 24px 20px;
            margin: 20px 0;
            box-shadow: 0 20px 40px rgba(124, 58, 237, 0.4);
            display: none;
        }
        
        .portfolio-card.active {
            display: block;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .portfolio-total {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .portfolio-label {
            font-size: 13px;
            opacity: 0.9;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .portfolio-amount {
            font-size: 42px;
            font-weight: 900;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .portfolio-metals {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        .portfolio-metal {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 16px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .portfolio-metal-name {
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .portfolio-metal-value {
            font-size: 22px;
            font-weight: 800;
        }
        
        /* Period Tabs */
        .period-tabs {
            display: flex;
            gap: 8px;
            margin: 20px 0;
            background: rgba(255, 255, 255, 0.05);
            padding: 6px;
            border-radius: 16px;
            backdrop-filter: blur(10px);
        }
        
        .period-tab {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 12px;
            background: transparent;
            color: rgba(255, 255, 255, 0.6);
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .period-tab.active {
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            color: #0f172a;
            box-shadow: 0 4px 12px rgba(251, 191, 36, 0.3);
        }
        
        /* History List */
        .history-list {
            display: none;
        }
        
        .history-list.active {
            display: block;
        }
        
        .history-item {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            display: grid;
            grid-template-columns: auto 1fr auto;
            gap: 16px;
            align-items: center;
        }
        
        .history-item.peak {
            background: rgba(251, 191, 36, 0.1);
            border-color: rgba(251, 191, 36, 0.3);
        }
        
        .history-time {
            font-size: 16px;
            font-weight: 700;
            color: #fbbf24;
        }
        
        .history-prices {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        
        .history-price {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .history-price strong {
            color: #fff;
            font-weight: 700;
        }
        
        .history-change {
            font-size: 16px;
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 8px;
        }
        
        .history-change.positive {
            color: #10b981;
            background: rgba(16, 185, 129, 0.1);
        }
        
        .history-change.negative {
            color: #ef4444;
            background: rgba(239, 68, 68, 0.1);
        }
        
        .history-change.neutral {
            color: rgba(255, 255, 255, 0.5);
        }
        
        /* Bottom Navigation */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 20px;
            padding-bottom: calc(12px + env(safe-area-inset-bottom));
            display: flex;
            justify-content: space-around;
            z-index: 100;
        }
        
        .nav-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 12px;
            background: transparent;
            color: rgba(255, 255, 255, 0.6);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
        }
        
        .nav-btn.active {
            background: rgba(251, 191, 36, 0.1);
            color: #fbbf24;
        }
        
        .nav-icon {
            font-size: 20px;
        }
        
        /* Modal */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(12px);
            z-index: 200;
            display: none;
            align-items: flex-end;
            padding: 0;
        }
        
        .modal.active {
            display: flex;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .modal-content {
            background: #1e293b;
            border-radius: 24px 24px 0 0;
            padding: 24px 20px;
            padding-bottom: calc(24px + env(safe-area-inset-bottom));
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
            animation: slideUp 0.3s ease;
        }
        
        @keyframes slideUp {
            from {
                transform: translateY(100%);
            }
            to {
                transform: translateY(0);
            }
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        
        .modal-title {
            font-size: 22px;
            font-weight: 800;
        }
        
        .modal-close {
            width: 36px;
            height: 36px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            font-size: 24px;
            color: #fff;
            cursor: pointer;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        .input-label {
            display: block;
            margin-bottom: 10px;
            font-weight: 700;
            font-size: 15px;
        }
        
        .input-field {
            width: 100%;
            padding: 16px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 14px;
            font-size: 18px;
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            font-weight: 600;
        }
        
        .input-field:focus {
            outline: none;
            border-color: #fbbf24;
            background: rgba(255, 255, 255, 0.08);
        }
        
        .modal-actions {
            display: flex;
            gap: 12px;
        }
        
        .btn {
            flex: 1;
            padding: 16px;
            border-radius: 14px;
            font-weight: 700;
            font-size: 16px;
            cursor: pointer;
            border: none;
            transition: transform 0.2s ease;
        }
        
        .btn:active {
            transform: scale(0.98);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            color: #0f172a;
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
        }
        
        /* Loading */
        .loading {
            text-align: center;
            padding: 40px 20px;
            color: rgba(255, 255, 255, 0.6);
        }
        
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(251, 191, 36, 0.2);
            border-top-color: #fbbf24;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
        }
        
        .empty-icon {
            font-size: 64px;
            margin-bottom: 16px;
            opacity: 0.3;
        }
        
        .empty-text {
            color: rgba(255, 255, 255, 0.6);
            font-size: 15px;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="header-top">
            <div class="logo">
                <span class="logo-text">📊 Metal Tracker</span>
            </div>
            <button class="refresh-btn" onclick="fetchPrices()" id="refreshBtn">⟳</button>
        </div>
        <div class="update-time" id="updateTime">Yükleniyor...</div>
    </div>

    <!-- Main Content -->
    <div class="container">
        <!-- Price Cards -->
        <div class="price-cards">
            <div class="price-card gold">
                <div class="price-label">Altın</div>
                <div class="price-value" id="goldPrice">-</div>
                <div class="price-unit">₺/gr</div>
            </div>
            <div class="price-card silver">
                <div class="price-label">Gümüş</div>
                <div class="price-value" id="silverPrice">-</div>
                <div class="price-unit">₺/gr</div>
            </div>
        </div>

        <!-- Portfolio Card -->
        <div class="portfolio-card" id="portfolioCard">
            <div class="portfolio-total">
                <div class="portfolio-label">Toplam Portföy</div>
                <div class="portfolio-amount" id="portfolioAmount">0,00 ₺</div>
            </div>
            <div class="portfolio-metals">
                <div class="portfolio-metal">
                    <div class="portfolio-metal-name">Altın</div>
                    <div class="portfolio-metal-value" id="goldValue">0 ₺</div>
                </div>
                <div class="portfolio-metal">
                    <div class="portfolio-metal-name">Gümüş</div>
                    <div class="portfolio-metal-value" id="silverValue">0 ₺</div>
                </div>
            </div>
        </div>

        <!-- Period Tabs -->
        <div class="period-tabs">
            <button class="period-tab active" onclick="switchPeriod('daily')" id="dailyTab">
                Günlük
            </button>
            <button class="period-tab" onclick="switchPeriod('weekly')" id="weeklyTab">
                Haftalık
            </button>
        </div>

        <!-- History Lists -->
        <div class="history-list active" id="dailyList">
            <div class="loading" id="dailyLoading">
                <div class="loading-spinner"></div>
                <div>Veriler yükleniyor...</div>
            </div>
        </div>

        <div class="history-list" id="weeklyList">
            <div class="loading" id="weeklyLoading">
                <div class="loading-spinner"></div>
                <div>Veriler yükleniyor...</div>
            </div>
        </div>
    </div>

    <!-- Bottom Navigation -->
    <div class="bottom-nav">
        <button class="nav-btn active" onclick="showView('home')">
            <span class="nav-icon">📊</span>
            <span>Fiyatlar</span>
        </button>
        <button class="nav-btn" onclick="showView('portfolio')">
            <span class="nav-icon">💼</span>
            <span>Portföy</span>
        </button>
    </div>

    <!-- Portfolio Modal -->
    <div class="modal" id="portfolioModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Portföy Ayarları</div>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            
            <div class="input-group">
                <label class="input-label">Altın (gram)</label>
                <input type="number" class="input-field" id="goldAmount" placeholder="0.0" 
                       step="0.1" min="0" oninput="updatePortfolio()">
            </div>
            
            <div class="input-group">
                <label class="input-label">Gümüş (gram)</label>
                <input type="number" class="input-field" id="silverAmount" placeholder="0.0" 
                       step="0.1" min="0" oninput="updatePortfolio()">
            </div>
            
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="clearPortfolio()">Sıfırla</button>
                <button class="btn btn-primary" onclick="closeModal()">Kaydet</button>
            </div>
        </div>
    </div>

    <script>
        let currentGoldPrice = 0;
        let currentSilverPrice = 0;
        let tableData = {};
        let currentPeriod = 'daily';

        async function fetchPrices() {
            const btn = document.getElementById('refreshBtn');
            btn.classList.add('spinning');
            
            try {
                const [goldRes, silverRes, tableRes] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data')
                ]);
                
                const goldData = await goldRes.json();
                const silverData = await silverRes.json();
                const tableDataRes = await tableRes.json();
                
                if (goldData.success) {
                    let cleanPrice = goldData.price.replace(/[^\\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                    document.getElementById('goldPrice').textContent = formatPrice(currentGoldPrice);
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                    document.getElementById('silverPrice').textContent = formatPrice(currentSilverPrice);
                }
                
                if (tableDataRes.success) {
                    tableData = tableDataRes.data;
                    updateHistoryLists();
                }
                
                const now = new Date();
                document.getElementById('updateTime').textContent = 'Hata oluştu';
            } finally {
                setTimeout(() => btn.classList.remove('spinning'), 1000);
            }
        }

        function updateHistoryLists() {
            updateDailyList();
            updateWeeklyList();
        }

        function updateDailyList() {
            const list = document.getElementById('dailyList');
            const loading = document.getElementById('dailyLoading');
            
            if (!tableData.daily || tableData.daily.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div><div class="empty-text">Günlük veri bulunamadı</div></div>';
                return;
            }
            
            loading.style.display = 'none';
            
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            let maxPortfolioValue = 0;
            let peakIndex = -1;
            
            if (goldAmount > 0 || silverAmount > 0) {
                tableData.daily.forEach((item, index) => {
                    const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                    if (portfolioValue > maxPortfolioValue) {
                        maxPortfolioValue = portfolioValue;
                        peakIndex = index;
                    }
                });
            }
            
            let html = '';
            tableData.daily.forEach((item, index) => {
                const isPeak = index === peakIndex && maxPortfolioValue > 0;
                const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                html += `
                    <div class="history-item ${isPeak ? 'peak' : ''}">
                        <div class="history-time">${item.time}</div>
                        <div class="history-prices">
                            <div class="history-price"><strong>${formatPrice(item.gold_price)}</strong> Altın</div>
                            <div class="history-price"><strong>${formatPrice(item.silver_price)}</strong> Gümüş</div>
                            ${portfolioValue > 0 ? `<div class="history-price"><strong>${formatCurrency(portfolioValue)}</strong> Portföy</div>` : ''}
                        </div>
                        <div class="history-change ${getChangeClass(item.change_percent)}">
                            ${formatChange(item.change_percent)}
                        </div>
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }

        function updateWeeklyList() {
            const list = document.getElementById('weeklyList');
            const loading = document.getElementById('weeklyLoading');
            
            if (!tableData.weekly || tableData.weekly.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-text">Haftalık veri bulunamadı</div></div>';
                return;
            }
            
            loading.style.display = 'none';
            
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            let maxPortfolioValue = 0;
            let peakIndex = -1;
            
            if (goldAmount > 0 || silverAmount > 0) {
                tableData.weekly.forEach((item, index) => {
                    const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                    if (portfolioValue > maxPortfolioValue) {
                        maxPortfolioValue = portfolioValue;
                        peakIndex = index;
                    }
                });
            }
            
            let html = '';
            tableData.weekly.forEach((item, index) => {
                const isPeak = index === peakIndex && maxPortfolioValue > 0;
                const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                html += `
                    <div class="history-item ${isPeak ? 'peak' : ''}">
                        <div class="history-time">${item.time} 📊</div>
                        <div class="history-prices">
                            <div class="history-price"><strong>${formatPrice(item.gold_price)}</strong> Altın</div>
                            <div class="history-price"><strong>${formatPrice(item.silver_price)}</strong> Gümüş</div>
                            ${portfolioValue > 0 ? `<div class="history-price"><strong>${formatCurrency(portfolioValue)}</strong> Portföy</div>` : ''}
                        </div>
                        <div class="history-change ${getChangeClass(item.change_percent)}">
                            ${formatChange(item.change_percent)}
                        </div>
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }

        function switchPeriod(period) {
            currentPeriod = period;
            
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            document.querySelectorAll('.history-list').forEach(list => list.classList.remove('active'));
            document.getElementById(period + 'List').classList.add('active');
        }

        function showView(view) {
            document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
            
            if (view === 'home') {
                event.target.closest('.nav-btn').classList.add('active');
            } else if (view === 'portfolio') {
                event.target.closest('.nav-btn').classList.add('active');
                document.getElementById('portfolioModal').classList.add('active');
            }
        }

        function closeModal() {
            document.getElementById('portfolioModal').classList.remove('active');
            document.querySelectorAll('.nav-btn').forEach((btn, index) => {
                if (index === 0) btn.classList.add('active');
                else btn.classList.remove('active');
            });
        }

        function updatePortfolio() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            const portfolioCard = document.getElementById('portfolioCard');
            
            if (totalValue > 0) {
                portfolioCard.classList.add('active');
                document.getElementById('portfolioAmount').textContent = formatCurrency(totalValue);
                document.getElementById('goldValue').textContent = formatCurrency(goldValue);
                document.getElementById('silverValue').textContent = formatCurrency(silverValue);
                
                updateHistoryLists();
            } else {
                portfolioCard.classList.remove('active');
            }
            
            savePortfolio();
        }

        function savePortfolio() {
            const goldAmount = document.getElementById('goldAmount').value;
            const silverAmount = document.getElementById('silverAmount').value;
            
            const expiryDate = new Date();
            expiryDate.setFullYear(expiryDate.getFullYear() + 1);
            
            document.cookie = `goldAmount=${goldAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
            document.cookie = `silverAmount=${silverAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
        }

        function loadPortfolio() {
            const cookies = document.cookie.split(';').reduce((acc, cookie) => {
                const [key, value] = cookie.trim().split('=');
                acc[key] = value;
                return acc;
            }, {});
            
            if (cookies.goldAmount && cookies.goldAmount !== 'undefined') {
                document.getElementById('goldAmount').value = cookies.goldAmount;
            }
            if (cookies.silverAmount && cookies.silverAmount !== 'undefined') {
                document.getElementById('silverAmount').value = cookies.silverAmount;
            }
        }

        function clearPortfolio() {
            if (confirm('Portföy sıfırlanacak. Emin misiniz?')) {
                document.getElementById('goldAmount').value = '';
                document.getElementById('silverAmount').value = '';
                
                document.cookie = 'goldAmount=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                document.cookie = 'silverAmount=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                
                updatePortfolio();
            }
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

        function formatCurrency(amount) {
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount) + ' ₺';
        }

        function formatPrice(price) {
            if (!price) return '0,00';
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(price);
        }

        document.getElementById('portfolioModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        window.onload = function() {
            loadPortfolio();
            fetchPrices();
            updatePortfolio();
        };
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return Response(HTML_TEMPLATE, mimetype='text/html')

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
                    'Güncellendi: ' + now.toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                
                updatePortfolio();
                
            } catch (error) {
                document.getElementById('updateTime').textContent = 'Hata oluştu';
            } finally {
                setTimeout(() => btn.classList.remove('spinning'), 1000);
            }
        }

        function updateHistoryLists() {
            updateDailyList();
            updateWeeklyList();
        }

        function updateDailyList() {
            const list = document.getElementById('dailyList');
            const loading = document.getElementById('dailyLoading');
            
            if (!tableData.daily || tableData.daily.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div><div class="empty-text">Günlük veri bulunamadı</div></div>';
                return;
            }
            
            loading.style.display = 'none';
            
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            let maxPortfolioValue = 0;
            let peakIndex = -1;
            
            if (goldAmount > 0 || silverAmount > 0) {
                tableData.daily.forEach((item, index) => {
                    const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                    if (portfolioValue > maxPortfolioValue) {
                        maxPortfolioValue = portfolioValue;
                        peakIndex = index;
                    }
                });
            }
            
            let html = '';
            tableData.daily.forEach((item, index) => {
                const isPeak = index === peakIndex && maxPortfolioValue > 0;
                const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                html += `
                    <div class="history-item ${isPeak ? 'peak' : ''}">
                        <div class="history-time">${item.time}</div>
                        <div class="history-prices">
                            <div class="history-price"><strong>${formatPrice(item.gold_price)}</strong> Altın</div>
                            <div class="history-price"><strong>${formatPrice(item.silver_price)}</strong> Gümüş</div>
                            ${portfolioValue > 0 ? `<div class="history-price"><strong>${formatCurrency(portfolioValue)}</strong> Portföy</div>` : ''}
                        </div>
                        <div class="history-change ${getChangeClass(item.change_percent)}">
                            ${formatChange(item.change_percent)}
                        </div>
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }

        function updateWeeklyList() {
            const list = document.getElementById('weeklyList');
            const loading = document.getElementById('weeklyLoading');
            
            if (!tableData.weekly || tableData.weekly.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-text">Haftalık veri bulunamadı</div></div>';
                return;
            }
            
            loading.style.display = 'none';
            
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            let maxPortfolioValue = 0;
            let peakIndex = -1;
            
            if (goldAmount > 0 || silverAmount > 0) {
                tableData.weekly.forEach((item, index) => {
                    const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                    if (portfolioValue > maxPortfolioValue) {
                        maxPortfolioValue = portfolioValue;
                        peakIndex = index;
                    }
                });
            }
            
            let html = '';
            tableData.weekly.forEach((item, index) => {
                const isPeak = index === peakIndex && maxPortfolioValue > 0;
                const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                html += `
                    <div class="history-item ${isPeak ? 'peak' : ''}">
                        <div class="history-time">${item.time} 📊</div>
                        <div class="history-prices">
                            <div class="history-price"><strong>${formatPrice(item.gold_price)}</strong> Altın</div>
                            <div class="history-price"><strong>${formatPrice(item.silver_price)}</strong> Gümüş</div>
                            ${portfolioValue > 0 ? `<div class="history-price"><strong>${formatCurrency(portfolioValue)}</strong> Portföy</div>` : ''}
                        </div>
                        <div class="history-change ${getChangeClass(item.change_percent)}">
                            ${formatChange(item.change_percent)}
                        </div>
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }

        function switchPeriod(period) {
            currentPeriod = period;
            
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            document.querySelectorAll('.history-list').forEach(list => list.classList.remove('active'));
            document.getElementById(period + 'List').classList.add('active');
        }

        function showView(view) {
            document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
            
            if (view === 'home') {
                event.target.closest('.nav-btn').classList.add('active');
            } else if (view === 'portfolio') {
                event.target.closest('.nav-btn').classList.add('active');
                document.getElementById('portfolioModal').classList.add('active');
            }
        }

        function closeModal() {
            document.getElementById('portfolioModal').classList.remove('active');
            document.querySelectorAll('.nav-btn').forEach((btn, index) => {
                if (index === 0) btn.classList.add('active');
                else btn.classList.remove('active');
            });
        }

        function updatePortfolio() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            const portfolioCard = document.getElementById('portfolioCard');
            
            if (totalValue > 0) {
                portfolioCard.classList.add('active');
                document.getElementById('portfolioAmount').textContent = formatCurrency(totalValue);
                document.getElementById('goldValue').textContent = formatCurrency(goldValue);
                document.getElementById('silverValue').textContent = formatCurrency(silverValue);
                
                updateHistoryLists();
            } else {
                portfolioCard.classList.remove('active');
            }
            
            savePortfolio();
        }

        function savePortfolio() {
            const goldAmount = document.getElementById('goldAmount').value;
            const silverAmount = document.getElementById('silverAmount').value;
            
            const expiryDate = new Date();
            expiryDate.setFullYear(expiryDate.getFullYear() + 1);
            
            document.cookie = `goldAmount=${goldAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
            document.cookie = `silverAmount=${silverAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
        }

        function loadPortfolio() {
            const cookies = document.cookie.split(';').reduce((acc, cookie) => {
                const [key, value] = cookie.trim().split('=');
                acc[key] = value;
                return acc;
            }, {});
            
            if (cookies.goldAmount && cookies.goldAmount !== 'undefined') {
                document.getElementById('goldAmount').value = cookies.goldAmount;
            }
            if (cookies.silverAmount && cookies.silverAmount !== 'undefined') {
                document.getElementById('silverAmount').value = cookies.silverAmount;
            }
        }

        function clearPortfolio() {
            if (confirm('Portföy sıfırlanacak. Emin misiniz?')) {
                document.getElementById('goldAmount').value = '';
                document.getElementById('silverAmount').value = '';
                
                document.cookie = 'goldAmount=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                document.cookie = 'silverAmount=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                
                updatePortfolio();
            }
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

        function formatCurrency(amount) {
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount) + ' ₺';
        }

        function formatPrice(price) {
            if (!price) return '0,00';
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(price);
        }

        document.getElementById('portfolioModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        window.onload = function() {
            loadPortfolio();
            fetchPrices();
            updatePortfolio();
        };
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return Response(HTML_TEMPLATE, mimetype='text/html')

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