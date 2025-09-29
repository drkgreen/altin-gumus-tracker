#!/usr/bin/env python3
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
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
    except Exception as e:
        print(f"Price history error: {e}")
        return {"records": []}

def get_table_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return None
        
        now = datetime.now(timezone.utc)
        thirty_days_ago = (now - timedelta(days=30)).timestamp()
        recent_records = [r for r in records 
                         if r.get("timestamp", 0) > thirty_days_ago 
                         and r.get("gold_price") and r.get("silver_price")]
        
        if not recent_records:
            return None
        
        # Günlük veriler (bugün her kayıt ayrı ayrı - 30dk aralıklarla)
        today = now.strftime("%Y-%m-%d")
        today_records = [r for r in recent_records if r.get("date") == today]
        
        daily_data = []
        for i, record in enumerate(sorted(today_records, key=lambda x: x.get("timestamp", 0), reverse=True)):
            timestamp = record.get("timestamp", 0)
            # UTC'den Türkiye saatine çevir (+3 saat)
            local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
            time_label = local_time.strftime("%H:%M")
            
            # Değişim hesaplama (bir önceki kayıt ile karşılaştır)
            change_percent = 0
            if i < len(today_records) - 1:
                prev_record = sorted(today_records, key=lambda x: x.get("timestamp", 0), reverse=True)[i + 1]
                if prev_record and prev_record.get("gold_price"):
                    price_diff = record["gold_price"] - prev_record["gold_price"]
                    change_percent = (price_diff / prev_record["gold_price"]) * 100
            
            daily_data.append({
                "time": time_label,
                "gold_price": record["gold_price"],
                "silver_price": record["silver_price"],
                "change_percent": change_percent
            })
        
        # Haftalık veriler (son 7 gün, günlük ortalamalar)
        weekly_data = []
        for i in range(7):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            day_records = [r for r in recent_records if r.get("date") == date]
            if day_records:
                avg_gold = sum(r["gold_price"] for r in day_records) / len(day_records)
                avg_silver = sum(r["silver_price"] for r in day_records) / len(day_records)
                
                # Değişim hesaplama (bir önceki gün ile karşılaştır)
                change_percent = 0
                if i < 6:
                    prev_date = (now - timedelta(days=i+1)).strftime("%Y-%m-%d")
                    prev_day_records = [r for r in recent_records if r.get("date") == prev_date]
                    if prev_day_records:
                        prev_avg_gold = sum(r["gold_price"] for r in prev_day_records) / len(prev_day_records)
                        price_diff = avg_gold - prev_avg_gold
                        change_percent = (price_diff / prev_avg_gold) * 100
                
                day_name = (now - timedelta(days=i)).strftime("%d.%m")
                weekly_data.insert(0, {
                    "time": day_name,
                    "gold_price": avg_gold,
                    "silver_price": avg_silver,
                    "change_percent": change_percent
                })
        
        return {
            "daily": daily_data,
            "weekly": weekly_data
        }
        
    except Exception as e:
        print(f"Table data error: {e}")
        return None

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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #667eea 100%);
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 390px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding: 0 5px; }
        
        .header {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 16px 20px; border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .logo { font-size: 20px; font-weight: 700; color: white; }
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
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            border-radius: 24px; padding: 24px 20px; color: white;
            box-shadow: 0 15px 35px rgba(238, 90, 36, 0.4);
            display: none; text-align: center;
        }
        .portfolio-amount { font-size: 42px; font-weight: 900; margin-bottom: 20px; }
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
        
        .price-history {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 24px; border: 1px solid rgba(255, 255, 255, 0.3);
            display: none;
        }
        .history-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
        }
        .history-title { font-size: 18px; font-weight: 700; color: #2c3e50; }
        .period-tabs {
            display: flex; gap: 8px;
            background: #f8f9fa; border-radius: 10px; padding: 4px;
        }
        .period-tab {
            padding: 8px 16px; border: none; border-radius: 6px;
            background: transparent; color: #6c757d;
            font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .period-tab.active { background: white; color: #2c3e50; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        
        .price-table {
            overflow-x: auto; border-radius: 12px; background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .price-table table {
            width: 100%; border-collapse: collapse;
        }
        .price-table th {
            background: #f8f9fa; padding: 12px 8px; text-align: left;
            font-weight: 600; color: #495057; font-size: 14px;
            border-bottom: 2px solid #e9ecef;
        }
        .price-table td {
            padding: 12px 8px; border-bottom: 1px solid #f1f3f4;
            font-size: 14px; color: #495057;
        }
        .price-table tr:hover {
            background: #f8f9fa;
        }
        .price-table .time { font-weight: 600; color: #2c3e50; }
        .price-table .price { font-weight: 600; }
        .price-table .portfolio { font-weight: 700; color: #e67e22; }
        .price-table .change {
            font-weight: 600; font-size: 13px;
        }
        .change.positive { color: #27ae60; }
        .change.negative { color: #e74c3c; }
        .change.neutral { color: #95a5a6; }
        
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(12px);
            z-index: 1000; display: none; align-items: center; justify-content: center; padding: 20px;
        }
        .modal-content {
            background: white; border-radius: 24px; padding: 28px;
            width: 100%; max-width: 350px; position: relative;
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .modal-title { font-size: 22px; font-weight: 800; color: #2c3e50; }
        .close-btn {
            width: 36px; height: 36px; border-radius: 10px; background: #f8f9fa;
            border: none; font-size: 18px; cursor: pointer; display: flex;
            align-items: center; justify-content: center;
        }
        .input-group { margin-bottom: 22px; }
        .input-label { display: block; margin-bottom: 10px; font-weight: 700; color: #2c3e50; font-size: 15px; }
        .input-field {
            width: 100%; padding: 16px; border: 2px solid #e9ecef;
            border-radius: 14px; font-size: 17px; background: #f8f9fa; font-weight: 600;
        }
        .input-field:focus { outline: none; border-color: #667eea; background: white; }
        .modal-actions { display: flex; gap: 14px; justify-content: flex-end; }
        .btn {
            padding: 14px 24px; border-radius: 12px; font-weight: 700;
            cursor: pointer; border: none; font-size: 15px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #e9ecef; color: #6c757d; }
        
        @media (max-width: 400px) {
            .container { max-width: 100%; }
            .history-header { flex-direction: column; gap: 12px; }
            .portfolio-metals { flex-direction: column; gap: 12px; }
            .metal-name { font-size: 17px; }
            .metal-price { font-size: 16px; }
            .metal-value { font-size: 24px; }
            .metal-item { padding: 20px; min-height: 130px; }
            .price-table th, .price-table td { padding: 8px 6px; font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <div class="logo">Metal Tracker</div>
                <div class="update-time" id="headerTime">--:--</div>
            </div>
            <div class="actions">
                <button class="action-btn" onclick="fetchPrice()" id="refreshBtn">⟳</button>
                <button class="action-btn" onclick="togglePortfolio()">⚙</button>
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
                </div>
                <div class="metal-item">
                    <div class="metal-header">
                        <div class="metal-name">Gümüş</div>
                    </div>
                    <div class="metal-price" id="silverCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="silverPortfolioValue">0,00 ₺</div>
                </div>
            </div>
        </div>
        
        <div class="price-history" id="priceHistory">
            <div class="history-header">
                <div class="history-title">Fiyat Geçmişi</div>
                <div class="period-tabs">
                    <button class="period-tab active" onclick="switchPeriod('daily')" id="dailyTab">Günlük</button>
                    <button class="period-tab" onclick="switchPeriod('weekly')" id="weeklyTab">Haftalık</button>
                </div>
            </div>
            <div class="price-table">
                <table>
                    <thead>
                        <tr>
                            <th>Saat</th>
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
    
    <div class="modal-overlay" id="portfolioModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Portföy Ayarları</div>
                <button class="close-btn" onclick="closeModal()">×</button>
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
                <button class="btn btn-primary" onclick="closeModal()">Tamam</button>
            </div>
        </div>
    </div>

    <script>
        let currentGoldPrice = 0;
        let currentSilverPrice = 0;
        let tableData = {};
        let currentPeriod = 'daily';

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                
                const [goldRes, silverRes, tableRes] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data')
                ]);
                
                const goldData = await goldRes.json();
                const silverData = await silverRes.json();
                const tableDataRes = await tableRes.json();
                
                if (goldData.success) {
                    let cleanPrice = goldData.price.replace(/[^\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (tableDataRes.success) {
                    tableData = tableDataRes.data;
                    updateTable();
                }
                
                document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                updatePortfolio();
                
            } catch (error) {
                console.error('Fetch error:', error);
            } finally {
                setTimeout(() => refreshBtn.style.transform = 'rotate(0deg)', 500);
            }
        }

        function switchPeriod(period) {
            currentPeriod = period;
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            updateTable();
        }

        function updateTable() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            if (!tableData[currentPeriod]) return;
            
            const tbody = document.getElementById('priceTableBody');
            tbody.innerHTML = '';
            
            tableData[currentPeriod].forEach(item => {
                const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="time">${item.time}</td>
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

        function togglePortfolio() {
            document.getElementById('portfolioModal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('portfolioModal').style.display = 'none';
        }

        function updatePortfolio() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            const portfolioSummary = document.getElementById('portfolioSummary');
            const priceHistory = document.getElementById('priceHistory');
            
            if (totalValue > 0) {
                portfolioSummary.style.display = 'block';
                priceHistory.style.display = 'block';
                
                document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
                document.getElementById('goldCurrentPrice').textContent = formatPrice(currentGoldPrice) + '/gr';
                document.getElementById('silverCurrentPrice').textContent = formatPrice(currentSilverPrice) + '/gr';
                document.getElementById('goldPortfolioValue').textContent = formatCurrency(goldValue);
                document.getElementById('silverPortfolioValue').textContent = formatCurrency(silverValue);
                
                updateTable();
            } else {
                portfolioSummary.style.display = 'none';
                priceHistory.style.display = 'none';
            }
            
            savePortfolio();
        }

        function savePortfolio() {
            const goldAmount = document.getElementById('goldAmount').value;
            const silverAmount = document.getElementById('silverAmount').value;
            
            // Cookie ile kalıcı kayıt (1 yıl geçerli)
            const expiryDate = new Date();
            expiryDate.setFullYear(expiryDate.getFullYear() + 1);
            
            document.cookie = `goldAmount=${goldAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
            document.cookie = `silverAmount=${silverAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
            
            // Yedek olarak in-memory de tut
            window.portfolioData = {
                gold: goldAmount,
                silver: silverAmount
            };
        }

        function loadPortfolio() {
            // Cookie'den yükle
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
            
            // Yedek: in-memory'den yükle
            if (!cookies.goldAmount && window.portfolioData) {
                document.getElementById('goldAmount').value = window.portfolioData.gold || '';
                document.getElementById('silverAmount').value = window.portfolioData.silver || '';
            }
        }

        function clearPortfolio() {
            if (confirm('Portföy sıfırlanacak. Emin misiniz?')) {
                document.getElementById('goldAmount').value = '';
                document.getElementById('silverAmount').value = '';
                
                // Cookie'leri sil
                document.cookie = 'goldAmount=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                document.cookie = 'silverAmount=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                
                // In-memory'yi temizle
                window.portfolioData = null;
                
                updatePortfolio();
            }
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

        document.getElementById('portfolioModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        window.onload = function() {
            loadPortfolio();
            fetchPrice();
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
    print("=" * 60)
    print("🚀 Metal Fiyat Takipçisi v4.0.0")
    print("=" * 60)
    print(f"🌐 Server: http://localhost:{port}")
    print(f"📱 Mobile: http://0.0.0.0:{port}")
    print("=" * 60)
    print("✨ Yeni Özellikler:")
    print("  • 📊 Tablo bazlı fiyat geçmişi")
    print("  • 📈 Değişim yüzdesi hesaplama")
    print("  • 💰 Portföy değeri sütunu")
    print("  • 🕐 Günlük/haftalık görünüm")
    print("  • 🎨 Responsive tablo tasarımı")
    print("  • 💾 Cookie ile kalıcı portföy kaydı")
    print("  • 🕕 30 dakikalık detaylı veri takibi")
    print("  • 🇹🇷 Türkiye saati (UTC+3)")
    print("=" * 60)
    print("📈 Veri Kaynakları:")
    print("  • Altın: YapıKredi (doviz.com)")
    print("  • Gümüş: VakıfBank (doviz.com)")
    print("  • Geçmiş: GitHub JSON")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)