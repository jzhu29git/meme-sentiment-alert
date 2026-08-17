# -*- coding: utf-8 -*-
"""
DexScreener & 链上 Meme 异动抓取器
支持 Solana / BSC / Base 等主流链
采用 httpx / curl 双重高可靠性网络客户端
"""
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
import httpx

from src.config import config

logger = logging.getLogger(__name__)


class DexFetcher:
    """DexScreener 链上热点与异动抓取器"""

    BASE_URL = "https://api.dexscreener.com"

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
            logger.warning("初始化 httpx 客户端异常: %s", e)
            self.client = None

    def _get_json(self, url: str) -> Optional[Any]:
        """通过 httpx 或系统 curl 获取 JSON 数据"""
        # 1. 尝试 httpx
        if self.client:
            try:
                resp = self.client.get(url)
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.debug("httpx 请求失败 [%s]: %s，尝试 curl 回退", url, e)

        # 2. 回退到 curl.exe
        try:
            cmd = ["curl.exe", "-s", "--max-time", str(self.timeout)]
            if self.proxy:
                cmd.extend(["--proxy", self.proxy])
            cmd.append(url)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 5)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception as e:
            logger.error("curl 回退请求失败 [%s]: %s", url, e)
        return None

    def fetch_boosted_tokens(self) -> List[Dict[str, Any]]:
        """获取全网/各公链社区助推 (Token Boosts) 热度最高的 Meme 代币"""
        url = f"{self.BASE_URL}/token-boosts/top/v1"
        data = self._get_json(url)
        if isinstance(data, list):
            filtered = [
                item for item in data
                if item.get("chainId", "").lower() in config.CHAINS
            ]
            logger.info("成功抓取 %d 个 Boosted 热门代币 (命中配置链: %d 个)", len(data), len(filtered))
            return filtered
        return []

    def fetch_latest_token_profiles(self) -> List[Dict[str, Any]]:
        """获取最新提交社交档案的 Meme 代币"""
        url = f"{self.BASE_URL}/token-profiles/latest/v1"
        data = self._get_json(url)
        if isinstance(data, list):
            filtered = [
                item for item in data
                if item.get("chainId", "").lower() in config.CHAINS
            ]
            logger.info("成功抓取 %d 个新档案代币 (命中配置链: %d 个)", len(data), len(filtered))
            return filtered
        return []

    def fetch_token_pairs(self, chain_id: str, token_address: str) -> List[Dict[str, Any]]:
        """获取指定代币在 Dex 上的所有交易对详情"""
        url = f"{self.BASE_URL}/latest/dex/tokens/{token_address}"
        data = self._get_json(url)
        if isinstance(data, dict):
            pairs = data.get("pairs") or []
            chain_pairs = [p for p in pairs if p.get("chainId", "").lower() == chain_id.lower()]
            chain_pairs.sort(key=lambda x: (x.get("liquidity") or {}).get("usd", 0) or 0, reverse=True)
            return chain_pairs
        return []

    def collect_hot_candidates(self) -> List[Dict[str, Any]]:
        """聚合全网最新异动 Meme 候选集并补充量价指标"""
        candidates: Dict[str, Dict[str, Any]] = {}

        # 1. 抓取社区 Boost 榜单
        boosts = self.fetch_boosted_tokens()
        for item in boosts[:15]:
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
        for item in profiles[:15]:
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
            main_pair = pairs[0]

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
