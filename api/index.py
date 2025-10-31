#!/usr/bin/env python3
"""
Metal Price Tracker Web App v2.0
Flask web uygulaması - optimize edilmiş verilerle haftalık görünüm
Güncellemeler: Gelişmiş istatistikler + Kalıcı session sistemi + Dark Blue Glassmorphism Tema
"""
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for, make_response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime, timezone, timedelta
import hashlib
import secrets

app = Flask(__name__)
CORS(app)

# Secret key sabit olsun (her restart'ta değişmesin)
SECRET_KEY = os.environ.get('SECRET_KEY', 'metal_tracker_secret_key_2024_permanent')
app.secret_key = SECRET_KEY

def load_portfolio_config():
    """GitHub'dan portföy ayarlarını ve hash'lenmiş şifreyi yükler"""
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/portfolio-config.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}
    except Exception:
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}

def verify_password(password):
    """Şifreyi hash'leyip GitHub'daki hash ile karşılaştırır"""
    config = load_portfolio_config()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == config.get("password_hash", "")

def load_price_history():
    """GitHub'dan fiyat geçmişini yükler"""
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/data/price-history.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"records": []}
    except Exception:
        return {"records": []}

def get_daily_data():
    """Son 2 günün tüm verilerini getir (30dk aralıklarla)"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        now = datetime.now(timezone.utc)
        daily_data = []
        
        # Son 2 günün verilerini al
        for day_offset in range(2):
            target_date = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            day_records = [r for r in records 
                          if r.get("date") == target_date 
                          and r.get("gold_price") 
                          and r.get("silver_price")
                          and not r.get("optimized", False)]  # Optimize edilmemiş kayıtlar
            
            if day_records:
                sorted_day_records = sorted(day_records, key=lambda x: x.get("timestamp", 0), reverse=True)
                
                for i, record in enumerate(sorted_day_records):
                    timestamp = record.get("timestamp", 0)
                    # UTC'den Türkiye saatine çevir (+3 saat)
                    local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
                    
                    # Eğer bugün değilse tarih de göster
                    if day_offset == 0:
                        time_label = local_time.strftime("%H:%M")
                    else:
                        time_label = local_time.strftime("%d.%m %H:%M")
                    
                    # Değişim hesaplama (bir önceki kayıt ile karşılaştır)
                    change_percent = 0
                    if i < len(sorted_day_records) - 1:
                        prev_record = sorted_day_records[i + 1]
                        if prev_record and prev_record.get("gold_price"):
                            price_diff = record["gold_price"] - prev_record["gold_price"]
                            change_percent = (price_diff / prev_record["gold_price"]) * 100
                    
                    daily_data.append({
                        "time": time_label,
                        "gold_price": record["gold_price"],
                        "silver_price": record["silver_price"],
                        "change_percent": change_percent,
                        "optimized": False
                    })
        
        return daily_data
        
    except Exception:
        return []

def get_weekly_optimized_data():
    """Son 30 günün optimize edilmiş verilerini getir (günlük peak değerler)"""
    try:
        history = load_price_history()
        records = history.get("records", [])
        
        if not records:
            return []
        
        # Optimize edilmiş kayıtları bul (günlük peak değerler)
        optimized_records = [
            r for r in records 
            if r.get("optimized") == True and r.get("daily_peak") == True
        ]
        
        # Son 30 günün optimize edilmiş verilerini al
        weekly_data = []
        weekly_temp = []
        now = datetime.now(timezone.utc)
        
        # Önce tüm günleri topla (eskiden yeniye)
        for i in range(29, -1, -1):  # 29'dan 0'a doğru (eskiden yeniye)
            target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            
            # O günün optimize edilmiş kaydını bul
            day_record = next(
                (r for r in optimized_records if r.get("date") == target_date), 
                None
            )
            
            if day_record:
                day_name = (now - timedelta(days=i)).strftime("%d.%m")
                weekly_temp.append({
                    "time": day_name,
                    "gold_price": day_record["gold_price"],
                    "silver_price": day_record["silver_price"],
                    "date_offset": i,
                    "peak_time": day_record.get("peak_time", "unknown"),
                    "portfolio_value": day_record.get("portfolio_value", 0)
                })
        
        # Şimdi değişim hesaplama
        for i, day_data in enumerate(weekly_temp):
            change_percent = 0
            
            # Bir önceki gün ile karşılaştır (eskiden yeniye sıralı listede)
            if i > 0:
                prev_day = weekly_temp[i-1]
                if prev_day["gold_price"] > 0:
                    price_diff = day_data["gold_price"] - prev_day["gold_price"]
                    change_percent = (price_diff / prev_day["gold_price"]) * 100
            
            weekly_data.append({
                "time": f"{day_data['time']} 📊",  # Peak değer işareti
                "gold_price": day_data["gold_price"],
                "silver_price": day_data["silver_price"],
                "change_percent": change_percent,
                "optimized": True,
                "peak_time": day_data["peak_time"],
                "portfolio_value": day_data["portfolio_value"]
            })
        
        # En son kayıt en başta olsun diye ters çevir (yeniden eskiye)
        weekly_data.reverse()
        
        return weekly_data
        
    except Exception:
        return []

def calculate_statistics(data_type='all'):
    """Belirtilen veri tipinden maksimum değerleri hesapla"""
    try:
        config = load_portfolio_config()
        
        if data_type == 'daily':
            data = get_daily_data()
        elif data_type == 'weekly':
            data = get_weekly_optimized_data()
        else:
            # Tüm veriler için
            daily_data = get_daily_data()
            weekly_data = get_weekly_optimized_data()
            data = daily_data + weekly_data
        
        if not data:
            return {
                "max_gold_price": 0,
                "max_silver_price": 0,
                "max_portfolio_value": 0
            }
        
        # Maksimum değerleri bul
        max_gold = max(item["gold_price"] for item in data)
        max_silver = max(item["silver_price"] for item in data)
        
        # Portföy hesaplaması için config'den miktarları al
        gold_amount = config.get("gold_amount", 0)
        silver_amount = config.get("silver_amount", 0)
        
        # En yüksek portföy değerini hesapla
        max_portfolio = 0
        if gold_amount > 0 or silver_amount > 0:
            portfolio_values = [
                (gold_amount * item["gold_price"]) + (silver_amount * item["silver_price"])
                for item in data
            ]
            max_portfolio = max(portfolio_values) if portfolio_values else 0
        
        return {
            "max_gold_price": max_gold,
            "max_silver_price": max_silver,
            "max_portfolio_value": max_portfolio
        }
        
    except Exception:
        return {
            "max_gold_price": 0,
            "max_silver_price": 0,
            "max_portfolio_value": 0
        }

def get_table_data():
    """Günlük ve haftalık veriler için farklı kaynak kullan"""
    try:
        daily_data = get_daily_data()
        weekly_data = get_weekly_optimized_data()
        
        # Her sekme için ayrı istatistik hesapla
        daily_stats = calculate_statistics('daily')
        weekly_stats = calculate_statistics('weekly')
        
        return {
            "daily": daily_data,
            "weekly": weekly_data,
            "statistics": {
                "daily": daily_stats,
                "weekly": weekly_stats
            }
        }
        
    except Exception:
        return {
            "daily": [], 
            "weekly": [], 
            "statistics": {
                "daily": {"max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0},
                "weekly": {"max_gold_price": 0, "max_silver_price": 0, "max_portfolio_value": 0}
            }
        }

def get_gold_price():
    """Yapı Kredi altın fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '6-gram-altin',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
        return None
        
    except Exception as e:
        raise Exception(f"Gold price error: {str(e)}")

def get_silver_price():
    """Vakıfbank gümüş fiyatını çeker"""
    try:
        url = "https://m.doviz.com/altin/vakifbank/gumus"
        headers = {'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_element = soup.find('span', {
            'data-socket-key': '5-gumus',
            'data-socket-attr': 'bid'
        })
        
        if price_element:
            return price_element.get_text(strip=True)
        return None
        
    except Exception as e:
        raise Exception(f"Silver price error: {str(e)}")

def is_authenticated():
    """Kullanıcının doğrulanıp doğrulanmadığını kontrol et"""
    # Session kontrolü
    if session.get('authenticated'):
        return True
    
    # Cookie kontrolü (alternatif yöntem)
    auth_token = request.cookies.get('auth_token')
    if auth_token:
        # Basit token doğrulama (gerçek projede daha güvenli olmalı)
        expected_token = hashlib.sha256(f"{SECRET_KEY}_authenticated".encode()).hexdigest()
        if auth_token == expected_token:
            # Session'ı yeniden oluştur
            session.permanent = True
            session['authenticated'] = True
            return True
    
    return False

def set_auth_cookie(response):
    """Doğrulama cookie'si ekle"""
    auth_token = hashlib.sha256(f"{SECRET_KEY}_authenticated".encode()).hexdigest()
    # Cookie'yi 1 yıl süreyle ayarla
    expires = datetime.now() + timedelta(days=365)
    response.set_cookie(
        'auth_token', 
        auth_token,
        expires=expires,
        httponly=True,
        secure=False,  # HTTPS için True yapın
        samesite='Lax'
    )
    return response

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker v2.0 - Dark Blue</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 25%, #334155 50%, #1e3a5f 75%, #0f172a 100%);
            background-attachment: fixed;
            min-height: 100vh; 
            padding: 20px; 
            color: #e2e8f0;
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(147, 51, 234, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 70%, rgba(16, 185, 129, 0.05) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
        }
        
        .container { 
            max-width: 480px; 
            margin: 0 auto; 
            display: flex; 
            flex-direction: column; 
            gap: 24px; 
            padding: 0 4px; 
            position: relative;
            z-index: 1;
        }
        
        /* Glassmorphism Card Base */
        .glass-card {
            background: rgba(15, 23, 42, 0.4);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(148, 163, 184, 0.1);
            box-shadow: 
                0 8px 32px rgba(0, 0, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }
        
        .glass-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        }
        
        .header {
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            padding: 20px 24px;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(24px);
            border: 1px solid rgba(148, 163, 184, 0.15);
        }
        
        .header-left { 
            display: flex; 
            align-items: center; 
            gap: 16px; 
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo { 
            font-size: 20px; 
            font-weight: 800; 
            color: #f8fafc;
            text-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        }
        
        .version { 
            font-size: 11px; 
            color: rgba(148, 163, 184, 0.8); 
            background: rgba(59, 130, 246, 0.2); 
            padding: 4px 10px; 
            border-radius: 12px;
            border: 1px solid rgba(59, 130, 246, 0.3);
            backdrop-filter: blur(10px);
        }
        
        .update-time { 
            font-size: 15px; 
            color: rgba(203, 213, 225, 0.9);
            font-weight: 500;
        }
        
        .actions { 
            display: flex; 
            gap: 12px; 
        }
        
        .action-btn {
            width: 48px; 
            height: 48px; 
            border-radius: 16px;
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(148, 163, 184, 0.2);
            color: #e2e8f0; 
            font-size: 20px; 
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex; 
            align-items: center; 
            justify-content: center;
            backdrop-filter: blur(12px);
            position: relative;
            overflow: hidden;
        }
        
        .action-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1));
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .action-btn:hover::before {
            opacity: 1;
        }
        
        .action-btn:hover { 
            background: rgba(30, 41, 59, 0.9);
            border-color: rgba(59, 130, 246, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(59, 130, 246, 0.2);
        }
        
        .portfolio-summary {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(147, 51, 234, 0.3) 100%);
            backdrop-filter: blur(24px);
            border-radius: 28px; 
            padding: 32px 24px; 
            color: white;
            box-shadow: 
                0 12px 40px rgba(0, 0, 0, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.15);
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .portfolio-summary::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.03), transparent);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%) translateY(-100%); }
            100% { transform: translateX(100%) translateY(100%); }
        }
        
        .portfolio-amount { 
            font-size: 48px; 
            font-weight: 900; 
            margin-bottom: 24px;
            background: linear-gradient(135deg, #f8fafc, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            position: relative;
            z-index: 1;
        }
        
        .portfolio-metals {
            display: flex; 
            justify-content: center; 
            gap: 12px;
            margin: 24px 0 0 0;
        }
        
        .metal-item {
            flex: 1;
            background: rgba(15, 23, 42, 0.4);
            backdrop-filter: blur(16px);
            border-radius: 20px; 
            padding: 20px 16px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            min-height: 160px;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .metal-item:hover {
            background: rgba(15, 23, 42, 0.6);
            border-color: rgba(59, 130, 246, 0.3);
            transform: translateY(-4px);
            box-shadow: 0 8px 32px rgba(59, 130, 246, 0.15);
        }
        
        .metal-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, rgba(59, 130, 246, 0.6), rgba(147, 51, 234, 0.6));
        }
        
        .metal-header { 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            margin-bottom: 16px; 
        }
        
        .metal-name { 
            font-size: 18px; 
            font-weight: 700;
            color: #f8fafc;
        }
        
        .metal-price { 
            font-size: 16px; 
            color: rgba(203, 213, 225, 0.8); 
            margin-bottom: 12px;
            font-weight: 500;
        }
        
        .metal-value { 
            font-size: 26px; 
            font-weight: 800;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .metal-amount { 
            font-size: 13px; 
            color: rgba(148, 163, 184, 0.8); 
            margin-top: 12px;
            font-weight: 500;
        }
        
        .statistics-section {
            background: rgba(15, 23, 42, 0.5);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 24px;
            border: 1px solid rgba(148, 163, 184, 0.15);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .statistics-title {
            font-size: 20px;
            font-weight: 800;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .statistics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 16px;
        }
        
        .stat-item {
            background: rgba(30, 41, 59, 0.6);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 20px 12px;
            text-align: center;
            border: 1px solid rgba(148, 163, 184, 0.15);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .stat-item:hover {
            background: rgba(30, 41, 59, 0.8);
            border-color: rgba(59, 130, 246, 0.3);
            transform: translateY(-2px);
        }
        
        .stat-label {
            font-size: 12px;
            color: rgba(148, 163, 184, 0.9);
            margin-bottom: 12px;
            line-height: 1.3;
            font-weight: 500;
        }
        
        .stat-value {
            font-size: 18px;
            font-weight: 800;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            word-wrap: break-word;
        }
        
        .price-history {
            background: rgba(15, 23, 42, 0.5);
            backdrop-filter: blur(20px);
            border-radius: 24px; 
            padding: 20px; 
            border: 1px solid rgba(148, 163, 184, 0.15);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .history-header {
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 20px;
        }
        
        .history-title { 
            font-size: 20px; 
            font-weight: 800; 
            color: #f8fafc;
        }
        
        .period-tabs {
            display: flex; 
            gap: 4px;
            background: rgba(30, 41, 59, 0.6); 
            border-radius: 16px; 
            padding: 6px;
            border: 1px solid rgba(148, 163, 184, 0.15);
            backdrop-filter: blur(12px);
        }
        
        .period-tab {
            padding: 10px 20px; 
            border: none; 
            border-radius: 12px;
            background: transparent; 
            color: rgba(203, 213, 225, 0.7);
            font-size: 13px; 
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }
        
        .period-tab.active { 
            background: rgba(59, 130, 246, 0.6);
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        
        .period-tab:hover:not(.active) {
            background: rgba(59, 130, 246, 0.2);
            color: #e2e8f0;
        }
        
        .price-table {
            overflow-x: auto; 
            border-radius: 16px; 
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(148, 163, 184, 0.15);
            backdrop-filter: blur(12px);
        }
        
        .price-table table {
            width: 100%; 
            border-collapse: collapse;
        }
        
        .price-table th {
            background: rgba(15, 23, 42, 0.8); 
            padding: 16px 12px; 
            text-align: left;
            font-weight: 700; 
            color: #f8fafc; 
            font-size: 14px;
            border-bottom: 2px solid rgba(59, 130, 246, 0.2); 
            white-space: nowrap;
            backdrop-filter: blur(8px);
        }
        
        .price-table td {
            padding: 16px 12px; 
            border-bottom: 1px solid rgba(148, 163, 184, 0.1);
            font-size: 14px; 
            color: #e2e8f0; 
            white-space: nowrap;
            font-weight: 500;
        }
        
       .price-table .time { 
            font-weight: 700; 
            color: #f8fafc;
        }
        
        .price-table .price { 
            font-weight: 600;
            color: #cbd5e1;
        }
        
        .price-table .portfolio { 
            font-weight: 800;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .price-table .change {
            font-weight: 700; 
            font-size: 14px;
        }
        
        .change.positive { 
            color: #10b981;
            text-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
        }
        
        .change.negative { 
            color: #ef4444;
            text-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
        }
        
        .change.neutral { 
            color: rgba(148, 163, 184, 0.8); 
        }
        
        /* Responsive Design */
        @media (max-width: 400px) {
            .container { 
                max-width: 100%; 
                padding: 0 2px; 
                gap: 20px;
            }
            
            .header {
                padding: 16px 20px;
            }
            
            .logo {
                font-size: 18px;
            }
            
            .portfolio-amount {
                font-size: 40px;
            }
            
            .history-header { 
                flex-direction: column; 
                gap: 16px; 
            }
            
            .portfolio-metals { 
                flex-direction: column; 
                gap: 16px; 
            }
            
            .metal-name { 
                font-size: 17px; 
            }
            
            .metal-price { 
                font-size: 15px; 
            }
            
            .metal-value { 
                font-size: 24px; 
            }
            
            .metal-item { 
                padding: 24px 20px; 
                min-height: 140px; 
            }
            
            .price-table th, .price-table td { 
                padding: 12px 8px; 
                font-size: 13px; 
            }
            
            .statistics-grid { 
                grid-template-columns: 1fr; 
                gap: 12px; 
            }
            
            .stat-item {
                padding: 16px 12px;
            }
            
            .period-tab {
                padding: 8px 16px;
                font-size: 12px;
            }
        }
        
        /* Scroll Animation */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .glass-card {
            animation: fadeInUp 0.6s ease-out;
        }
        
        .container > *:nth-child(1) { animation-delay: 0.1s; }
        .container > *:nth-child(2) { animation-delay: 0.2s; }
        .container > *:nth-child(3) { animation-delay: 0.3s; }
        .container > *:nth-child(4) { animation-delay: 0.4s; }
        
        /* Loading States */
        .loading {
            position: relative;
            overflow: hidden;
        }
        
        .loading::after {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.2), transparent);
            animation: loading 1.5s infinite;
        }
        
        @keyframes loading {
            0% { left: -100%; }
            100% { left: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header glass-card">
            <div class="header-left">
                <div class="logo-section">
                    <div class="logo">Metal Tracker</div>
                    <div class="version">v2.0</div>
                </div>
                <div class="update-time" id="headerTime">--:--</div>
            </div>
            <div class="actions">
                <button class="action-btn" onclick="fetchPrice()" id="refreshBtn">⟳</button>
                <button class="action-btn" onclick="logout()" title="Çıkış">🚪</button>
            </div>
        </div>
        
        <div class="portfolio-summary glass-card" id="portfolioSummary">
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="portfolio-metals">
                <div class="metal-item">
                    <div class="metal-header">
                        <div class="metal-name">Altın</div>
                    </div>
                    <div class="metal-price" id="goldCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="goldPortfolioValue">0,00 ₺</div>
                    <div class="metal-amount" id="goldAmount">0 gr</div>
                </div>
                <div class="metal-item">
                    <div class="metal-header">
                        <div class="metal-name">Gümüş</div>
                    </div>
                    <div class="metal-price" id="silverCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="silverPortfolioValue">0,00 ₺</div>
                    <div class="metal-amount" id="silverAmount">0 gr</div>
                </div>
            </div>
        </div>
        
        <div class="statistics-section glass-card">
            <div class="statistics-title">📊 Maksimum Değerler</div>
            <div class="statistics-grid">
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Altın Fiyatı</div>
                    <div class="stat-value" id="maxGoldPrice">0 ₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Gümüş Fiyatı</div>
                    <div class="stat-value" id="maxSilverPrice">0 ₺</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">En Yüksek<br>Portföy Tutarı</div>
                    <div class="stat-value" id="maxPortfolioValue">0 ₺</div>
                </div>
            </div>
        </div>
        
        <div class="price-history glass-card" id="priceHistory">
            <div class="history-header">
                <div class="history-title">Fiyat Geçmişi</div>
                <div class="period-tabs">
                    <button class="period-tab active" onclick="switchPeriod('daily')" id="dailyTab">Günlük</button>
                    <button class="period-tab" onclick="switchPeriod('weekly')" id="weeklyTab">Aylık</button>
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
                        <!-- Dynamic content -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let currentGoldPrice = 0;
        let currentSilverPrice = 0;
        let tableData = {};
        let currentPeriod = 'daily';
        let portfolioConfig = {};

        async function fetchPrice() {
            const refreshBtn = document.getElementById('refreshBtn');
            
            try {
                refreshBtn.style.transform = 'rotate(360deg)';
                refreshBtn.style.background = 'rgba(59, 130, 246, 0.3)';
                
                const [goldRes, silverRes, tableRes, configRes] = await Promise.all([
                    fetch('/api/gold-price'),
                    fetch('/api/silver-price'),
                    fetch('/api/table-data'),
                    fetch('/api/portfolio-config')
                ]);
                
                const goldData = await goldRes.json();
                const silverData = await silverRes.json();
                const tableDataRes = await tableRes.json();
                const configData = await configRes.json();
                
                if (goldData.success) {
                    let cleanPrice = goldData.price.replace(/[^\\d,]/g, '');
                    currentGoldPrice = parseFloat(cleanPrice.replace(',', '.'));
                    document.getElementById('goldCurrentPrice').textContent = goldData.price;
                }
                
                if (silverData.success) {
                    let cleanPrice = silverData.price.replace(/[^\\d,]/g, '');
                    currentSilverPrice = parseFloat(cleanPrice.replace(',', '.'));
                    document.getElementById('silverCurrentPrice').textContent = silverData.price;
                }
                
                if (configData.success) {
                    portfolioConfig = configData.config;
                    document.getElementById('goldAmount').textContent = portfolioConfig.gold_amount + ' gr';
                    document.getElementById('silverAmount').textContent = portfolioConfig.silver_amount + ' gr';
                }
                
                if (tableDataRes.success) {
                    tableData = tableDataRes.data;
                    updateTable();
                    updateStatistics();
                }
                
                document.getElementById('headerTime').textContent = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
                updatePortfolio();
                
            } catch (error) {
                console.error('Fetch error:', error);
                refreshBtn.style.background = 'rgba(239, 68, 68, 0.3)';
            } finally {
                setTimeout(() => {
                    refreshBtn.style.transform = 'rotate(0deg)';
                    refreshBtn.style.background = 'rgba(30, 41, 59, 0.8)';
                }, 500);
            }
        }

        function updateStatistics() {
            if (tableData.statistics && tableData.statistics[currentPeriod]) {
                const stats = tableData.statistics[currentPeriod];
                document.getElementById('maxGoldPrice').textContent = formatPrice(stats.max_gold_price);
                document.getElementById('maxSilverPrice').textContent = formatPrice(stats.max_silver_price);
                document.getElementById('maxPortfolioValue').textContent = formatCurrency(stats.max_portfolio_value);
                
                // İstatistik başlığını güncelle
                const periodText = currentPeriod === 'daily' ? 'Günlük' : 'Aylık';
                document.querySelector('.statistics-title').textContent = `📊 ${periodText} Maksimum Değerler`;
            }
        }

        function switchPeriod(period) {
            currentPeriod = period;
            document.querySelectorAll('.period-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(period + 'Tab').classList.add('active');
            
            const timeHeader = document.getElementById('timeHeader');
            if (period === 'daily') {
                timeHeader.textContent = 'Saat';
            } else if (period === 'weekly') {
                timeHeader.textContent = 'Tarih';
            }
            
            updateTable();
            updateStatistics();
        }

        function updateTable() {
            const goldAmount = portfolioConfig.gold_amount || 0;
            const silverAmount = portfolioConfig.silver_amount || 0;
            
            if (!tableData[currentPeriod]) return;
            
            const tbody = document.getElementById('priceTableBody');
            tbody.innerHTML = '';
            
            tableData[currentPeriod].forEach((item, index) => {
                let portfolioValue = (goldAmount * item.gold_price) + (silverAmount * item.silver_price);
                
                const row = document.createElement('tr');
                row.style.animationDelay = `${index * 0.05}s`;
                
                const timeDisplay = item.optimized ? 
                    `<span title="Günün peak değeri (${item.peak_time || 'bilinmiyor'})">${item.time}</span>` : 
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

        function updatePortfolio() {
            const goldAmount = portfolioConfig.gold_amount || 0;
            const silverAmount = portfolioConfig.silver_amount || 0;
            
            const goldValue = goldAmount * currentGoldPrice;
            const silverValue = silverAmount * currentSilverPrice;
            const totalValue = goldValue + silverValue;
            
            document.getElementById('totalAmount').textContent = formatCurrency(totalValue);
            document.getElementById('goldPortfolioValue').textContent = formatCurrency(goldValue);
            document.getElementById('silverPortfolioValue').textContent = formatCurrency(silverValue);
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

        function logout() {
            if (confirm('Oturumu kapatmak istediğinize emin misiniz?')) {
                fetch('/logout', {method: 'POST'}).then(() => {
                    window.location.href = '/login';
                });
            }
        }

        // Loading animation on page load
        window.onload = function() {
            // Add staggered fade-in animation
            const cards = document.querySelectorAll('.glass-card');
            cards.forEach((card, index) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px)';
                
                setTimeout(() => {
                    card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, index * 150);
            });
            
            setTimeout(() => {
                fetchPrice();
            }, 800);
        };
    </script>
</body>
</html>