#!/usr/bin/env python3
"""
Metal Price Tracker Web App v3.0 - Secure Version
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
        
        today_records = [r for r in records if r.get("date") == today and r.get("gold_price") and r.get("silver_price") and not r.get("optimized", False)]
        
        if today_records:
            sorted_records = sorted(today_records, key=lambda x: x.get("timestamp", 0), reverse=True)
            for i, record in enumerate(sorted_records):
                timestamp = record.get("timestamp", 0)
                local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
                time_label = local_time.strftime("%H:%M")
                change_percent = 0
                if i < len(sorted_records) - 1:
                    prev_record = sorted_records[i + 1]
                    if prev_record and prev_record.get("gold_price"):
                        price_diff = record["gold_price"] - prev_record["gold_price"]
                        change_percent = (price_diff / prev_record["gold_price"]) * 100
                hourly_data.append({"time": time_label, "gold_price": record["gold_price"], "silver_price": record["silver_price"], "change_percent": change_percent, "optimized": False})
        return hourly_data
    except:
        return []

def get_daily_optimized_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        if not records:
            return []
        daily_peaks = [r for r in records if r.get("daily_peak") == True]
        daily_data = []
        daily_temp = []
        now = datetime.now(timezone.utc)
        for i in range(6, -1, -1):
            target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            day_record = next((r for r in daily_peaks if r.get("date") == target_date), None)
            if day_record:
                day_name = (now - timedelta(days=i)).strftime("%d.%m")
                daily_temp.append({"time": day_name, "gold_price": day_record["gold_price"], "silver_price": day_record["silver_price"], "peak_time": day_record.get("peak_time", "unknown"), "portfolio_value": day_record.get("portfolio_value", 0)})
        for i, day_data in enumerate(daily_temp):
            change_percent = 0
            if i > 0:
                prev_day = daily_temp[i-1]
                if prev_day["gold_price"] > 0:
                    price_diff = day_data["gold_price"] - prev_day["gold_price"]
                    change_percent = (price_diff / prev_day["gold_price"]) * 100
            daily_data.append({"time": f"{day_data['time']}", "gold_price": day_data["gold_price"], "silver_price": day_data["silver_price"], "change_percent": change_percent, "optimized": True, "peak_time": day_data["peak_time"], "portfolio_value": day_data["portfolio_value"]})
        daily_data.reverse()
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
                monthly_temp.append({"time": month_label, "gold_price": month_record["gold_price"], "silver_price": month_record["silver_price"], "peak_time": month_record.get("peak_time", "unknown"), "peak_date": month_record.get("date", "unknown"), "portfolio_value": month_record.get("portfolio_value", 0)})
        for i, month_data in enumerate(monthly_temp):
            change_percent = 0
            if i > 0:
                prev_month = monthly_temp[i-1]
                if prev_month["gold_price"] > 0:
                    price_diff = month_data["gold_price"] - prev_month["gold_price"]
                    change_percent = (price_diff / prev_month["gold_price"]) * 100
            monthly_data.append({"time": f"{month_data['time']}", "gold_price": month_data["gold_price"], "silver_price": month_data["silver_price"], "change_percent": change_percent, "optimized": True, "peak_time": month_data["peak_time"], "peak_date": month_data["peak_date"], "portfolio_value": month_data["portfolio_value"]})
        monthly_data.reverse()
        return monthly_data
    except:
        return []

def get_table_data():
    try:
        return {"hourly": get_hourly_data(), "daily": get_daily_optimized_data(), "monthly": get_monthly_optimized_data()}
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
<title>Metal Tracker v3.0</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);background-attachment:fixed;min-height:100vh;padding:15px;color:#e2e8f0}
.container{max-width:440px;margin:0 auto;display:flex;flex-direction:column;gap:18px;padding:12px;padding-top:85px;min-height:100vh}
.header{position:fixed;top:15px;left:50%;transform:translateX(-50%);width:440px;display:flex;justify-content:space-between;align-items:center;background:rgba(15,23,42,0.8);backdrop-filter:blur(20px);border:1px solid rgba(59,130,246,0.2);border-radius:16px;padding:16px 20px;box-shadow:0 8px 32px rgba(0,0,0,0.4);z-index:1000}
.header-left{display:flex;align-items:center;gap:12px}
.header-center{flex:1;display:flex;justify-content:center}
.logo{font-size:16px;font-weight:700;color:#60a5fa;white-space:nowrap}
.version{font-size:9px;color:#60a5fa;background:rgba(59,130,246,0.2);padding:3px 6px;border-radius:6px}
.update-time{font-size:14px;color:#60a5fa;font-weight:600;background:rgba(59,130,246,0.15);padding:6px 12px;border-radius:8px;border:1px solid rgba(59,130,246,0.3);white-space:nowrap}
.actions{display:flex;gap:8px}
.action-btn{width:36px;height:36px;border-radius:8px;background:rgba(15,23,42,0.6);border:1px solid rgba(59,130,246,0.3);color:#60a5fa;font-size:14px;cursor:pointer;transition:all 0.3s;display:flex;align-items:center;justify-content:center}
.action-btn:hover{background:rgba(59,130,246,0.2);transform:translateY(-1px)}
.portfolio-summary{background:rgba(15,23,42,0.6);backdrop-filter:blur(20px);border:1px solid rgba(59,130,246,0.2);border-radius:20px;padding:20px;box-shadow:0 10px 40px rgba(0,0,0,0.3);text-align:center}
.portfolio-amount{font-size:28px;font-weight:800;margin-bottom:20px;color:#60a5fa;white-space:nowrap}
.portfolio-metals{display:flex;gap:10px;margin-top:16px}
.metal-item{flex:1;background:rgba(15,23,42,0.4);border:1px solid rgba(59,130,246,0.15);border-radius:12px;padding:18px 12px;min-height:120px;text-align:center;transition:all 0.3s}
.metal-item:hover{background:rgba(59,130,246,0.1);transform:translateY(-1px)}
.metal-name{font-size:15px;font-weight:600;color:#60a5fa;margin-bottom:8px;white-space:nowrap}
.metal-amount{font-size:12px;color:rgba(226,232,240,0.7);margin-bottom:6px;white-space:nowrap}
.metal-price{font-size:12px;color:rgba(226,232,240,0.6);margin-bottom:8px;white-space:nowrap}
.metal-value{font-size:16px;font-weight:700;color:#e2e8f0;white-space:nowrap}
.statistics-section{margin-top:12px}
.statistics-grid{display:flex;gap:6px}
.stat-item{flex:1;background:rgba(15,23,42,0.4);border:1px solid rgba(59,130,246,0.15);border-radius:12px;padding:14px 8px;text-align:center;min-height:90px;display:flex;flex-direction:column;justify-content:center;transition:all 0.3s}
.stat-item:hover{background:rgba(59,130,246,0.1);transform:translateY(-1px)}
.stat-title{font-size:10px;font-weight:600;color:#60a5fa;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stat-value{font-size:14px;font-weight:700;color:#e2e8f0;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stat-time{font-size:9px;color:rgba(226,232,240,0.6);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.price-history{background:rgba(15,23,42,0.6);backdrop-filter:blur(20px);border:1px solid rgba(59,130,246,0.2);border-radius:16px;padding:16px 8px;box-shadow:0 10px 40px rgba(0,0,0,0.3);margin:0 -4px;width:calc(100% + 8px)}
.history-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding:0 8px;gap:8px}
.history-title{font-size:14px;font-weight:600;color:#60a5fa;white-space:nowrap}
.period-tabs{display:flex;gap:3px;background:rgba(15,23,42,0.8);border:1px solid rgba(59,130,246,0.2);border-radius:8px;padding:3px}
.period-tab{padding:6px 10px;border:none;border-radius:6px;background:transparent;color:rgba(226,232,240,0.6);font-size:10px;font-weight:500;cursor:pointer;transition:all 0.3s;white-space:nowrap}
.period-tab.active{background:rgba(59,130,246,0.3);color:#60a5fa}
.price-table{overflow-x:auto;border-radius:12px;background:rgba(15,23,42,0.4);border:1px solid rgba(59,130,246,0.15);margin:0 6px;max-height:300px;overflow-y:auto}
.price-table table{width:100%;border-collapse:collapse}
.price-table thead{position:sticky;top:0;background:rgba(15,23,42,0.9);z-index:10}
.price-table th{background:rgba(15,23,42,0.9);padding:10px 6px;text-align:left;font-weight:600;color:#60a5fa;font-size:11px;border-bottom:1px solid rgba(59,130,246,0.2);white-space:nowrap}
.price-table td{padding:8px 6px;border-bottom:1px solid rgba(59,130,246,0.1);font-size:11px;color:rgba(226,232,240,0.8);white-space:nowrap}
.price-table tr:hover{background:rgba(59,130,246,0.05)}
.price-table .time{font-weight:600;color:#e2e8f0}
.price-table .price{font-weight:600;color:#60a5fa}
.price-table .portfolio{font-weight:700;color:#3b82f6}
.price-table .change{font-weight:600;font-size:10px}
.change.positive{color:#22c55e}
.change.negative{color:#ef4444}
.change.neutral{color:rgba(226,232,240,0.5)}
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
.container{max-width:95%;padding:8px;padding-top:75px}
.header{width:95%;top:8px;padding:12px 16px}
.header-center{display:none}
.update-time{position:absolute;top:100%;left:50%;transform:translateX(-50%);margin-top:3px;font-size:11px;padding:4px 8px}
.history-header{flex-direction:column;gap:8px}
.period-tabs{justify-content:center}
.price-table{margin:0 3px;max-height:250px}
}
</style>
</head>
<body>
<div class="login-screen" id="loginScreen" style="display:none;">
<div class="login-box">
<div class="login-title">🔐 Metal Tracker</div>
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
<div class="version">v3.0</div>
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
<tbody id="priceTableBody"></tbody>
</table>
</div>
</div>
</div>
<script>
let currentGoldPrice=0,currentSilverPrice=0,tableData={},currentPeriod='hourly',goldAmount=0,silverAmount=0;
document.addEventListener('DOMContentLoaded',function(){initializeApp()});
async function initializeApp(){const token=localStorage.getItem('auth_token'),expiry=localStorage.getItem('auth_expiry');if(token&&expiry&&new Date().getTime()<parseInt(expiry)){try{const response=await fetch('/api/verify-session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token})});const data=await response.json();if(data.valid){showMainApp();await loadPortfolioConfig();await fetchPrice();return}}catch(error){console.error('Auth verification error:',error)}}showLoginScreen()}
function showLoginScreen(){document.getElementById('loadingScreen').style.display='none';document.getElementById('loginScreen').style.display='flex';document.getElementById('mainApp').style.display='none'}
function showMainApp(){document.getElementById('loadingScreen').style.display='none';document.getElementById('loginScreen').style.display='none';document.getElementById('mainApp').style.display='flex'}
async function login(){const password=document.getElementById('passwordInput').value;if(!password)return;try{const response=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:password})});const data=await response.json();if(data.success){const expiry=new Date();expiry.setDate(expiry.getDate()+30);document.cookie=`auth_token=${data.token}; expires=${expiry.toUTCString()}; path=/`;localStorage.setItem('auth_token',data.token);localStorage.setItem('auth_expiry',expiry.getTime());showMainApp();await loadPortfolioConfig();await fetchPrice()}else{document.getElementById('loginError').style.display='block';document.getElementById('passwordInput').value=''}}catch(error){document.getElementById('loginError').style.display='block'}}
function logout(){document.cookie='auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';localStorage.removeItem('auth_token');localStorage.removeItem('auth_expiry');document.getElementById('passwordInput').value='';document.getElementById('loginError').style.display='none';showLoginScreen()}
async function loadPortfolioConfig(){try{const response=await fetch('/api/portfolio-config');const data=await response.json();if(data.success){goldAmount=data.gold_amount;silverAmount=data.silver_amount}}catch(error){console.error('Portfolio config error:',error)}}
async function fetchPrice(){const refreshBtn=document.getElementById('refreshBtn');try{refreshBtn.style.transform='rotate(360deg)';const[goldResponse,silverResponse,tableResponse]=await Promise.all([fetch('/api/gold-price'),fetch('/api/silver-price'),fetch('/api/table-data')]);const goldData=await goldResponse.json(),silverData=await silverResponse.json(),tableDataResult=await tableResponse.json();if(goldData.success){let cleaned=goldData.price.replace(/[^\d,]/g,'');currentGoldPrice=parseFloat(cleaned.replace(',','.'))}if(silverData.success){let cleaned=silverData.price.replace(/[^\d,]/g,'');currentSilverPrice=parseFloat(cleaned.replace(',','.'))}if(tableDataResult.success){tableData=tableDataResult.data;updateTable()}document.getElementById('headerTime').textContent=new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'});updatePortfolio()}catch(error){console.error('Fetch price error:',error)}finally{setTimeout(()=>refreshBtn.style.transform='rotate(0deg)',500)}}
function switchPeriod(period){currentPeriod=period;document.querySelectorAll('.period-tab').forEach(tab=>tab.classList.remove('active'));document.getElementById(period+'Tab').classList.add('active');const header=document.getElementById('timeHeader');if(period==='hourly')header.textContent='Saat';else if(period==='daily')header.textContent='Tarih';else if(period==='monthly')header.textContent='Ay';updateTable()}
function updateTable(){if(!tableData||!tableData[currentPeriod])return;const tbody=document.getElementById('priceTableBody');tbody.innerHTML='';updateStatistics();tableData[currentPeriod].forEach((item,index)=>{let portfolioValue=(goldAmount*item.gold_price)+(silverAmount*item.silver_price);const row=document.createElement('tr');const timeDisplay=item.optimized?`<span title="Peak değer (${item.peak_time||'bilinmiyor'})">${item.time}</span>`:item.time;row.innerHTML=`<td class="time">${timeDisplay}</td><td class="price">${formatPrice(item.gold_price)}</td><td class="price">${formatPrice(item.silver_price)}</td><td class="portfolio">${portfolioValue>0?formatCurrency(portfolioValue):'-'}</td><td class="change ${getChangeClass(item.change_percent)}">${formatChange(item.change_percent)}</td>`;tbody.appendChild(row)})}
function updateStatistics(){if(!tableData||!tableData[currentPeriod]||tableData[currentPeriod].length===0){document.getElementById('highestGold').textContent='0,00 ₺';document.getElementById('highestGoldTime').textContent='--:--';document.getElementById('highestSilver').textContent='0,00 ₺';document.getElementById('highestSilverTime').textContent='--:--';document.getElementById('highestPortfolio').textContent='0,00 ₺';document.getElementById('highestPortfolioTime').textContent='--:--';return}let highestGold={price:0,time:''},highestSilver={price:0,time:''},highestPortfolio={value:0,time:''};tableData[currentPeriod].forEach(item=>{if(item.gold_price>highestGold.price){highestGold={price:item.gold_price,time:item.time}}if(item.silver_price>highestSilver.price){highestSilver={price:item.silver_price,time:item.time}}if(goldAmount>0||silverAmount>0){const portfolioValue=(goldAmount*item.gold_price)+(silverAmount*item.silver_price);if(portfolioValue>highestPortfolio.value){highestPortfolio={value:portfolioValue,time:item.time}}}});document.getElementById('highestGold').textContent=formatPrice(highestGold.price);document.getElementById('highestGoldTime').textContent=highestGold.time||'--:--';document.getElementById('highestSilver').textContent=formatPrice(highestSilver.price);document.getElementById('highestSilverTime').textContent=highestSilver.time||'--:--';if(highestPortfolio.value>0){document.getElementById('highestPortfolio').textContent=formatCurrency(highestPortfolio.value);document.getElementById('highestPortfolioTime').textContent=highestPortfolio.time||'--:--'}else{document.getElementById('highestPortfolio').textContent='0,00 ₺';document.getElementById('highestPortfolioTime').textContent='--:--'}}
function getChangeClass(changePercent){if(changePercent>0)return 'positive';if(changePercent<0)return 'negative';return 'neutral'}
function formatChange(changePercent){if(changePercent===0)return '0.00%';const sign=changePercent>0?'+':'';return `${sign}${changePercent.toFixed(2)}%`}
function updatePortfolio(){const goldValue=goldAmount*currentGoldPrice,silverValue=silverAmount*currentSilverPrice,totalValue=goldValue+silverValue;document.getElementById('totalAmount').textContent=formatCurrency(totalValue);document.getElementById('goldAmount').textContent=goldAmount+' gr';document.getElementById('silverAmount').textContent=silverAmount+' gr';document.getElementById('goldCurrentPrice').textContent=formatPrice(currentGoldPrice)+'/gr';document.getElementById('silverCurrentPrice').textContent=formatPrice(currentSilverPrice)+'/gr';document.getElementById('goldPortfolioValue').textContent=formatCurrency(goldValue);document.getElementById('silverPortfolioValue').textContent=formatCurrency(silverValue);updateTable()}
function formatCurrency(amount){if(!amount||amount===0)return '0,00 ₺';return new Intl.NumberFormat('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(amount)+' ₺'}
function formatPrice(price){if(!price||price===0)return '0,00 ₺';return new Intl.NumberFormat('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(price)+' ₺'}
</script>
<style>@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style>
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