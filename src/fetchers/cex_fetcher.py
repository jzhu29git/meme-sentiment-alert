# -*- coding: utf-8 -*-
"""
CEX (Binance & OKX) 交易所热点与 Meme 异动抓取器
监控币安与欧易现货市场的 24h 飙升榜、巨量成交额与 Meme 币异动
采用公开开放端点，100% 免 Key、免登录
"""
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
import httpx

from src.config import config

logger = logging.getLogger(__name__)

# 知名及热门 Meme 币代币标识集 (持续维护与动态扩充)
KNOWN_MEME_SYMBOLS = {
    "DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "BOME", "NEIRO",
    "PNUT", "ACT", "GOAT", "MOODENG", "MEME", "TURBO", "ORDI", "SATS",
    "1000SATS", "1000CAT", "1000CHEEMS", "1000RATS", "PEOPLE", "BABYDOGE",
    "MEW", "MYRO", "POPCAT", "SLERF", "PONKE", "BRETT", "DEGEN", "PENGU",
    "AI16Z", "VIRTUAL", "GIGA", "SPX", "TOSHI", "MOG", "WOJAK", "LADYS"
}


class CEXFetcher:
    """中心化交易所 (Binance & OKX) 热点抓取器"""

    BINANCE_VISION_URL = "https://data-api.binance.vision/api/v3/ticker/24hr"
    OKX_TICKERS_URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        proxy = config.HTTP_PROXY or config.HTTPS_PROXY or (config.get_overseas_proxies() or {}).get("http")
        self.proxy = proxy
        try:
            self.client = httpx.Client(
                proxy=proxy if proxy else None,
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        except Exception as e:
            logger.warning("初始化 CEX httpx 客户端异常: %s", e)
            self.client = None

    def _get_json(self, url: str) -> Optional[Any]:
        """通过 httpx 或 curl 获取 JSON"""
        if self.client:
            try:
                resp = self.client.get(url)
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.debug("CEX httpx 失败 [%s]: %s，尝试 curl 回退", url, e)

        try:
            cmd = ["curl.exe", "-s", "--max-time", str(self.timeout)]
            if self.proxy:
                cmd.extend(["--proxy", self.proxy])
            cmd.append(url)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 5)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception as e:
            logger.error("CEX curl 失败 [%s]: %s", url, e)
        return None

    def fetch_binance_hot(self, min_gain_pct: float = 8.0, min_quote_vol: float = 3000000) -> List[Dict[str, Any]]:
        """
        获取币安 USDT 交易对中 24h 涨幅突增或高热度 Meme
        """
        data = self._get_json(self.BINANCE_VISION_URL)
        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            symbol = item.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue

            base_coin = symbol[:-4]
            price_change_pct = float(item.get("priceChangePercent") or 0)
            quote_vol = float(item.get("quoteVolume") or 0)  # USDT 成交额
            last_price = float(item.get("lastPrice") or 0)
            high_price = float(item.get("highPrice") or 0)
            low_price = float(item.get("lowPrice") or 0)

            is_meme = base_coin.upper() in KNOWN_MEME_SYMBOLS

            # 触发判定：A. 已知 Meme 币且有活跃放量; B. 全市场 24h 飙升大涨 (涨幅 >= min_gain_pct 且成交额 >= 300万美元)
            if (is_meme and price_change_pct >= 5.0 and quote_vol >= 1000000) or (price_change_pct >= min_gain_pct and quote_vol >= min_quote_vol):
                reasons = []
                if is_meme:
                    reasons.append(f"🐶 币安热门 Meme 币聚焦 (${base_coin})")
                reasons.append(f"⚡ 24h 涨幅: +{price_change_pct:.2f}%")
                reasons.append(f"💰 24h 成交额: ${quote_vol:,.0f}")

                # 评分 (0-100)
                score = min(99, int(price_change_pct * 1.5 + (quote_vol / 50000000) * 20 + (15 if is_meme else 0)))

                results.append({
                    "exchange": "BINANCE",
                    "symbol": base_coin,
                    "pair": symbol,
                    "priceUsd": last_price,
                    "priceChange24h": price_change_pct,
                    "quoteVolume24h": quote_vol,
                    "highPrice24h": high_price,
                    "lowPrice24h": low_price,
                    "isMeme": is_meme,
                    "score": max(50, score),
                    "reasons": reasons,
                    "url": f"https://www.binance.com/zh-CN/trade/{base_coin}_USDT",
                })

        results.sort(key=lambda x: x["priceChange24h"], reverse=True)
        logger.info("成功抓取币安 CEX 异动标的 %d 个", len(results))
        return results

    def fetch_okx_hot(self, min_gain_pct: float = 8.0, min_quote_vol: float = 2000000) -> List[Dict[str, Any]]:
        """
        获取欧易 OKX 现货 USDT 交易对中 24h 涨幅榜与 Meme 异动
        """
        raw = self._get_json(self.OKX_TICKERS_URL)
        if not isinstance(raw, dict):
            return []

        tickers = raw.get("data") or []
        results = []

        for item in tickers:
            inst_id = item.get("instId", "")
            if not inst_id.endswith("-USDT"):
                continue

            base_coin = inst_id.split("-")[0]
            last_price = float(item.get("last") or 0)
            open_24h = float(item.get("open24h") or 0)
            vol_ccy_24h = float(item.get("volCcy24h") or 0)  # USDT 成交额

            if open_24h <= 0:
                continue

            price_change_pct = ((last_price - open_24h) / open_24h) * 100
            is_meme = base_coin.upper() in KNOWN_MEME_SYMBOLS

            if (is_meme and price_change_pct >= 5.0 and vol_ccy_24h >= 800000) or (price_change_pct >= min_gain_pct and vol_ccy_24h >= min_quote_vol):
                reasons = []
                if is_meme:
                    reasons.append(f"🐶 OKX 热门 Meme 币聚焦 (${base_coin})")
                reasons.append(f"⚡ 24h 涨幅: +{price_change_pct:.2f}%")
                reasons.append(f"💰 24h 成交额: ${vol_ccy_24h:,.0f}")

                score = min(99, int(price_change_pct * 1.5 + (vol_ccy_24h / 40000000) * 20 + (15 if is_meme else 0)))

                results.append({
                    "exchange": "OKX",
                    "symbol": base_coin,
                    "pair": inst_id,
                    "priceUsd": last_price,
                    "priceChange24h": price_change_pct,
                    "quoteVolume24h": vol_ccy_24h,
                    "isMeme": is_meme,
                    "score": max(50, score),
                    "reasons": reasons,
                    "url": f"https://www.okx.com/zh-hans/trade-spot/{base_coin.lower()}-usdt",
                })

        results.sort(key=lambda x: x["priceChange24h"], reverse=True)
        logger.info("成功抓取欧易 OKX CEX 异动标的 %d 个", len(results))
        return results

    def collect_cex_candidates(self) -> List[Dict[str, Any]]:
        """汇总 Binance 与 OKX 的 Top 异动集合"""
        binance_items = self.fetch_binance_hot()[:6]
        okx_items = self.fetch_okx_hot()[:6]
        return binance_items + okx_items
