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

def get_chart_data():
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
        
        # Günlük veriler (bugün saat saat)
        today = now.strftime("%Y-%m-%d")
        today_records = [r for r in recent_records if r.get("date") == today]
        
        hourly_data = {}
        for record in today_records:
            timestamp = record.get("timestamp", 0)
            hour = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%H:00")
            if hour not in hourly_data:
                hourly_data[hour] = {"gold_prices": [], "silver_prices": []}
            hourly_data[hour]["gold_prices"].append(record["gold_price"])
            hourly_data[hour]["silver_prices"].append(record["silver_price"])
        
        daily_data = []
        for hour in sorted(hourly_data.keys()):
            gold_avg = sum(hourly_data[hour]["gold_prices"]) / len(hourly_data[hour]["gold_prices"])
            silver_avg = sum(hourly_data[hour]["silver_prices"]) / len(hourly_data[hour]["silver_prices"])
            daily_data.append({
                "hour": hour,
                "gold_price": gold_avg,
                "silver_price": silver_avg
            })
        
        # Haftalık veriler (son 7 gün)
        weekly_data = []
        for i in range(7):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            day_records = [r for r in recent_records if r.get("date") == date]
            if day_records:
                avg_gold = sum(r["gold_price"] for r in day_records) / len(day_records)
                avg_silver = sum(r["silver_price"] for r in day_records) / len(day_records)
                day_name = (now - timedelta(days=i)).strftime("%a")
                weekly_data.insert(0, {
                    "day": day_name,
                    "gold_price": avg_gold,
                    "silver_price": avg_silver
                })
        
        # Aylık veriler (son 30 gün, 5'er günlük gruplar)
        monthly_data = []
        for i in range(6):
            period_start = now - timedelta(days=(i+1)*5)
            period_end = now - timedelta(days=i*5)
            
            period_records = [r for r in recent_records 
                            if period_start.timestamp() <= r.get("timestamp", 0) <= period_end.timestamp()]
            
            if period_records:
                avg_gold = sum(r["gold_price"] for r in period_records) / len(period_records)
                avg_silver = sum(r["silver_price"] for r in period_records) / len(period_records)
                period_label = period_start.strftime("%d.%m")
                monthly_data.insert(0, {
                    "period": period_label,
                    "gold_price": avg_gold,
                    "silver_price": avg_silver
                })
        
        return {
            "daily": daily_data,
            "weekly": weekly_data,
            "monthly": monthly_data
        }
        
    except Exception as e:
        print(f"Chart data error: {e}")
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
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #667eea 100%);
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 390px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
        
        .header {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 16px 20px; border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .header-left {
            display: flex; align-items: center; gap: 12px;
        }
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
            border-radius: 24px; padding: 28px; color: white;
            box-shadow: 0 15px 35px rgba(238, 90, 36, 0.4);
            display: none; text-align: center;
        }
        .portfolio-amount { font-size: 42px; font-weight: 900; margin-bottom: 20px; }
        .portfolio-metals {
            display: flex; justify-content: space-between; gap: 16px;
            margin-top: 16px;
        }
        .metal-item {
            flex: 1; background: rgba(255, 255, 255, 0.15); border-radius: 16px; padding: 16px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .metal-header {
            display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
        }
        .metal-icon {
            width: 32px; height: 32px; border-radius: 8px; display: flex;
            align-items: center; justify-content: center; font-size: 14px; font-weight: 700;
        }
        .metal-icon.gold { background: rgba(243, 156, 18, 0.3); color: #f39c12; }
        .metal-icon.silver { background: rgba(149, 165, 166, 0.3); color: #95a5a6; }
        .metal-name { font-size: 14px; font-weight: 600; }
        .metal-price { font-size: 13px; opacity: 0.8; margin-bottom: 8px; }
        .metal-value { font-size: 18px; font-weight: 700; }
        
        .chart-container {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 24px; border: 1px solid rgba(255, 255, 255, 0.3);
            display: none;
        }
        .chart-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
        }
        .chart-title { font-size: 18px; font-weight: 700; color: #2c3e50; }
        .chart-tabs {
            display: flex; gap: 8px;
            background: #f8f9fa; border-radius: 10px; padding: 4px;
        }
        .chart-tab {
            padding: 8px 16px; border: none; border-radius: 6px;
            background: transparent; color: #6c757d;
            font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .chart-tab.active { background: white; color: #2c3e50; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart-wrapper {
            position: relative; height: 300px; margin-bottom: 16px;
        }
        .chart-legend {
            display: flex; justify-content: center; gap: 20px; margin-top: 16px;
        }
        .legend-item {
            display: flex; align-items: center; gap: 8px; font-size: 14px; color: #6c757d;
            cursor: pointer; transition: opacity 0.3s;
        }
        .legend-item.disabled { opacity: 0.4; }
        .legend-color {
            width: 16px; height: 3px; border-radius: 2px;
        }
        .legend-color.gold { background: linear-gradient(45deg, #f39c12, #d35400); }
        .legend-color.silver { background: linear-gradient(45deg, #95a5a6, #7f8c8d); }
        
        .status-bar {
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 14px; padding: 14px 18px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .status-text { color: white; font-size: 15px; font-weight: 600; }
        .status-time { color: rgba(255, 255, 255, 0.8); font-size: 13px; }
        
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
            .chart-header { flex-direction: column; gap: 12px; }
            .portfolio-metals { flex-direction: column; gap: 12px; }
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
        
        <div class="chart-container" id="chartContainer">
            <div class="chart-header">
                <div class="chart-title">Portföy Grafiği</div>
                <div class="chart-tabs">
                    <button class="chart-tab active" onclick="switchChart('daily')" id="dailyChartTab">Günlük</button>
                    <button class="chart-tab" onclick="switchChart('weekly')" id="weeklyChartTab">Haftalık</button>
                    <button class="chart-tab" onclick="switchChart('monthly')" id="monthlyChartTab">Aylık</button>
                </div>
            </div>
            <div class="chart-wrapper">
                <canvas id="portfolioChart"></canvas>
            </div>
            <div class="chart-legend">
                <div class="legend-item" onclick="toggleDataset('gold')" id="goldLegend">
                    <div class="legend-color gold"></div>
                    <span>Altın Portföyü</span>
                </div>
                <div class="legend-item" onclick="toggleDataset('silver')" id="silverLegend">
                    <div class="legend-color silver"></div>
                    <span>Gümüş Portföyü</span>
                </div>
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
        let chartData = {};
        let portfolioChart = null;
        let currentChartPeriod = 'daily';
        let visibleDatasets = { gold: true, silver: true };

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                
                const [goldRes, silverRes, chartRes] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/chart-data')
                ]);
                
                const goldData = await goldRes.json();
                const silverData = await silverRes.json();
                const chartDataRes = await chartRes.json();
                
                if (goldData.success) {
                    let cleanPrice = goldData.price.replace(/[^\\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (chartDataRes.success) {
                    chartData = chartDataRes.data;
                    updateChart();
                }
                
                document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                updatePortfolio();
                
            } catch (error) {
                console.error('Fetch error:', error);
            } finally {
                setTimeout(() => refreshBtn.style.transform = 'rotate(0deg)', 500);
            }
        }

        function switchChart(period) {
            currentChartPeriod = period;
            document.querySelectorAll('.chart-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'ChartTab').classList.add('active');
            updateChart();
        }

        function toggleDataset(type) {
            visibleDatasets[type] = !visibleDatasets[type];
            const legend = document.getElementById(type + 'Legend');
            if (visibleDatasets[type]) {
                legend.classList.remove('disabled');
            } else {
                legend.classList.add('disabled');
            }
            updateChart();
        }

        function updateChart() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            if (!chartData[currentChartPeriod] || (goldAmount === 0 && silverAmount === 0)) {
                if (portfolioChart) {
                    portfolioChart.destroy();
                    portfolioChart = null;
                }
                return;
            }
            
            const data = chartData[currentChartPeriod];
            const labels = data.map(item => {
                if (currentChartPeriod === 'daily') return item.hour;
                if (currentChartPeriod === 'weekly') return item.day;
                return item.period;
            });
            
            const goldPortfolioData = data.map(item => goldAmount * item.gold_price);
            const silverPortfolioData = data.map(item => silverAmount * item.silver_price);
            
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            
            if (portfolioChart) {
                portfolioChart.destroy();
            }
            
            const datasets = [];
            
            if (visibleDatasets.gold && goldAmount > 0) {
                datasets.push({
                    label: 'Altın Portföyü',
                    data: goldPortfolioData,
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                });
            }
            
            if (visibleDatasets.silver && silverAmount > 0) {
                datasets.push({
                    label: 'Gümüş Portföyü',
                    data: silverPortfolioData,
                    borderColor: '#95a5a6',
                    backgroundColor: 'rgba(149, 165, 166, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                });
            }
            
            portfolioChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    if (value >= 1000000) {
                                        return (value / 1000000).toFixed(1) + 'M₺';
                                    } else if (value >= 1000) {
                                        return (value / 1000).toFixed(0) + 'K₺';
                                    }
                                    return new Intl.NumberFormat('tr-TR', {maximumFractionDigits: 2}).format(value) + '₺';
                                }
                            }
                        }
                    },
                    elements: {
                        point: { radius: 4, hoverRadius: 6 }
                    }
                }
            });
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
            const chartContainer = document.getElementById('chartContainer');
            
            if (totalValue > 0) {
                portfolioSummary.style.display = 'block';
                chartContainer.style.display = 'block';
                
                document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
                document.getElementById('goldCurrentPrice').textContent = formatPrice(currentGoldPrice) + '/gr';
                document.getElementById('silverCurrentPrice').textContent = formatPrice(currentSilverPrice) + '/gr';
                document.getElementById('goldPortfolioValue').textContent = formatCurrency(goldValue);
                document.getElementById('silverPortfolioValue').textContent = formatCurrency(silverValue);
                
                updateChart();
            } else {
                portfolioSummary.style.display = 'none';
                chartContainer.style.display = 'none';
                if (portfolioChart) {
                    portfolioChart.destroy();
                    portfolioChart = null;
                }
            }
            
            savePortfolio();
        }

        function savePortfolio() {
            try {
                localStorage.setItem('goldAmount', document.getElementById('goldAmount').value);
                localStorage.setItem('silverAmount', document.getElementById('silverAmount').value);
            } catch (e) {}
        }

        function loadPortfolio() {
            try {
                const gold = localStorage.getItem('goldAmount');
                const silver = localStorage.getItem('silverAmount');
                if (gold) document.getElementById('goldAmount').value = gold;
                if (silver) document.getElementById('silverAmount').value = silver;
            } catch (e) {}
        }

        function clearPortfolio() {
            if (confirm('Portföy sıfırlanacak. Emin misiniz?')) {
                document.getElementById('goldAmount').value = '';
                document.getElementById('silverAmount').value = '';
                try {
                    localStorage.removeItem('goldAmount');
                    localStorage.removeItem('silverAmount');
                } catch (e) {}
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

@app.route('/api/chart-data')
def api_chart_data():
    try:
        data = get_chart_data()
        return jsonify({'success': bool(data), 'data': data or {}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Metal Fiyat Takipçisi v2.7.0")
    print("Redesigned Portfolio with Chart Controls")
    print(f"URL: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)