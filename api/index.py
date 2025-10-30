#!/usr/bin/env python3
"""
Metal Price Tracker Web App v2.0
Flask web uygulaması - optimize edilmiş verilerle haftalık görünüm
Güncellemeler: Gelişmiş istatistikler + Kalıcı session sistemi
"""
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
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
app.secret_key = secrets.token_hex(16)

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
    """Son 2 günün tüm verilerini getir (30dk aralıklarla)"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        now = datetime.now(timezone.utc)
        daily_data = []
        
        # Son 2 günün verilerini al
        for day_offset in range(2):
            target_date = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            day_records = [r for r in records 
                          if r.get("date") == target_date 
                          and r.get("gold_price") 
                          and r.get("silver_price")
                          and not r.get("optimized", False)]  # Optimize edilmemiş kayıtlar
            
            if day_records:
                sorted_day_records = sorted(day_records, key=lambda x: x.get("timestamp", 0), reverse=True)
                
                for i, record in enumerate(sorted_day_records):
                    timestamp = record.get("timestamp", 0)
                    # UTC'den Türkiye saatine çevir (+3 saat)
                    local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
                    
                    # Eğer bugün değilse tarih de göster
                    if day_offset == 0:
                        time_label = local_time.strftime("%H:%M")
                    else:
                        time_label = local_time.strftime("%d.%m %H:%M")
                    
                    # Değişim hesaplama (bir önceki kayıt ile karşılaştır)
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
    """Son 30 günün optimize edilmiş verilerini getir (günlük peak değerler)"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        # Optimize edilmiş kayıtları bul (günlük peak değerler)
        optimized_records = [
            r for r in records 
            if r.get("optimized") == True and r.get("daily_peak") == True
        ]
        
        # Son 30 günün optimize edilmiş verilerini al
        weekly_data = []
        weekly_temp = []
        now = datetime.now(timezone.utc)
        
        # Önce tüm günleri topla (eskiden yeniye)
        for i in range(29, -1, -1):  # 29'dan 0'a doğru (eskiden yeniye)
            target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            
            # O günün optimize edilmiş kaydını bul
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
        
        # Şimdi değişim hesaplama
        for i, day_data in enumerate(weekly_temp):
            change_percent = 0
            
            # Bir önceki gün ile karşılaştır (eskiden yeniye sıralı listede)
            if i > 0:
                prev_day = weekly_temp[i-1]
                if prev_day["gold_price"] > 0:
                    price_diff = day_data["gold_price"] - prev_day["gold_price"]
                    change_percent = (price_diff / prev_day["gold_price"]) * 100
            
            weekly_data.append({
                "time": f"{day_data['time']} 📊",  # Peak değer işareti
                "gold_price": day_data["gold_price"],
                "silver_price": day_data["silver_price"],
                "change_percent": change_percent,
                "optimized": True,
                "peak_time": day_data["peak_time"],
                "portfolio_value": day_data["portfolio_value"]
            })
        
        # En son kayıt en başta olsun diye ters çevir (yeniden eskiye)
        weekly_data.reverse()
        
        return weekly_data
        
    except Exception:
        return []

def calculate_statistics(data_type='all'):
    """Belirtilen veri tipinden maksimum değerleri hesapla"""
    try:
        config = load_portfolio_config()
        
        if data_type == 'daily':
            data = get_daily_data()
        elif data_type == 'weekly':
            data = get_weekly_optimized_data()
        else:
            # Tüm veriler için
            daily_data = get_daily_data()
            weekly_data = get_weekly_optimized_data()
            data = daily_data + weekly_data
        
        if not data:
            return {
                "max_gold_price": 0,
                "max_silver_price": 0,
                "max_portfolio_value": 0
            }
        
        # Maksimum değerleri bul
        max_gold = max(item["gold_price"] for item in data)
        max_silver = max(item["silver_price"] for item in data)
        
        # Portföy hesaplaması için config'den miktarları al
        gold_amount = config.get("gold_amount", 0)
        silver_amount = config.get("silver_amount", 0)
        
        # En yüksek portföy değerini hesapla
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
        return {
            "max_gold_price": 0,
            "max_silver_price": 0,
            "max_portfolio_value": 0
        }

def get_table_data():
    """Günlük ve haftalık veriler için farklı kaynak kullan"""
    try:
        daily_data = get_daily_data()
        weekly_data = get_weekly_optimized_data()
        
        # Her sekme için ayrı istatistik hesapla
        daily_stats = calculate_statistics('daily')
        weekly_stats = calculate_statistics('weekly')
        
        return {
            "daily": daily_data,
            "weekly": weekly_data,
            "statistics": {
                "daily": daily_stats,
                "weekly": weekly_stats
            }
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

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh; padding: 20px; color: #e2e8f0;
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 24px; padding: 24px 20px; color: white;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        .portfolio-amount { font-size: 42px; font-weight: 900; margin-bottom: 20px; }
        .portfolio-info { font-size: 12px; opacity: 0.8; margin-top: 8px; }
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
        .metal-amount { font-size: 12px; opacity: 0.7; margin-top: 8px; }
        
        .statistics-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .statistics-title {
            font-size: 18px;
            font-weight: 700;
            color: #ffd700;
            margin-bottom: 16px;
            text-align: center;
        }
        .statistics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
        }
        .stat-item {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 14px 10px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .stat-label {
            font-size: 11px;
            opacity: 0.8;
            margin-bottom: 8px;
            line-height: 1.2;
        }
        .stat-value {
            font-size: 16px;
            font-weight: 800;
            color: #ffd700;
            word-wrap: break-word;
        }
        
        .price-history {
            background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 16px; border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .history-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
        }
        .history-title { font-size: 18px; font-weight: 700; color: #ffffff; }
        .period-tabs {
            display: flex; gap: 8px;
            background: rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 4px;
        }
        .period-tab {
            padding: 8px 16px; border: none; border-radius: 6px;
            background: transparent; color: rgba(255, 255, 255, 0.7);
            font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .period-tab.active { background: rgba(255, 255, 255, 0.2); color: #ffffff; }
        
        .price-table {
            overflow-x: auto; border-radius: 12px; background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .price-table table {
            width: 100%; border-collapse: collapse;
        }
        .price-table th {
            background: rgba(255, 255, 255, 0.1); padding: 12px 8px; text-align: left;
            font-weight: 600; color: rgba(255, 255, 255, 0.9); font-size: 13px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1); white-space: nowrap;
        }
        .price-table td {
            padding: 12px 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 13px; color: #e2e8f0; white-space: nowrap;
        }
        .price-table tr:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        .price-table .time { font-weight: 600; color: rgba(255, 255, 255, 0.9); }
        .price-table .price { font-weight: 600; }
        .price-table .portfolio { font-weight: 700; color: #ffd700; }
        .price-table .change {
            font-weight: 600; font-size: 13px;
        }
        .change.positive { color: #4ade80; }
        .change.negative { color: #f87171; }
        .change.neutral { color: rgba(255, 255, 255, 0.7); }
        
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
            .statistics-grid { grid-template-columns: 1fr; gap: 8px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
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
        
        <div class="portfolio-summary" id="portfolioSummary">
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="portfolio-metals">
                <div class="metal-item">
                    <div class="metal-header">
                        <div class="metal-name">Altın</div>
                    </div>
                    <div class="metal-price" id="goldCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="goldPortfolioValue">0,00 ₺</div>
                    <div class="metal-amount" id="goldAmount">0 gr</div>
                </div>
                <div class="metal-item">
                    <div class="metal-header">
                        <div class="metal-name">Gümüş</div>
                    </div>
                    <div class="metal-price" id="silverCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="silverPortfolioValue">0,00 ₺</div>
                    <div class="metal-amount" id="silverAmount">0 gr</div>
                </div>
            </div>
        </div>
        
        <div class="statistics-section">
            <div class="statistics-title">📊 Maksimum Değerler</div>
            <div class="statistics-grid">
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Altın Fiyatı</div>
                    <div class="stat-value" id="maxGoldPrice">0 ₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Gümüş Fiyatı</div>
                    <div class="stat-value" id="maxSilverPrice">0 ₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Portföy Tutarı</div>
                    <div class="stat-value" id="maxPortfolioValue">0 ₺</div>
                </div>
            </div>
        </div>
        
        <div class="price-history" id="priceHistory">
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
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data'),
                    fetch('/api/portfolio-config')
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
                document.getElementById('maxGoldPrice').textContent = formatPrice(stats.max_gold_price);
                document.getElementById('maxSilverPrice').textContent = formatPrice(stats.max_silver_price);
                document.getElementById('maxPortfolioValue').textContent = formatCurrency(stats.max_portfolio_value);
                
                // İstatistik başlığını güncelle
                const periodText = currentPeriod === 'daily' ? 'Günlük' : 'Aylık';
                document.querySelector('.statistics-title').textContent = `${periodText} Maksimum Değerler`;
            }
        }

        function switchPeriod(period) {
            currentPeriod = period;
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            const timeHeader = document.getElementById('timeHeader');
            if (period === 'daily') {
                timeHeader.textContent = 'Saat';
            } else if (period === 'weekly') {
                timeHeader.textContent = 'Tarih';
            }
            
            updateTable();
            updateStatistics(); // İstatistikleri de güncelle
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

@app.before_request
def make_session_permanent():
    """Her request'te session'ı kalıcı yap"""
    session.permanent = True

@app.route('/')
def index():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE)

@app.route('/login')
def login():
    if 'authenticated' in session:
        return redirect(url_for('index'))
    
    html = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <meta name="theme-color" content="#1e3c72">
    <title>Metal Tracker - Giriş</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px 30px;
            width: 100%;
            max-width: 400px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .logo {
            font-size: 24px;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .logo-icon { font-size: 28px; }
        
        .subtitle {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 32px;
        }
        
        .form-group {
            margin-bottom: 24px;
            text-align: left;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
            color: #e2e8f0;
        }
        
        .form-input {
            width: 100%;
            padding: 16px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            font-size: 16px;
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
            transition: all 0.3s ease;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255, 255, 255, 0.1);
        }
        
        .form-input::placeholder {
            color: rgba(255, 255, 255, 0.5);
        }
        
        .login-btn {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 16px;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .login-btn:active {
            transform: translateY(0);
        }
        
        .login-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .error-message {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
            color: #f87171;
            font-size: 14px;
            display: none;
        }
        
        .error-message.show {
            display: block;
        }
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
                <input type="password" class="form-input" id="password" placeholder="Şifrenizi girin" required autocomplete="current-password">
            </div>
            
            <div class="error-message" id="errorMessage">
                Hatalı şifre! Lütfen tekrar deneyin.
            </div>
            
            <button type="submit" class="login-btn" id="loginBtn">
                Giriş Yap
            </button>
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
                    headers: {
                        'Content-Type': 'application/json'
                    },
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
        
        document.getElementById('password').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleLogin(e);
            }
        });
        
        window.onload = function() {
            document.getElementById('password').focus();
        };
    </script>
</body>
</html>'''
    return html

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if verify_password(password):
            session.permanent = True  # Bu satır önemli!
            session['authenticated'] = True
            # Session'un kalıcı olduğundan emin ol
            app.permanent_session_lifetime = timedelta(days=30)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Invalid password'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

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
        # Şifreyi döndürme
        config.pop('password_hash', None)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Kalıcı session ayarları (30 gün)
    app.permanent_session_lifetime = timedelta(days=30)
    
    # Session cookie ayarları - kalıcı olması için
    app.config.update(
        SESSION_COOKIE_SECURE=False,  # HTTPS için True yapın
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_PERMANENT=False,  # Bu False olmalı, session.permanent ile kontrol edilecek
        PERMANENT_SESSION_LIFETIME=timedelta(days=30)
    )
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)