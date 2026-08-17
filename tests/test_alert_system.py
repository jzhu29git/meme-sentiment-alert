# -*- coding: utf-8 -*-
"""
单元测试与功能验证
"""
import pytest
from src.engine.sentiment_analyzer import SentimentAnalyzer
from src.engine.dedup_manager import DedupManager
from src.notifiers.feishu_notifier import FeishuNotifier


def test_sentiment_analyzer_token_trigger():
    analyzer = SentimentAnalyzer()
    
    # 构造触发异动的 Meme 代币数据
    mock_token = {
        "chainId": "bsc",
        "tokenAddress": "0x5fd0d8fecf408f61080cea470249026d3e02fb3d",
        "pairAddress": "0x311188be",
        "baseToken": {"name": "Niulai", "symbol": "NIULAI"},
        "priceUsd": 0.005,
        "fdv": 5000000,
        "liquidity": {"usd": 50000},
        "priceChange": {"m5": 25.0, "h1": 80.0, "h24": 200.0},
        "volume": {"m5": 30000, "h1": 150000, "h24": 500000},
        "txns": {"m5": {"buys": 45, "sells": 5}},
        "source": "boosted",
        "totalAmount": 100,
    }
    
    alert = analyzer.analyze_token(mock_token)
    assert alert is not None
    assert alert["type"] == "TOKEN"
    assert alert["symbol"] == "NIULAI"
    assert alert["score"] >= 80
    assert len(alert["reasons"]) >= 1


def test_sentiment_analyzer_low_liquidity_filter():
    analyzer = SentimentAnalyzer()
    
    # 流动性过小（垃圾币/假币），应被过滤
    mock_token_scam = {
        "chainId": "solana",
        "tokenAddress": "fake123",
        "baseToken": {"name": "ScamCoin", "symbol": "SCAM"},
        "liquidity": {"usd": 500},  # 低于 MIN_LIQUIDITY_USD (5000)
        "priceChange": {"m5": 50.0},
        "volume": {"m5": 20000},
        "txns": {"m5": {"buys": 30, "sells": 0}},
    }
    
    alert = analyzer.analyze_token(mock_token_scam)
    assert alert is None


def test_dedup_manager(tmp_path):
    state_file = tmp_path / "test_dedup.json"
    dedup = DedupManager(state_file=state_file)
    
    key = "TOKEN:BSC:0x123"
    assert dedup.is_fresh_alert(key) is True
    
    dedup.mark_alerted(key)
    assert dedup.is_fresh_alert(key) is False


def test_feishu_card_builder():
    notifier = FeishuNotifier()
    mock_alert = {
        "type": "TOKEN",
        "name": "Niulai",
        "symbol": "NIULAI",
        "chain": "BSC",
        "tokenAddress": "0x5fd0d8fe",
        "pairAddress": "0x311188be",
        "priceUsd": 0.005,
        "fdv": 5000000,
        "liquidityUsd": 50000,
        "volumeM5": 30000,
        "volumeH1": 150000,
        "priceChangeM5": 25.0,
        "priceChangeH1": 80.0,
        "buysM5": 45,
        "sellsM5": 5,
        "score": 88,
        "reasons": ["⚡ 5m成交量突破 $30,000"],
        "riskFlags": [],
        "url": "https://dexscreener.com/bsc/0x5fd0d8fe",
    }
    
    card = notifier.build_token_card(mock_alert)
    assert card["header"]["title"]["content"].startswith("🔥【Meme异动预警】")
    assert len(card["elements"]) == 2


def test_feishu_digest_card_with_cex():
    notifier = FeishuNotifier()
    mock_tokens = [{
        "symbol": "PEPE",
        "chain": "SOLANA",
        "priceChangeM5": 35.0,
        "priceChangeH1": 100.0,
        "volumeM5": 50000,
        "liquidityUsd": 80000,
        "score": 90,
        "tokenAddress": "token123",
    }]
    mock_nfts = [{
        "name": "牛来",
        "chain": "BSC",
        "floorPrice": 0.04,
        "volume24h": 2.5,
        "elementUrl": "https://element.market/collections/niulais",
        "reasons": ["热度飙升"],
    }]
    mock_cex = [{
        "symbol": "DOGE",
        "exchange": "BINANCE",
        "priceChange24h": 18.5,
        "quoteVolume24h": 85000000,
        "url": "https://www.binance.com/zh-CN/trade/DOGE_USDT",
        "isMeme": True,
    }]

    digest = notifier.build_digest_card(mock_tokens, mock_nfts, mock_cex)
    assert digest["header"]["title"]["content"].startswith("⚡【全网 Meme / CEX / NFT 舆情异动简报】")
    assert len(digest["elements"]) == 2
