document.getElementById('portfolioChart').addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        });

        function handleSwipe() {
            if (!chartData[currentChartPeriod]) return;
            
            const totalPoints = chartData[currentChartPeriod].length;
            const maxWindows = Math.ceil(totalPoints / MAX_VISIBLE_POINTS) - 1;
            
            const swipeThreshold = 50; // Minimum swipe mesafesi
            
            if (touchEndX < touchStartX - swipeThreshold) {
                // Sola kaydır (daha eski verilere git)
                if (currentViewWindow < maxWindows) {
                    currentViewWindow++;
                    updateChart();
                    updateScrollIndicator();
                }
            }
            
            if (touchEndX > touchStartX + swipeThreshold) {
                // Sağa kaydır (daha yeni verilere git)
                if (currentViewWindow > 0) {
                    currentViewWindow--;
                    updateChart();
                    updateScrollIndicator();
                }
            }
        }

        window.onload = function() {
            loadPortfolio();
            fetchPrice();
            updatePortfolio();
        };

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
                
                updateListView();
            } else {
                portfolioSummary.style.display = 'none';
                chartContainer.style.display = 'none';
            }
            
            savePortfolio();
        }
        
        function updateListView() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            const listContainer = document.getElementById('listView');
            
            if (!chartData[currentChartPeriod] || (goldAmount === 0 && silverAmount === 0)) {
                listContainer.innerHTML = `
                    <div class="no-data">
                        <div class="no-data-icon">📊</div>
                        <div class="no-data-text">Veri yükleniyor veya portföy boş...</div>
                    </div>
                `;
                return;
            }
            
            const data = chartData[currentChartPeriod];
            
            // İstatistikler hesapla
            const goldPrices = data.map(d => d.gold_price);
            const silverPrices = data.map(d => d.silver_price);
            const portfolioValues = data.map(d => (goldAmount * d.gold_price) + (silverAmount * d.silver_price));
            
            const maxGold = Math.max(...goldPrices);
            const minGold = Math.min(...goldPrices);
            const avgGold = goldPrices.reduce((a, b) => a + b, 0) / goldPrices.length;
            
            const changePercent = ((portfolioValues[portfolioValues.length - 1] - portfolioValues[0]) / portfolioValues[0] * 100).toFixed(2);
            
            let html = `
                <div class="summary-card">
                    <div class="summary-title">📊 ${getPeriodLabel(currentChartPeriod)} Özet</div>
                    <div class="summary-stats">
                        <div class="summary-stat">
                            <div class="summary-stat-label">En Yüksek Altın</div>
                            <div class="summary-stat-value">${formatPrice(maxGold)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="summary-stat-label">En Düşük Altın</div>
                            <div class="summary-stat-value">${formatPrice(minGold)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="summary-stat-label">Ortalama Altın</div>
                            <div class="summary-stat-value">${formatPrice(avgGold)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="summary-stat-label">Portföy Değişim</div>
                            <div class="summary-stat-value">${changePercent > 0 ? '↑' : '↓'} ${Math.abs(changePercent)}%</div>
                        </div>
                    </div>
                </div>
                
                <div class="price-table">
                    <div class="table-header">
                        <div>Saat</div>
                        <div>Altın</div>
                        <div>Gümüş</div>
                        <div>Portföy</div>
                    </div>
                    <div class="table-body">
            `;
            
            // Satırları oluştur (tersine çevir - en yeni önce)
            const reversedData = [...data].reverse();
            reversedData.forEach((item, index) => {
                const isLatest = index === 0;
                const timeLabel = getTimeLabel(item, currentChartPeriod);
                
                const goldPrice = item.gold_price;
                const silverPrice = item.silver_price;
                const portfolioValue = (goldAmount * goldPrice) + (silverAmount * silverPrice);
                
                // Değişim hesapla (bir önceki kayıtla karşılaştır)
                let goldChange = 0;
                let silverChange = 0;
                let portfolioChange = 0;
                
                if (index < reversedData.length - 1) {
                    const prevItem = reversedData[index + 1];
                    goldChange = ((goldPrice - prevItem.gold_price) / prevItem.gold_price * 100);
                    silverChange = ((silverPrice - prevItem.silver_price) / prevItem.silver_price * 100);
                    const prevPortfolioValue = (goldAmount * prevItem.gold_price) + (silverAmount * prevItem.silver_price);
                    portfolioChange = ((portfolioValue - prevPortfolioValue) / prevPortfolioValue * 100);
                }
                
                html += `
                    <div class="table-row ${isLatest ? 'latest' : ''}">
                        <div class="row-time">
                            ${timeLabel}
                            ${isLatest ? '<div class="time-badge">CANLI</div>' : ''}
                        </div>
                        
                        <div class="row-cell">
                            <div class="cell-price">${formatPriceShort(goldPrice)}</div>
                            ${goldChange !== 0 ? `
                                <div class="cell-change ${goldChange > 0 ? 'change-up' : 'change-down'}">
                                    ${goldChange > 0 ? '↑' : '↓'}${Math.abs(goldChange).toFixed(1)}%
                                </div>
                            ` : ''}
                        </div>
                        
                        <div class="row-cell">
                            <div class="cell-price">${formatPriceShort(silverPrice)}</div>
                            ${silverChange !== 0 ? `
                                <div class="cell-change ${silverChange > 0 ? 'change-up' : 'change-down'}">
                                    ${silverChange > 0 ? '↑' : '↓'}${Math.abs(silverChange).toFixed(1)}%
                                </div>
                            ` : ''}
                        </div>
                        
                        <div class="row-cell">
                            <div class="cell-price">${formatCurrencyShort(portfolioValue)}</div>
                            ${portfolioChange !== 0 ? `
                                <div class="cell-change ${portfolioChange > 0 ? 'change-up' : 'change-down'}">
                                    ${portfolioChange > 0 ? '↑' : '↓'}${Math.abs(portfolioChange).toFixed(1)}%
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
            
            listContainer.innerHTML = html;
            listContainer.style.display = 'block';
        }
        
        function getPeriodLabel(period) {
            switch(period) {
                case 'daily': return 'Günlük';
                case 'weekly': return 'Haftalık';
                case 'monthly': return 'Aylık';
                default: return '';
            }
        }
        
        function getTimeLabel(item, period) {
            if (period === 'daily') return item.time;
            if (period === 'weekly') return item.day;
            return item.period;
        }
        
        function formatPriceShort(price) {
            if (!price) return '0₺';
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(price) + '₺';
        }
        
        function formatCurrencyShort(amount) {
            if (amount >= 1000) {
                return (amount / 1000).toFixed(1) + 'K₺';
            }
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(amount) + '₺';
        }
        
        function togglePortfolio() {
            document.getElementById('portfolioModal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('portfolioModal').style.display = 'none';
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
            // Liste görünümünü varsayılan olarak göster
            switchView('list');
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
    print("=" * 50)
    print("🚀 Metal Fiyat Takipçisi v3.0.0")
    print("📊 Kaydırılabilir Grafik Özelliği")
    print("✨ Maksimum 5 Veri Noktası Görünümü")
    print("=" * 50)
    print(f"🌐 Server: http://localhost:{port}")
    print(f"📱 Mobile: http://0.0.0.0:{port}")
    print("=" * 50)
    print("🔥 Yeni Özellikler:")
    print("  • Yatay kaydırılabilir grafik")
    print("  • Maksimum 5 dikey çizgi gösterimi")
    print("  • Touch swipe desteği (← →)")
    print("  • Klavye ok tuşları ile kaydırma")
    print("  • Scroll gösterge noktaları")
    print("  • Doğrudan nokta seçimi")
    print("  • 30 dakikalık detaylı veri")
    print("  • Türkiye saati (UTC+3)")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)