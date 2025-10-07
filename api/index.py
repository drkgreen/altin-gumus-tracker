#!/usr/bin/env python3
"""
Metal Price Tracker Web App v2.0 - Dark Modern Theme
"""
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
CORS(app)

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
                        "change_percent": change_percent
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
                    "silver_price": day_record["silver_price"]
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
                "change_percent": change_percent
            })
        
        weekly_data.reverse()
        
        return weekly_data
        
    except Exception:
        return []

def get_table_data():
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

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <meta name="theme-color" content="#1a202c">
    <title>Metal Tracker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a202c;
            color: #e2e8f0;
            min-height: 100vh;
            padding-bottom: 20px;
        }
        
        .header {
            background: #2d3748;
            padding: 12px 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 1px solid #4a5568;
        }
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 600px;
            margin: 0 auto;
        }
        .logo {
            font-size: 17px;
            font-weight: 700;
            color: #f7fafc;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .logo-icon { font-size: 20px; }
        
        .header-actions {
            display: flex;
            gap: 8px;
        }
        .header-btn {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: #4a5568;
            border: 1px solid #718096;
            color: #f7fafc;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .header-btn:active {
            background: #718096;
            transform: scale(0.95);
        }
        .header-btn.spinning { animation: spin 1s ease-in-out; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        
        .update-info {
            font-size: 11px;
            color: #a0aec0;
            text-align: center;
            margin-top: 6px;
        }
        
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
        }
        
        .portfolio-card {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border-radius: 20px;
            padding: 20px 16px;
            margin-bottom: 20px;
            color: white;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            display: none;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .portfolio-card.active { display: block; }
        
        .portfolio-total {
            text-align: center;
            padding: 16px 12px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            margin-bottom: 12px;
            backdrop-filter: blur(10px);
        }
        .portfolio-total-value {
            font-size: 34px;
            font-weight: 900;
            word-wrap: break-word;
        }
        
        .portfolio-breakdown {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .portfolio-item {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 12px 10px;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        .portfolio-item-label {
            font-size: 11px;
            opacity: 0.9;
            margin-bottom: 6px;
        }
        .portfolio-item-value {
            font-size: 14px;
            font-weight: 800;
            word-wrap: break-word;
            line-height: 1.2;
            margin-bottom: 8px;
        }
        .portfolio-item-price {
            font-size: 12px;
            opacity: 0.85;
            font-weight: 600;
        }
        
        .tabs {
            display: flex;
            gap: 6px;
            margin-bottom: 16px;
            background: #2d3748;
            padding: 5px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.15);
            border: 1px solid #4a5568;
        }
        .tab {
            flex: 1;
            padding: 8px 6px;
            border: none;
            border-radius: 8px;
            background: transparent;
            color: #a0aec0;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }
        .tab.active {
            background: #4a5568;
            color: #f7fafc;
        }
        
        .history-section { display: none; }
        .history-section.active { display: block; }
        
        .history-item {
            background: #2d3748;
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.15);
            border: 1px solid #4a5568;
        }
        .history-item.peak {
            background: linear-gradient(135deg, #744210 0%, #d69e2e 100%);
            border: 1px solid #f6ad55;
            color: #2d3748;
        }
        
        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .history-time {
            font-size: 12px;
            font-weight: 600;
            color: #cbd5e1;
        }
        .history-item.peak .history-time {
            color: #2d3748;
        }
        .history-portfolio {
            font-size: 15px;
            font-weight: 700;
            color: #f6ad55;
        }
        .history-item.peak .history-portfolio {
            color: #2d3748;
        }
        
        .history-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .history-metals {
            display: flex;
            gap: 12px;
        }
        .history-metal {
            font-size: 11px;
            color: #a0aec0;
        }
        .history-item.peak .history-metal {
            color: #2d3748;
        }
        .history-metal span {
            font-weight: 600;
            color: #e2e8f0;
        }
        .history-item.peak .history-metal span {
            color: #1a202c;
        }
        .history-change {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            background: #4a5568;
        }
        .history-change.positive { background: #065f46; color: #34d399; }
        .history-change.negative { background: #991b1b; color: #f87171; }
        .history-change.neutral { background: #4a5568; color: #cbd5e1; }
        
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 200;
            display: none;
            align-items: flex-end;
            backdrop-filter: blur(8px);
        }
        .modal.active { display: flex; }
        .modal-content {
            background: #2d3748;
            border-radius: 24px 24px 0 0;
            padding: 24px 20px 40px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
            animation: slideUp 0.3s ease;
            border: 1px solid #4a5568;
            border-bottom: none;
        }
        @keyframes slideUp {
            from { transform: translateY(100%); }
            to { transform: translateY(0); }
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-title {
            font-size: 19px;
            font-weight: 800;
            color: #f7fafc;
        }
        .modal-close {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: #4a5568;
            border: 1px solid #718096;
            font-size: 20px;
            color: #a0aec0;
            cursor: pointer;
        }
        .input-group { margin-bottom: 18px; }
        .input-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
            color: #e2e8f0;
        }
        .input-field {
            width: 100%;
            padding: 14px;
            border: 2px solid #4a5568;
            border-radius: 12px;
            font-size: 16px;
            background: #1a202c;
            color: #f7fafc;
        }
        .input-field:focus {
            outline: none;
            border-color: #6366f1;
            background: #2d3748;
        }
        .input-field::placeholder {
            color: #718096;
        }
        .modal-actions {
            display: flex;
            gap: 10px;
        }
        .btn {
            flex: 1;
            padding: 14px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 15px;
            cursor: pointer;
            border: none;
            transition: all 0.3s ease;
        }
        .btn:active { transform: scale(0.98); }
        .btn-primary {
            background: #6366f1;
            color: white;
        }
        .btn-secondary {
            background: #4a5568;
            color: #a0aec0;
            border: 1px solid #718096;
        }
        
        .loading {
            text-align: center;
            padding: 40px 20px;
            color: #718096;
        }
        .loading-spinner {
            width: 32px;
            height: 32px;
            border: 3px solid #4a5568;
            border-top-color: #6366f1;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 12px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }
        .stats-card {
            background: #2d3748;
            border-radius: 12px;
            padding: 14px 12px;
            border: 1px solid #4a5568;
            text-align: center;
        }
        .stats-card-title {
            font-size: 11px;
            color: #a0aec0;
            margin-bottom: 6px;
            font-weight: 600;
        }
        .stats-card-value {
            font-size: 16px;
            font-weight: 800;
            color: #f7fafc;
            margin-bottom: 4px;
        }
        .stats-card-change {
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .stats-card-change.positive { background: #065f46; color: #34d399; }
        .stats-card-change.negative { background: #991b1b; color: #f87171; }
        .stats-card-change.neutral { background: #4a5568; color: #cbd5e1; }
        
        .chart-container {
            background: #2d3748;
            border-radius: 12px;
            padding: 16px 12px;
            margin-bottom: 16px;
            border: 1px solid #4a5568;
        }
        .chart-title {
            font-size: 14px;
            font-weight: 700;
            color: #f7fafc;
            margin-bottom: 12px;
            text-align: center;
        }
        .mini-chart {
            width: 100%;
            height: 120px;
            background: #1a202c;
            border-radius: 8px;
            position: relative;
            overflow: hidden;
            border: 1px solid #4a5568;
        }
        .chart-line {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 100%;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(99, 102, 241, 0.05) 100%);
            border-top: 2px solid #6366f1;
            border-radius: 8px 8px 0 0;
        }
        .chart-points {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            align-items: end;
            justify-content: space-between;
            padding: 8px;
        }
        .chart-point {
            width: 4px;
            background: #6366f1;
            border-radius: 2px;
            box-shadow: 0 0 4px rgba(99, 102, 241, 0.5);
        }
        
        .analysis-list {
            background: #2d3748;
            border-radius: 12px;
            padding: 14px;
            border: 1px solid #4a5568;
        }
        .analysis-title {
            font-size: 14px;
            font-weight: 700;
            color: #f7fafc;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .analysis-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #4a5568;
        }
        .analysis-item:last-child {
            border-bottom: none;
        }
        .analysis-label {
            font-size: 12px;
            color: #a0aec0;
            font-weight: 600;
        }
        .analysis-value {
            font-size: 12px;
            font-weight: 700;
            color: #f7fafc;
        }
        .analysis-trend {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 6px;
        }
        .analysis-trend.bullish { background: #065f46; color: #34d399; }
        .analysis-trend.bearish { background: #991b1b; color: #f87171; }
        .analysis-trend.neutral { background: #4a5568; color: #cbd5e1; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <span class="logo-icon">📊</span>
                <span>Metal Tracker</span>
            </div>
            <div class="header-actions">
                <button class="header-btn" onclick="fetchData()" id="refreshBtn">↻</button>
                <button class="header-btn" onclick="openPortfolio()">⚙</button>
            </div>
        </div>
        <div class="update-info" id="updateInfo">Yükleniyor...</div>
    </div>

    <div class="container">
        <div class="portfolio-card" id="portfolioCard">
            <div class="portfolio-total">
                <div class="portfolio-total-value" id="portfolioTotal">0 ₺</div>
            </div>
            
            <div class="portfolio-breakdown">
                <div class="portfolio-item">
                    <div class="portfolio-item-label">Altın</div>
                    <div class="portfolio-item-price" id="goldPrice">-</div>
                    <div class="portfolio-item-value" id="goldPortfolio">0 ₺</div>
                </div>
                <div class="portfolio-item">
                    <div class="portfolio-item-label">Gümüş</div>
                    <div class="portfolio-item-price" id="silverPrice">-</div>
                    <div class="portfolio-item-value" id="silverPortfolio">0 ₺</div>
                </div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('daily')" id="dailyTab">Günlük</button>
            <button class="tab" onclick="switchTab('weekly')" id="weeklyTab">Haftalık</button>
            <button class="tab" onclick="switchTab('stats')" id="statsTab">İstatistik</button>
        </div>

        <div class="history-section active" id="dailySection">
            <div class="loading">
                <div class="loading-spinner"></div>
                <div>Veriler yükleniyor...</div>
            </div>
        </div>

        <div class="history-section" id="weeklySection">
            <div class="loading">
                <div class="loading-spinner"></div>
                <div>Veriler yükleniyor...</div>
            </div>
        </div>

        <div class="history-section" id="statsSection">
            <div class="stats-grid">
                <div class="stats-card">
                    <div class="stats-card-title">7 Gün Değişim</div>
                    <div class="stats-card-value" id="weeklyChange">+%3.2</div>
                    <div class="stats-card-change positive">↗️ Yükseliş</div>
                </div>
                <div class="stats-card">
                    <div class="stats-card-title">Volatilite</div>
                    <div class="stats-card-value" id="volatility">%2.8</div>
                    <div class="stats-card-change neutral">Düşük</div>
                </div>
                <div class="stats-card">
                    <div class="stats-card-title">En Yüksek</div>
                    <div class="stats-card-value" id="weeklyHigh">5,247₺</div>
                    <div class="stats-card-change positive">29.09</div>
                </div>
                <div class="stats-card">
                    <div class="stats-card-title">En Düşük</div>
                    <div class="stats-card-value" id="weeklyLow">4,892₺</div>
                    <div class="stats-card-change negative">22.09</div>
                </div>
            </div>

            <div class="chart-container">
                <div class="chart-title">📈 Son 7 Gün Altın Trendi</div>
                <div class="mini-chart">
                    <div class="chart-line"></div>
                    <div class="chart-points" id="chartPoints">
                        <div class="chart-point" style="height: 45%;"></div>
                        <div class="chart-point" style="height: 52%;"></div>
                        <div class="chart-point" style="height: 38%;"></div>
                        <div class="chart-point" style="height: 65%;"></div>
                        <div class="chart-point" style="height: 78%;"></div>
                        <div class="chart-point" style="height: 85%;"></div>
                        <div class="chart-point" style="height: 92%;"></div>
                    </div>
                </div>
            </div>

            <div class="analysis-list">
                <div class="analysis-title">🔍 Fiyat Analizi</div>
                
                <div class="analysis-item">
                    <div class="analysis-label">Destek Seviyesi</div>
                    <div class="analysis-value">4,950₺ <span class="analysis-trend neutral">Güçlü</span></div>
                </div>
                
                <div class="analysis-item">
                    <div class="analysis-label">Direnç Seviyesi</div>
                    <div class="analysis-value">5,200₺ <span class="analysis-trend bullish">Test</span></div>
                </div>
                
                <div class="analysis-item">
                    <div class="analysis-label">En Kazançlı Gün</div>
                    <div class="analysis-value">+%1.8 <span class="analysis-trend bullish">28.09</span></div>
                </div>
                
                <div class="analysis-item">
                    <div class="analysis-label">En Kayıplı Gün</div>
                    <div class="analysis-value">-%1.2 <span class="analysis-trend bearish">22.09</span></div>
                </div>
                
                <div class="analysis-item">
                    <div class="analysis-label">Ortalama Değişim</div>
                    <div class="analysis-value">+%0.3 <span class="analysis-trend bullish">Pozitif</span></div>
                </div>
                
                <div class="analysis-item">
                    <div class="analysis-label">Trend Gücü</div>
                    <div class="analysis-value">Güçlü <span class="analysis-trend bullish">Yükseliş</span></div>
                </div>
            </div>
        </div>
    </div>

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
                <button class="btn btn-primary" onclick="saveAndClose()">Kaydet</button>
            </div>
        </div>
    </div>

    <script>
        let goldPrice = 0;
        let silverPrice = 0;
        let tableData = {};
        let currentTab = 'daily';

        async function fetchData() {
            const btn = document.getElementById('refreshBtn');
            btn.classList.add('spinning');
            
            try {
                const [g, s, t] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data')
                ]);
                
                const gold = await g.json();
                const silver = await s.json();
                const table = await t.json();
                
                if (gold.success) {
                    let p = gold.price.replace(/[^\\d,]/g, '');
                    goldPrice = parseFloat(p.replace(',', '.'));
                    document.getElementById('goldPrice').textContent = gold.price;
                }
                
                if (silver.success) {
                    let p = silver.price.replace(/[^\\d,]/g, '');
                    silverPrice = parseFloat(p.replace(',', '.'));
                    document.getElementById('silverPrice').textContent = silver.price;
                }
                
                if (table.success) {
                    tableData = table.data;
                    renderHistory();
                }
                
                document.getElementById('updateInfo').textContent = 
                    `Son güncelleme: ${new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'})}`;
                
                updatePortfolio();
                
            } catch (error) {
                document.getElementById('updateInfo').textContent = 'Güncelleme hatası';
            } finally {
                setTimeout(() => btn.classList.remove('spinning'), 500);
            }
        }

        function renderHistory() {
            if (currentTab === 'stats') {
                updateStatsSection();
                return;
            }
            
            const data = tableData[currentTab] || [];
            const section = document.getElementById(currentTab + 'Section');
            
            if (data.length === 0) {
                section.innerHTML = '<div class="loading"><div>Veri bulunamadı</div></div>';
                return;
            }

            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            let maxPortfolioValue = 0;
            let peakIndices = [];
            
            if (goldAmount > 0 || silverAmount > 0) {
                data.forEach((item, index) => {
                    const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                    
                    if (portfolioValue > maxPortfolioValue) {
                        maxPortfolioValue = portfolioValue;
                        peakIndices = [index];
                    } else if (portfolioValue === maxPortfolioValue && portfolioValue > 0) {
                        peakIndices.push(index);
                    }
                });
            }

            let html = '';
            data.forEach((item, index) => {
                const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                const isPeak = peakIndices.includes(index) && maxPortfolioValue > 0;
                
                const changeClass = item.change_percent > 0 ? 'positive' : 
                                  item.change_percent < 0 ? 'negative' : 'neutral';
                const changeText = item.change_percent === 0 ? '0.00%' : 
                                 (item.change_percent > 0 ? '+' : '') + item.change_percent.toFixed(2) + '%';

                html += `
                    <div class="history-item ${isPeak ? 'peak' : ''}">
                        <div class="history-header">
                            <div class="history-time">${item.time}</div>
                            <div class="history-portfolio">${portfolioValue > 0 ? formatCurrency(portfolioValue) : '-'}</div>
                        </div>
                        <div class="history-footer">
                            <div class="history-metals">
                                <div class="history-metal">Altın: <span>${formatPrice(item.gold_price)}</span></div>
                                <div class="history-metal">Gümüş: <span>${formatPrice(item.silver_price)}</span></div>
                            </div>
                            <div class="history-change ${changeClass}">${changeText}</div>
                        </div>
                    </div>
                `;
            });
            
            section.innerHTML = html;
        }

        function updateStatsSection() {
            const dailyData = tableData.daily || [];
            const weeklyData = tableData.weekly || [];
            
            if (dailyData.length === 0 && weeklyData.length === 0) return;
            
            // Son 7 günün verilerini al
            const recent7Days = [...dailyData, ...weeklyData]
                .sort((a, b) => new Date(b.time) - new Date(a.time))
                .slice(0, 7);
            
            if (recent7Days.length < 2) return;
            
            // İstatistikleri hesapla
            const prices = recent7Days.map(d => d.gold_price);
            const highest = Math.max(...prices);
            const lowest = Math.min(...prices);
            const firstPrice = recent7Days[recent7Days.length - 1].gold_price;
            const lastPrice = recent7Days[0].gold_price;
            const weeklyChangePercent = ((lastPrice - firstPrice) / firstPrice) * 100;
            
            // Volatilite hesapla
            const avgPrice = prices.reduce((sum, p) => sum + p, 0) / prices.length;
            const variance = prices.reduce((sum, p) => sum + Math.pow(p - avgPrice, 2), 0) / prices.length;
            const volatility = Math.sqrt(variance) / avgPrice * 100;
            
            // En büyük günlük değişimleri bul
            let maxDailyChange = 0;
            let minDailyChange = 0;
            let avgDailyChange = 0;
            let changeCount = 0;
            
            for (let i = 0; i < recent7Days.length - 1; i++) {
                const change = ((recent7Days[i].gold_price - recent7Days[i + 1].gold_price) / recent7Days[i + 1].gold_price) * 100;
                maxDailyChange = Math.max(maxDailyChange, change);
                minDailyChange = Math.min(minDailyChange, change);
                avgDailyChange += change;
                changeCount++;
            }
            avgDailyChange = changeCount > 0 ? avgDailyChange / changeCount : 0;
            
            // Değerleri güncelle
            document.getElementById('weeklyChange').textContent = 
                (weeklyChangePercent >= 0 ? '+' : '') + weeklyChangePercent.toFixed(1) + '%';
            document.getElementById('volatility').textContent = volatility.toFixed(1) + '%';
            document.getElementById('weeklyHigh').textContent = formatPrice(highest).replace(' ₺', '₺');
            document.getElementById('weeklyLow').textContent = formatPrice(lowest).replace(' ₺', '₺');
            
            // Mini grafik güncelle
            updateMiniChart(prices.reverse());
        }

        function updateMiniChart(prices) {
            const chartPoints = document.getElementById('chartPoints');
            if (!chartPoints || prices.length === 0) return;
            
            const minPrice = Math.min(...prices);
            const maxPrice = Math.max(...prices);
            const priceRange = maxPrice - minPrice;
            
            let html = '';
            prices.forEach(price => {
                const heightPercent = priceRange > 0 ? 
                    20 + ((price - minPrice) / priceRange) * 70 : 50;
                html += `<div class="chart-point" style="height: ${heightPercent}%;"></div>`;
            });
            
            chartPoints.innerHTML = html;
        }

        function switchTab(tab) {
            currentTab = tab;
            
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tab + 'Tab').classList.add('active');
            
            document.querySelectorAll('.history-section').forEach(s => s.classList.remove('active'));
            document.getElementById(tab + 'Section').classList.add('active');
            
            renderHistory();
        }

        function updatePortfolio() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            const goldValue = goldAmount * goldPrice;
            const silverValue = silverAmount * silverPrice;
            const totalValue = goldValue + silverValue;
            
            const portfolioCard = document.getElementById('portfolioCard');
            
            if (totalValue > 0) {
                portfolioCard.classList.add('active');
                
                document.getElementById('portfolioTotal').textContent = formatCurrency(totalValue);
                document.getElementById('goldPortfolio').textContent = formatCurrency(goldValue);
                document.getElementById('silverPortfolio').textContent = formatCurrency(silverValue);
                
                renderHistory();
            } else {
                portfolioCard.classList.remove('active');
                renderHistory();
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

        function openPortfolio() {
            document.getElementById('portfolioModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('portfolioModal').classList.remove('active');
        }

        function saveAndClose() {
            savePortfolio();
            closeModal();
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

        function formatCurrency(amount) {
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount) + ' ₺';
        }

        function formatPrice(price) {
            if (!price) return '0,00 ₺';
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(price) + ' ₺';
        }

        document.getElementById('portfolioModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        window.onload = function() {
            loadPortfolio();
            fetchData();
            updatePortfolio();
        };
    </script>
</body>
</html>'''

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