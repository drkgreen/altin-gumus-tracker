#!/usr/bin/env python3
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os

app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Fiyat Takipçisi</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        .title {
            color: #333;
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #f39c12, #d35400);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle { color: #666; font-size: 14px; margin-bottom: 30px; }
        .price-display {
            background: linear-gradient(135deg, #f39c12, #d35400);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(243, 156, 18, 0.3);
        }
        .price-display.silver {
            background: linear-gradient(135deg, #95a5a6, #7f8c8d);
            box-shadow: 0 10px 25px rgba(149, 165, 166, 0.3);
        }
        .price-value {
            font-size: 32px;
            font-weight: 900;
            margin-bottom: 5px;
            animation: pulse 2s infinite;
        }
        .price-label { font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }
        .status {
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
            font-weight: 600;
        }
        .status.loading { background: #3498db; color: white; }
        .status.success { background: #2ecc71; color: white; }
        .status.error { background: #e74c3c; color: white; }
        .last-update { color: #666; font-size: 12px; margin-bottom: 15px; }
        .next-update { color: #888; font-size: 12px; margin-bottom: 20px; }
        .controls { display: flex; gap: 10px; justify-content: center; }
        button {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
        .loading-spinner {
            width: 20px; height: 20px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top: 2px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .footer {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(0,0,0,0.1);
            font-size: 12px;
            color: #999;
        }
        .portfolio-section {
            margin-top: 20px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 15px;
            border: 2px solid rgba(102, 126, 234, 0.2);
            animation: slideDown 0.3s ease;
        }
        .portfolio-header {
            text-align: center;
            margin-bottom: 20px;
        }
        .portfolio-header h3 {
            color: #333;
            font-size: 18px;
            margin-bottom: 5px;
        }
        .portfolio-header p {
            color: #666;
            font-size: 12px;
        }
        .input-group {
            margin-bottom: 15px;
        }
        .input-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }
        .input-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s ease;
            background: white;
        }
        .input-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .portfolio-results {
            margin-top: 20px;
            padding: 15px;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 10px;
        }
        .portfolio-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        .portfolio-item:last-child {
            border-bottom: none;
        }
        .metal-name {
            font-weight: 600;
            color: #333;
        }
        .metal-value {
            font-weight: 700;
            color: #f39c12;
        }
        .portfolio-total {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
            padding: 15px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            border-radius: 10px;
            color: white;
        }
        .total-label {
            font-weight: 700;
            font-size: 16px;
        }
        .total-value {
            font-weight: 900;
            font-size: 18px;
            animation: pulse 2s infinite;
        }
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">🏆 METAL FİYATLARI</h1>
        <p class="subtitle">Canlı Piyasa Verileri</p>
        
        <div class="price-display">
            <div class="price-value" id="goldPrice">---.-- TL</div>
            <div class="price-label">Yapı Kredi - Gram Altın</div>
        </div>
        
        <div class="price-display silver">
            <div class="price-value" id="silverPrice">---.-- TL</div>
            <div class="price-label">Vakıfbank - Gram Gümüş</div>
        </div>
        
        <div class="status loading" id="status">
            <span class="loading-spinner"></span>Fiyatlar alınıyor...
        </div>
        
        <div class="last-update" id="lastUpdate">Son güncelleme: Henüz yok</div>
        
        <div class="controls">
            <button onclick="fetchPrice()" id="refreshBtn">🔄 Yenile</button>
            <button onclick="togglePortfolio()" id="portfolioBtn">💰 Portföy</button>
        </div>
        
        <div class="portfolio-section" id="portfolioSection" style="display: none;">
            <div class="portfolio-header">
                <h3>💰 Portföy Hesaplayıcı</h3>
                <p>Elinizdeki metal miktarlarını girin</p>
            </div>
            
            <div class="input-group">
                <label for="goldAmount">🏆 Altın (gram):</label>
                <input type="number" id="goldAmount" placeholder="0" step="0.1" min="0" oninput="calculatePortfolio()">
            </div>
            
            <div class="input-group">
                <label for="silverAmount">🥈 Gümüş (gram):</label>
                <input type="number" id="silverAmount" placeholder="0" step="0.1" min="0" oninput="calculatePortfolio()">
            </div>
            
            <div class="portfolio-results">
                <div class="portfolio-item">
                    <span class="metal-name">🏆 Altın Değeri:</span>
                    <span class="metal-value" id="goldValue">0,00 TL</span>
                </div>
                <div class="portfolio-item">
                    <span class="metal-name">🥈 Gümüş Değeri:</span>
                    <span class="metal-value" id="silverValue">0,00 TL</span>
                </div>
                <div class="portfolio-total">
                    <span class="total-label">💎 TOPLAM DEĞ ER:</span>
                    <span class="total-value" id="totalValue">0,00 TL</span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            API Endpoints: <br>
            <code>/api/gold-price</code> | <code>/api/silver-price</code>
        </div>
    </div>

    <script>
        let currentGoldPrice = 0;
        let currentSilverPrice = 0;

        async function fetchPrice() {
            const statusEl = document.getElementById('status');
            const goldPriceEl = document.getElementById('goldPrice');
            const silverPriceEl = document.getElementById('silverPrice');
            const lastUpdateEl = document.getElementById('lastUpdate');
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                statusEl.className = 'status loading';
                statusEl.innerHTML = '<span class="loading-spinner"></span>Fiyatlar alınıyor...';
                refreshBtn.disabled = true;
                
                // Altın fiyatını al
                const goldResponse = await fetch('/api/gold-price');
                const goldData = await goldResponse.json();
                
                // Gümüş fiyatını al
                const silverResponse = await fetch('/api/silver-price');
                const silverData = await silverResponse.json();
                
                let successCount = 0;
                let errorMessages = [];
                
                if (goldData.success) {
                    goldPriceEl.textContent = goldData.price + ' TL';
                    // Sayısal değeri kaydet (virgülü noktaya çevir)
                    currentGoldPrice = parseFloat(goldData.price.replace(',', '.').replace(/[^\d.]/g, ''));
                    successCount++;
                } else {
                    goldPriceEl.textContent = 'Veri alınamadı';
                    currentGoldPrice = 0;
                    errorMessages.push('Altın: ' + goldData.error);
                }
                
                if (silverData.success) {
                    silverPriceEl.textContent = silverData.price + ' TL';
                    // Sayısal değeri kaydet (virgülü noktaya çevir)
                    currentSilverPrice = parseFloat(silverData.price.replace(',', '.').replace(/[^\d.]/g, ''));
                    successCount++;
                } else {
                    silverPriceEl.textContent = 'Veri alınamadı';
                    currentSilverPrice = 0;
                    errorMessages.push('Gümüş: ' + silverData.error);
                }
                
                if (successCount === 2) {
                    statusEl.className = 'status success';
                    statusEl.textContent = '✅ Tüm fiyatlar güncellendi';
                } else if (successCount === 1) {
                    statusEl.className = 'status success';
                    statusEl.textContent = '⚠️ Kısmi güncelleme başarılı';
                } else {
                    statusEl.className = 'status error';
                    statusEl.textContent = '❌ Fiyatlar alınamadı';
                }
                
                lastUpdateEl.textContent = `Son güncelleme: ${new Date().toLocaleTimeString('tr-TR')}`;
                
                // Portföy hesaplamasını güncelle
                calculatePortfolio();
                
            } catch (error) {
                console.error('Hata:', error);
                statusEl.className = 'status error';
                statusEl.textContent = `❌ Hata: ${error.message}`;
                goldPriceEl.textContent = 'Veri alınamadı';
                silverPriceEl.textContent = 'Veri alınamadı';
            } finally {
                refreshBtn.disabled = false;
            }
        }

        function togglePortfolio() {
            const portfolioSection = document.getElementById('portfolioSection');
            const portfolioBtn = document.getElementById('portfolioBtn');
            
            if (portfolioSection.style.display === 'none') {
                portfolioSection.style.display = 'block';
                portfolioBtn.textContent = '📊 Gizle';
                calculatePortfolio();
            } else {
                portfolioSection.style.display = 'none';
                portfolioBtn.textContent = '💰 Portföy';
            }
        }

        function calculatePortfolio() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            // Türk lirası formatında göster
            document.getElementById('goldValue').textContent = formatCurrency(goldValue);
            document.getElementById('silverValue').textContent = formatCurrency(silverValue);
            document.getElementById('totalValue').textContent = formatCurrency(totalValue);
        }

        function formatCurrency(amount) {
            return new Intl.NumberFormat('tr-TR', {
                style: 'decimal',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount) + ' TL';
        }

        // Sayfa yüklendiğinde ilk kez çalıştır
        window.onload = function() {
            fetchPrice();
        };
    </script>
</body>
</html>
'''

def get_silver_price():
    try:
        url = "https://m.doviz.com/altin/vakifbank/gumus"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Gümüş fiyatı için doğru elementi ara
        price_element = soup.find('span', {
            'data-socket-key': '5-gumus',
            'data-socket-attr': 'bid'
        })
        
        if not price_element:
            # Alternatif arama
            price_element = soup.find('span', {
                'data-socket-key': lambda x: x and 'gumus' in x.lower(),
                'data-socket-attr': 'bid'
            })
        
        if price_element:
            return price_element.get_text(strip=True)
            
        return None
        
    except Exception as e:
        raise Exception(f"Gümüş veri çekme hatası: {str(e)}")

def get_gold_price():
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Spesifik elementi ara
        price_element = soup.find('span', {
            'data-socket-key': '6-gram-altin',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
        
        # Alternatif arama
        alt_element = soup.find('span', {'data-socket-key': lambda x: x and 'gram-altin' in x})
        if alt_element:
            return alt_element.get_text(strip=True)
            
        return None
        
    except Exception as e:
        raise Exception(f"Altın veri çekme hatası: {str(e)}")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/silver-price')
def api_silver_price():
    try:
        price = get_silver_price()
        if price:
            return jsonify({'success': True, 'price': price})
        else:
            return jsonify({'success': False, 'error': 'Gümüş fiyat elementi bulunamadı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gold-price')
def api_gold_price():
    try:
        price = get_gold_price()
        if price:
            return jsonify({'success': True, 'price': price})
        else:
            return jsonify({'success': False, 'error': 'Altın fiyat elementi bulunamadı'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
