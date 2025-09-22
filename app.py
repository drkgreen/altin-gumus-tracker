#!/usr/bin/env python3
# Metal Fiyat Takipçisi v2.3.0
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
    <title>Metal Fiyat Takipçisi</title>
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
        
        /* Status */
        .status-bar {
            background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(20px);
            border-radius: 12px; padding: 12px 16px; border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex; justify-content: space-between; align-items: center;
        }
        .status-text { color: white; font-size: 14px; font-weight: 500; }
        .status-time { color: rgba(255, 255, 255, 0.8); font-size: 12px; }
        
        /* Portfolio Input Modal */
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
        
        /* Loading States */
        .loading { opacity: 0.6; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        
        /* Responsive */
        @media (max-width: 400px) {
            .app-container { max-width: 100%; }
            .portfolio-breakdown { flex-direction: column; gap: 12px; }
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
    print("🏆 Metal Fiyat Takipçisi v2.3.0")
    print("📅 Modern Card-Based UI")
    print(f"📱 URL: http://localhost:{port}")
    print("🎨 Kullanıcı dostu tasarım")
    print("⚡ Flask 3.0.0 | Python 3.13.4")
    print("⏹️  Durdurmak için Ctrl+C")
    print("-" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)