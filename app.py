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
        
        # Günlük veriler (bugün her kayıt ayrı ayrı - 30dk aralıklarla)
        today = now.strftime("%Y-%m-%d")
        today_records = [r for r in recent_records if r.get("date") == today]
        
        daily_data = []
        for record in sorted(today_records, key=lambda x: x.get("timestamp", 0)):
            timestamp = record.get("timestamp", 0)
            local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
            time_label = local_time.strftime("%H:%M")
            
            daily_data.append({
                "time": time_label,
                "gold_price": record["gold_price"],
                "silver_price": record["silver_price"]
            })
        
        # Haftalık veriler
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
        
        # Aylık veriler
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

# HTML_TEMPLATE başlangıç
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/1.2.1/chartjs-plugin-zoom.min.js"></script>
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
            overflow: hidden; cursor: grab; user-select: none;
        }
        .chart-wrapper:active { cursor: grabbing; }
        .chart-wrapper.dragging { cursor: grabbing; }
        
        .scroll-indicator {
            display: flex; justify-content: center; align-items: center; gap: 8px;
            margin-top: 12px; color: #6c757d; font-size: 13px;
        }
        .scroll-dots { display: flex; gap: 4px; }
        .scroll-dot {
            width: 6px; height: 6px; border-radius: 50%;
            background: #d1d5db; transition: all 0.3s; cursor: pointer;
        }
        .scroll-dot:hover { background: #9ca3af; }
        .scroll-dot.active { background: #667eea; width: 20px; border-radius: 3px; }
        
        .chart-legend {
            display: flex; justify-content: center; gap: 20px; margin-top: 16px;
        }
        .legend-item {
            display: flex; align-items: center; gap: 8px; font-size: 14px; color: #6c757d;
            cursor: pointer; transition: opacity 0.3s;
        }
        .legend-item.disabled { opacity: 0.4; }
        .legend-color { width: 16px; height: 3px; border-radius: 2px; }
        .legend-color.gold { background: linear-gradient(45deg, #f39c12, #d35400); }
        .legend-color.silver { background: linear-gradient(45deg, #95a5a6, #7f8c8d); }
# PARÇA 2/3 - HTML_TEMPLATE devamı

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
            cursor: pointer; border: none; font-size: 15px; transition: all 0.3s ease;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5568d3; transform: translateY(-1px); }
        .btn-secondary { background: #e9ecef; color: #6c757d; }
        .btn-secondary:hover { background: #dee2e6; }
        
        @media (max-width: 400px) {
            .container { max-width: 100%; }
            .chart-header { flex-direction: column; gap: 12px; }
            .portfolio-metals { flex-direction: column; gap: 12px; }
            .metal-name { font-size: 17px; }
            .metal-price { font-size: 16px; }
            .metal-value { font-size: 24px; }
            .metal-item { padding: 20px; min-height: 130px; }
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
            
            <div class="scroll-indicator">
                <span>◀</span>
                <div class="scroll-dots" id="scrollDots"></div>
                <span>▶</span>
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
        let currentViewWindow = 0;
        const MAX_VISIBLE_POINTS = 5;
        
        let isDragging = false;
        let dragStartX = 0;
        let dragCurrentX = 0;
        let dragThreshold = 30;

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
                    let cleanPrice = goldData.price.replace(/[^\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (chartDataRes.success) {
                    chartData = chartDataRes.data;
                    currentViewWindow = 0;
                    updateChart();
                    updateScrollIndicator();
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
            currentViewWindow = 0;
            document.querySelectorAll('.chart-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'ChartTab').classList.add('active');
            updateChart();
            updateScrollIndicator();
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

        function getVisibleData(fullData) {
            if (!fullData || fullData.length === 0) return fullData;
            
            const totalPoints = fullData.length;
            if (totalPoints <= MAX_VISIBLE_POINTS) return fullData;
            
            const totalWindows = Math.ceil(totalPoints / MAX_VISIBLE_POINTS);
            const windowIndex = totalWindows - 1 - currentViewWindow;
            const startIndex = windowIndex * MAX_VISIBLE_POINTS;
            const endIndex = Math.min(startIndex + MAX_VISIBLE_POINTS, totalPoints);
            
            return fullData.slice(startIndex, endIndex);
        }

        function updateScrollIndicator() {
            const dotsContainer = document.getElementById('scrollDots');
            if (!chartData[currentChartPeriod]) {
                dotsContainer.innerHTML = '';
                return;
            }
            
            const totalPoints = chartData[currentChartPeriod].length;
            const totalWindows = Math.ceil(totalPoints / MAX_VISIBLE_POINTS);
            
            if (totalWindows <= 1) {
                dotsContainer.innerHTML = '';
                return;
            }
            
            dotsContainer.innerHTML = '';
            for (let i = 0; i < totalWindows; i++) {
                const dot = document.createElement('div');
                dot.className = 'scroll-dot';
                if (i === (totalWindows - 1 - currentViewWindow)) {
                    dot.classList.add('active');
                }
                dotsContainer.appendChild(dot);
            }
        }
# PARÇA 3/3 - JavaScript updateChart fonksiyonu ve Flask routes

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
            
            const fullData = chartData[currentChartPeriod];
            const visibleData = getVisibleData(fullData);
            
            const labels = visibleData.map(item => {
                if (currentChartPeriod === 'daily') return item.time;
                if (currentChartPeriod === 'weekly') return item.day;
                return item.period;
            });
            
            const goldPortfolioData = visibleData.map(item => goldAmount * item.gold_price);
            const silverPortfolioData = visibleData.map(item => silverAmount * item.silver_price);
            
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            
            if (portfolioChart) {
                portfolioChart.destroy();
            }
            
            const datasets = [];
            
            if (visibleDatasets.gold && goldAmount > 0) {
                const goldGradient = ctx.createLinearGradient(0, 0, 0, 300);
                goldGradient.addColorStop(0, 'rgba(243, 156, 18, 0.6)');
                goldGradient.addColorStop(0.5, 'rgba(243, 156, 18, 0.3)');
                goldGradient.addColorStop(1, 'rgba(243, 156, 18, 0.05)');
                
                datasets.push({
                    label: 'Altın Portföyü',
                    data: goldPortfolioData,
                    borderColor: '#f39c12',
                    backgroundColor: goldGradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#f39c12',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#f39c12',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 3
                });
            }
            
            if (visibleDatasets.silver && silverAmount > 0) {
                const silverGradient = ctx.createLinearGradient(0, 0, 0, 300);
                silverGradient.addColorStop(0, 'rgba(149, 165, 166, 0.6)');
                silverGradient.addColorStop(0.5, 'rgba(149, 165, 166, 0.3)');
                silverGradient.addColorStop(1, 'rgba(149, 165, 166, 0.05)');
                
                datasets.push({
                    label: 'Gümüş Portföyü',
                    data: silverPortfolioData,
                    borderColor: '#95a5a6',
                    backgroundColor: silverGradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#95a5a6',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#95a5a6',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 3
                });
            }
            
            portfolioChart = new Chart(ctx, {
                type: 'line',
                data: { labels: labels, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 },
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            displayColors: true,
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) label += ': ';
                                    if (context.parsed.y !== null) {
                                        label += formatCurrency(context.parsed.y);
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: true, color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                            ticks: { font: { size: 11, weight: '600' }, color: '#6c757d' }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                            ticks: {
                                font: { size: 11, weight: '600' },
                                color: '#6c757d',
                                callback: function(value) {
                                    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M₺';
                                    else if (value >= 1000) return (value / 1000).toFixed(0) + 'K₺';
                                    return new Intl.NumberFormat('tr-TR', {maximumFractionDigits: 0}).format(value) + '₺';
                                }
                            }
                        }
                    },
                    elements: { line: { borderJoinStyle: 'round', borderCapStyle: 'round' } },
                    animation: { duration: 750, easing: 'easeInOutQuart' }
                }
            });
        }

        // Mouse & Touch events
        const chartWrapper = document.getElementById('portfolioChart');
        
        chartWrapper.addEventListener('mousedown', function(e) {
            if (!chartData[currentChartPeriod]) return;
            isDragging = true;
            dragStartX = e.clientX;
            chartWrapper.parentElement.classList.add('dragging');
            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            dragCurrentX = e.clientX;
        });

        document.addEventListener('mouseup', function(e) {
            if (!isDragging) return;
            isDragging = false;
            chartWrapper.parentElement.classList.remove('dragging');
            
            const dragDistance = dragStartX - dragCurrentX;
            if (Math.abs(dragDistance) > dragThreshold) {
                const totalPoints = chartData[currentChartPeriod].length;
                const maxWindows = Math.ceil(totalPoints / MAX_VISIBLE_POINTS) - 1;
                
                if (dragDistance < 0 && currentViewWindow < maxWindows) {
                    currentViewWindow++;
                    updateChart();
                    updateScrollIndicator();
                } else if (dragDistance > 0 && currentViewWindow > 0) {
                    currentViewWindow--;
                    updateChart();
                    updateScrollIndicator();
                }
            }
            dragStartX = 0;
            dragCurrentX = 0;
        });

        let touchStartX = 0;
        chartWrapper.addEventListener('touchstart', function(e) {
            if (!chartData[currentChartPeriod]) return;
            touchStartX = e.changedTouches[0].clientX;
            chartWrapper.parentElement.classList.add('dragging');
        }, { passive: true });

        chartWrapper.addEventListener('touchend', function(e) {
            if (!chartData[currentChartPeriod]) return;
            chartWrapper.parentElement.classList.remove('dragging');
            
            const touchEndX = e.changedTouches[0].clientX;
            const swipeDistance = touchStartX - touchEndX;
            
            if (Math.abs(swipeDistance) > 50) {
                const totalPoints = chartData[currentChartPeriod].length;
                const maxWindows = Math.ceil(totalPoints / MAX_VISIBLE_POINTS) - 1;
                
                if (swipeDistance < 0 && currentViewWindow < maxWindows) {
                    currentViewWindow++;
                    updateChart();
                    updateScrollIndicator();
                } else if (swipeDistance > 0 && currentViewWindow > 0) {
                    currentViewWindow--;
                    updateChart();
                    updateScrollIndicator();
                }
            }
        });

        document.addEventListener('keydown', function(e) {
            if (!chartData[currentChartPeriod]) return;
            const totalPoints = chartData[currentChartPeriod].length;
            const maxWindows = Math.ceil(totalPoints / MAX_VISIBLE_POINTS) - 1;
            
            if (e.key === 'ArrowLeft' && currentViewWindow < maxWindows) {
                currentViewWindow++;
                updateChart();
                updateScrollIndicator();
            } else if (e.key === 'ArrowRight' && currentViewWindow > 0) {
                currentViewWindow--;
                updateChart();
                updateScrollIndicator();
            }
        });

        document.getElementById('scrollDots').addEventListener('click', function(e) {
            if (e.target.classList.contains('scroll-dot')) {
                const dots = Array.from(this.children);
                const clickedIndex = dots.indexOf(e.target);
                if (clickedIndex !== -1) {
                    const totalPoints = chartData[currentChartPeriod].length;
                    const totalWindows = Math.ceil(totalPoints / MAX_VISIBLE_POINTS);
                    currentViewWindow = totalWindows - 1 - clickedIndex;
                    updateChart();
                    updateScrollIndicator();
                }
            }
        });

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
                updateScrollIndicator();
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
            const goldAmount = document.getElementById('goldAmount').value;
            const silverAmount = document.getElementById('silverAmount').value;
            const expiryDate = new Date();
            expiryDate.setFullYear(expiryDate.getFullYear() + 1);
            document.cookie = `goldAmount=${goldAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
            document.cookie = `silverAmount=${silverAmount}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
            window.portfolioData = { gold: goldAmount, silver: silverAmount };
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
                window.portfolioData = null;
                updatePortfolio();
            }
        }

        function formatCurrency(amount) {
            return new Intl.NumberFormat('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(amount) + '₺';
        }

        function formatPrice(price) {
            if (!price) return '0,00₺';
            return new Intl.NumberFormat('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(price) + '₺';
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
    print("=" * 70)
    print("🚀 Metal Fiyat Takipçisi v3.1.0 - GRADIENT EDITION")
    print("=" * 70)
    print(f"🌐 Server: http://localhost:{port}")
    print(f"📱 Mobile: http://0.0.0.0:{port}")
    print("=" * 70)
    print("✨ Özellikler:")
    print("  • 🎨 Gradient area chart")
    print("  • 💎 Hover noktalar (5-8px)")
    print("  • 🖱️  Mouse drag + Touch swipe")
    print("  • 💾 Cookie kalıcı kayıt")
    print("  • 📊 Max 5 veri noktası")
    print("=" * 70)
    app.run(host='0.0.0.0', port=port, debug=False)