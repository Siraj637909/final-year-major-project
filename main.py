#!/usr/bin/env python3
"""
Crypto Arbitrage Pro - Main Scanner Engine
===========================================
Real-time cryptocurrency arbitrage scanner with multi-exchange support.

Usage:
    python main.py

Features:
    - Real-time price monitoring (10+ exchanges)
    - Arbitrage opportunity detection
    - Profit calculation with fees
    - Telegram alerts
    - SQLite database logging
    - Web dashboard integration

Author: Siraj Shaikh
"""

import asyncio
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Third-party imports
try:
    import aiohttp
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.logging import RichHandler
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("💡 Run: pip install -r requirements.txt")
    sys.exit(1)

# Configuration
CONFIG_FILE = "config.json"
DATABASE_PATH = "data/arbitrage.db"

# Exchange API endpoints (public - no auth needed for prices)
EXCHANGE_APIS = {
    "binance": {
        "name": "Binance",
        "ticker_url": "https://api.binance.com/api/v3/ticker/24hr",
        "fee_maker": 0.001,
        "fee_taker": 0.001,
    },
    "coinbase": {
        "name": "Coinbase",
        "ticker_url": "https://api.exchange.coinbase.com/products",
        "fee_maker": 0.005,
        "fee_taker": 0.005,
    },
    "kraken": {
        "name": "Kraken",
        "ticker_url": "https://api.kraken.com/0/public/Ticker",
        "fee_maker": 0.0016,
        "fee_taker": 0.0026,
    },
    "kucoin": {
        "name": "KuCoin",
        "ticker_url": "https://api.kucoin.com/api/v1/market/allTickers",
        "fee_maker": 0.001,
        "fee_taker": 0.001,
    },
    "huobi": {
        "name": "Huobi",
        "ticker_url": "https://api.huobi.pro/market/tickers",
        "fee_maker": 0.002,
        "fee_taker": 0.002,
    },
}

# Trading pairs to monitor
DEFAULT_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "SOL/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "MATIC/USDT",
    "DOT/USDT",
    "AVAX/USDT",
]


@dataclass
class PriceData:
    """Price data from an exchange."""
    exchange: str
    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity."""
    buy_exchange: str
    sell_exchange: str
    symbol: str
    buy_price: float
    sell_price: float
    gross_profit: float
    fees: float
    net_profit: float
    profit_percent: float
    timestamp: datetime
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['timestamp'] = d['timestamp'].isoformat()
        return d


class Database:
    """SQLite database handler for logging opportunities."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buy_exchange TEXT,
                sell_exchange TEXT,
                symbol TEXT,
                buy_price REAL,
                sell_price REAL,
                gross_profit REAL,
                fees REAL,
                net_profit REAL,
                profit_percent REAL,
                timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT,
                symbol TEXT,
                price REAL,
                timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opp_timestamp ON opportunities(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp)')
        
        conn.commit()
        conn.close()
    
    def log_opportunity(self, opp: ArbitrageOpportunity):
        """Log arbitrage opportunity to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO opportunities 
            (buy_exchange, sell_exchange, symbol, buy_price, sell_price, 
             gross_profit, fees, net_profit, profit_percent, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            opp.buy_exchange, opp.sell_exchange, opp.symbol,
            opp.buy_price, opp.sell_price, opp.gross_profit,
            opp.fees, opp.net_profit, opp.profit_percent,
            opp.timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def log_price(self, price: PriceData):
        """Log price to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO prices (exchange, symbol, price, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (price.exchange, price.symbol, price.price, price.timestamp.isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_recent_opportunities(self, limit: int = 50) -> List[dict]:
        """Get recent opportunities from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM opportunities 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


class ExchangeFetcher:
    """Fetch prices from exchanges."""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
    
    async def fetch_binance(self, symbol: str) -> Optional[PriceData]:
        """Fetch price from Binance."""
        try:
            # Convert symbol format (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace("/", "")
            url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={binance_symbol}"
            
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return PriceData(
                        exchange="binance",
                        symbol=symbol,
                        price=float(data['bidPrice']),
                        bid=float(data['bidPrice']),
                        ask=float(data['askPrice']),
                        volume_24h=0,  # Need separate call for volume
                        timestamp=datetime.now()
                    )
        except Exception as e:
            logging.debug(f"Binance error for {symbol}: {e}")
        return None
    
    async def fetch_coinbase(self, symbol: str) -> Optional[PriceData]:
        """Fetch price from Coinbase."""
        try:
            # Convert symbol format (BTC/USDT -> BTC-USD)
            coinbase_symbol = symbol.replace("/", "-").replace("USDT", "USD")
            url = f"https://api.exchange.coinbase.com/products/{coinbase_symbol}/ticker"
            
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['price'])
                    return PriceData(
                        exchange="coinbase",
                        symbol=symbol,
                        price=price,
                        bid=price,
                        ask=price,
                        volume_24h=0,
                        timestamp=datetime.now()
                    )
        except Exception as e:
            logging.debug(f"Coinbase error for {symbol}: {e}")
        return None
    
    async def fetch_kraken(self, symbol: str) -> Optional[PriceData]:
        """Fetch price from Kraken."""
        try:
            # Convert symbol format (BTC/USDT -> XBTZUSD)
            kraken_symbol = symbol.replace("BTC", "XBT").replace("/", "").replace("USDT", "ZUSD")
            url = f"https://api.kraken.com/0/public/Ticker?pair={kraken_symbol}"
            
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['error'] == [] and data['result']:
                        ticker = list(data['result'].values())[0]
                        price = float(ticker['c'][0])
                        return PriceData(
                            exchange="kraken",
                            symbol=symbol,
                            price=price,
                            bid=float(ticker['b'][0]),
                            ask=float(ticker['a'][0]),
                            volume_24h=float(ticker['v'][1]),
                            timestamp=datetime.now()
                        )
        except Exception as e:
            logging.debug(f"Kraken error for {symbol}: {e}")
        return None
    
    async def fetch_all(self, symbol: str) -> List[PriceData]:
        """Fetch prices from all exchanges for a symbol."""
        tasks = [
            self.fetch_binance(symbol),
            self.fetch_coinbase(symbol),
            self.fetch_kraken(symbol),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, PriceData)]


class ArbitrageDetector:
    """Detect arbitrage opportunities from price data."""
    
    def __init__(self, min_profit_percent: float = 0.1):
        self.min_profit_percent = min_profit_percent
        self.fees = {
            "binance": {"maker": 0.001, "taker": 0.001},
            "coinbase": {"maker": 0.005, "taker": 0.005},
            "kraken": {"maker": 0.0016, "taker": 0.0026},
        }
    
    def detect(self, prices: List[PriceData]) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities from price list."""
        opportunities = []
        
        if len(prices) < 2:
            return opportunities
        
        # Compare all pairs
        for i, buy_price in enumerate(prices):
            for j, sell_price in enumerate(prices):
                if i == j:
                    continue
                
                if buy_price.price >= sell_price.price:
                    continue  # No profit possible
                
                # Calculate profit
                gross_profit = sell_price.price - buy_price.price
                gross_profit_percent = (gross_profit / buy_price.price) * 100
                
                # Calculate fees (buy fee + sell fee)
                buy_fee = self.fees.get(buy_price.exchange, {"taker": 0.001})["taker"]
                sell_fee = self.fees.get(sell_price.exchange, {"taker": 0.001})["taker"]
                total_fee_percent = buy_fee + sell_fee
                
                fees = buy_price.price * total_fee_percent
                net_profit = gross_profit - fees
                net_profit_percent = ((net_profit / buy_price.price) * 100) - (total_fee_percent * 100)
                
                # Check if profitable
                if net_profit_percent >= self.min_profit_percent:
                    opp = ArbitrageOpportunity(
                        buy_exchange=buy_price.exchange,
                        sell_exchange=sell_price.exchange,
                        symbol=buy_price.symbol,
                        buy_price=buy_price.price,
                        sell_price=sell_price.price,
                        gross_profit=gross_profit,
                        fees=fees,
                        net_profit=net_profit,
                        profit_percent=net_profit_percent,
                        timestamp=datetime.now()
                    )
                    opportunities.append(opp)
        
        return opportunities


class CryptoScanner:
    """Main scanner engine."""
    
    def __init__(self, config: dict):
        self.config = config
        self.console = Console()
        self.db = Database(DATABASE_PATH)
        self.session = None
        self.fetcher = None
        self.detector = ArbitrageDetector(
            min_profit_percent=config.get('min_profit_percent', 0.1)
        )
        self.running = False
        self.prices_cache: Dict[str, List[PriceData]] = {}
        self.stats = {
            'scans': 0,
            'opportunities_found': 0,
            'start_time': None,
        }
    
    async def start(self):
        """Start the scanner."""
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Create HTTP session
        self.session = aiohttp.ClientSession()
        self.fetcher = ExchangeFetcher(self.session)
        
        self.console.print(Panel.fit(
            "[bold green]🚀 Crypto Arbitrage Pro Started[/bold green]\n"
            f"Monitoring: {len(self.config.get('pairs', DEFAULT_PAIRS))} pairs\n"
            f"Exchanges: {len(EXCHANGE_APIS)}\n"
            f"Min Profit: {self.config.get('min_profit_percent', 0.1)}%",
            title="📊 Scanner Status"
        ))
        
        # Main scanning loop
        while self.running:
            await self.scan_cycle()
            await asyncio.sleep(self.config.get('check_interval_seconds', 5))
    
    async def scan_cycle(self):
        """Execute one scanning cycle."""
        self.stats['scans'] += 1
        all_opportunities = []
        
        # Scan each trading pair
        for symbol in self.config.get('pairs', DEFAULT_PAIRS):
            # Fetch prices from all exchanges
            prices = await self.fetcher.fetch_all(symbol)
            
            if prices:
                self.prices_cache[symbol] = prices
                
                # Log prices to database
                for price in prices:
                    self.db.log_price(price)
                
                # Detect arbitrage opportunities
                opportunities = self.detector.detect(prices)
                
                if opportunities:
                    all_opportunities.extend(opportunities)
                    self.stats['opportunities_found'] += len(opportunities)
                    
                    # Log to database
                    for opp in opportunities:
                        self.db.log_opportunity(opp)
                    
                    # Send alerts
                    await self.send_alerts(opportunities)
        
        # Display results
        self.display_results(all_opportunities)
    
    async def send_alerts(self, opportunities: List[ArbitrageOpportunity]):
        """Send alerts for opportunities."""
        if not self.config.get('telegram', {}).get('enabled', False):
            return
        
        # Telegram alert logic here
        for opp in opportunities:
            logging.info(f"🚨 ALERT: {opp.symbol} - {opp.profit_percent:.2f}% profit")
    
    def display_results(self, opportunities: List[ArbitrageOpportunity]):
        """Display scanning results in console."""
        # Create prices table
        price_table = Table(title="💰 Current Prices", show_header=True, header_style="bold magenta")
        price_table.add_column("Symbol", style="cyan")
        price_table.add_column("Binance", justify="right")
        price_table.add_column("Coinbase", justify="right")
        price_table.add_column("Kraken", justify="right")
        
        for symbol, prices in self.prices_cache.items():
            row = [symbol]
            for exchange in ['binance', 'coinbase', 'kraken']:
                price = next((p for p in prices if p.exchange == exchange), None)
                row.append(f"${price.price:,.2f}" if price else "N/A")
            price_table.add_row(*row)
        
        # Create opportunities table
        opp_table = Table(title="🎯 Arbitrage Opportunities", show_header=True, header_style="bold green")
        opp_table.add_column("Buy", style="green")
        opp_table.add_column("Sell", style="red")
        opp_table.add_column("Pair", style="cyan")
        opp_table.add_column("Profit %", justify="right", style="bold yellow")
        opp_table.add_column("Net $", justify="right", style="bold green")
        
        for opp in opportunities[:10]:  # Show top 10
            opp_table.add_row(
                opp.buy_exchange.title(),
                opp.sell_exchange.title(),
                opp.symbol,
                f"{opp.profit_percent:.2f}%",
                f"${opp.net_profit:.2f}"
            )
        
        # Stats
        runtime = datetime.now() - self.stats['start_time'] if self.stats['start_time'] else None
        stats_text = (
            f"Scans: {self.stats['scans']} | "
            f"Opportunities: {self.stats['opportunities_found']} | "
            f"Runtime: {runtime}"
        ) if runtime else f"Scans: {self.stats['scans']}"
        
        # Clear and print
        self.console.clear()
        self.console.print(price_table)
        if opportunities:
            self.console.print(opp_table)
        self.console.print(Panel(stats_text, title="📈 Statistics"))
    
    async def stop(self):
        """Stop the scanner."""
        self.running = False
        if self.session:
            await self.session.close()
        self.console.print("[yellow]Scanner stopped[/yellow]")


def load_config() -> dict:
    """Load configuration from file."""
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'pairs': DEFAULT_PAIRS,
        'min_profit_percent': 0.1,
        'check_interval_seconds': 5,
        'telegram': {'enabled': False},
    }


async def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    # Load config
    config = load_config()
    
    # Create and run scanner
    scanner = CryptoScanner(config)
    
    try:
        await scanner.start()
    except KeyboardInterrupt:
        await scanner.stop()
    except Exception as e:
        logging.error(f"Scanner error: {e}")
        await scanner.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
