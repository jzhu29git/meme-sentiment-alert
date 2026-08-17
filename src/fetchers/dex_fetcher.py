# -*- coding: utf-8 -*-
"""
DexScreener & 链上 Meme 异动抓取器
支持 Solana / BSC / Base 等主流链
"""
import logging
from typing import Any, Dict, List, Optional
import requests

from src.config import config

logger = logging.getLogger(__name__)


class DexFetcher:
    """DexScreener 链上热点与异动抓取器"""

    BASE_URL = "https://api.dexscreener.com"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })

    def fetch_boosted_tokens(self) -> List[Dict[str, Any]]:
        """获取全网/各公链社区助推 (Token Boosts) 热度最高的 Meme 代币"""
        url = f"{self.BASE_URL}/token-boosts/top/v1"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    # 过滤只保留目标公链
                    filtered = [
                        item for item in data
                        if item.get("chainId", "").lower() in config.CHAINS
                    ]
                    logger.info("成功抓取 %d 个 Boosted 热门代币 (命中配置链: %d 个)", len(data), len(filtered))
                    return filtered
            logger.warning("抓取 Boosted 代币返回状态码: %s", resp.status_code)
        except Exception as e:
            logger.error("抓取 Boosted 代币异常: %s", e)
        return []

    def fetch_latest_token_profiles(self) -> List[Dict[str, Any]]:
        """获取最新提交社交档案的 Meme 代币 (通常意味着团队开始启动宣发/投放)"""
        url = f"{self.BASE_URL}/token-profiles/latest/v1"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    filtered = [
                        item for item in data
                        if item.get("chainId", "").lower() in config.CHAINS
                    ]
                    logger.info("成功抓取 %d 个新档案代币 (命中配置链: %d 个)", len(data), len(filtered))
                    return filtered
            logger.warning("抓取 Token Profiles 返回状态码: %s", resp.status_code)
        except Exception as e:
            logger.error("抓取 Token Profiles 异常: %s", e)
        return []

    def fetch_token_pairs(self, chain_id: str, token_address: str) -> List[Dict[str, Any]]:
        """获取指定代币在 Dex 上的所有交易对详情（含5m/1h成交量、买卖单数、流动性等）"""
        url = f"{self.BASE_URL}/latest/dex/tokens/{token_address}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs") or []
                # 过滤对应链并按流动性降序排序
                chain_pairs = [p for p in pairs if p.get("chainId", "").lower() == chain_id.lower()]
                chain_pairs.sort(key=lambda x: (x.get("liquidity") or {}).get("usd", 0) or 0, reverse=True)
                return chain_pairs
        except Exception as e:
            logger.error("查询代币交易对失败 [%s:%s]: %s", chain_id, token_address, e)
        return []

    def search_trending_pairs(self, query: str) -> List[Dict[str, Any]]:
        """根据关键词搜索交易对"""
        url = f"{self.BASE_URL}/latest/dex/search?q={query}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs") or []
                return [p for p in pairs if p.get("chainId", "").lower() in config.CHAINS]
        except Exception as e:
            logger.error("搜索交易对失败 [%s]: %s", query, e)
        return []

    def collect_hot_candidates(self) -> List[Dict[str, Any]]:
        """聚合全网最新异动 Meme 候选集并补充量价指标"""
        candidates: Dict[str, Dict[str, Any]] = {}

        # 1. 抓取社区 Boost 榜单
        boosts = self.fetch_boosted_tokens()
        for item in boosts[:15]:  # 取前15个
            chain = item.get("chainId", "").lower()
            addr = item.get("tokenAddress", "")
            key = f"{chain}:{addr}"
            if key not in candidates:
                candidates[key] = {
                    "source": "boosted",
                    "chainId": chain,
                    "tokenAddress": addr,
                    "url": item.get("url", ""),
                    "icon": item.get("icon", ""),
                    "description": item.get("description", ""),
                    "totalAmount": item.get("totalAmount", 0),
                }

        # 2. 抓取最新宣发 Token Profiles
        profiles = self.fetch_latest_token_profiles()
        for item in profiles[:15]:  # 取前15个
            chain = item.get("chainId", "").lower()
            addr = item.get("tokenAddress", "")
            key = f"{chain}:{addr}"
            if key not in candidates:
                candidates[key] = {
                    "source": "profile",
                    "chainId": chain,
                    "tokenAddress": addr,
                    "url": item.get("url", ""),
                    "icon": item.get("icon", ""),
                    "description": item.get("description", ""),
                }

        # 3. 逐个查询详细交易对行情数据
        enriched_list: List[Dict[str, Any]] = []
        for key, item in candidates.items():
            pairs = self.fetch_token_pairs(item["chainId"], item["tokenAddress"])
            if not pairs:
                continue
            main_pair = pairs[0]  # 取流动性最大的主池

            merged = {
                **item,
                "pairAddress": main_pair.get("pairAddress", ""),
                "baseToken": main_pair.get("baseToken", {}),
                "quoteToken": main_pair.get("quoteToken", {}),
                "priceUsd": float(main_pair.get("priceUsd") or 0),
                "priceNative": main_pair.get("priceNative", ""),
                "priceChange": main_pair.get("priceChange", {}),
                "volume": main_pair.get("volume", {}),
                "txns": main_pair.get("txns", {}),
                "liquidity": main_pair.get("liquidity", {}),
                "fdv": main_pair.get("fdv", 0),
                "marketCap": main_pair.get("marketCap", 0),
                "pairCreatedAt": main_pair.get("pairCreatedAt", 0),
                "dexId": main_pair.get("dexId", ""),
                "info": main_pair.get("info", {}),
            }
            enriched_list.append(merged)

        logger.info("聚合完成，共获取 %d 个链上 Meme 深度行情标的", len(enriched_list))
        return enriched_list
