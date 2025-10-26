#!/usr/bin/env python3
"""
Metal Price Tracker Web App v2.0 - With Login System
"""
from flask import Flask, jsonify, request, session, redirect, url_for
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
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

@app.route('/')
def index():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    
    config = load_portfolio_config()
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <meta name="theme-color" content="#1e3c72">
    <title>Metal Tracker</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding-bottom: 20px;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 600px;
            margin: 0 auto;
        }}
        .logo {{
            font-size: 17px;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .logo-icon {{ font-size: 20px; }}
        
        .header-actions {{
            display: flex;
            gap: 8px;
        }}
        .header-btn {{
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.15);
            border: none;
            font-size: 18px;
            color: #ffffff;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .header-btn:active {{
            background: rgba(255, 255, 255, 0.25);
            transform: scale(0.95);
        }}
        .header-btn.spinning {{ animation: spin 1s ease-in-out; }}
        @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
        
        .update-info {{
            font-size: 11px;
            color: rgba(255, 255, 255, 0.7);
            text-align: center;
            margin-top: 6px;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
        }}
        
        .portfolio-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 20px 16px;
            margin-bottom: 20px;
            color: white;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .portfolio-total {{
            text-align: center;
            padding: 16px 12px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            margin-bottom: 12px;
            backdrop-filter: blur(10px);
        }}
        .portfolio-total-value {{
            font-size: 34px;
            font-weight: 900;
            word-wrap: break-word;
        }}
        .portfolio-info {{
            font-size: 12px;
            opacity: 0.8;
            margin-top: 8px;
        }}
        
        .portfolio-breakdown {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .portfolio-item {{
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 12px 10px;
            text-align: center;
            backdrop-filter: blur(10px);
        }}
        .portfolio-item-label {{
            font-size: 11px;
            opacity: 0.9;
            margin-bottom: 6px;
        }}
        .portfolio-item-value {{
            font-size: 14px;
            font-weight: 800;
            word-wrap: break-word;
            line-height: 1.2;
            margin-bottom: 8px;
        }}
        .portfolio-item-price {{
            font-size: 12px;
            opacity: 0.85;
            font-weight: 600;
        }}
        .portfolio-item-amount {{
            font-size: 10px;
            opacity: 0.7;
            margin-top: 4px;
        }}
        
        .tabs {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            padding: 5px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .tab {{
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            background: transparent;
            color: rgba(255, 255, 255, 0.7);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .tab.active {{
            background: rgba(255, 255, 255, 0.2);
            color: #ffffff;
        }}
        
        .history-section {{ display: none; }}
        .history-section.active {{ display: block; }}
        
        .history-item {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 6px;
            color: #e2e8f0;
        }}
        .history-item.peak {{
            background: linear-gradient(135deg, rgba(255, 193, 7, 0.2) 0%, rgba(255, 152, 0, 0.2) 100%);
            border: 1px solid rgba(255, 193, 7, 0.3);
        }}
        
        .history-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .history-time {{
            font-size: 12px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
        }}
        .history-portfolio {{
            font-size: 15px;
            font-weight: 700;
            color: #ffd700;
        }}
        
        .history-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .history-metals {{
            display: flex;
            gap: 12px;
        }}
        .history-metal {{
            font-size: 11px;
            color: rgba(255, 255, 255, 0.7);
        }}
        .history-metal span {{
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
        }}
        .history-change {{
            font-size: 11px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.1);
        }}
        .history-change.positive {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; }}
        .history-change.negative {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
        .history-change.neutral {{ background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.7); }}
        
        .loading {{
            text-align: center;
            padding: 40px 20px;
            color: rgba(255, 255, 255, 0.6);
        }}
        .loading-spinner {{
            width: 32px;
            height: 32px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 12px;
        }}
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
                <button class="header-btn" onclick="logout()" title="Çıkış">🚪</button>
            </div>
        </div>
        <div class="update-info" id="updateInfo">Yükleniyor...</div>
    </div>

    <div class="container">
        <div class="portfolio-card">
            <div class="portfolio-total">
                <div class="portfolio-total-value" id="portfolioTotal">0 ₺</div>
                <div class="portfolio-info">
                    Altın: {config.get('gold_amount', 0)}gr | Gümüş: {config.get('silver_amount', 0)}gr
                </div>
            </div>
            
            <div class="portfolio-breakdown">
                <div class="portfolio-item">
                    <div class="portfolio-item-label">Altın</div>
                    <div class="portfolio-item-price" id="goldPrice">-</div>
                    <div class="portfolio-item-value" id="goldPortfolio">0 ₺</div>
                    <div class="portfolio-item-amount">{config.get('gold_amount', 0)} gram</div>
                </div>
                <div class="portfolio-item">
                    <div class="portfolio-item-label">Gümüş</div>
                    <div class="portfolio-item-price" id="silverPrice">-</div>
                    <div class="portfolio-item-value" id="silverPortfolio">0 ₺</div>
                    <div class="portfolio-item-amount">{config.get('silver_amount', 0)} gram</div>
                </div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('daily')" id="dailyTab">Günlük</button>
            <button class="tab" onclick="switchTab('weekly')" id="weeklyTab">Aylık</button>
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
        
        <div class="debug-panel" id="debugPanel">
            <div class="debug-title">API Debug Bilgileri:</div>
            <div class="debug-content" id="apiDebugContent">Henüz veri yüklenmedi...</div>
        </div>
    </div>

    <script>
        let goldPrice = 0;
        let silverPrice = 0;
        let tableData = {{}};
        let currentTab = 'daily';
        const goldAmount = {config.get('gold_amount', 0)};
        const silverAmount = {config.get('silver_amount', 0)};

        async function fetchData() {{
            const btn = document.getElementById('refreshBtn');
            btn.classList.add('spinning');
            
            try {{
                const [g, s, t] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data')
                ]);
                
                const gold = await g.json();
                const silver = await s.json();
                const table = await t.json();
                
                if (gold.success) {{
                    let p = gold.price.replace(/[^\\d,]/g, '');
                    goldPrice = parseFloat(p.replace(',', '.'));
                    document.getElementById('goldPrice').textContent = gold.price;
                }}
                
                if (silver.success) {{
                    let p = silver.price.replace(/[^\\d,]/g, '');
                    silverPrice = parseFloat(p.replace(',', '.'));
                    document.getElementById('silverPrice').textContent = silver.price;
                }}
                
                if (table.success) {{
                    tableData = table.data;
                    renderHistory();
                }}
                
                document.getElementById('updateInfo').textContent = 'Son güncelleme: ' + new Date().toLocaleTimeString('tr-TR');
                updatePortfolio();
                
            }} catch (error) {{
                document.getElementById('updateInfo').textContent = 'Güncelleme hatası';
            }} finally {{
                setTimeout(() => btn.classList.remove('spinning'), 500);
            }}
        }}

        function switchTab(tab) {{
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.history-section').forEach(s => s.classList.remove('active'));
            
            document.getElementById(tab + 'Tab').classList.add('active');
            document.getElementById(tab + 'Section').classList.add('active');
            
            renderHistory();
        }}

        function renderHistory() {{
            const section = document.getElementById(currentTab + 'Section');
            const data = tableData[currentTab] || [];
            
            if (data.length === 0) {{
                section.innerHTML = '<div class="loading"><div class="loading-spinner"></div><div>Veri bulunamadı</div></div>';
                return;
            }}

            let html = '';
            let maxPortfolio = 0;
            
            if (goldAmount > 0 || silverAmount > 0) {{
                maxPortfolio = Math.max(...data.map(d => (goldAmount * d.gold_price) + (silverAmount * d.silver_price)));
            }}
            
            data.forEach(item => {{
                const portfolio = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                const isPeak = portfolio > 0 && portfolio === maxPortfolio;
                
                const changeClass = item.change_percent > 0 ? 'positive' : item.change_percent < 0 ? 'negative' : 'neutral';
                const changeText = item.change_percent === 0 ? '0.00%' : (item.change_percent > 0 ? '+' : '') + item.change_percent.toFixed(2) + '%';
                
                html += `
                    <div class="history-item ${{isPeak ? 'peak' : ''}}">
                        <div class="history-header">
                            <div class="history-time">${{item.time}}</div>
                            <div class="history-portfolio">${{portfolio > 0 ? formatCurrency(portfolio) : '-'}}</div>
                        </div>
                        <div class="history-footer">
                            <div class="history-metals">
                                <div class="history-metal">Altın: <span>${{formatPrice(item.gold_price)}}</span></div>
                                <div class="history-metal">Gümüş: <span>${{formatPrice(item.silver_price)}}</span></div>
                            </div>
                            <div class="history-change ${{changeClass}}">${{changeText}}</div>
                        </div>
                    </div>
                `;
            }});
            
            section.innerHTML = html;
        }}

        function updatePortfolio() {{
            const goldValue = goldAmount * goldPrice;
            const silverValue = silverAmount * silverPrice;
            const totalValue = goldValue + silverValue;
            
            document.getElementById('portfolioTotal').textContent = formatCurrency(totalValue);
            document.getElementById('goldPortfolio').textContent = formatCurrency(goldValue);
            document.getElementById('silverPortfolio').textContent = formatCurrency(silverValue);
            
            renderHistory();
        }}

        function formatCurrency(amount) {{
            return new Intl.NumberFormat('tr-TR', {{
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }}).format(amount) + ' ₺';
        }}

        function formatPrice(price) {{
            return new Intl.NumberFormat('tr-TR', {{
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }}).format(price) + ' ₺';
        }}

        function logout() {{
            if (confirm('Oturumu kapatmak istediğinize emin misiniz?')) {{
                fetch('/logout', {{method: 'POST'}}).then(() => {{
                    window.location.href = '/login';
                }});
            }}
        }}

        window.onload = function() {{
            fetchData();
            updatePortfolio();
        }};
    </script>
</body>
</html>'''
    return html

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
        
        .debug-logs {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 16px;
            margin-top: 20px;
        }
        
        .debug-title {
            font-size: 14px;
            font-weight: 600;
            color: #ffd700;
            margin-bottom: 8px;
        }
        
        .debug-content {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.8);
            font-family: 'Courier New', monospace;
            background: rgba(0, 0, 0, 0.2);
            padding: 12px;
            border-radius: 6px;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
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
        
        <div class="debug-logs" id="debugLogs">
            <div class="debug-title">Debug Logları:</div>
            <div class="debug-content" id="debugContent">Henüz giriş denenmedi...</div>
        </div>
    </div>

    <script>
        async function handleLogin(event) {
            event.preventDefault();
            
            const password = document.getElementById('password').value;
            const errorMessage = document.getElementById('errorMessage');
            const loginBtn = document.getElementById('loginBtn');
            const debugContent = document.getElementById('debugContent');
            
            // Debug logları temizle
            debugContent.innerHTML = 'Login işlemi başlatılıyor...<br>';
            
            // Hata mesajını gizle
            errorMessage.classList.remove('show');
            
            // Butonu devre dışı bırak
            loginBtn.disabled = true;
            loginBtn.textContent = 'Giriş yapılıyor...';
            
            try {
                debugContent.innerHTML += `Şifre gönderiliyor: "${password}"<br>`;
                
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ password: password })
                });
                
                const result = await response.json();
                
                // Debug bilgilerini güzel formatta göster
                if (result.debug) {
                    debugContent.innerHTML += '<br><strong>Debug Bilgileri:</strong><br>';
                    debugContent.innerHTML += `• Alınan şifre: "${result.debug.received_password}"<br>`;
                    debugContent.innerHTML += `• Şifre uzunluğu: ${result.debug.password_length}<br>`;
                    debugContent.innerHTML += `• Generate edilen hash: ${result.debug.generated_hash}<br>`;
                    debugContent.innerHTML += `• GitHub'dan okunan hash: ${result.debug.stored_hash}<br>`;
                    debugContent.innerHTML += `• Config yüklendi mi: ${result.debug.config_loaded}<br>`;
                    debugContent.innerHTML += `• Hash'ler eşleşiyor mu: ${result.debug.hashes_match}<br>`;
                    debugContent.innerHTML += `• Login sonucu: ${result.debug.login_result}<br>`;
                    
                    if (result.debug.error) {
                        debugContent.innerHTML += `• Hata: ${result.debug.error}<br>`;
                    }
                }
                
                if (result.success) {
                    debugContent.innerHTML += 'Login başarılı! Ana sayfaya yönlendiriliyor...<br>';
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1000);
                } else {
                    debugContent.innerHTML += `Login başarısız: ${result.error}<br>`;
                    errorMessage.classList.add('show');
                    document.getElementById('password').value = '';
                    document.getElementById('password').focus();
                }
            } catch (error) {
                debugContent.innerHTML += `Bağlantı hatası: ${error.message}<br>`;
                errorMessage.textContent = 'Bağlantı hatası! Lütfen tekrar deneyin.';
                errorMessage.classList.add('show');
            } finally {
                loginBtn.disabled = false;
                loginBtn.textContent = 'Giriş Yap';
            }
        }
        
        // Enter tuşu ile form gönderimi
        document.getElementById('password').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleLogin(e);
            }
        });
        
        // Sayfa yüklendiğinde şifre alanına odaklan
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
        
        # Debug bilgileri
        debug_info = {
            'received_password': password,
            'password_length': len(password),
            'password_bytes': password.encode().hex()
        }
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        debug_info['generated_hash'] = password_hash
        
        config = load_portfolio_config()
        stored_hash = config.get("password_hash", "")
        debug_info['stored_hash'] = stored_hash
        debug_info['config_loaded'] = bool(config)
        debug_info['hashes_match'] = password_hash == stored_hash
        
        if verify_password(password):
            session['authenticated'] = True
            session.permanent = True
            debug_info['login_result'] = 'SUCCESS'
            return jsonify({'success': True, 'debug': debug_info})
        else:
            debug_info['login_result'] = 'FAILED'
            return jsonify({'success': False, 'error': 'Invalid password', 'debug': debug_info})
    except Exception as e:
        debug_info = {'error': str(e), 'error_type': type(e).__name__}
        return jsonify({'success': False, 'error': str(e), 'debug': debug_info})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/gold-price')
def api_gold_price():
    if 'authenticated' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        price = get_gold_price()
        return jsonify({'success': bool(price), 'price': price or ''})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/silver-price')
def api_silver_price():
    if 'authenticated' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        price = get_silver_price()
        # Debug bilgisi ekle
        debug_info = {
            'raw_price': price,
            'price_found': price is not None,
            'price_type': type(price).__name__ if price else None
        }
        return jsonify({
            'success': bool(price), 
            'price': price or '',
            'debug': debug_info
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'debug': {'exception': str(e), 'exception_type': type(e).__name__}
        })

@app.route('/api/table-data')
def api_table_data():
    if 'authenticated' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        data = get_table_data()
        
        # Debug bilgisi ekle
        debug_info = {
            'daily_count': len(data.get('daily', [])),
            'weekly_count': len(data.get('weekly', [])),
            'daily_sample': data.get('daily', [])[:2] if data.get('daily') else [],
            'weekly_sample': data.get('weekly', [])[:2] if data.get('weekly') else []
        }
        
        return jsonify({
            'success': bool(data), 
            'data': data or {},
            'debug': debug_info
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'debug': {'exception': str(e), 'exception_type': type(e).__name__}
        })

@app.route('/api/portfolio-config')
def api_portfolio_config():
    if 'authenticated' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    try:
        config = load_portfolio_config()
        # Şifreyi döndürme
        config.pop('password_hash', None)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    import os
    app.permanent_session_lifetime = timedelta(days=30)  # 30 gün session
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)