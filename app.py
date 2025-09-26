#!/usr/bin/env python3
# Metal Fiyat Takipçisi v2.5.0
# Son Güncelleme: 21.09.2025
# Python 3.13.4 | Flask 3.0.0

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Fiyat Takipçisi</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #667eea 100%);
            min-height: 100vh; padding: 20px; overflow-x: hidden;
        }
        .app-container {
            max-width: 390px; margin: 0 auto;
            display: flex; flex-direction: column; gap: 20px;
        }
        
        /* Header */
        .header {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 16px 20px; border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .logo { font-size: 20px; font-weight: 700; color: white; }
        .actions { display: flex; gap: 10px; }
        .action-btn {
            width: 44px; height: 44px; border-radius: 12px;
            background: rgba(255, 255, 255, 0.2); border: none;
            color: white; font-size: 18px; cursor: pointer;
            transition: all 0.3s ease; display: flex; align-items: center; justify-content: center;
        }
        .action-btn:hover { background: rgba(255, 255, 255, 0.3); transform: scale(1.05); }
        
        /* Portfolio Summary - Enhanced */
        .portfolio-summary {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            border-radius: 24px; padding: 28px; color: white;
            box-shadow: 0 15px 35px rgba(238, 90, 36, 0.4);
            display: none; text-align: center;
        }
        .portfolio-amount { 
            font-size: 42px; font-weight: 900; margin-bottom: 20px; 
            text-align: center; letter-spacing: -1px;
        }
        .portfolio-breakdown {
            display: flex; justify-content: space-between; gap: 20px;
            margin-top: 16px;
        }
        .breakdown-item { flex: 1; text-align: center; }
        .breakdown-label { font-size: 12px; opacity: 0.8; margin-bottom: 6px; }
        .breakdown-value { font-size: 22px; font-weight: 700; }
        
        /* Stats Tabs */
        .stats-container {
            background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(20px);
            border-radius: 20px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.2);
            display: none;
        }
        .stats-tabs {
            display: flex; gap: 8px; margin-bottom: 20px;
            background: rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 4px;
        }
        .tab-btn {
            flex: 1; padding: 10px; border: none; border-radius: 8px;
            background: transparent; color: rgba(255, 255, 255, 0.7);
            font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .tab-btn.active {
            background: white; color: #2c3e50;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .stats-content { min-height: 200px; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .stat-card {
            background: rgba(255, 255, 255, 0.15); border-radius: 12px; 
            padding: 16px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .stat-title { color: white; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
        .stat-price { color: white; font-size: 16px; font-weight: 700; margin-bottom: 4px; }
        .stat-portfolio { 
            font-size: 18px; font-weight: 800; margin-top: 6px;
            background: linear-gradient(45deg, #4ade80, #22c55e);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .stat-change {
            font-size: 11px; margin-top: 4px; padding: 2px 6px;
            border-radius: 6px; font-weight: 500;
        }
        .stat-change.up { background: rgba(74, 222, 128, 0.2); color: #4ade80; }
        .stat-change.down { background: rgba(248, 113, 113, 0.2); color: #f87171; }
        
        /* Price Cards */
        .price-cards { display: flex; flex-direction: column; gap: 16px; }
        .price-card {
            background: rgba(255, 255, 255, 0.95); border-radius: 18px;
            padding: 22px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        .price-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;
        }
        .metal-info { display: flex; align-items: center; gap: 14px; }
        .metal-icon {
            width: 44px; height: 44px; border-radius: 12px; display: flex;
            align-items: center; justify-content: center; font-size: 18px; font-weight: 700;
        }
        .metal-icon.gold { background: linear-gradient(135deg, #f39c12, #d35400); color: white; }
        .metal-icon.silver { background: linear-gradient(135deg, #95a5a6, #7f8c8d); color: white; }
        .metal-details h3 { font-size: 17px; font-weight: 700; color: #2c3e50; margin-bottom: 4px; }
        .metal-details p { font-size: 13px; color: #7f8c8d; }
        .price-value { font-size: 26px; font-weight: 800; color: #2c3e50; }
        .price-change {
            display: flex; align-items: center; gap: 6px; margin-top: 10px;
            font-size: 13px; font-weight: 500;
        }
        
        /* Status */
        .status-bar {
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 14px; padding: 14px 18px; border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex; justify-content: space-between; align-items: center;
        }
        .status-text { color: white; font-size: 15px; font-weight: 600; }
        .status-time { color: rgba(255, 255, 255, 0.8); font-size: 13px; }
        
        /* Portfolio Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(12px);
            z-index: 1000; display: none; align-items: center; justify-content: center;
            padding: 20px;
        }
        .modal-content {
            background: white; border-radius: 24px; padding: 28px;
            width: 100%; max-width: 350px; position: relative;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .modal-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;
        }
        .modal-title { font-size: 22px; font-weight: 800; color: #2c3e50; }
        .close-btn {
            width: 36px; height: 36px; border-radius: 10px; background: #f8f9fa;
            border: none; font-size: 18px; cursor: pointer; display: flex;
            align-items: center; justify-content: center; font-weight: 600;
        }
        .input-group { margin-bottom: 22px; }
        .input-label {
            display: block; margin-bottom: 10px; font-weight: 700;
            color: #2c3e50; font-size: 15px;
        }
        .input-field {
            width: 100%; padding: 16px; border: 2px solid #e9ecef;
            border-radius: 14px; font-size: 17px; transition: border-color 0.3s;
            background: #f8f9fa; font-weight: 600;
        }
        .input-field:focus {
            outline: none; border-color: #667eea; background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }
        .modal-actions {
            display: flex; gap: 14px; justify-content: flex-end;
        }
        .btn {
            padding: 14px 24px; border-radius: 12px; font-weight: 700;
            cursor: pointer; transition: all 0.3s; border: none; font-size: 15px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #e9ecef; color: #6c757d; }
        .btn:hover { transform: translateY(-2px); }
        
        /* Animations */
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; } }
        
        /* Responsive */
        @media (max-width: 400px) {
            .app-container { max-width: 100%; padding: 0 10px; }
            .portfolio-breakdown { flex-direction: column; gap: 12px; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Header -->
        <div class="header">
            <div class="logo">Metal Tracker</div>
            <div class="actions">
                <button class="action-btn" onclick="fetchPrice()" id="refreshBtn" title="Yenile">⟳</button>
                <button class="action-btn" onclick="togglePortfolio()" title="Portföy">⚙</button>
            </div>
        </div>
        
        <!-- Portfolio Summary -->
        <div class="portfolio-summary" id="portfolioSummary">
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="portfolio-breakdown">
                <div class="breakdown-item">
                    <div class="breakdown-label">Altın</div>
                    <div class="breakdown-value" id="goldBreakdown">0₺</div>
                </div>
                <div class="breakdown-item">
                    <div class="breakdown-label">Gümüş</div>
                    <div class="breakdown-value" id="silverBreakdown">0₺</div>
                </div>
            </div>
        </div>
        
        <!-- Stats Container -->
        <div class="stats-container" id="statsContainer">
            <div class="stats-tabs">
                <button class="tab-btn active" onclick="switchTab('daily')" id="dailyTab">Günlük</button>
                <button class="tab-btn" onclick="switchTab('weekly')" id="weeklyTab">Haftalık</button>
                <button class="tab-btn" onclick="switchTab('monthly')" id="monthlyTab">Aylık</button>
            </div>
            <div class="stats-content">
                <div class="stats-grid" id="statsGrid">
                    <!-- Stats will be populated here -->
                </div>
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
        let allStats = {};
        let currentTab = 'daily';

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            const statusText = document.getElementById('statusText');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                refreshBtn.style.transition = 'transform 0.5s ease';
                statusText.textContent = 'Güncelleştiriliyor...';
                
                const [goldResponse, silverResponse, statsResponse] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/period-stats')
                ]);
                
                const goldData = await goldResponse.json();
                const silverData = await silverResponse.json();
                const statsData = await statsResponse.json();
                
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
                
                if (statsData.success) {
                    allStats = statsData.data;
                    updateStatsDisplay();
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

        function switchTab(period) {
            currentTab = period;
            
            // Update tab buttons
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            updateStatsDisplay();
        }

        function updateStatsDisplay() {
            const statsGrid = document.getElementById('statsGrid');
            const stats = allStats[currentTab];
            
            if (!stats) {
                statsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.7); padding: 40px;">Veri bulunamadı</div>';
                return;
            }
            
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-title">Altın En Yüksek</div>
                    <div class="stat-price">${formatPrice(stats.gold_high)}</div>
                    ${goldAmount > 0 ? `<div class="stat-portfolio">${formatCurrency(goldAmount * stats.gold_high)}</div>` : ''}
                </div>
                <div class="stat-card">
                    <div class="stat-title">Altın En Düşük</div>
                    <div class="stat-price">${formatPrice(stats.gold_low)}</div>
                    ${goldAmount > 0 ? `<div class="stat-portfolio">${formatCurrency(goldAmount * stats.gold_low)}</div>` : ''}
                </div>
                <div class="stat-card">
                    <div class="stat-title">Gümüş En Yüksek</div>
                    <div class="stat-price">${formatPrice(stats.silver_high)}</div>
                    ${silverAmount > 0 ? `<div class="stat-portfolio">${formatCurrency(silverAmount * stats.silver_high)}</div>` : ''}
                </div>
                <div class="stat-card">
                    <div class="stat-title">Gümüş En Düşük</div>
                    <div class="stat-price">${formatPrice(stats.silver_low)}</div>
                    ${silverAmount > 0 ? `<div class="stat-portfolio">${formatCurrency(silverAmount * stats.silver_low)}</div>` : ''}
                </div>
            `;
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
            const statsContainer = document.getElementById('statsContainer');
            
            if (totalValue > 0) {
                portfolioSummary.style.display = 'block';
                statsContainer.style.display = 'block';
                document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
                document.getElementById('goldBreakdown').textContent = formatCurrency(goldValue);
                document.getElementById('silverBreakdown').textContent = formatCurrency(silverValue);
                updateStatsDisplay();
            } else {
                portfolioSummary.style.display = 'none';
                statsContainer.style.display = 'none';
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

        function formatPrice(price) {
            if (!price) return '-₺';
            return new Intl.NumberFormat('tr-TR', {
                style: 'decimal',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(price) + '₺';
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

def load_price_history():
    """GitHub'dan fiyat geçmişini yükler"""
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/data/price-history.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"records": []}
    except Exception as e:
        print(f"Price history yükleme hatası: {e}")
        return {"records": []}

def calculate_period_stats():
    """Günlük, haftalık ve aylık istatistikleri hesaplar"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return None
        
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Filtreleme fonksiyonu
        def filter_records(start_date):
            return [r for r in records 
                   if r.get("date") >= start_date 
                   and r.get("gold_price") and r.get("silver_price")]
        
        daily_records = filter_records(today)
        weekly_records = filter_records(week_ago)
        monthly_records = filter_records(month_ago)
        
        def calculate_stats(records_list):
            if not records_list:
                return None
            gold_prices = [r["gold_price"] for r in records_list]
            silver_prices = [r["silver_price"] for r in records_list]
            return {
                "gold_high": max(gold_prices),
                "gold_low": min(gold_prices),
                "silver_high": max(silver_prices),
                "silver_low": min(silver_prices),
                "records_count": len(records_list)
            }
        
        return {
            "daily": calculate_stats(daily_records),
            "weekly": calculate_stats(weekly_records),
            "monthly": calculate_stats(monthly_records)
        }
        
    except Exception as e:
        print(f"Period stats hesaplama hatası: {e}")
        return None

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