#!/usr/bin/env python3
# Metal Fiyat Takipçisi v2.4.0
# Son Güncelleme: 22.09.2025
# GitHub Actions entegrasyonlu

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Fiyat Takipçisi</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #667eea 100%);
            min-height: 100vh; padding: 20px; overflow-x: hidden;
        }
        .app-container {
            max-width: 380px; margin: 0 auto;
            display: flex; flex-direction: column; gap: 20px;
        }
        
        /* Header */
        .header {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 16px 20px; border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .logo { font-size: 20px; font-weight: 700; color: white; }
        .actions {
            display: flex; gap: 10px;
        }
        .action-btn {
            width: 44px; height: 44px; border-radius: 12px;
            background: rgba(255, 255, 255, 0.2); border: none;
            color: white; font-size: 18px; cursor: pointer;
            transition: all 0.3s ease; display: flex; align-items: center; justify-content: center;
        }
        .action-btn:hover { background: rgba(255, 255, 255, 0.3); transform: scale(1.05); }
        
        /* Portfolio Summary */
        .portfolio-summary {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            border-radius: 20px; padding: 24px; color: white;
            box-shadow: 0 10px 30px rgba(238, 90, 36, 0.3);
            display: none;
        }
        .portfolio-title { font-size: 14px; opacity: 0.9; margin-bottom: 8px; font-weight: 500; }
        .portfolio-amount { font-size: 32px; font-weight: 800; margin-bottom: 16px; }
        .portfolio-breakdown {
            display: flex; justify-content: space-between; gap: 16px;
        }
        .breakdown-item { flex: 1; text-align: center; }
        .breakdown-label { font-size: 11px; opacity: 0.8; margin-bottom: 4px; }
        .breakdown-value { font-size: 16px; font-weight: 600; }
        
        /* Price Cards */
        .price-cards { display: flex; flex-direction: column; gap: 16px; }
        .price-card {
            background: rgba(255, 255, 255, 0.95); border-radius: 16px;
            padding: 20px; box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .price-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
        }
        .metal-info { display: flex; align-items: center; gap: 12px; }
        .metal-icon {
            width: 40px; height: 40px; border-radius: 10px; display: flex;
            align-items: center; justify-content: center; font-size: 18px;
        }
        .metal-icon.gold { background: linear-gradient(135deg, #f39c12, #d35400); color: white; }
        .metal-icon.silver { background: linear-gradient(135deg, #95a5a6, #7f8c8d); color: white; }
        .metal-details h3 { font-size: 16px; font-weight: 600; color: #2c3e50; margin-bottom: 4px; }
        .metal-details p { font-size: 12px; color: #7f8c8d; }
        .price-value { font-size: 24px; font-weight: 800; color: #2c3e50; }
        .price-change {
            display: flex; align-items: center; gap: 4px; margin-top: 8px;
            font-size: 12px; font-weight: 500;
        }
        
        /* Stats Card */
        .stats-card {
            background: rgba(255, 255, 255, 0.95); border-radius: 16px;
            padding: 20px; box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: none;
        }
        .stats-header {
            display: flex; justify-content: between; align-items: center; margin-bottom: 16px;
        }
        .stats-title { font-size: 18px; font-weight: 700; color: #2c3e50; }
        .chart-container {
            position: relative; height: 200px; margin-bottom: 16px;
        }
        .stats-summary {
            display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
        }
        .stat-item {
            background: #f8f9fa; padding: 12px; border-radius: 8px; text-align: center;
        }
        .stat-label { font-size: 11px; color: #6c757d; margin-bottom: 4px; }
        .stat-value { font-size: 16px; font-weight: 600; color: #2c3e50; }
        
        /* Status Bar */
        .status-bar {
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 12px; padding: 12px 16px; border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex; justify-content: space-between; align-items: center;
        }
        .status-text { color: white; font-size: 14px; font-weight: 500; }
        .status-time { color: rgba(255, 255, 255, 0.8); font-size: 12px; }
        
        /* Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(10px);
            z-index: 1000; display: none; align-items: center; justify-content: center;
            padding: 20px;
        }
        .modal-content {
            background: white; border-radius: 20px; padding: 24px;
            width: 100%; max-width: 340px; position: relative;
        }
        .modal-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
        }
        .modal-title { font-size: 20px; font-weight: 700; color: #2c3e50; }
        .close-btn {
            width: 32px; height: 32px; border-radius: 8px; background: #f8f9fa;
            border: none; font-size: 16px; cursor: pointer; display: flex;
            align-items: center; justify-content: center;
        }
        .input-group { margin-bottom: 20px; }
        .input-label {
            display: block; margin-bottom: 8px; font-weight: 600;
            color: #2c3e50; font-size: 14px;
        }
        .input-field {
            width: 100%; padding: 14px; border: 2px solid #e9ecef;
            border-radius: 12px; font-size: 16px; transition: border-color 0.3s;
            background: #f8f9fa;
        }
        .input-field:focus {
            outline: none; border-color: #667eea; background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }
        .modal-actions {
            display: flex; gap: 12px; justify-content: flex-end;
        }
        .btn {
            padding: 12px 20px; border-radius: 10px; font-weight: 600;
            cursor: pointer; transition: all 0.3s; border: none; font-size: 14px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #e9ecef; color: #6c757d; }
        .btn:hover { transform: translateY(-1px); }
        
        /* Loading */
        .loading { opacity: 0.6; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Header -->
        <div class="header">
            <div class="logo">Metal Tracker</div>
            <div class="actions">
                <button class="action-btn" onclick="fetchPrice()" id="refreshBtn" title="Yenile">⟳</button>
                <button class="action-btn" onclick="toggleStats()" id="statsBtn" title="İstatistikler">📊</button>
                <button class="action-btn" onclick="togglePortfolio()" title="Portföy">⚙</button>
            </div>
        </div>
        
        <!-- Portfolio Summary -->
        <div class="portfolio-summary" id="portfolioSummary">
            <div class="portfolio-title">Toplam Portföy Değeri</div>
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="portfolio-breakdown">
                <div class="breakdown-item">
                    <div class="breakdown-label">Altın</div>
                    <div class="breakdown-value" id="goldBreakdown">0g • 0₺</div>
                </div>
                <div class="breakdown-item">
                    <div class="breakdown-label">Gümüş</div>
                    <div class="breakdown-value" id="silverBreakdown">0g • 0₺</div>
                </div>
            </div>
        </div>
        
        <!-- Stats Card -->
        <div class="stats-card" id="statsCard">
            <div class="stats-header">
                <div class="stats-title">Son 24 Saat</div>
            </div>
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
            <div class="stats-summary" id="statsSummary">
                <!-- Stats will be inserted here -->
            </div>
        </div>
        
        <!-- Price Cards -->
        <div class="price-cards">
            <div class="price-card">
                <div class="price-header">
                    <div class="metal-info">
                        <div class="metal-icon gold">Au</div>
                        <div class="metal-details">
                            <h3>Altın</h3>
                            <p>Yapı Kredi • Gram</p>
                        </div>
                    </div>
                    <div class="price-value" id="goldPrice">-.--₺</div>
                </div>
                <div class="price-change">
                    <span id="goldChange">Son güncelleme bekleniyor</span>
                </div>
            </div>
            
            <div class="price-card">
                <div class="price-header">
                    <div class="metal-info">
                        <div class="metal-icon silver">Ag</div>
                        <div class="metal-details">
                            <h3>Gümüş</h3>
                            <p>Vakıfbank • Gram</p>
                        </div>
                    </div>
                    <div class="price-value" id="silverPrice">-.--₺</div>
                </div>
                <div class="price-change">
                    <span id="silverChange">Son güncelleme bekleniyor</span>
                </div>
            </div>
        </div>
        
        <!-- Status Bar -->
        <div class="status-bar">
            <div class="status-text" id="statusText">Veriler yükleniyor...</div>
            <div class="status-time" id="statusTime">--:--</div>
        </div>
    </div>
    
    <!-- Portfolio Modal -->
    <div class="modal-overlay" id="portfolioModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Portföy Ayarları</div>
                <button class="close-btn" onclick="closePortfolioModal()">×</button>
            </div>
            
            <div class="input-group">
                <label class="input-label" for="goldAmount">Altın Miktarı (gram)</label>
                <input type="number" class="input-field" id="goldAmount" placeholder="0.0" 
                       step="0.1" min="0" oninput="updatePortfolio()">
            </div>
            
            <div class="input-group">
                <label class="input-label" for="silverAmount">Gümüş Miktarı (gram)</label>
                <input type="number" class="input-field" id="silverAmount" placeholder="0.0" 
                       step="0.1" min="0" oninput="updatePortfolio()">
            </div>
            
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="clearPortfolio()">Sıfırla</button>
                <button class="btn btn-primary" onclick="closePortfolioModal()">Tamam</button>
            </div>
        </div>
    </div>

    <script>
        let currentGoldPrice = 0;
        let currentSilverPrice = 0;
        let priceChart = null;
        let historicalData = null;

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            const statusText = document.getElementById('statusText');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                refreshBtn.style.transition = 'transform 0.5s ease';
                statusText.textContent = 'Güncelleştiriliyor...';
                
                const [goldResponse, silverResponse] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price')
                ]);
                
                const goldData = await goldResponse.json();
                const silverData = await silverResponse.json();
                
                let successCount = 0;
                
                if (goldData.success) {
                    document.getElementById('goldPrice').textContent = goldData.price + '₺';
                    document.getElementById('goldChange').textContent = 'Güncel veri';
                    let cleanPrice = goldData.price.replace(/[^\\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                    successCount++;
                }
                
                if (silverData.success) {
                    document.getElementById('silverPrice').textContent = silverData.price + '₺';
                    document.getElementById('silverChange').textContent = 'Güncel veri';
                    let cleanPrice = silverData.price.replace(/[^\\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                    successCount++;
                }
                
                statusText.textContent = successCount === 2 ? 'Tüm veriler güncel' : 'Kısmi güncelleme';
                document.getElementById('statusTime').textContent = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                
                updatePortfolio();
                
            } catch (error) {
                statusText.textContent = 'Güncelleme hatası';
                console.error('Fetch error:', error);
            } finally {
                setTimeout(() => {
                    refreshBtn.style.transform = 'rotate(0deg)';
                }, 500);
            }
        }

        async function loadHistoricalData() {
            try {
                const response = await fetch('/api/historical-data');
                const data = await response.json();
                if (data.success) {
                    historicalData = data.data;
                    return data.data;
                }
            } catch (error) {
                console.error('Historical data load error:', error);
            }
            return null;
        }

        function toggleStats() {
            const statsCard = document.getElementById('statsCard');
            const statsBtn = document.getElementById('statsBtn');
            
            if (statsCard.style.display === 'none') {
                statsCard.style.display = 'block';
                loadAndDisplayStats();
            } else {
                statsCard.style.display = 'none';
            }
        }

        async function loadAndDisplayStats() {
            const data = await loadHistoricalData();
            if (!data || !data.prices || data.prices.length === 0) {
                document.getElementById('statsSummary').innerHTML = '<div style="text-align: center; color: #6c757d; grid-column: 1/-1;">Henüz yeterli veri yok</div>';
                return;
            }

            // Son 24 saatlik veri
            const last24h = data.prices.slice(-24);
            
            if (last24h.length === 0) return;

            // Chart oluştur
            createPriceChart(last24h);
            
            // İstatistikler hesapla
            const goldPrices = last24h.filter(p => p.gold_price).map(p => p.gold_price);
            const silverPrices = last24h.filter(p => p.silver_price).map(p => p.silver_price);
            
            const goldStats = calculateStats(goldPrices);
            const silverStats = calculateStats(silverPrices);
            
            // İstatistikleri göster
            const summaryHtml = `
                <div class="stat-item">
                    <div class="stat-label">Altın Ortalama</div>
                    <div class="stat-value">${goldStats.avg.toFixed(2)}₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Gümüş Ortalama</div>
                    <div class="stat-value">${silverStats.avg.toFixed(2)}₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Altın Min/Max</div>
                    <div class="stat-value">${goldStats.min.toFixed(2)} / ${goldStats.max.toFixed(2)}₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Gümüş Min/Max</div>
                    <div class="stat-value">${silverStats.min.toFixed(2)} / ${silverStats.max.toFixed(2)}₺</div>
                </div>
            `;
            
            document.getElementById('statsSummary').innerHTML = summaryHtml;
        }

        function calculateStats(prices) {
            if (prices.length === 0) return { avg: 0, min: 0, max: 0 };
            
            const avg = prices.reduce((sum, p) => sum + p, 0) / prices.length;
            const min = Math.min(...prices);
            const max = Math.max(...prices);
            
            return { avg, min, max };
        }

        function createPriceChart(data) {
            const ctx = document.getElementById('priceChart').getContext('2d');
            
            if (priceChart) {
                priceChart.destroy();
            }
            
            const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'}));
            const goldData = data.map(d => d.gold_price);
            const silverData = data.map(d => d.silver_price);
            
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Altın',
                            data: goldData,
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.1)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.1
                        },
                        {
                            label: 'Gümüş',
                            data: silverData,
                            borderColor: '#95a5a6',
                            backgroundColor: 'rgba(149, 165, 166, 0.1)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.1,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: {
                                drawOnChartArea: false,
                            },
                        }
                    }
                }
            });
        }

        function togglePortfolio() {
            document.getElementById('portfolioModal').style.display = 'flex';
        }

        function closePortfolioModal() {
            document.getElementById('portfolioModal').style.display = 'none';
        }

        function updatePortfolio() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            const portfolioSummary = document.getElementById('portfolioSummary');
            
            if (totalValue > 0) {
                portfolioSummary.style.display = 'block';
                document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
                document.getElementById('goldBreakdown').textContent = goldAmount.toFixed(1) + 'g • ' + formatCurrency(goldValue);
                document.getElementById('silverBreakdown').textContent = silverAmount.toFixed(1) + 'g • ' + formatCurrency(silverValue);
            } else {
                portfolioSummary.style.display = 'none';
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
                const goldAmount = localStorage.getItem('goldAmount');
                const silverAmount = localStorage.getItem('silverAmount');
                if (goldAmount) document.getElementById('goldAmount').value = goldAmount;
                if (silverAmount) document.getElementById('silverAmount').value = silverAmount;
            } catch (e) {}
        }

        function clearPortfolio() {
            if (confirm('Portföy verilerini sıfırlamak istediğinizden emin misiniz?')) {
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
                style: 'decimal',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(amount) + '₺';
        }

        // Modal dışına tıklayınca kapat
        document.getElementById('portfolioModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closePortfolioModal();
            }
        });

        window.onload = function() {
            loadPortfolio();
            fetchPrice();
            updatePortfolio();
        };
    </script>
</body>
</html>'''

def get_gold_price():
    """Yapı Kredi altın fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '6-gram-altin',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
        
        alt_element = soup.find('span', {
            'data-socket-key': lambda x: x and 'gram-altin' in x,
            'data-socket-attr': 'bid'
        })
        
        if alt_element:
            return alt_element.get_text(strip=True)
            
        return None
        
    except Exception as e:
        raise Exception(f"Altın veri çekme hatası: {str(e)}")

def get_silver_price():
    """Vakıfbank gümüş fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/vakifbank/gumus"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '5-gumus',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
        
        price_element = soup.find('span', {
            'data-socket-key': lambda x: x and 'gumus' in x.lower(),
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
            
        return None
        
    except Exception as e:
        raise Exception(f"Gümüş veri çekme hatası: {str(e)}")

def load_historical_data():
    """GitHub'dan toplanan geçmiş verileri yükle"""
    try:
        # GitHub Raw URL
        github_url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/data/prices.json"
        
        response = requests.get(github_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            # Yerel dosya varsa onu kullan
            if os.path.exists('data/prices.json'):
                with open('data/prices.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
    except Exception as e:
        print(f"Historical data load error: {e}")
    
    return {"prices": [], "last_updated": None}

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/gold-price')
def api_gold_price():
    """Altın fiyatı API endpoint"""
    try:
@app.route('/api/gold-price')
def api_gold_price():
    """Altın fiyatı API endpoint"""
    try:
        price = get_gold_price()
        if price:
            return jsonify({'success': True, 'price': price})
        else:
            return jsonify({'success': False, 'error': 'Altın fiyat elementi bulunamadı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/silver-price')
def api_silver_price():
    """Gümüş fiyatı API endpoint"""
    try:
        price = get_silver_price()
        if price:
            return jsonify({'success': True, 'price': price})
        else:
            return jsonify({'success': False, 'error': 'Gümüş fiyat elementi bulunamadı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/historical-data')
def api_historical_data():
    """Geçmiş veriler API endpoint"""
    try:
        data = load_historical_data()
        if data and 'prices' in data:
            return jsonify({'success': True, 'data': data})
        else:
            return jsonify({'success': False, 'error': 'Geçmiş veri bulunamadı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🏆 Metal Fiyat Takipçisi v2.4.0")
    print("📊 GitHub Actions entegrasyonlu")
    print("📈 İstatistik ve grafik özellikleri")
    print(f"📱 URL: http://localhost:{port}")
    print("⚡ Flask 3.0.0 | Python 3.13.4")
    print("⏹️  Durdurmak için Ctrl+C")
    print("-" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)