 </div>
        </div>
        
        <div class="price-history" id="priceHistory">
            <div class="history-header">
                <div class="history-title">Fiyat Geçmişi</div>
                <div class="period-tabs">
                    <button class="period-tab active" onclick="switchPeriod('hourly')" id="hourlyTab">Saatlik</button>
                    <button class="period-tab" onclick="switchPeriod('daily')" id="dailyTab">Günlük</button>
                    <button class="period-tab" onclick="switchPeriod('monthly')" id="monthlyTab">Aylık</button>
                </div>
            </div>
            <div class="price-table">
                <table>
                    <thead>
                        <tr>
                            <th id="timeHeader">Saat</th>
                            <th>Altın</th>
                            <th>Gümüş</th>
                            <th>Portföy</th>
                            <th>Değişim</th>
                        </tr>
                    </thead>
                    <tbody id="priceTableBody">
                    </tbody>
                </table>
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
        let tableData = {};
        let currentPeriod = 'hourly';

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                
                const [goldRes, silverRes, tableRes] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data')
                ]);
                
                const goldData = await goldRes.json();
                const silverData = await silverRes.json();
                const tableDataRes = await tableRes.json();
                
                if (goldData.success) {
                    let cleanPrice = goldData.price.replace(/[^\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                }
                
                if (tableDataRes.success) {
                    tableData = tableDataRes.data;
                    updateTable();
                }
                
                document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                updatePortfolio();
                
            } catch (error) {
                console.error('Fetch error:', error);
            } finally {
                setTimeout(() => refreshBtn.style.transform = 'rotate(0deg)', 500);
            }
        }

        function switchPeriod(period) {
            currentPeriod = period;
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            const timeHeader = document.getElementById('timeHeader');
            if (period === 'hourly') {
                timeHeader.textContent = 'Saat';
            } else if (period === 'daily') {
                timeHeader.textContent = 'Tarih';
            } else if (period === 'monthly') {
                timeHeader.textContent = 'Ay';
            }
            
            updateTable();
        }
function updateTable() {
            const goldAmount = parseFloat(document.getElementById('goldAmount').value) || 0;
            const silverAmount = parseFloat(document.getElementById('silverAmount').value) || 0;
            
            if (!tableData[currentPeriod]) return;
            
            const tbody = document.getElementById('priceTableBody');
            tbody.innerHTML = '';
            
            let maxPortfolioValue = 0;
            let peakIndices = [];
            
            if (goldAmount > 0 || silverAmount > 0) {
                tableData[currentPeriod].forEach((item, index) => {
                    const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                    
                    if (portfolioValue > maxPortfolioValue) {
                        maxPortfolioValue = portfolioValue;
                        peakIndices = [index];
                    } else if (portfolioValue === maxPortfolioValue && portfolioValue > 0) {
                        peakIndices.push(index);
                    }
                });
            }
            
            tableData[currentPeriod].forEach((item, index) => {
                let portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                const row = document.createElement('tr');
                
                const isPeakRow = peakIndices.includes(index) && maxPortfolioValue > 0;
                if (isPeakRow) {
                    row.classList.add('peak-row');
                }
                
                const timeDisplay = item.optimized ? 
                    `<span title="Peak değer (${item.peak_time || 'bilinmiyor'})">${item.time}</span>` : 
                    item.time;
                
                row.innerHTML = `
                    <td class="time">${timeDisplay}</td>
                    <td class="price">${formatPrice(item.gold_price)}</td>
                    <td class="price">${formatPrice(item.silver_price)}</td>
                    <td class="portfolio">${portfolioValue > 0 ? formatCurrency(portfolioValue) : '-'}</td>
                    <td class="change ${getChangeClass(item.change_percent)}">${formatChange(item.change_percent)}</td>
                `;
                tbody.appendChild(row);
            });
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
            } else {
                portfolioSummary.style.display = 'none';
                priceHistory.style.display = 'none';
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
            
            window.portfolioData = {
                gold: goldAmount,
                silver: silverAmount
            };
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
            
            if (!cookies.goldAmount && window.portfolioData) {
                document.getElementById('goldAmount').value = window.portfolioData.gold || '';
                document.getElementById('silverAmount').value = window.portfolioData.silver || '';
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
