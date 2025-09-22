#!/usr/bin/env python3
# Metal Fiyat Takipçisi v2.2.0
# Son Güncelleme: 21.09.2025
# Python 3.13.4 | Flask 3.0.0

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Fiyat Takipçisi v2.2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
            border-radius: 20px; padding: 30px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            text-align: center; max-width: 400px; width: 100%;
            position: relative;
        }
        .title { color: #333; font-size: 24px; font-weight: 700; margin-bottom: 10px;
            background: linear-gradient(45deg, #f39c12, #d35400); -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; background-clip: text;
        }
        .subtitle { color: #666; font-size: 14px; margin-bottom: 30px; }
        
        /* Portfolio Total Display */
        .portfolio-total-main {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white; padding: 25px; border-radius: 15px; margin-bottom: 20px;
            box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
            display: none;
        }
        .portfolio-total-main .total-label {
            font-size: 14px; opacity: 0.9; margin-bottom: 5px;
            text-transform: uppercase; letter-spacing: 1px;
        }
        .portfolio-total-main .total-value {
            font-size: 36px; font-weight: 900;
            animation: pulse 2s infinite;
        }
        
        /* Portfolio Details */
        .portfolio-details {
            background: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 10px;
            margin-bottom: 20px; display: none;
        }
        .portfolio-item {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        .portfolio-item:last-child { border-bottom: none; }
        .metal-name { font-weight: 600; color: #333; font-size: 14px; }
        .metal-value { font-weight: 700; color: #f39c12; font-size: 14px; }
        
        .price-display {
            background: linear-gradient(135deg, #f39c12, #d35400); color: white;
            padding: 20px; border-radius: 15px; margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(243, 156, 18, 0.3);
        }
        .price-display.silver { background: linear-gradient(135deg, #95a5a6, #7f8c8d); box-shadow: 0 10px 25px rgba(149, 165, 166, 0.3); }
        .price-value { font-size: 32px; font-weight: 900; margin-bottom: 5px; animation: pulse 2s infinite; }
        .price-label { font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }
        .status { padding: 10px; border-radius: 10px; margin-bottom: 20px; font-size: 14px; font-weight: 600; }
        .status.loading { background: #3498db; color: white; }
        .status.success { background: #2ecc71; color: white; }
        .status.error { background: #e74c3c; color: white; }
        .last-update { color: #666; font-size: 12px; margin-bottom: 15px; }
        .controls {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }
        .controls button {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            padding: 0;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        button {
            background: linear-gradient(45deg, #667eea, #764ba2); color: white; border: none;
            padding: 10px 20px; border-radius: 25px; font-size: 14px; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
        .loading-spinner {
            width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.3);
            border-top: 2px solid white; border-radius: 50%; animation: spin 1s linear infinite;
            display: inline-block; margin-right: 10px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        /* Simplified Portfolio Input Section */
        .portfolio-input-section {
            margin-top: 20px; padding: 20px; background: rgba(255, 255, 255, 0.8);
            border-radius: 15px; border: 2px solid rgba(102, 126, 234, 0.2);
            animation: slideDown 0.3s ease; display: none;
        }
        .portfolio-header { text-align: center; margin-bottom: 20px; }
        .portfolio-header h3 { color: #333; font-size: 18px; margin-bottom: 5px; }
        .portfolio-header p { color: #666; font-size: 12px; }
        .input-group { margin-bottom: 15px; text-align: left; }
        .input-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 14px; }
        .input-group input {
            width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px;
            font-size: 16px; transition: border-color 0.3s ease; background: white;
        }
        .input-group input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .portfolio-controls { text-align: center; margin-top: 15px; }
        .clear-btn {
            background: linear-gradient(45deg, #e74c3c, #c0392b); color: white; border: none;
            padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease;
        }
        .clear-btn:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(231, 76, 60, 0.4); }
        
        @keyframes slideDown { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
        .footer { margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(0,0,0,0.1); font-size: 12px; color: #999; }
        .version-info {
            margin-top: 15px; padding: 15px; background: rgba(102, 126, 234, 0.1);
            border-radius: 10px; font-size: 11px; color: #667eea; line-height: 1.5;
        }
        .version-title { font-weight: 600; margin-bottom: 8px; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <p class="subtitle">Canlı Piyasa Verileri</p>
        
        <!-- Simplified Portfolio Input - En Üstte -->
        <div class="portfolio-input-section" id="portfolioInputSection">
            <div class="portfolio-header">
                <h3>⚙️ Portföy Ayarları</h3>
                <p>Elinizdeki metal miktarlarını girin</p>
            </div>
            
            <div class="input-group">
                <label for="goldAmount">🏆 Altın Miktarı (gram):</label>
                <input type="number" id="goldAmount" placeholder="0" step="0.1" min="0" 
                       oninput="calculatePortfolio(); savePortfolio()">
            </div>
            
            <div class="input-group">
                <label for="silverAmount">🥈 Gümüş Miktarı (gram):</label>
                <input type="number" id="silverAmount" placeholder="0" step="0.1" min="0" 
                       oninput="calculatePortfolio(); savePortfolio()">
            </div>
            
            <div class="portfolio-controls">
                <button onclick="clearPortfolio()" class="clear-btn">🗑️ Sıfırla</button>
            </div>
        </div>
        
        <!-- Portfolio Total - Ana Görünüm -->
        <div class="portfolio-total-main" id="portfolioTotalMain">
            <div class="total-label">💎 PORTFÖY TOPLAM DEĞERİ</div>
            <div class="total-value" id="totalValueMain">0,00 TL</div>
        </div>
        
        <!-- Portfolio Details - Ana Görünüm -->
        <div class="portfolio-details" id="portfolioDetailsMain">
            <div class="portfolio-item">
                <span class="metal-name">🏆 Altın:</span>
                <span class="metal-value" id="goldGramMain">0 gram</span>
            </div>
            <div class="portfolio-item">
                <span class="metal-name">🥈 Gümüş:</span>
                <span class="metal-value" id="silverGramMain">0 gram</span>
            </div>
            <div class="portfolio-item">
                <span class="metal-name">💰 Altın Değeri:</span>
                <span class="metal-value" id="goldValueMain">0,00 TL</span>
            </div>
            <div class="portfolio-item">
                <span class="metal-name">💰 Gümüş Değeri:</span>
                <span class="metal-value" id="silverValueMain">0,00 TL</span>
            </div>
        </div>
        
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
            <button onclick="fetchPrice()" id="refreshBtn" title="Yenile">🔄</button>
            <button onclick="togglePortfolio()" id="portfolioBtn" title="Portföy Ayarları">⚙️</button>
        </div>
        
        <!-- Simplified Portfolio Input -->
        <div class="portfolio-input-section" id="portfolioInputSection">
            <div class="portfolio-header">
                <h3>⚙️ Portföy Ayarları</h3>
                <p>Elinizdeki metal miktarlarını girin</p>
            </div>
            
            <div class="input-group">
                <label for="goldAmount">🏆 Altın Miktarı (gram):</label>
                <input type="number" id="goldAmount" placeholder="0" step="0.1" min="0" 
                       oninput="calculatePortfolio(); savePortfolio()">
            </div>
            
            <div class="input-group">
                <label for="silverAmount">🥈 Gümüş Miktarı (gram):</label>
                <input type="number" id="silverAmount" placeholder="0" step="0.1" min="0" 
                       oninput="calculatePortfolio(); savePortfolio()">
            </div>
            
            <div class="portfolio-controls">
                <button onclick="clearPortfolio()" class="clear-btn">🗑️ Sıfırla</button>
            </div>
        </div>
        
        <div class="footer">
            Versiyon: v2.2.0
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
                
                const [goldResponse, silverResponse] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price')
                ]);
                
                const goldData = await goldResponse.json();
                const silverData = await silverResponse.json();
                
                let successCount = 0;
                
                if (goldData.success) {
                    goldPriceEl.textContent = goldData.price + ' TL';
                    let cleanPrice = goldData.price.replace(/[^\\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                    successCount++;
                } else {
                    goldPriceEl.textContent = 'Veri alınamadı';
                    currentGoldPrice = 0;
                }
                
                if (silverData.success) {
                    silverPriceEl.textContent = silverData.price + ' TL';
                    let cleanPrice = silverData.price.replace(/[^\\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                    successCount++;
                } else {
                    silverPriceEl.textContent = 'Veri alınamadı';
                    currentSilverPrice = 0;
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
                calculatePortfolio();
                
            } catch (error) {
                statusEl.className = 'status error';
                statusEl.textContent = `❌ Hata: ${error.message}`;
                goldPriceEl.textContent = 'Veri alınamadı';
                silverPriceEl.textContent = 'Veri alınamadı';
            } finally {
                refreshBtn.disabled = false;
            }
        }

        function togglePortfolio() {
            const inputSection = document.getElementById('portfolioInputSection');
            const portfolioBtn = document.getElementById('portfolioBtn');
            
            if (inputSection.style.display === 'none') {
                inputSection.style.display = 'block';
                // Buton metnini değiştirmiyoruz, sadece ikon
            } else {
                inputSection.style.display = 'none';
                // Buton metnini değiştirmiyoruz, sadece ikon
            }
        }

        function calculatePortfolio() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            // Ana sayfada göster
            const portfolioTotalMain = document.getElementById('portfolioTotalMain');
            const portfolioDetailsMain = document.getElementById('portfolioDetailsMain');
            
            if (totalValue > 0) {
                portfolioTotalMain.style.display = 'block';
                portfolioDetailsMain.style.display = 'block';
                
                document.getElementById('totalValueMain').textContent = formatCurrency(totalValue);
                document.getElementById('goldGramMain').textContent = goldAmount.toFixed(1) + ' gram';
                document.getElementById('silverGramMain').textContent = silverAmount.toFixed(1) + ' gram';
                document.getElementById('goldValueMain').textContent = formatCurrency(goldValue);
                document.getElementById('silverValueMain').textContent = formatCurrency(silverValue);
            } else {
                portfolioTotalMain.style.display = 'none';
                portfolioDetailsMain.style.display = 'none';
            }
        }

        function savePortfolio() {
            try {
                const goldAmount = document.getElementById('goldAmount').value;
                const silverAmount = document.getElementById('silverAmount').value;
                localStorage.setItem('portfolioGold', goldAmount);
                localStorage.setItem('portfolioSilver', silverAmount);
            } catch (e) {}
        }

        function loadPortfolio() {
            try {
                const savedGold = localStorage.getItem('portfolioGold');
                const savedSilver = localStorage.getItem('portfolioSilver');
                if (savedGold && savedGold !== 'null' && savedGold !== '') {
                    document.getElementById('goldAmount').value = savedGold;
                }
                if (savedSilver && savedSilver !== 'null' && savedSilver !== '') {
                    document.getElementById('silverAmount').value = savedSilver;
                }
            } catch (e) {}
        }

        function clearPortfolio() {
            if (confirm('Portföy verilerini sıfırlamak istediğinizden emin misiniz?')) {
                document.getElementById('goldAmount').value = '';
                document.getElementById('silverAmount').value = '';
                try {
                    localStorage.removeItem('portfolioGold');
                    localStorage.removeItem('portfolioSilver');
                } catch (e) {}
                calculatePortfolio();
            }
        }

        function formatCurrency(amount) {
            return new Intl.NumberFormat('tr-TR', {
                style: 'decimal',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount) + ' TL';
        }

        window.onload = function() {
            loadPortfolio();
            fetchPrice();
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

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template_string(HTML_TEMPLATE)

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🏆 Metal Fiyat Takipçisi v2.2.0")
    print("📅 Son Güncelleme: 21.09.2025")
    print(f"📱 URL: http://localhost:{port}")
    print("🔄 Yeniden tasarlanmış layout")
    print("⚡ Flask 3.0.0 | Python 3.13.4")
    print("📊 Portföy bilgileri ana sayfada")
    print("⏹️  Durdurmak için Ctrl+C")
    print("-" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)