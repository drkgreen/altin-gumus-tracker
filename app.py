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
    print("Metal Fiyat Takipçisi v3.0.0")
    print("Redesigned Portfolio Interface")
    print(f"URL: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Metal Fiyat Takipçisi v3.0.0")
    print("Redesigned Portfolio Interface")
    print(f"URL: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)