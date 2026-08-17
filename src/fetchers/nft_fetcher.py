# -*- coding: utf-8 -*-
"""
NFT 市场热点与异动抓取器
主要支持 Element Market、OpenSea 及热门 Meme NFT 集合
"""
import logging
from typing import Any, Dict, List, Optional
import requests

from src.config import config

logger = logging.getLogger(__name__)


class NFTFetcher:
    """NFT 市场热点抓取器"""

    ELEMENT_API_BASE = "https://api.element.market/api/v1"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        proxies = config.get_overseas_proxies()
        if proxies:
            self.session.proxies.update(proxies)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })

    def fetch_element_collection_info(self, slug: str) -> Optional[Dict[str, Any]]:
        """查询指定 Element 集合（如 niulais）的实时地板价与成交数据"""
        url = f"{self.ELEMENT_API_BASE}/collections/{slug}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0 or "data" in data:
                    return data.get("data")
        except Exception as e:
            logger.warning("查询 Element 集合 [%s] 异常: %s", slug, e)
        return None

    def fetch_trending_nft_collections(self, chain: str = "bsc") -> List[Dict[str, Any]]:
        """获取指定链的 NFT 热门/飙升榜单"""
        url = f"{self.ELEMENT_API_BASE}/market/ranking"
        params = {
            "chain": chain,
            "sort_by": "volume_24h",
            "time_range": "24h",
            "limit": 20,
        }
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                res = resp.json()
                items = res.get("data", {}).get("list", []) or []
                logger.info("成功抓取 Element [%s] 链热门 NFT 集合 %d 个", chain, len(items))
                return items
        except Exception as e:
            logger.warning("抓取 Element 热门 NFT 榜单失败 [%s]: %s", chain, e)
        return []

    def scan_monitored_meme_nfts(self) -> List[Dict[str, Any]]:
        """
        专门扫描已知重点热点 Meme NFT 列表（如《牛来》等现象级项目）
        以及从榜单中挖掘异动集合
        """
        monitored_slugs = ["niulais"]
        results = []

        for slug in monitored_slugs:
            info = self.fetch_element_collection_info(slug)
            if info:
                results.append({
                    "name": info.get("name", slug),
                    "slug": slug,
                    "chain": info.get("chain", "bsc"),
                    "contractAddress": info.get("contract_address", ""),
                    "floorPrice": info.get("floor_price", 0),
                    "volume24h": info.get("volume_24h", 0),
                    "volumeTotal": info.get("volume_total", 0),
                    "owners": info.get("num_owners", 0),
                    "totalSupply": info.get("total_supply", 0),
                    "elementUrl": f"https://element.market/collections/{slug}",
                    "twitter": info.get("twitter_url", ""),
                    "description": info.get("description", ""),
                })

        # 结合 BSC 和 Ethereum 趋势榜
        for ch in ["bsc", "ethereum"]:
            trending = self.fetch_trending_nft_collections(ch)
            for item in trending[:5]:
                slug = item.get("slug") or item.get("collection_slug", "")
                if not slug or any(r["slug"] == slug for r in results):
                    continue
                results.append({
                    "name": item.get("name", slug),
                    "slug": slug,
                    "chain": ch,
                    "contractAddress": item.get("contract_address", ""),
                    "floorPrice": float(item.get("floor_price") or 0),
                    "volume24h": float(item.get("volume_24h") or 0),
                    "volumeChange24h": float(item.get("volume_change_24h") or 0),
                    "owners": int(item.get("num_owners") or 0),
                    "elementUrl": f"https://element.market/collections/{slug}",
                    "description": item.get("description", ""),
                })

        return results
