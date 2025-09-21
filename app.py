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
        <div class="next-update" id="nextUpdate">Sonraki güncelleme: 5 dakika sonra</div>
        
        <div class="controls">
            <button onclick="fetchPrice()" id="refreshBtn">🔄 Yenile</button>
            <button onclick="toggleAuto()" id="autoBtn">⏹️ Durdur</button>
        </div>
        
        <div class="footer">
            API Endpoints: <br>
            <code>/api/gold-price</code> | <code>/api/silver-price</code>
        </div>
    </div>

    <script>
        let autoUpdate = true;
        let updateInterval;
        let countdown;
        let nextUpdateTime = 0;

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
                    successCount++;
                } else {
                    goldPriceEl.textContent = 'Veri alınamadı';
                    errorMessages.push('Altın: ' + goldData.error);
                }
                
                if (silverData.success) {
                    silverPriceEl.textContent = silverData.price + ' TL';
                    successCount++;
                } else {
                    silverPriceEl.textContent = 'Veri alınamadı';
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

        function startCountdown() {
            nextUpdateTime = 5 * 60;
            const nextUpdateEl = document.getElementById('nextUpdate');
            
            countdown = setInterval(() => {
                if (nextUpdateTime <= 0) {
                    nextUpdateEl.textContent = 'Güncelleniyor...';
                    return;
                }
                
                const minutes = Math.floor(nextUpdateTime / 60);
                const seconds = nextUpdateTime % 60;
                nextUpdateEl.textContent = `Sonraki güncelleme: ${minutes}:${seconds.toString().padStart(2, '0')}`;
                nextUpdateTime--;
            }, 1000);
        }

        function toggleAuto() {
            const autoBtn = document.getElementById('autoBtn');
            const nextUpdateEl = document.getElementById('nextUpdate');
            
            if (autoUpdate) {
                clearInterval(updateInterval);
                clearInterval(countdown);
                autoUpdate = false;
                autoBtn.textContent = '▶️ Başlat';
                nextUpdateEl.textContent = 'Otomatik güncelleme durduruldu';
            } else {
                startAutoUpdate();
                autoUpdate = true;
                autoBtn.textContent = '⏹️ Durdur';
            }
        }

        function startAutoUpdate() {
            updateInterval = setInterval(() => {
                fetchPrice();
                startCountdown();
            }, 5 * 60 * 1000);
            
            startCountdown();
        }

        window.onload = function() {
            fetchPrice();
            startAutoUpdate();
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
        
        # Gümüş fiyatı için spesifik elementi ara (satış fiyatı)
        price_element = soup.find('span', {
            'data-socket-key': lambda x: x and 'gumus' in x.lower(),
            'data-socket-attr': 'ask'  # satış fiyatı
        })
        
        if not price_element:
            # Alternatif arama
            price_element = soup.find('span', {
                'data-socket-attr': 'ask'
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
