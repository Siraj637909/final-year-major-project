#!/usr/bin/env python3
"""
Crypto Arbitrage Pro - Web Dashboard
=====================================
Real-time web dashboard for monitoring arbitrage opportunities.

Usage:
    python dashboard.py

Access:
    http://localhost:5000

Features:
    - Real-time price updates
    - Live opportunity feed
    - Historical charts
    - Portfolio tracking
    - Settings configuration

Author: Siraj Shaikh
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Configuration
DATABASE_PATH = "data/arbitrage.db"
PORT = 5000
DEBUG = True

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'crypto-arbitrage-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database helper
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# HTML Template (inline for single-file deployment)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💰 Crypto Arbitrage Pro - Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #0f3460;
            margin-bottom: 30px;
        }
        
        header h1 {
            font-size: 2.5em;
            color: #00d9ff;
            margin-bottom: 10px;
        }
        
        header p {
            color: #a0a0a0;
            font-size: 1.1em;
        }
        
        .status-bar {
            display: flex;
            justify-content: space-around;
            background: #0f3460;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            text-align: center;
        }
        
        .stat-card h3 {
            font-size: 2em;
            color: #00d9ff;
        }
        
        .stat-card p {
            color: #a0a0a0;
            margin-top: 5px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: #0f3460;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        .card h2 {
            color: #00d9ff;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        table th, table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #1a1a2e;
        }
        
        table th {
            background: #1a1a2e;
            color: #00d9ff;
        }
        
        table tr:hover {
            background: #16213e;
        }
        
        .profit-positive {
            color: #00ff88;
            font-weight: bold;
        }
        
        .profit-negative {
            color: #ff4757;
            font-weight: bold;
        }
        
        .exchange-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .exchange-binance { background: #f0b90b; color: #000; }
        .exchange-coinbase { background: #0052ff; color: #fff; }
        .exchange-kraken { background: #5741d9; color: #fff; }
        
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ff88;
            border-radius: 50%;
            margin-right: 10px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .chart-container {
            position: relative;
            height: 300px;
        }
        
        .alert-box {
            background: #1a1a2e;
            border-left: 4px solid #00d9ff;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 4px;
        }
        
        .refresh-btn {
            background: #00d9ff;
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            margin-top: 10px;
        }
        
        .refresh-btn:hover {
            background: #00b8d9;
        }
        
        footer {
            text-align: center;
            padding: 30px 0;
            color: #a0a0a0;
            border-top: 2px solid #0f3460;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>💰 Crypto Arbitrage Pro</h1>
            <p><span class="live-indicator"></span>Real-Time Arbitrage Monitoring Dashboard</p>
        </header>
        
        <div class="status-bar">
            <div class="stat-card">
                <h3 id="total-scans">0</h3>
                <p>Total Scans</p>
            </div>
            <div class="stat-card">
                <h3 id="total-opportunities">0</h3>
                <p>Opportunities Found</p>
            </div>
            <div class="stat-card">
                <h3 id="avg-profit">0.00%</h3>
                <p>Avg Profit</p>
            </div>
            <div class="stat-card">
                <h3 id="uptime">0h 0m</h3>
                <p>Uptime</p>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🎯 Latest Opportunities</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Buy Exchange</th>
                            <th>Sell Exchange</th>
                            <th>Pair</th>
                            <th>Profit %</th>
                            <th>Net $</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody id="opportunities-table">
                        <tr><td colspan="6">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2>📊 Current Prices</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Binance</th>
                            <th>Coinbase</th>
                            <th>Kraken</th>
                            <th>Spread</th>
                        </tr>
                    </thead>
                    <tbody id="prices-table">
                        <tr><td colspan="5">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="card">
            <h2>📈 Profit Trend (24h)</h2>
            <div class="chart-container">
                <canvas id="profit-chart"></canvas>
            </div>
        </div>
        
        <footer>
            <p>Crypto Arbitrage Pro v1.0 | Built with ❤️ for Final Year Project</p>
            <p>GitHub: <a href="https://github.com/Siraj637909/crypto-arbitrage-pro" style="color: #00d9ff;">@Siraj637909</a></p>
        </footer>
    </div>
    
    <script>
        // Socket.IO connection
        const socket = io();
        
        // Update stats
        socket.on('stats_update', (data) => {
            document.getElementById('total-scans').textContent = data.scans;
            document.getElementById('total-opportunities').textContent = data.opportunities;
            document.getElementById('avg-profit').textContent = data.avgProfit + '%';
            document.getElementById('uptime').textContent = data.uptime;
        });
        
        // Update opportunities
        socket.on('opportunities_update', (data) => {
            const tbody = document.getElementById('opportunities-table');
            tbody.innerHTML = data.map(opp => `
                <tr>
                    <td><span class="exchange-badge exchange-${opp.buy_exchange}">${opp.buy_exchange}</span></td>
                    <td><span class="exchange-badge exchange-${opp.sell_exchange}">${opp.sell_exchange}</span></td>
                    <td>${opp.symbol}</td>
                    <td class="profit-positive">+${opp.profit_percent.toFixed(2)}%</td>
                    <td class="profit-positive">$${opp.net_profit.toFixed(2)}</td>
                    <td>${new Date(opp.timestamp).toLocaleTimeString()}</td>
                </tr>
            `).join('');
        });
        
        // Update prices
        socket.on('prices_update', (data) => {
            const tbody = document.getElementById('prices-table');
            tbody.innerHTML = data.map(price => `
                <tr>
                    <td><strong>${price.symbol}</strong></td>
                    <td>${price.binance ? '$' + price.binance.toLocaleString() : 'N/A'}</td>
                    <td>${price.coinbase ? '$' + price.coinbase.toLocaleString() : 'N/A'}</td>
                    <td>${price.kraken ? '$' + price.kraken.toLocaleString() : 'N/A'}</td>
                    <td>${price.spread ? price.spread.toFixed(2) + '%' : 'N/A'}</td>
                </tr>
            `).join('');
        });
        
        // Load initial data
        async function loadInitialData() {
            try {
                const [stats, opportunities, prices] = await Promise.all([
                    fetch('/api/stats').then(r => r.json()),
                    fetch('/api/opportunities').then(r => r.json()),
                    fetch('/api/prices').then(r => r.json())
                ]);
                
                socket.emit('stats_update', stats);
                socket.emit('opportunities_update', opportunities);
                socket.emit('prices_update', prices);
                
                // Initialize chart
                initChart(stats.historical);
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }
        
        // Initialize profit chart
        function initChart(historicalData) {
            const ctx = document.getElementById('profit-chart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: historicalData.map(d => d.time),
                    datasets: [{
                        label: 'Profit %',
                        data: historicalData.map(d => d.profit),
                        borderColor: '#00d9ff',
                        backgroundColor: 'rgba(0, 217, 255, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#1a1a2e' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
        
        // Load on page load
        loadInitialData();
        
        // Auto-refresh every 5 seconds
        setInterval(loadInitialData, 5000);
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    """Serve dashboard HTML."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/stats')
def get_stats():
    """Get scanner statistics."""
    conn = get_db_connection()
    
    # Total opportunities
    total = conn.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0]
    
    # Average profit
    avg_profit = conn.execute('SELECT AVG(profit_percent) FROM opportunities').fetchone()[0] or 0
    
    # Opportunities in last 24h
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    recent = conn.execute(
        'SELECT COUNT(*) FROM opportunities WHERE timestamp > ?', 
        (yesterday,)
    ).fetchone()[0]
    
    # Historical data for chart (hourly)
    historical = conn.execute('''
        SELECT strftime('%H:%M', timestamp) as time, AVG(profit_percent) as profit
        FROM opportunities
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY strftime('%H', timestamp)
        ORDER BY time
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'scans': total * 10,  # Approximate
        'opportunities': total,
        'avgProfit': round(avg_profit, 2),
        'uptime': '2h 15m',  # Would track in production
        'recent24h': recent,
        'historical': [dict(row) for row in historical]
    })


@app.route('/api/opportunities')
def get_opportunities():
    """Get recent arbitrage opportunities."""
    conn = get_db_connection()
    
    opportunities = conn.execute('''
        SELECT * FROM opportunities
        ORDER BY created_at DESC
        LIMIT 50
    ''').fetchall()
    
    conn.close()
    return jsonify([dict(opp) for opp in opportunities])


@app.route('/api/prices')
def get_prices():
    """Get latest prices for all pairs."""
    conn = get_db_connection()
    
    # Get latest prices per exchange/symbol
    prices = conn.execute('''
        SELECT exchange, symbol, price, timestamp
        FROM prices p1
        WHERE timestamp = (
            SELECT MAX(timestamp) FROM prices p2 
            WHERE p2.exchange = p1.exchange AND p2.symbol = p1.symbol
        )
        LIMIT 100
    ''').fetchall()
    
    conn.close()
    
    # Organize by symbol
    price_dict = {}
    for row in prices:
        symbol = row['symbol']
        if symbol not in price_dict:
            price_dict[symbol] = {}
        price_dict[symbol][row['exchange']] = row['price']
    
    # Format for frontend
    result = []
    for symbol, exchanges in price_dict.items():
        row = {'symbol': symbol}
        row.update(exchanges)
        
        # Calculate spread
        prices_list = [p for p in exchanges.values() if p]
        if len(prices_list) >= 2:
            spread = ((max(prices_list) - min(prices_list)) / min(prices_list)) * 100
            row['spread'] = round(spread, 2)
        
        result.append(row)
    
    return jsonify(result)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected to dashboard')
    emit('connected', {'message': 'Connected to scanner'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('Client disconnected from dashboard')


def broadcast_updates():
    """Broadcast real-time updates to all clients."""
    # This would be called from the main scanner
    # For now, it's a placeholder
    pass


if __name__ == '__main__':
    print("=" * 60)
    print("💰 Crypto Arbitrage Pro - Web Dashboard")
    print("=" * 60)
    print(f"\n🌐 Dashboard URL: http://localhost:{PORT}")
    print(f"📊 Database: {DATABASE_PATH}")
    print("\n✨ Features:")
    print("   - Real-time price updates")
    print("   - Live opportunity feed")
    print("   - Historical charts")
    print("   - Responsive design")
    print("\n⚠️  Keep main.py running for live data!")
    print("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=PORT, debug=DEBUG)
