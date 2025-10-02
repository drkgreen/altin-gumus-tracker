todayData.forEach(record => {
                const portfolioValue = (goldAmount * record.gold_price) + (silverAmount * record.silver_price);
                console.log('Record:', record.time, 'Portfolio:', portfolioValue);
                
                if (portfolioValue > maxPortfolioValue) {
                    maxPortfolioValue = portfolioValue;
                    peakRecord = {
                        time: record.time,
                        gold_price: record.gold_price,
                        silver_price: record.silver_price,
                        portfolio_value: portfolioValue
                    };
                }
            });
            
            console.log('Peak record found:', peakRecord);
            
            if (peakRecord) {
                document.getElementById('peakTime').textContent = peakRecord.time;
                document.getElementById('peakGold').textContent = formatPrice(peakRecord.gold_price);
                document.getElementById('peakSilver').textContent = formatPrice(peakRecord.silver_price);
                document.getElementById('peakPortfolioValue').textContent = formatCurrency(peakRecord.portfolio_value);
                
                document.getElementById('todayPeakCard').style.display = 'block';
            } else {
                document.getElementById('todayPeakCard').style.display = 'none';
            }
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
                updateTodayPeak(); // Peak kartını güncelle
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
    app.run(host='0.0.0.0', port=port, debug=False)