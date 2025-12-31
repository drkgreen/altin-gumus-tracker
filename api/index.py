#!/usr/bin/env python3
"""
Metal Price Tracker Web App v3.0 - Secure Version
Flask web uygulaması - Şifre korumalı
"""
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
CORS(app)

def load_portfolio_config():
    try:
        with open('portfolio-config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"gold_amount": 0, "silver_amount": 0, "password_hash": ""}

def verify_password(password):
    try:
        config = load_portfolio_config()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == config.get("password_hash", "")
    except:
        return False

def load_price_history():
    try:
        url = "https://raw.githubusercontent.com/drkgreen/altin-gumus-tracker/main/data/price-history.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"records": []}
    except:
        return {"records": []}

def get_hourly_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        if not records:
            return []
        
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        hourly_data = []
        
        today_records = [r for r in records if r.get("date") == today and r.get("gold_price") and r.get("silver_price") and not r.get("optimized", False)]
        
        if today_records:
            sorted_records = sorted(today_records, key=lambda x: x.get("timestamp", 0), reverse=True)
            for i, record in enumerate(sorted_records):
                timestamp = record.get("timestamp", 0)
                local_time = datetime.fromtimestamp(timestamp, timezone.utc) + timedelta(hours=3)
                time_label = local_time.strftime("%H:%M")
                change_percent = 0
                if i < len(sorted_records) - 1:
                    prev_record = sorted_records[i + 1]
                    if prev_record and prev_record.get("gold_price"):
                        price_diff = record["gold_price"] - prev_record["gold_price"]
                        change_percent = (price_diff / prev_record["gold_price"]) * 100
                hourly_data.append({"time": time_label, "gold_price": record["gold_price"], "silver_price": record["silver_price"], "change_percent": change_percent, "optimized": False})
        return hourly_data
    except:
        return []

def get_daily_optimized_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        if not records:
            return []
        daily_peaks = [r for r in records if r.get("daily_peak") == True]
        daily_data = []
        daily_temp = []
        now = datetime.now(timezone.utc)
        for i in range(6, -1, -1):
            target_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            day_record = next((r for r in daily_peaks if r.get("date") == target_date),         <div class="header">
            <div class="header-left">
                <div class="logo">🔐 Metal Tracker</div>
                <div class="version">v3.0</div>
            </div>
            <div class="header-center">
                <div class="update-time" id="headerTime">--:--</div>
            </div>
            <div class="actions">
                <button class="action-btn" onclick="fetchPrice()" id="refreshBtn" title="Yenile">⟳</button>
                <button class="action-btn" onclick="logout()" title="Çıkış">🚪</button>
            </div>
        </div>)
            if day_record:
                day_name = (now - timedelta(days=i)).strftime("%d.%m")
                daily_temp.append({"time": day_name, "gold_price": day_record["gold_price"], "silver_price": day_record["silver_price"], "peak_time": day_record.get("peak_time", "unknown"), "portfolio_value": day_record.get("portfolio_value", 0)})
        for i, day_data in enumerate(daily_temp):
            change_percent = 0
            if i > 0:
                prev_day = daily_temp[i-1]
                if prev_day["gold_price"] > 0:
                    price_diff = day_data["gold_price"] - prev_day["gold_price"]
                    change_percent = (price_diff / prev_day["gold_price"]) * 100
            daily_data.append({"time": f"{day_data['time']}", "gold_price": day_data["gold_price"], "silver_price": day_data["silver_price"], "change_percent": change_percent, "optimized": True, "peak_time": day_data["peak_time"], "portfolio_value": day_data["portfolio_value"]})
        daily_data.reverse()
        return daily_data
    except:
        return []

def get_monthly_optimized_data():
    try:
        history = load_price_history()
        records = history.get("records", [])
        if not records:
            return []
        monthly_peaks = [r for r in records if r.get("monthly_peak") == True]
        monthly_data = []
        monthly_temp = []
        now = datetime.now(timezone.utc)
        for i in range(11, -1, -1):
            target_month = (now - timedelta(days=i*30)).strftime("%Y-%m")
            month_record = next((r for r in monthly_peaks if r.get("date", "").startswith(target_month)), None)
            if month_record:
                month_date = datetime.strptime(month_record["date"], "%Y-%m-%d")
                month_names = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
                month_label = f"{month_names[month_date.month]} {month_date.year}"
                monthly_temp.append({"time": month_label, "gold_price": month_record["gold_price"], "silver_price": month_record["silver_price"], "peak_time": month_record.get("peak_time", "unknown"), "peak_date": month_record.get("date", "unknown"), "portfolio_value": month_record.get("portfolio_value", 0)})
        for i, month_data in enumerate(monthly_temp):
            change_percent = 0
            if i > 0:
                prev_month = monthly_temp[i-1]
                if prev_month["gold_price"] > 0:
                    price_diff = month_data["gold_price"] - prev_month["gold_price"]
                    change_percent = (price_diff / prev_month["gold_price"]) * 100
            monthly_data.append({"time": f"{month_data['time']}", "gold_price": month_data["gold_price"], "silver_price": month_data["silver_price"], "change_percent": change_percent, "optimized": True, "peak_time": month_data["peak_time"], "peak_date": month_data["peak_date"], "portfolio_value": month_data["portfolio_value"]})
        monthly_data.reverse()
        return monthly_data
    except:
        return []

def get_table_data():
    try:
        return {"hourly": get_hourly_data(), "daily": get_daily_optimized_data(), "monthly": get_monthly_optimized_data()}
    except:
        return {"hourly": [], "daily": [], "monthly": []}

def get_gold_price():
    try:
        url = "https://m.doviz.com/altin/yapikredi/gram-altin"
        headers = {'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        price_element = soup.find('span', {'data-socket-key': '6-gram-altin', 'data-socket-attr': 'bid'})
        if price_element:
            return price_element.get_text(strip=True)
        return None
    except Exception as e:
        raise Exception(f"Gold price error: {str(e)}")

def get_silver_price():
    try:
        url = "https://m.doviz.com/altin/vakifbank/gumus"
        headers = {'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        price_element = soup.find('span', {'data-socket-key': '5-gumus', 'data-socket-attr': 'bid'})
        if price_element:
            return price_element.get_text(strip=True)
        return None
    except Exception as e:
        raise Exception(f"Silver price error: {str(e)}")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Tracker v3.0</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            min-height: 100vh;
            padding: 15px;
            color: #334155;
        }

        .container {
            max-width: min(95vw, 420px);
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: max(4px, min(1.5vh, 12px));
            padding: max(2px, min(1vw, 8px));
            position: relative;
            z-index: 1;
            min-height: 100vh;
            box-sizing: border-box;
        }

        .login-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #1a202c 0%, #2d3748 50%, #1a202c 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        }

        .loading-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #1a202c 0%, #2d3748 50%, #1a202c 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 3000;
        }

        .loading-box {
            text-align: center;
        }

        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(99, 179, 237, 0.3);
            border-top: 3px solid #63b3ed;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            color: #63b3ed;
            font-size: 16px;
            font-weight: 500;
        }

        .login-box {
            background: rgba(45, 55, 72, 0.8);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(74, 85, 104, 0.5);
            border-radius: 16px;
            padding: 32px;
            width: 90%;
            max-width: 360px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }

        .login-title {
            font-size: 24px;
            font-weight: 700;
            color: #63b3ed;
            text-align: center;
            margin-bottom: 24px;
        }

        .login-input {
            width: 100%;
            padding: 14px 18px;
            background: rgba(45, 55, 72, 0.6);
            border: 1px solid rgba(74, 85, 104, 0.6);
            border-radius: 12px;
            font-size: 16px;
            margin-bottom: 18px;
            font-weight: 500;
            color: #e2e8f0;
            transition: all 0.3s ease;
        }

        .login-input:focus {
            outline: none;
            border-color: #63b3ed;
            background: rgba(45, 55, 72, 0.8);
        }

        .login-input::placeholder {
            color: rgba(226, 232, 240, 0.5);
        }

        .login-btn {
            width: 100%;
            padding: 14px;
            background: #4299e1;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .login-btn:hover {
            background: #3182ce;
            transform: translateY(-1px);
        }

        .login-error {
            color: #f56565;
            text-align: center;
            margin-top: 12px;
            font-size: 14px;
            font-weight: 500;
            display: none;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(45, 55, 72, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(74, 85, 104, 0.4);
            border-radius: max(8px, min(2vw, 14px));
            padding: max(8px, min(2vh, 16px)) max(10px, min(3vw, 20px));
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            min-height: max(40px, min(8vh, 60px));
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            min-width: 0;
        }

        .header-info {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }

        .logo {
            font-size: 16px;
            font-weight: 700;
            color: #63b3ed;
            white-space: nowrap;
        }

        .version {
            font-size: 9px;
            color: rgba(99, 179, 237, 0.7);
            background: rgba(99, 179, 237, 0.15);
            padding: 2px 6px;
            border-radius: 6px;
            white-space: nowrap;
        }

        .update-time {
            font-size: 12px;
            color: rgba(226, 232, 240, 0.8);
            font-weight: 500;
            margin-left: auto;
            white-space: nowrap;
        }

        .header-info {
            display: flex;
            align-items: center;
            gap: max(6px, min(1.5vw, 10px));
            flex-shrink: 0;
        }

        .logo {
            font-size: max(14px, min(4vw, 18px));
            font-weight: 700;
            color: #63b3ed;
            white-space: nowrap;
        }

        .version {
            font-size: max(8px, min(2.5vw, 11px));
            color: rgba(99, 179, 237, 0.7);
            background: rgba(99, 179, 237, 0.15);
            padding: max(2px, min(0.5vh, 4px)) max(4px, min(1vw, 8px));
            border-radius: max(4px, min(1vw, 8px));
            white-space: nowrap;
        }

        .actions {
            display: flex;
            gap: max(6px, min(1.5vw, 10px));
            flex-shrink: 0;
        }

        .action-btn {
            width: max(32px, min(8vw, 40px));
            height: max(32px, min(8vw, 40px));
            border-radius: max(6px, min(1.5vw, 10px));
            background: rgba(45, 55, 72, 0.8);
            border: 1px solid rgba(74, 85, 104, 0.4);
            color: #63b3ed;
            font-size: max(12px, min(3.5vw, 16px));
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .action-btn:hover {
            background: rgba(99, 179, 237, 0.2);
            border-color: #63b3ed;
        }

        .portfolio-summary {
            background: rgba(45, 55, 72, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(74, 85, 104, 0.4);
            border-radius: 16px;
            padding: 20px 18px;
            color: #e2e8f0;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.2);
            text-align: center;
        }

        .portfolio-amount {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 20px;
            color: #63b3ed;
        }

        .portfolio-metals {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin: 20px 0 0 0;
        }

        .metal-item {
            flex: 1;
            background: rgba(45, 55, 72, 0.6);
            border: 1px solid rgba(74, 85, 104, 0.3);
            border-radius: 12px;
            padding: 16px 12px;
            min-height: 130px;
            transition: all 0.3s ease;
        }

        .metal-item:hover {
            background: rgba(45, 55, 72, 0.8);
            border-color: rgba(99, 179, 237, 0.4);
        }

        .metal-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            margin-bottom: 12px;
        }

        .metal-name {
            font-size: 16px;
            font-weight: 600;
            color: #63b3ed;
        }

        .metal-amount {
            font-size: 12px;
            color: rgba(226, 232, 240, 0.7);
            margin-bottom: 6px;
            font-weight: 500;
        }

        .metal-price {
            font-size: 13px;
            color: rgba(226, 232, 240, 0.6);
            margin-bottom: 8px;
        }

        .metal-value {
            font-size: 18px;
            font-weight: 700;
            color: #e2e8f0;
        }

        .price-history {
            background: rgba(45, 55, 72, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(74, 85, 104, 0.4);
            border-radius: max(10px, min(2.5vw, 16px));
            padding: max(10px, min(2.5vh, 20px)) max(4px, min(1vw, 8px));
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.2);
            margin: 0 max(-4px, min(-1vw, -8px));
            width: calc(100% + max(8px, min(2vw, 16px)));
            flex: 1;
            min-height: 0;
        }

        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
            padding: 0 10px;
            gap: 8px;
        }

        .history-title {
            font-size: 14px;
            font-weight: 600;
            color: #63b3ed;
            flex-shrink: 0;
        }

        .period-tabs {
            display: flex;
            gap: 2px;
            background: rgba(45, 55, 72, 0.8);
            border: 1px solid rgba(74, 85, 104, 0.3);
            border-radius: 8px;
            padding: 2px;
            flex-shrink: 0;
        }

        .period-tab {
            padding: 6px 10px;
            border: none;
            border-radius: 6px;
            background: transparent;
            color: rgba(226, 232, 240, 0.6);
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
        }

        .period-tab.active {
            background: rgba(99, 179, 237, 0.2);
            color: #63b3ed;
        }

        .price-table {
            overflow-x: auto;
            border-radius: 10px;
            background: rgba(45, 55, 72, 0.5);
            border: 1px solid rgba(74, 85, 104, 0.2);
            margin: 0 8px;
            max-height: max(300px, min(40vh, 400px));
            overflow-y: auto;
        }

        .price-table table {
            width: 100%;
            border-collapse: collapse;
        }

        .price-table thead {
            position: sticky;
            top: 0;
            background: rgba(45, 55, 72, 0.95);
            z-index: 10;
        }

        .price-table th {
            background: rgba(45, 55, 72, 0.8);
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            color: #63b3ed;
            font-size: 12px;
            border-bottom: 1px solid rgba(74, 85, 104, 0.3);
            white-space: nowrap;
        }

        .price-table td {
            padding: 10px 8px;
            border-bottom: 1px solid rgba(74, 85, 104, 0.1);
            font-size: 12px;
            color: rgba(226, 232, 240, 0.8);
            white-space: nowrap;
        }

        .price-table tr:hover {
            background: rgba(99, 179, 237, 0.05);
        }

        .price-table .time {
            font-weight: 600;
            color: #e2e8f0;
        }

        .price-table .price {
            font-weight: 600;
            color: #63b3ed;
        }

        .price-table .portfolio {
            font-weight: 700;
            color: #4299e1;
            line-height: 1.2;
        }

        .price-table .change {
            font-weight: 600;
            font-size: 11px;
        }

        .change.positive {
            color: #68d391;
        }

        .change.negative {
            color: #f56565;
        }

        .change.neutral {
            color: rgba(226, 232, 240, 0.5);
        }

        .statistics-section {
            margin-top: 12px;
            padding-top: 0;
        }

        .statistics-grid {
            display: flex;
            gap: 6px;
        }

        .stat-item {
            flex: 1;
            background: rgba(45, 55, 72, 0.6);
            border: 1px solid rgba(74, 85, 104, 0.3);
            border-radius: 10px;
            padding: 16px 12px;
            text-align: center;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: all 0.3s ease;
        }

        .stat-item:hover {
            background: rgba(45, 55, 72, 0.8);
            border-color: rgba(99, 179, 237, 0.4);
        }

        .stat-title {
            font-size: 11px;
            font-weight: 600;
            color: #63b3ed;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 15px;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 4px;
        }

        .stat-time {
            font-size: 10px;
            color: rgba(226, 232, 240, 0.6);
            font-weight: 500;
        }

        @media (max-width: 480px) {
            .container {
                max-width: 100%;
                padding: 0 8px;
                gap: 6px;
            }

            .header {
                padding: 10px 12px;
                min-height: 50px;
            }

            .header-left {
                gap: 6px;
            }

            .logo {
                font-size: 14px;
            }

            .version {
                font-size: 8px;
                padding: 1px 4px;
            }

            .update-time {
                font-size: 11px;
            }

            .actions {
                gap: 6px;
            }

            .action-btn {
                width: 32px;
                height: 32px;
                font-size: 12px;
            }

            .portfolio-summary {
                padding: 20px 16px;
            }

            .portfolio-amount {
                font-size: 28px;
                margin-bottom: 20px;
            }

            .portfolio-metals {
                gap: 12px;
                margin-top: 20px;
            }

            .metal-item {
                padding: 16px 12px;
                min-height: 120px;
            }

            .metal-name {
                font-size: 16px;
                margin-bottom: 10px;
            }

            .metal-amount {
                font-size: 12px;
                margin-bottom: 6px;
            }

            .metal-price {
                font-size: 12px;
                margin-bottom: 8px;
            }

            .metal-value {
                font-size: 18px;
            }

            .price-history {
                padding: 12px 4px;
                margin: 0 -4px;
                width: calc(100% + 8px);
            }

            .history-header {
                padding: 0 6px;
                gap: 6px;
                margin-bottom: 12px;
            }

            .history-title {
                font-size: 13px;
            }

            .period-tab {
                padding: 5px 8px;
                font-size: 10px;
            }

            .statistics-summary {
                padding: 14px 12px;
                gap: 10px;
            }

            .stat-item {
                padding: 12px 8px;
                min-height: 85px;
            }

            .stat-title {
                font-size: 11px;
                margin-bottom: 6px;
            }

            .stat-value {
                font-size: 14px;
                margin-bottom: 3px;
            }

            .stat-time {
                font-size: 10px;
            }
        }

        @media (max-width: 360px) {
            .container {
                padding: 0 4px;
                gap: 12px;
            }

            .portfolio-metals {
                flex-direction: column;
                gap: 8px;
            }

            .metal-item {
                padding: 16px 10px;
                min-height: 100px;
            }

            .metal-name {
                font-size: 15px;
                margin-bottom: 8px;
            }

            .metal-amount {
                font-size: 11px;
                margin-bottom: 4px;
            }

            .metal-price {
                font-size: 11px;
                margin-bottom: 6px;
            }

            .metal-value {
                font-size: 16px;
            }

            .history-header {
                flex-direction: column;
                gap: 8px;
                align-items: stretch;
            }

            .period-tabs {
                justify-content: center;
            }

            .period-tab {
                flex: 1;
                text-align: center;
            }
        }

        @media (min-width: 481px) and (max-width: 768px) {
            .container {
                max-width: 450px;
                gap: 16px;
            }

            .portfolio-metals {
                gap: 12px;
            }

            .metal-item {
                max-width: 200px;
            }

            .statistics-summary {
                gap: 12px;
            }

            .stat-item {
                min-height: 90px;
                padding: 14px 10px;
            }

            .stat-title {
                font-size: 12px;
            }

            .stat-value {
                font-size: 15px;
            }

            .stat-time {
                font-size: 11px;
            }
        } 13px;
            }

            .metal-price {
                font-size: 14px;
            }

            .metal-value {
                font-size: 20px;
            }

            .metal-item {
                padding: 18px;
                min-height: 140px;
            }

            .price-table th,
            .price-table td {
                padding: 12px 8px;
                font-size: 12px;
            }

            .price-history {
                padding: 16px 6px;
                margin: 0 -6px;
                width: calc(100% + 12px);
            }

            .price-table {
                margin: 0 8px;
            }

            .history-header {
                padding: 0 10px;
            }

            .period-tabs {
                flex-wrap: wrap;
            }

            .period-tab {
                font-size: 12px;
                padding: 8px 12px;
            }

            .header {
                padding: 16px 20px;
            }

            .portfolio-amount {
                font-size: 36px;
            }

            .portfolio-summary {
                padding: 24px 20px;
            }
        }
    </style>
</head>
<body>
    <div class="login-screen" id="loginScreen" style="display:none;">
        <div class="login-box">
            <div class="login-title">🔐 Metal Tracker</div>
            <input type="password" class="login-input" id="passwordInput" placeholder="Şifre" onkeypress="if(event.key==='Enter')login()">
            <button class="login-btn" onclick="login()">Giriş</button>
            <div class="login-error" id="loginError">Hatalı şifre!</div>
        </div>
    </div>

    <div class="loading-screen" id="loadingScreen">
        <div class="loading-box">
            <div class="loading-spinner"></div>
            <div class="loading-text">Metal Tracker yükleniyor...</div>
        </div>
    </div>

    <div class="container" id="mainApp" style="display:none;">
        <div class="header">
            <div class="header-left">
                <div>
                    <div class="logo">Metal Tracker</div>
                    <div class="version">v3.0</div>
                </div>
                <div class="update-time" id="headerTime">--:--</div>
            </div>
            <div class="actions">
                <button class="action-btn" onclick="fetchPrice()" id="refreshBtn" title="Yenile">⟳</button>
                <button class="action-btn" onclick="logout()" title="Çıkış">🚪</button>
            </div>
        </div>

        <div class="portfolio-summary">
            <div class="portfolio-amount" id="totalAmount">0,00 ₺</div>
            <div class="portfolio-metals">
                <div class="metal-item">
                    <div class="metal-name">Altın</div>
                    <div class="metal-amount" id="goldAmount">0 gr</div>
                    <div class="metal-price" id="goldCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="goldPortfolioValue">0,00 ₺</div>
                </div>
                <div class="metal-item">
                    <div class="metal-name">Gümüş</div>
                    <div class="metal-amount" id="silverAmount">0 gr</div>
                    <div class="metal-price" id="silverCurrentPrice">0,00 ₺/gr</div>
                    <div class="metal-value" id="silverPortfolioValue">0,00 ₺</div>
                </div>
            </div>
            
            <div class="statistics-section">
                <div class="statistics-grid">
                    <div class="stat-item">
                        <div class="stat-title">En Yüksek Altın</div>
                        <div class="stat-value" id="highestGold">0,00 ₺</div>
                        <div class="stat-time" id="highestGoldTime">--:--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-title">En Yüksek Gümüş</div>
                        <div class="stat-value" id="highestSilver">0,00 ₺</div>
                        <div class="stat-time" id="highestSilverTime">--:--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-title">En Yüksek Portföy</div>
                        <div class="stat-value" id="highestPortfolio">0,00 ₺</div>
                        <div class="stat-time" id="highestPortfolioTime">--:--</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="price-history">
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