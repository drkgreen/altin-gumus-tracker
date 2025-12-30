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
                    <tbody id="priceTableBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let currentGoldPrice = 0;
        let currentSilverPrice = 0;
        let tableData = {};
        let currentPeriod = 'hourly';
        let goldAmount = 0;
        let silverAmount = 0;

        async function login() {
            const password = document.getElementById('passwordInput').value;
            if (!password) return;

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: password })
                });
                
                const data = await response.json();
            
            if (data.valid) {
                showMainApp();
                await loadPortfolioConfig();
                await fetchPrice();
                return;
            }
        } catch (error) {
            console.error('Auth verification error:', error);
        }
    }
    
    showLoginScreen();
}

function showLoginScreen() {
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('mainApp').style.display = 'none';
}

function showMainApp() {
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('mainApp').style.display = 'flex';
}

async function login() {
    const password = document.getElementById('passwordInput').value;
    if (!password) return;
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const expiry = new Date();
            expiry.setDate(expiry.getDate() + 30);
            document.cookie = `auth_token=${data.token}; expires=${expiry.toUTCString()}; path=/`;
            localStorage.setItem('auth_token', data.token);
            localStorage.setItem('auth_expiry', expiry.getTime());
            
            showMainApp();
            await loadPortfolioConfig();
            await fetchPrice();
        } else {
            document.getElementById('loginError').style.display = 'block';
            document.getElementById('passwordInput').value = '';
        }
    } catch (error) {
        document.getElementById('loginError').style.display = 'block';
    }
}

function logout() {
    document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_expiry');
    
    document.getElementById('passwordInput').value = '';
    document.getElementById('loginError').style.display = 'none';
    showLoginScreen();
}

async function loadPortfolioConfig() {
    try {
        const response = await fetch('/api/portfolio-config');
        const data = await response.json();
        
        if (data.success) {
            goldAmount = data.gold_amount;
            silverAmount = data.silver_amount;
        }
    } catch (error) {
        console.error('Portfolio config error:', error);
    }
}

async function fetchPrice() {
    const refreshBtn = document.getElementById('refreshBtn');
    
    try {
        refreshBtn.style.transform = 'rotate(360deg)';
        
        const [goldResponse, silverResponse, tableResponse] = await Promise.all([
            fetch('/api/gold-price'),
            fetch('/api/silver-price'),
            fetch('/api/table-data')
        ]);
        
        const goldData = await goldResponse.json();
        const silverData = await silverResponse.json();
        const tableDataResult = await tableResponse.json();
        
        if (goldData.success) {
            let cleaned = goldData.price.replace(/[^\d,]/g, '');
            currentGoldPrice = parseFloat(cleaned.replace(',', '.'));
        }
        
        if (silverData.success) {
            let cleaned = silverData.price.replace(/[^\d,]/g, '');
            currentSilverPrice = parseFloat(cleaned.replace(',', '.'));
        }
        
        if (tableDataResult.success) {
            tableData = tableDataResult.data;
            updateTable();
        }
        
        document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        updatePortfolio();
        
    } catch (error) {
        console.error('Fetch price error:', error);
    } finally {
        setTimeout(() => refreshBtn.style.transform = 'rotate(0deg)', 500);
    }
}

function switchPeriod(period) {
    currentPeriod = period;
    document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(period + 'Tab').classList.add('active');
    
    const header = document.getElementById('timeHeader');
    if (period === 'hourly') header.textContent = 'Saat';
    else if (period === 'daily') header.textContent = 'Tarih';
    else if (period === 'monthly') header.textContent = 'Ay';
    
    updateTable();
}

function updateTable() {
    if (!tableData || !tableData[currentPeriod]) return;
    
    const tbody = document.getElementById('priceTableBody');
    tbody.innerHTML = '';
    
    updateStatistics();
    
    tableData[currentPeriod].forEach((item, index) => {
        let portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
        const row = document.createElement('tr');
        
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

function updateStatistics() {
    if (!tableData || !tableData[currentPeriod] || tableData[currentPeriod].length === 0) {
        document.getElementById('highestGold').textContent = '0,00 ₺';
        document.getElementById('highestGoldTime').textContent = '--:--';
        document.getElementById('highestSilver').textContent = '0,00 ₺';
        document.getElementById('highestSilverTime').textContent = '--:--';
        document.getElementById('highestPortfolio').textContent = '0,00 ₺';
        document.getElementById('highestPortfolioTime').textContent = '--:--';
        return;
    }

    let highestGold = { price: 0, time: '' };
    let highestSilver = { price: 0, time: '' };
    let highestPortfolio = { value: 0, time: '' };

    tableData[currentPeriod].forEach(item => {
        if (item.gold_price > highestGold.price) {
            highestGold = { price: item.gold_price, time: item.time };
        }

        if (item.silver_price > highestSilver.price) {
            highestSilver = { price: item.silver_price, time: item.time };
        }

        if (goldAmount > 0 || silverAmount > 0) {
            const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
            if (portfolioValue > highestPortfolio.value) {
                highestPortfolio = { value: portfolioValue, time: item.time };
            }
        }
    });

    document.getElementById('highestGold').textContent = formatPrice(highestGold.price);
    document.getElementById('highestGoldTime').textContent = highestGold.time || '--:--';
    document.getElementById('highestSilver').textContent = formatPrice(highestSilver.price);
    document.getElementById('highestSilverTime').textContent = highestSilver.time || '--:--';
    
    if (highestPortfolio.value > 0) {
        document.getElementById('highestPortfolio').textContent = formatCurrency(highestPortfolio.value);
        document.getElementById('highestPortfolioTime').textContent = highestPortfolio.time || '--:--';
    } else {
        document.getElementById('highestPortfolio').textContent = '0,00 ₺';
        document.getElementById('highestPortfolioTime').textContent = '--:--';
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

function updatePortfolio() {
    const goldValue = goldAmount * currentGoldPrice;
    const silverValue = silverAmount * currentSilverPrice;
    const totalValue = goldValue + silverValue;
    
    document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
    document.getElementById('goldAmount').textContent = goldAmount + ' gr';
    document.getElementById('silverAmount').textContent = silverAmount + ' gr';
    document.getElementById('goldCurrentPrice').textContent = formatPrice(currentGoldPrice) + '/gr';
    document.getElementById('silverCurrentPrice').textContent = formatPrice(currentSilverPrice) + '/gr';
    document.getElementById('goldPortfolioValue').textContent = formatCurrency(goldValue);
    document.getElementById('silverPortfolioValue').textContent = formatCurrency(silverValue);
    
    updateTable();
}

function formatCurrency(amount) {
    if (!amount || amount === 0) return '0,00 ₺';
    return new Intl.NumberFormat('tr-TR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount) + ' ₺';
}

function formatPrice(price) {
    if (!price || price === 0) return '0,00 ₺';
    return new Intl.NumberFormat('tr-TR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(price) + ' ₺';
}
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        password = data.get('password', '')
        if verify_password(password):
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            return jsonify({'success': True, 'token': password_hash})
        else:
            return jsonify({'success': False, 'error': 'Invalid password'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/verify-session', methods=['POST'])
def api_verify_session():
    try:
        data = request.get_json()
        token = data.get('token', '')
        config = load_portfolio_config()
        is_valid = token == config.get("password_hash", "")
        return jsonify({'valid': is_valid})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/api/portfolio-config')
def api_portfolio_config():
    try:
        config = load_portfolio_config()
        return jsonify({
            'success': True, 
            'gold_amount': config.get('gold_amount', 0), 
            'silver_amount': config.get('silver_amount', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
    app.run(host='0.0.0.0', port=port, debug=False)json();
                
                if (data.success) {
                    const expiry = new Date();
                    expiry.setDate(expiry.getDate() + 30);
                    document.cookie = `auth_token=${data.token}; expires=${expiry.toUTCString()}; path=/`;
                    localStorage.setItem('auth_token', data.token);
                    localStorage.setItem('auth_expiry', expiry.getTime());
                    
                    showMainApp();
                    await loadPortfolioConfig();
                    await fetchPrice();
                } else {
                    document.getElementById('loginError').style.display = 'block';
                    document.getElementById('passwordInput').value = '';
                }
            } catch (error) {
                document.getElementById('loginError').style.display = 'block';
            }
        }

        function logout() {
            document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_expiry');
            
            document.getElementById('passwordInput').value = '';
            document.getElementById('loginError').style.display = 'none';
            showLoginScreen();
        }

        async function loadPortfolioConfig() {
            try {
                const response = await fetch('/api/portfolio-config');
                const data = await response.json();
                
                if (data.success) {
                    goldAmount = data.gold_amount;
                    silverAmount = data.silver_amount;
                }
            } catch (error) {
                console.error('Portfolio config error:', error);
            }
        }

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                
                const [goldResponse, silverResponse, tableResponse] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data')
                ]);
                
                const goldData = await goldResponse.json();
                const silverData = await silverResponse.json();
                const tableDataResult = await tableResponse.json();
                
                if (goldData.success) {
                    let cleaned = goldData.price.replace(/[^\d,]/g, '');
                    currentGoldPrice = parseFloat(cleaned.replace(',', '.'));
                }
                
                if (silverData.success) {
                    let cleaned = silverData.price.replace(/[^\d,]/g, '');
                    currentSilverPrice = parseFloat(cleaned.replace(',', '.'));
                }
                
                if (tableDataResult.success) {
                    tableData = tableDataResult.data;
                    updateTable();
                }
                
                document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                updatePortfolio();
                
            } catch (error) {
                console.error('Fetch price error:', error);
            } finally {
                setTimeout(() => refreshBtn.style.transform = 'rotate(0deg)', 500);
            }
        }

        function switchPeriod(period) {
            currentPeriod = period;
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            const header = document.getElementById('timeHeader');
            if (period === 'hourly') header.textContent = 'Saat';
            else if (period === 'daily') header.textContent = 'Tarih';
            else if (period === 'monthly') header.textContent = 'Ay';
            
            updateTable();
        }

        function updateTable() {
            if (!tableData || !tableData[currentPeriod]) return;
            
            const tbody = document.getElementById('priceTableBody');
            tbody.innerHTML = '';
            
            // İstatistikleri hesapla
            updateStatistics();
            
            tableData[currentPeriod].forEach((item, index) => {
                let portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                const row = document.createElement('tr');
                
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

        function updateStatistics() {
            if (!tableData || !tableData[currentPeriod] || tableData[currentPeriod].length === 0) {
                // Veri yoksa sıfırla
                document.getElementById('highestGold').textContent = '0,00 ₺';
                document.getElementById('highestGoldTime').textContent = '--:--';
                document.getElementById('highestSilver').textContent = '0,00 ₺';
                document.getElementById('highestSilverTime').textContent = '--:--';
                document.getElementById('highestPortfolio').textContent = '0,00 ₺';
                document.getElementById('highestPortfolioTime').textContent = '--:--';
                return;
            }

            let highestGold = { price: 0, time: '' };
            let highestSilver = { price: 0, time: '' };
            let highestPortfolio = { value: 0, time: '' };

            tableData[currentPeriod].forEach(item => {
                // En yüksek altın fiyatı
                if (item.gold_price > highestGold.price) {
                    highestGold = { price: item.gold_price, time: item.time };
                }

                // En yüksek gümüş fiyatı
                if (item.silver_price > highestSilver.price) {
                    highestSilver = { price: item.silver_price, time: item.time };
                }

                // En yüksek portföy değeri (sadece kullanıcının metalı varsa)
                if (goldAmount > 0 || silverAmount > 0) {
                    const portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                    if (portfolioValue > highestPortfolio.value) {
                        highestPortfolio = { value: portfolioValue, time: item.time };
                    }
                }
            });

            // İstatistikleri güncelle
            document.getElementById('highestGold').textContent = formatPrice(highestGold.price);
            document.getElementById('highestGoldTime').textContent = highestGold.time || '--:--';
            document.getElementById('highestSilver').textContent = formatPrice(highestSilver.price);
            document.getElementById('highestSilverTime').textContent = highestSilver.time || '--:--';
            
            if (highestPortfolio.value > 0) {
                document.getElementById('highestPortfolio').textContent = formatCurrency(highestPortfolio.value);
                document.getElementById('highestPortfolioTime').textContent = highestPortfolio.time || '--:--';
            } else {
                document.getElementById('highestPortfolio').textContent = '0,00 ₺';
                document.getElementById('highestPortfolioTime').textContent = '--:--';
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

        function updatePortfolio() {
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
            document.getElementById('goldAmount').textContent = goldAmount + ' gr';
            document.getElementById('silverAmount').textContent = silverAmount + ' gr';
            document.getElementById('goldCurrentPrice').textContent = formatPrice(currentGoldPrice) + '/gr';
            document.getElementById('silverCurrentPrice').textContent = formatPrice(currentSilverPrice) + '/gr';
            document.getElementById('goldPortfolioValue').textContent = formatCurrency(goldValue);
            document.getElementById('silverPortfolioValue').textContent = formatCurrency(silverValue);
            
            updateTable();
        }

        function formatCurrency(amount) {
            if (!amount || amount === 0) return '0,00 ₺';
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount) + ' ₺';
        }

        function formatPrice(price) {
            if (!price || price === 0) return '0,00 ₺';
            return new Intl.NumberFormat('tr-TR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(price) + ' ₺';
        }

        // Sayfa yüklendiğinde hemen auth kontrolü
        document.addEventListener('DOMContentLoaded', function() {
            initializeApp();
        });

        async function initializeApp() {
            // Hızlı localStorage kontrolü
            const token = localStorage.getItem('auth_token');
            const expiry = localStorage.getItem('auth_expiry');
            
            if (token && expiry && new Date().getTime() < parseInt(expiry)) {
                // Token var ve geçerli, hızlı geçiş
                try {
                    const response = await fetch('/api/verify-session', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ token: token })
                    });
                    
                    const data = await response.json();
                    
                    if (data.valid) {
                        // Başarılı, ana uygulamayı göster
                        showMainApp();
                        await loadPortfolioConfig();
                        await fetchPrice();
                        return;
                    }
                } catch (error) {
                    console.error('Auth verification error:', error);
                }
            }
            
            // Token yok veya geçersiz, login ekranını göster
            showLoginScreen();
        }

        function showLoginScreen() {
            document.getElementById('loadingScreen').style.display = 'none';
            document.getElementById('loginScreen').style.display = 'flex';
            document.getElementById('mainApp').style.display = 'none';
        }

        function showMainApp() {
            document.getElementById('loadingScreen').style.display = 'none';
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('mainApp').style.display = 'flex';
        }
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        password = data.get('password', '')
        if verify_password(password):
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            return jsonify({'success': True, 'token': password_hash})
        else:
            return jsonify({'success': False, 'error': 'Invalid password'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/verify-session', methods=['POST'])
def api_verify_session():
    try:
        data = request.get_json()
        token = data.get('token', '')
        config = load_portfolio_config()
        is_valid = token == config.get("password_hash", "")
        return jsonify({'valid': is_valid})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/api/portfolio-config')
def api_portfolio_config():
    try:
        config = load_portfolio_config()
        return jsonify({
            'success': True, 
            'gold_amount': config.get('gold_amount', 0), 
            'silver_amount': config.get('silver_amount', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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