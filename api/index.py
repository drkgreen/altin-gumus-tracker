#!/usr/bin/env python3
"""
Metal Price Tracker Web App v3.1 - Scroll Kaldırıldı
Flask web uygulaması - Şifre korumalı
"""
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
CORS(app)

def load_portfolio_config():
    try:
        with open('portfolio-config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}

def verify_password(password):
    try:
        config = load_portfolio_config()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == config.get("password_hash", "")
    except:
        return False

def load_price_history():
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/data/price-history.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"records": []}
    except:
        return {"records": []}

def get_hourly_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        if not records:
            return []
        
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        hourly_data = []
        
        # SADECE BUGÜNKÜ saatlik kayıtları al
        today_records = [r for r in records if r.get("date") == today and not r.get("optimized", False) and r.get("gold_price") and r.get("silver_price")]
        
        if today_records:
            sorted_records = sorted(today_records, key=lambda x: x.get("timestamp", 0))
            for i, record in enumerate(sorted_records):
                timestamp = record.get("timestamp", 0)
                local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
                time_label = local_time.strftime("%H:%M")
                change_percent = 0
                if i > 0:
                    prev_record = sorted_records[i - 1]
                    if prev_record and prev_record.get("gold_price"):
                        price_diff = record["gold_price"] - prev_record["gold_price"]
                        change_percent = (price_diff / prev_record["gold_price"]) * 100
                hourly_data.append({
                    "time": time_label,
                    "gold_price": record["gold_price"],
                    "silver_price": record["silver_price"],
                    "change_percent": change_percent,
                    "optimized": False,
                    "is_peak": False
                })
        return hourly_data
    except:
        return []

def get_daily_optimized_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        if not records:
            return []
        
        # TÜM daily_peak kayıtları al
        daily_peaks = [r for r in records if r.get("daily_peak") == True]
        daily_data = []
        
        # Tarihe göre sırala
        sorted_peaks = sorted(daily_peaks, key=lambda x: x.get("date", ""))
        
        for i, day_record in enumerate(sorted_peaks):
            day_date = datetime.strptime(day_record["date"], "%Y-%m-%d")
            day_name = day_date.strftime("%d.%m.%Y")
            
            change_percent = 0
            if i > 0:
                prev_day = sorted_peaks[i-1]
                if prev_day["gold_price"] > 0:
                    price_diff = day_record["gold_price"] - prev_day["gold_price"]
                    change_percent = (price_diff / prev_day["gold_price"]) * 100
            
            daily_data.append({
                "time": day_name,
                "gold_price": day_record["gold_price"],
                "silver_price": day_record["silver_price"],
                "change_percent": change_percent,
                "optimized": True,
                "peak_time": day_record.get("peak_time", "unknown"),
                "portfolio_value": day_record.get("portfolio_value", 0),
                "is_peak": True
            })
        
        return daily_data
    except:
        return []

def get_monthly_optimized_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        if not records:
            return []
        monthly_peaks = [r for r in records if r.get("monthly_peak") == True]
        monthly_data = []
        monthly_temp = []
        now = datetime.now(timezone.utc)
        for i in range(11, -1, -1):
            target_month = (now - timedelta(days=i*30)).strftime("%Y-%m")
            month_record = next((r for r in monthly_peaks if r.get("date", "").startswith(target_month)), None)
            if month_record:
                month_date = datetime.strptime(month_record["date"], "%Y-%m-%d")
                month_names = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
                month_label = f"{month_names[month_date.month]} {month_date.year}"
                monthly_temp.append({
                    "time": month_label,
                    "gold_price": month_record["gold_price"],
                    "silver_price": month_record["silver_price"],
                    "peak_time": month_record.get("peak_time", "unknown"),
                    "peak_date": month_record.get("date", "unknown"),
                    "portfolio_value": month_record.get("portfolio_value", 0)
                })
        for i, month_data in enumerate(monthly_temp):
            change_percent = 0
            if i > 0:
                prev_month = monthly_temp[i-1]
                if prev_month["gold_price"] > 0:
                    price_diff = month_data["gold_price"] - prev_month["gold_price"]
                    change_percent = (price_diff / prev_month["gold_price"]) * 100
            monthly_data.append({
                "time": month_data['time'],
                "gold_price": month_data["gold_price"],
                "silver_price": month_data["silver_price"],
                "change_percent": change_percent,
                "optimized": True,
                "peak_time": month_data["peak_time"],
                "peak_date": month_data["peak_date"],
                "portfolio_value": month_data["portfolio_value"],
                "is_peak": True
            })
        return monthly_data
    except:
        return []

def get_table_data():
    try:
        return {
            "hourly": get_hourly_data(),
            "daily": get_daily_optimized_data(),
            "monthly": get_monthly_optimized_data()
        }
    except:
        return {"hourly": [], "daily": [], "monthly": []}

def get_gold_price():
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        price_element = soup.find('span', {'data-socket-key': '6-gram-altin', 'data-socket-attr': 'bid'})
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
        price_element = soup.find('span', {'data-socket-key': '5-gumus', 'data-socket-attr': 'bid'})
        if price_element:
            return price_element.get_text(strip=True)
        return None
    except Exception as e:
        raise Exception(f"Silver price error: {str(e)}")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Metal Tracker v3.1</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);background-attachment:fixed;min-height:100vh;padding:0;color:#e2e8f0}
.container{max-width:100%;margin:0 auto;display:flex;flex-direction:column;gap:0;padding:0;padding-top:80px;min-height:100vh}
.header{position:fixed;top:0;left:0;right:0;width:100%;display:flex;justify-content:space-between;align-items:center;background:rgba(15,23,42,0.95);backdrop-filter:blur(20px);border-bottom:1px solid rgba(59,130,246,0.2);padding:16px 20px;box-shadow:0 4px 20px rgba(0,0,0,0.4);z-index:1000}
.header-left{display:flex;align-items:center;gap:12px}
.header-center{flex:1;display:flex;justify-content:center}
.logo{font-size:16px;font-weight:700;color:#60a5fa;white-space:nowrap}
.version{font-size:9px;color:#60a5fa;background:rgba(59,130,246,0.2);padding:3px 6px;border-radius:6px}
.update-time{font-size:14px;color:#60a5fa;font-weight:600;background:rgba(59,130,246,0.15);padding:6px 12px;border-radius:8px;border:1px solid rgba(59,130,246,0.3);white-space:nowrap}
.actions{display:flex;gap:8px}
.action-btn{width:36px;height:36px;border-radius:8px;background:rgba(15,23,42,0.6);border:1px solid rgba(59,130,246,0.3);color:#60a5fa;font-size:14px;cursor:pointer;transition:all 0.3s;display:flex;align-items:center;justify-content:center}
.action-btn:hover{background:rgba(59,130,246,0.2);transform:translateY(-1px)}
.portfolio-summary{background:rgba(15,23,42,0.6);backdrop-filter:blur(20px);border-bottom:1px solid rgba(59,130,246,0.2);padding:20px 2px;box-shadow:0 4px 20px rgba(0,0,0,0.3);text-align:center}
.portfolio-amount{font-size:33px;font-weight:800;margin-bottom:20px;color:#60a5fa;white-space:nowrap}
.portfolio-metals{display:flex;gap:0;margin-top:16px}
.metal-item{flex:1;background:transparent;border:none;border-radius:0;padding:18px 12px;min-height:120px;text-align:center;transition:all 0.3s;position:relative}
.metal-item:not(:last-child)::after{content:'';position:absolute;right:0;top:10%;height:80%;width:1px;background:rgba(59,130,246,0.3)}
.metal-item:hover{background:rgba(59,130,246,0.05);transform:none}
.metal-name{font-size:20px;font-weight:600;color:#60a5fa;margin-bottom:8px;white-space:nowrap}
.metal-amount{font-size:17px;color:rgba(226,232,240,0.7);margin-bottom:6px;white-space:nowrap}
.metal-price{font-size:17px;color:rgba(226,232,240,0.6);margin-bottom:8px;white-space:nowrap}
.metal-value{font-size:21px;font-weight:700;color:#e2e8f0;white-space:nowrap}
.statistics-section{margin-top:12px;display:none}
.statistics-grid{display:flex;gap:0}
.stat-item{flex:1;background:transparent;border:none;border-radius:0;padding:14px 8px;text-align:center;min-height:90px;display:flex;flex-direction:column;justify-content:center;transition:all 0.3s;position:relative}
.stat-item:not(:last-child)::after{content:'';position:absolute;right:0;top:10%;height:80%;width:1px;background:rgba(59,130,246,0.3)}
.stat-item:hover{background:rgba(59,130,246,0.05);transform:none}
.stat-title{font-size:10px;font-weight:600;color:#60a5fa;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stat-value{font-size:14px;font-weight:700;color:#e2e8f0;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stat-time{font-size:9px;color:rgba(226,232,240,0.6);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.price-history{background:rgba(15,23,42,0.6);backdrop-filter:blur(20px);padding:20px 2px;padding-bottom:20px;border-top:1px solid rgba(59,130,246,0.2)}
.history-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;gap:8px}
.history-title{font-size:14px;font-weight:600;color:#60a5fa;white-space:nowrap}
.period-tabs{display:flex;gap:3px;background:rgba(15,23,42,0.8);border:1px solid rgba(59,130,246,0.2);border-radius:8px;padding:3px}
.period-tab{padding:6px 10px;border:none;border-radius:6px;background:transparent;color:rgba(226,232,240,0.6);font-size:10px;font-weight:500;cursor:pointer;transition:all 0.3s;white-space:nowrap}
.period-tab.active{background:rgba(59,130,246,0.3);color:#60a5fa}
.charts-container{display:flex;flex-direction:column;gap:16px}
.chart-wrapper{background:rgba(15,23,42,0.4);border:1px solid rgba(59,130,246,0.15);border-radius:12px;padding:16px;position:relative}
.chart-content{display:flex;gap:8px;align-items:stretch}
.chart-y-axis{width:60px;flex-shrink:0;display:flex;flex-direction:column;justify-content:space-between;padding:10px 5px;font-size:9px;color:rgba(226,232,240,0.7)}
.y-axis-label{text-align:right;white-space:nowrap}
.chart-canvas-wrapper{flex:1;height:200px;position:relative}
.chart-canvas{width:100%!important;height:200px!important}
.chart-title{font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:12px;text-align:left}
.chart-title-value{color:#ef4444;font-weight:700}
.login-screen{position:fixed;top:0;left:0;width:100%;height:100%;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);display:flex;align-items:center;justify-content:center;z-index:2000}
.login-box{background:rgba(15,23,42,0.8);backdrop-filter:blur(20px);border:1px solid rgba(59,130,246,0.3);border-radius:20px;padding:32px;width:90%;max-width:360px;box-shadow:0 20px 60px rgba(0,0,0,0.5)}
.login-title{font-size:24px;font-weight:800;color:#60a5fa;text-align:center;margin-bottom:24px}
.login-input{width:100%;padding:14px 16px;background:rgba(15,23,42,0.8);border:1px solid rgba(59,130,246,0.3);border-radius:12px;font-size:16px;margin-bottom:16px;color:#e2e8f0;transition:all 0.3s}
.login-input:focus{outline:none;border-color:#60a5fa;background:rgba(15,23,42,0.9)}
.login-input::placeholder{color:rgba(226,232,240,0.5)}
.login-btn{width:100%;padding:14px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:white;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;transition:all 0.3s}
.login-btn:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(59,130,246,0.4)}
.login-error{color:#ef4444;text-align:center;margin-top:12px;font-size:14px;display:none}
@media (max-width:460px){
.container{max-width:100%;padding:0;padding-top:70px}
.header{top:0;left:0;right:0;width:100%;padding:12px 16px;border-radius:0}
.header-center{display:none}
.update-time{position:absolute;top:100%;left:50%;transform:translateX(-50%);margin-top:3px;font-size:11px;padding:4px 8px}
.history-header{flex-direction:column;gap:8px}
.period-tabs{justify-content:center}
.chart-y-axis{width:50px;font-size:8px;padding:5px 3px}
.chart-canvas-wrapper{height:180px}
.chart-canvas{height:180px!important}
.portfolio-summary{padding:16px 2px}
.price-history{padding:16px 2px}
}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="login-screen" id="loginScreen" style="display:none;">
<div class="login-box">
<div class="login-title">🔐 Metal Tracker v3.1</div>
<input type="password" class="login-input" id="passwordInput" placeholder="Şifre" onkeypress="if(event.key==='Enter')login()">
<button class="login-btn" onclick="login()">Giriş</button>
<div class="login-error" id="loginError">Hatalı şifre!</div>
</div>
</div>
<div class="loading-screen" id="loadingScreen">
<div style="text-align:center"><div style="width:32px;height:32px;border:3px solid rgba(96,165,250,0.3);border-top:3px solid #60a5fa;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 12px"></div><div style="color:#60a5fa;font-size:14px">Yükleniyor...</div></div>
</div>
<div class="container" id="mainApp" style="display:none;">
<div class="header">
<div class="header-left">
<div style="display:flex;align-items:center;gap:8px">
<div class="logo">Metal Tracker</div>
<div class="version">v3.1</div>
</div>
</div>
<div class="header-center">
<div class="update-time" id="headerTime">--:--</div>
</div>
<div class="actions">
<button class="action-btn" onclick="fetchPrice()" id="refreshBtn" title="Yenile">⟳</button>
<button class="action-btn" onclick="logout()" title="Çıkış">🚪</button>
</div>
</div>
<div class="portfolio-summary">
<div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
<div class="portfolio-metals">
<div class="metal-item">
<div class="metal-name">Altın</div>
<div class="metal-amount" id="goldAmount">0 gr</div>
<div class="metal-price" id="goldCurrentPrice">0,00 ₺/gr</div>
<div class="metal-value" id="goldPortfolioValue">0,00 ₺</div>
</div>
<div class="metal-item">
<div class="metal-name">Gümüş</div>
<div class="metal-amount" id="silverAmount">0 gr</div>
<div class="metal-price" id="silverCurrentPrice">0,00 ₺/gr</div>
<div class="metal-value" id="silverPortfolioValue">0,00 ₺</div>
</div>
</div>
<div class="statistics-section">
<div class="statistics-grid">
<div class="stat-item">
<div class="stat-title">En Yüksek Altın</div>
<div class="stat-value" id="highestGold">0,00 ₺</div>
<div class="stat-time" id="highestGoldTime">--:--</div>
</div>
<div class="stat-item">
<div class="stat-title">En Yüksek Gümüş</div>
<div class="stat-value" id="highestSilver">0,00 ₺</div>
<div class="stat-time" id="highestSilverTime">--:--</div>
</div>
<div class="stat-item">
<div class="stat-title">En Yüksek Portföy</div>
<div class="stat-value" id="highestPortfolio">0,00 ₺</div>
<div class="stat-time" id="highestPortfolioTime">--:--</div>
</div>
</div>
</div>
</div>
<div class="price-history">
<div class="history-header">
<div class="history-title">Fiyat Geçmişi</div>
<div class="period-tabs">
<button class="period-tab active" onclick="switchPeriod('hourly')" id="hourlyTab">Saatlik</button>
<button class="period-tab" onclick="switchPeriod('daily')" id="dailyTab">Günlük</button>
<button class="period-tab" onclick="switchPeriod('monthly')" id="monthlyTab">Aylık</button>
</div>
</div>
<div class="charts-container">
<div class="chart-wrapper">
<div class="chart-title">
Altın: <span class="chart-title-value" id="goldChartValue">--</span>
</div>
<div class="chart-content">
<div class="chart-y-axis" id="goldYAxis"></div>
<div class="chart-canvas-wrapper">
<canvas id="goldChart" class="chart-canvas"></canvas>
</div>
</div>
</div>
<div class="chart-wrapper">
<div class="chart-title">
Gümüş: <span class="chart-title-value" id="silverChartValue">--</span>
</div>
<div class="chart-content">
<div class="chart-y-axis" id="silverYAxis"></div>
<div class="chart-canvas-wrapper">
<canvas id="silverChart" class="chart-canvas"></canvas>
</div>
</div>
</div>
<div class="chart-wrapper">
<div class="chart-title">
Portföy: <span class="chart-title-value" id="portfolioChartValue">--</span>
</div>
<div class="chart-content">
<div class="chart-y-axis" id="portfolioYAxis"></div>
<div class="chart-canvas-wrapper">
<canvas id="portfolioChart" class="chart-canvas"></canvas>
</div>
</div>
</div>
</div>
</div>
</div>
<script>
let currentGoldPrice = 0;
let currentSilverPrice = 0;
let tableData = {};
let currentPeriod = 'hourly';
let goldAmount = 0;
let silverAmount = 0;
let goldChart = null;
let silverChart = null;
let portfolioChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    const token = localStorage.getItem('auth_token');
    const expiry = localStorage.getItem('auth_expiry');
    
    if (token && expiry && new Date().getTime() < parseInt(expiry)) {
        try {
            const response = await fetch('/api/verify-session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token: token})
            });
            const data = await response.json();
            if (data.valid) {
                showMainApp();
                await loadPortfolioConfig();
                await fetchPrice();
                return;
            }
        } catch (error) {
            console.error('Auth verification error:', error);
        }
    }
    showLoginScreen();
}

function showLoginScreen() {
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('mainApp').style.display = 'none';
}

function showMainApp() {
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('mainApp').style.display = 'flex';
}

async function login() {
    const password = document.getElementById('passwordInput').value;
    if (!password) return;
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: password})
        });
        const data = await response.json();
        
        if (data.success) {
            const expiry = new Date();
            expiry.setDate(expiry.getDate() + 30);
            document.cookie = `auth_token=${data.token}; expires=${expiry.toUTCString()}; path=/`;
            localStorage.setItem('auth_token', data.token);
            localStorage.setItem('auth_expiry', expiry.getTime());
            showMainApp();
            await loadPortfolioConfig();
            await fetchPrice();
        } else {
            document.getElementById('loginError').style.display = 'block';
            document.getElementById('passwordInput').value = '';
        }
    } catch (error) {
        document.getElementById('loginError').style.display = 'block';
    }
}

function logout() {
    document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_expiry');
    document.getElementById('passwordInput').value = '';
    document.getElementById('loginError').style.display = 'none';
    showLoginScreen();
}

async function loadPortfolioConfig() {
    try {
        const response = await fetch('/api/portfolio-config');
        const data = await response.json();
        if (data.success) {
            goldAmount = data.gold_amount;
            silverAmount = data.silver_amount;
        }
    } catch (error) {
        console.error('Portfolio config error:', error);
    }
}

async function fetchPrice() {
    const refreshBtn = document.getElementById('refreshBtn');
    try {
        refreshBtn.style.transform = 'rotate(360deg)';
        
        const [goldResponse, silverResponse, tableResponse] = await Promise.all([
            fetch('/api/gold-price'),
            fetch('/api/silver-price'),
            fetch('/api/table-data')
        ]);
        
        const goldData = await goldResponse.json();
        const silverData = await silverResponse.json();
        const tableDataResult = await tableResponse.json();
        
        if (goldData.success) {
            let cleaned = goldData.price.replace(/[^\d,]/g, '');
            currentGoldPrice = parseFloat(cleaned.replace(',', '.'));
        }
        
        if (silverData.success) {
            let cleaned = silverData.price.replace(/[^\d,]/g, '');
            currentSilverPrice = parseFloat(cleaned.replace(',', '.'));
        }
        
        if (tableDataResult.success) {
            tableData = tableDataResult.data;
            updateCharts();
        }
        
        document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        updatePortfolio();
    } catch (error) {
        console.error('Fetch price error:', error);
    } finally {
        setTimeout(() => refreshBtn.style.transform = 'rotate(0deg)', 500);
    }
}

function switchPeriod(period) {
    currentPeriod = period;
    document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(period + 'Tab').classList.add('active');
    updateCharts();
}

function updateCharts() {
    if (!tableData || !tableData[currentPeriod]) return;
    
    const data = tableData[currentPeriod];
    if (data.length === 0) return;
    
    const labels = data.map(item => item.time);
    const goldPrices = data.map(item => item.gold_price);
    const silverPrices = data.map(item => item.silver_price);
    const portfolioValues = data.map(item => (goldAmount * item.gold_price) + (silverAmount * item.silver_price));
    
    // En yüksek değerleri bul
    const maxGold = Math.max(...goldPrices);
    const maxSilver = Math.max(...silverPrices);
    const maxPortfolio = Math.max(...portfolioValues);
    
    // Başlıkları güncelle
    document.getElementById('goldChartValue').textContent = formatPrice(maxGold);
    document.getElementById('silverChartValue').textContent = formatPrice(maxSilver);
    document.getElementById('portfolioChartValue').textContent = formatCurrency(maxPortfolio);
    
    // 3 ayrı grafik oluştur (scroll kaldırıldı)
    createSingleChart('goldChart', 'goldYAxis', 'Altın', labels, goldPrices, '#fbbf24', false);
    createSingleChart('silverChart', 'silverYAxis', 'Gümüş', labels, silverPrices, '#94a3b8', false);
    createSingleChart('portfolioChart', 'portfolioYAxis', 'Portföy', labels, portfolioValues, '#60a5fa', true);
}

function createCustomYAxis(yAxisId, data, isPortfolio) {
    const yAxisElement = document.getElementById(yAxisId);
    if (!yAxisElement) return;
    
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min;
    const step = range / 5;
    
    const labels = [];
    for (let i = 5; i >= 0; i--) {
        const value = min + (step * i);
        if (isPortfolio) {
            labels.push(formatCurrency(value));
        } else {
            labels.push(formatPrice(value));
        }
    }
    
    yAxisElement.innerHTML = labels.map(label => 
        `<div class="y-axis-label">${label}</div>`
    ).join('');
}

function createSingleChart(canvasId, yAxisId, label, labels, data, color, isPortfolio) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    // Custom Y ekseni oluştur
    createCustomYAxis(yAxisId, data, isPortfolio);
    
    // Eski grafiği temizle
    if (canvasId === 'goldChart' && goldChart) {
        goldChart.destroy();
        goldChart = null;
    }
    if (canvasId === 'silverChart' && silverChart) {
        silverChart.destroy();
        silverChart = null;
    }
    if (canvasId === 'portfolioChart' && portfolioChart) {
        portfolioChart.destroy();
        portfolioChart = null;
    }
    
    // Gradient oluştur
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, color + 'AA');
    gradient.addColorStop(1, color + '10');
    
    const chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: color,
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHitRadius: 15,
                pointBackgroundColor: color,
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#60a5fa',
                    bodyColor: '#e2e8f0',
                    borderColor: 'rgba(59, 130, 246, 0.3)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        title: ctx => ctx[0].label,
                        label: ctx => {
                            const value = ctx.parsed.y;
                            let formatted;
                            if (isPortfolio) {
                                formatted = formatCurrency(value);
                            } else {
                                formatted = formatPrice(value);
                            }
                            return `${label}: ${formatted}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(59, 130, 246, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: 'rgba(226, 232, 240, 0.7)',
                        font: {
                            size: 10
                        },
                        maxRotation: 0,
                        autoSkip: true,
                        autoSkipPadding: 20,
                        maxTicksLimit: 8
                    }
                },
                y: {
                    display: false
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            }
        }
    });
    
    // Chart referansını sakla
    if (canvasId === 'goldChart') goldChart = chart;
    if (canvasId === 'silverChart') silverChart = chart;
    if (canvasId === 'portfolioChart') portfolioChart = chart;
}

function updatePortfolio() {
    const goldValue = goldAmount * currentGoldPrice;
    const silverValue = silverAmount * currentSilverPrice;
    const totalValue = goldValue + silverValue;
    
    document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
    document.getElementById('goldAmount').textContent = goldAmount + ' gr';
    document.getElementById('silverAmount').textContent = silverAmount + ' gr';
    document.getElementById('goldCurrentPrice').textContent = formatPrice(currentGoldPrice) + '/gr';
    document.getElementById('silverCurrentPrice').textContent = formatPrice(currentSilverPrice) + '/gr';
    document.getElementById('goldPortfolioValue').textContent = formatCurrency(goldValue);
    document.getElementById('silverPortfolioValue').textContent = formatCurrency(silverValue);
}

function formatCurrency(amount) {
    if (!amount || amount === 0) return '0,00 ₺';
    return new Intl.NumberFormat('tr-TR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount) + ' ₺';
}

function formatPrice(price) {
    if (!price || price === 0) return '0,00 ₺';
    return new Intl.NumberFormat('tr-TR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(price) + ' ₺';
}
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        password = data.get('password', '')
        if verify_password(password):
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            return jsonify({'success': True, 'token': password_hash})
        else:
            return jsonify({'success': False, 'error': 'Invalid password'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/verify-session', methods=['POST'])
def api_verify_session():
    try:
        data = request.get_json()
        token = data.get('token', '')
        config = load_portfolio_config()
        is_valid = token == config.get("password_hash", "")
        return jsonify({'valid': is_valid})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/api/portfolio-config')
def api_portfolio_config():
    try:
        config = load_portfolio_config()
        return jsonify({
            'success': True, 
            'gold_amount': config.get('gold_amount', 0), 
            'silver_amount': config.get('silver_amount', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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