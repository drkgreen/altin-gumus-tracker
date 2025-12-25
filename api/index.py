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
            daily_data.append({"time": f"{day_data['time']} 📊", "gold_price": day_data["gold_price"], "silver_price": day_data["silver_price"], "change_percent": change_percent, "optimized": True, "peak_time": day_data["peak_time"], "portfolio_value": day_data["portfolio_value"]})
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
            monthly_data.append({"time": f"{month_data['time']} 🏆", "gold_price": month_data["gold_price"], "silver_price": month_data["silver_price"], "change_percent": change_percent, "optimized": True, "peak_time": month_data["peak_time"], "peak_date": month_data["peak_date"], "portfolio_value": month_data["portfolio_value"]})
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

body{
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:linear-gradient(135deg,#0a0a0a 0%,#1a1a1a 25%,#0d1b2a 50%,#1a1a1a 75%,#0a0a0a 100%);
background-attachment:fixed;
min-height:100vh;
padding:20px;
color:#e0e0e0;
overflow-x:hidden;
}

body::before{
content:'';
position:fixed;
top:0;
left:0;
width:100%;
height:100%;
background:radial-gradient(circle at 20% 80%,rgba(16,185,129,0.15) 0%,transparent 50%),
radial-gradient(circle at 80% 20%,rgba(6,182,212,0.1) 0%,transparent 50%),
radial-gradient(circle at 40% 40%,rgba(16,185,129,0.08) 0%,transparent 50%);
pointer-events:none;
z-index:-1;
}

.container{
max-width:480px;
margin:0 auto;
display:flex;
flex-direction:column;
gap:24px;
padding:0 4px;
position:relative;
z-index:1;
}

.login-screen{
position:fixed;
top:0;
left:0;
width:100%;
height:100%;
background:linear-gradient(135deg,#0a0a0a 0%,#1a1a1a 25%,#0d1b2a 50%,#1a1a1a 75%,#0a0a0a 100%);
display:flex;
align-items:center;
justify-content:center;
z-index:2000;
backdrop-filter:blur(20px);
}

.login-box{
background:rgba(255,255,255,0.05);
backdrop-filter:blur(30px);
border:1px solid rgba(16,185,129,0.3);
border-radius:24px;
padding:40px;
width:90%;
max-width:400px;
box-shadow:0 25px 80px rgba(0,0,0,0.5),
inset 0 1px 0 rgba(255,255,255,0.1);
}

.login-title{
font-size:28px;
font-weight:800;
color:#10b981;
text-align:center;
margin-bottom:30px;
text-shadow:0 0 20px rgba(16,185,129,0.5);
}

.login-input{
width:100%;
padding:16px 20px;
background:rgba(255,255,255,0.08);
backdrop-filter:blur(20px);
border:1px solid rgba(16,185,129,0.2);
border-radius:16px;
font-size:17px;
margin-bottom:20px;
font-weight:500;
color:#e0e0e0;
transition:all 0.3s ease;
}

.login-input:focus{
outline:none;
border-color:#10b981;
box-shadow:0 0 0 3px rgba(16,185,129,0.2);
background:rgba(255,255,255,0.12);
}

.login-input::placeholder{
color:rgba(224,224,224,0.6);
}

.login-btn{
width:100%;
padding:16px;
background:linear-gradient(135deg,#10b981 0%,#059669 100%);
color:white;
border:none;
border-radius:16px;
font-size:17px;
font-weight:700;
cursor:pointer;
transition:all 0.3s ease;
box-shadow:0 8px 25px rgba(16,185,129,0.3);
}

.login-btn:hover{
background:linear-gradient(135deg,#059669 0%,#047857 100%);
transform:translateY(-2px);
box-shadow:0 12px 35px rgba(16,185,129,0.4);
}

.login-error{
color:#ef4444;
text-align:center;
margin-top:15px;
font-size:14px;
font-weight:600;
display:none;
}

.header{
display:flex;
justify-content:space-between;
align-items:center;
background:rgba(255,255,255,0.05);
backdrop-filter:blur(30px);
border:1px solid rgba(16,185,129,0.2);
border-radius:20px;
padding:20px 24px;
box-shadow:0 8px 32px rgba(0,0,0,0.3),
inset 0 1px 0 rgba(255,255,255,0.1);
}

.header-left{
display:flex;
align-items:center;
gap:16px;
}

.logo{
font-size:20px;
font-weight:800;
color:#10b981;
text-shadow:0 0 15px rgba(16,185,129,0.6);
}

.version{
font-size:11px;
color:rgba(16,185,129,0.8);
background:rgba(16,185,129,0.15);
padding:4px 10px;
border-radius:10px;
border:1px solid rgba(16,185,129,0.2);
}

.update-time{
font-size:14px;
color:rgba(224,224,224,0.8);
font-weight:500;
}

.actions{
display:flex;
gap:12px;
}

.action-btn{
width:48px;
height:48px;
border-radius:14px;
background:rgba(255,255,255,0.08);
backdrop-filter:blur(20px);
border:1px solid rgba(16,185,129,0.2);
color:#10b981;
font-size:18px;
cursor:pointer;
transition:all 0.3s ease;
display:flex;
align-items:center;
justify-content:center;
}

.action-btn:hover{
background:rgba(16,185,129,0.2);
border-color:#10b981;
transform:translateY(-2px);
box-shadow:0 8px 20px rgba(16,185,129,0.3);
}

.portfolio-summary{
background:rgba(255,255,255,0.05);
backdrop-filter:blur(30px);
border:1px solid rgba(16,185,129,0.3);
border-radius:24px;
padding:28px 24px;
color:#e0e0e0;
box-shadow:0 15px 50px rgba(0,0,0,0.4),
inset 0 1px 0 rgba(255,255,255,0.1);
text-align:center;
position:relative;
overflow:hidden;
}

.portfolio-summary::before{
content:'';
position:absolute;
top:-50%;
left:-50%;
width:200%;
height:200%;
background:radial-gradient(circle,rgba(16,185,129,0.1) 0%,transparent 50%);
animation:pulse 4s ease-in-out infinite;
pointer-events:none;
}

@keyframes pulse{
0%,100%{opacity:0.3}
50%{opacity:0.8}
}

.portfolio-amount{
font-size:44px;
font-weight:900;
margin-bottom:24px;
color:#10b981;
text-shadow:0 0 20px rgba(16,185,129,0.5);
position:relative;
z-index:2;
}

.portfolio-metals{
display:flex;
justify-content:center;
gap:16px;
margin:24px 0 0 0;
position:relative;
z-index:2;
}

.metal-item{
flex:1;
background:rgba(255,255,255,0.08);
backdrop-filter:blur(20px);
border:1px solid rgba(16,185,129,0.2);
border-radius:18px;
padding:20px 16px;
min-height:160px;
transition:all 0.3s ease;
}

.metal-item:hover{
background:rgba(255,255,255,0.12);
border-color:rgba(16,185,129,0.4);
transform:translateY(-2px);
}

.metal-header{
display:flex;
align-items:center;
justify-content:center;
gap:8px;
margin-bottom:16px;
}

.metal-name{
font-size:18px;
font-weight:700;
color:#10b981;
}

.metal-amount{
font-size:14px;
color:rgba(224,224,224,0.8);
margin-bottom:8px;
font-weight:500;
}

.metal-price{
font-size:15px;
color:rgba(224,224,224,0.7);
margin-bottom:12px;
}

.metal-value{
font-size:22px;
font-weight:700;
color:#e0e0e0;
}

.price-history{
background:rgba(255,255,255,0.05);
backdrop-filter:blur(30px);
border:1px solid rgba(16,185,129,0.2);
border-radius:20px;
padding:20px 8px;
box-shadow:0 15px 50px rgba(0,0,0,0.4),
inset 0 1px 0 rgba(255,255,255,0.1);
margin:0 -8px;
width:calc(100% + 16px);
}

.history-header{
display:flex;
justify-content:space-between;
align-items:center;
margin-bottom:20px;
padding:0 16px;
}

.history-title{
font-size:20px;
font-weight:700;
color:#10b981;
}

.period-tabs{
display:flex;
gap:6px;
background:rgba(255,255,255,0.05);
backdrop-filter:blur(20px);
border:1px solid rgba(16,185,129,0.2);
border-radius:12px;
padding:6px;
}

.period-tab{
padding:10px 16px;
border:none;
border-radius:8px;
background:transparent;
color:rgba(224,224,224,0.7);
font-size:13px;
font-weight:600;
cursor:pointer;
transition:all 0.3s ease;
}

.period-tab.active{
background:rgba(16,185,129,0.2);
color:#10b981;
box-shadow:0 2px 8px rgba(16,185,129,0.3);
}

.price-table{
overflow-x:auto;
border-radius:14px;
background:rgba(255,255,255,0.03);
backdrop-filter:blur(20px);
border:1px solid rgba(16,185,129,0.15);
margin:0 12px;
}

.price-table table{
width:100%;
border-collapse:collapse;
}

.price-table th{
background:rgba(255,255,255,0.08);
backdrop-filter:blur(20px);
padding:14px 10px;
text-align:left;
font-weight:600;
color:#10b981;
font-size:13px;
border-bottom:1px solid rgba(16,185,129,0.2);
white-space:nowrap;
}

.price-table td{
padding:14px 10px;
border-bottom:1px solid rgba(255,255,255,0.05);
font-size:13px;
color:rgba(224,224,224,0.9);
white-space:nowrap;
transition:all 0.3s ease;
}

.price-table tr:hover{
background:rgba(16,185,129,0.05);
}

.price-table .time{
font-weight:600;
color:#e0e0e0;
}

.price-table .price{
font-weight:600;
color:#10b981;
}

.price-table .portfolio{
font-weight:700;
color:#06d6a0;
}

.price-table .change{
font-weight:600;
font-size:13px;
}

.change.positive{
color:#10b981;
text-shadow:0 0 5px rgba(16,185,129,0.5);
}

.change.negative{
color:#ef4444;
text-shadow:0 0 5px rgba(239,68,68,0.5);
}

.change.neutral{
color:rgba(224,224,224,0.6);
}

.peak-row{
background:rgba(16,185,129,0.1)!important;
border-left:3px solid #10b981;
box-shadow:inset 0 0 20px rgba(16,185,129,0.2);
animation:peakPulse 3s ease-in-out infinite;
}

@keyframes peakPulse{
0%,100%{background:rgba(16,185,129,0.1)!important}
50%{background:rgba(16,185,129,0.2)!important}
}

@media (max-width:400px){
.container{
max-width:100%;
padding:0 2px;
gap:20px;
}

.history-header{
flex-direction:column;
gap:14px;
}

.portfolio-metals{
flex-direction:column;
gap:14px;
}

.metal-name{
font-size:17px;
}

.metal-amount{
font-size:13px;
}

.metal-price{
font-size:14px;
}

.metal-value{
font-size:20px;
}

.metal-item{
padding:18px;
min-height:140px;
}

.price-table th,.price-table td{
padding:12px 8px;
font-size:12px;
}

.price-history{
padding:16px 6px;
margin:0 -6px;
width:calc(100% + 12px);
}

.price-table{
margin:0 8px;
}

.history-header{
padding:0 10px;
}

.period-tabs{
flex-wrap:wrap;
}

.period-tab{
font-size:12px;
padding:8px 12px;
}

.header{
padding:16px 20px;
}

.portfolio-amount{
font-size:36px;
}

.portfolio-summary{
padding:24px 20px;
}
}
</style>
</head>
<body>
<div class="login-screen" id="loginScreen">
<div class="login-box">
<div class="login-title">🔐 Metal Tracker</div>
<input type="password" class="login-input" id="passwordInput" placeholder="Şifre" onkeypress="if(event.key==='Enter')login()">
<button class="login-btn" onclick="login()">Giriş</button>
<div class="login-error" id="loginError">Hatalı şifre!</div>
</div>
</div>
<div class="container" id="mainApp" style="display:none;">
<div class="header">
<div class="header-left">
<div><div class="logo">Metal Tracker</div><div class="version">v3.0</div></div>
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
<div class="metal-header"><div class="metal-name">🥇 Altın</div></div>
<div class="metal-amount" id="goldAmount">0 gr</div>
<div class="metal-price" id="goldCurrentPrice">0,00 ₺/gr</div>
<div class="metal-value" id="goldPortfolioValue">0,00 ₺</div>
</div>
<div class="metal-item">
<div class="metal-header"><div class="metal-name">🥈 Gümüş</div></div>
<div class="metal-amount" id="silverAmount">0 gr</div>
<div class="metal-price" id="silverCurrentPrice">0,00 ₺/gr</div>
<div class="metal-value" id="silverPortfolioValue">0,00 ₺</div>
</div>
</div>
</div>
<div class="price-history">
<div class="history-header">
<div class="history-title">📈 Fiyat Geçmişi</div>
<div class="period-tabs">
<button class="period-tab active" onclick="switchPeriod('hourly')" id="hourlyTab">Saatlik</button>
<button class="period-tab" onclick="switchPeriod('daily')" id="dailyTab">Günlük</button>
<button class="period-tab" onclick="switchPeriod('monthly')" id="monthlyTab">Aylık</button>
</div>
</div>
<div class="price-table">
<table>
<thead><tr><th id="timeHeader">Saat</th><th>Altın</th><th>Gümüş</th><th>Portföy</th><th>Değişim</th></tr></thead>
<tbody id="priceTableBody"></tbody>
</table>
</div>
</div>
</div>
<script>
let currentGoldPrice=0,currentSilverPrice=0,tableData={},currentPeriod='hourly',goldAmount=0,silverAmount=0;async function login(){const p=document.getElementById('passwordInput').value;if(!p)return;try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});const d=await r.json();if(d.success){const exp=new Date();exp.setDate(exp.getDate()+30);document.cookie=`auth_token=${d.token}; expires=${exp.toUTCString()}; path=/`;localStorage.setItem('auth_token',d.token);localStorage.setItem('auth_expiry',exp.getTime());document.getElementById('loginScreen').style.display='none';document.getElementById('mainApp').style.display='flex';await loadPortfolioConfig();await fetchPrice()}else{document.getElementById('loginError').style.display='block';document.getElementById('passwordInput').value=''}}catch(e){document.getElementById('loginError').style.display='block'}}async function checkAuth(){let token=localStorage.getItem('auth_token');const expiry=localStorage.getItem('auth_expiry');if(!token||!expiry||new Date().getTime()>parseInt(expiry)){const c=document.cookie.split(';').find(ck=>ck.trim().startsWith('auth_token='));if(c){token=c.split('=')[1]}else{document.getElementById('loginScreen').style.display='flex';document.getElementById('mainApp').style.display='none';return false}}try{const r=await fetch('/api/verify-session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token})});const d=await r.json();if(d.valid){document.getElementById('loginScreen').style.display='none';document.getElementById('mainApp').style.display='flex';await loadPortfolioConfig();await fetchPrice();return true}else{logout();return false}}catch(e){logout();return false}}function logout(){document.cookie='auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';localStorage.removeItem('auth_token');localStorage.removeItem('auth_expiry');document.getElementById('loginScreen').style.display='flex';document.getElementById('mainApp').style.display='none';document.getElementById('passwordInput').value='';document.getElementById('loginError').style.display='none'}async function loadPortfolioConfig(){try{const r=await fetch('/api/portfolio-config');const d=await r.json();if(d.success){goldAmount=d.gold_amount;silverAmount=d.silver_amount}}catch(e){}}async function fetchPrice(){const r=document.getElementById('refreshBtn');try{r.style.transform='rotate(360deg)';const[g,s,t]=await Promise.all([fetch('/api/gold-price'),fetch('/api/silver-price'),fetch('/api/table-data')]);const gd=await g.json(),sd=await s.json(),td=await t.json();if(gd.success){let c=gd.price.replace(/[^\d,]/g,'');currentGoldPrice=parseFloat(c.replace(',','.'))}if(sd.success){let c=sd.price.replace(/[^\d,]/g,'');currentSilverPrice=parseFloat(c.replace(',','.'))}if(td.success){tableData=td.data;updateTable()}document.getElementById('headerTime').textContent=new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'});updatePortfolio()}catch(e){}finally{setTimeout(()=>r.style.transform='rotate(0deg)',500)}}function switchPeriod(p){currentPeriod=p;document.querySelectorAll('.period-tab').forEach(t=>t.classList.remove('active'));document.getElementById(p+'Tab').classList.add('active');const h=document.getElementById('timeHeader');if(p==='hourly')h.textContent='Saat';else if(p==='daily')h.textContent='Tarih';else if(p==='monthly')h.textContent='Ay';updateTable()}function updateTable(){if(!tableData[currentPeriod])return;const tb=document.getElementById('priceTableBody');tb.innerHTML='';let mv=0,pi=[];if(goldAmount>0||silverAmount>0){tableData[currentPeriod].forEach((it,i)=>{const pv=(goldAmount*it.gold_price)+(silverAmount*it.silver_price);if(pv>mv){mv=pv;pi=[i]}else if(pv===mv&&pv>0)pi.push(i)})}tableData[currentPeriod].forEach((it,i)=>{let pv=(goldAmount*it.gold_price)+(silverAmount*it.silver_price);const r=document.createElement('tr');if(pi.includes(i)&&mv>0)r.classList.add('peak-row');const td=it.optimized?`<span title="Peak değer (${it.peak_time||'bilinmiyor'})">${it.time}</span>`:it.time;r.innerHTML=`<td class="time">${td}</td><td class="price">${formatPrice(it.gold_price)}</td><td class="price">${formatPrice(it.silver_price)}</td><td class="portfolio">${pv>0?formatCurrency(pv):'-'}</td><td class="change ${getChangeClass(it.change_percent)}">${formatChange(it.change_percent)}</td>`;tb.appendChild(r)})}function getChangeClass(c){if(c>0)return 'positive';if(c<0)return 'negative';return 'neutral'}function formatChange(c){if(c===0)return '0.00%';const s=c>0?'+':'';return `${s}${c.toFixed(2)}%`}function updatePortfolio(){const gv=goldAmount*currentGoldPrice,sv=silverAmount*currentSilverPrice,tv=gv+sv;document.getElementById('totalAmount').textContent=formatCurrency(tv);document.getElementById('goldAmount').textContent=goldAmount+' gr';document.getElementById('silverAmount').textContent=silverAmount+' gr';document.getElementById('goldCurrentPrice').textContent=formatPrice(currentGoldPrice)+'/gr';document.getElementById('silverCurrentPrice').textContent=formatPrice(currentSilverPrice)+'/gr';document.getElementById('goldPortfolioValue').textContent=formatCurrency(gv);document.getElementById('silverPortfolioValue').textContent=formatCurrency(sv);updateTable()}function formatCurrency(a){return new Intl.NumberFormat('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(a)+' ₺'}function formatPrice(p){if(!p)return '0,00 ₺';return new Intl.NumberFormat('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(p)+' ₺'}window.onload=function(){checkAuth()};