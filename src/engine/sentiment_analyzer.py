# -*- coding: utf-8 -*-
"""
舆情与异动评分引擎
综合评估链上代币与 NFT 的爆发潜质、资金抢筹程度与风险等级
"""
import logging
from typing import Any, Dict, List, Optional
from src.config import config

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """舆情异动分析器"""

    def analyze_token(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        分析单个 Meme 代币是否达到告警阈值并计算热度评分
        """
        # 1. 基础信息提取
        name = token.get("baseToken", {}).get("name", "Unknown")
        symbol = token.get("baseToken", {}).get("symbol", "UNKNOWN")
        chain = token.get("chainId", "unknown").upper()
        token_addr = token.get("tokenAddress", "")
        pair_addr = token.get("pairAddress", "")

        liquidity_usd = float((token.get("liquidity") or {}).get("usd", 0) or 0)
        fdv = float(token.get("fdv") or token.get("marketCap") or 0)
        price_usd = float(token.get("priceUsd") or 0)

        price_changes = token.get("priceChange") or {}
        p_m5 = float(price_changes.get("m5") or 0)
        p_h1 = float(price_changes.get("h1") or 0)
        p_h24 = float(price_changes.get("h24") or 0)

        volumes = token.get("volume") or {}
        v_m5 = float(volumes.get("m5") or 0)
        v_h1 = float(volumes.get("h1") or 0)
        v_h24 = float(volumes.get("h24") or 0)

        txns_m5 = (token.get("txns") or {}).get("m5") or {}
        buys_m5 = int(txns_m5.get("buys") or 0)
        sells_m5 = int(txns_m5.get("sells") or 0)
        total_txns_m5 = buys_m5 + sells_m5

        # 2. 基础硬性过滤 (防死币、极低流动性假币)
        if liquidity_usd < config.MIN_LIQUIDITY_USD:
            # 流动性过小不触发预警
            return None

        # 3. 异动触发条件判定 (Trigger Triggers)
        reasons = []
        is_triggered = False

        # 条件 A: 5分钟成交量与价格共振拉升
        if v_m5 >= config.MIN_VOLUME_5M_USD and p_m5 >= config.MIN_PRICE_CHANGE_5M:
            is_triggered = True
            reasons.append(f"⚡ 5m成交量突破 ${v_m5:,.0f} 且价格短线拉升 +{p_m5:.1f}%")

        # 条件 B: 买单异常密集涌入 (抢筹)
        if buys_m5 >= config.MIN_BUYS_5M:
            buy_ratio = (buys_m5 / max(sells_m5, 1))
            if buy_ratio >= config.MIN_BUY_SELL_RATIO:
                is_triggered = True
                reasons.append(f"🔥 5m买卖单比高达 {buy_ratio:.1f}:1 ({buys_m5}笔买入/{sells_m5}笔卖出)")

        # 条件 C: 社区顶级 Boost 且流动性健康
        if token.get("source") == "boosted" and token.get("totalAmount", 0) > 50:
            is_triggered = True
            reasons.append(f"🚀 DexScreener社区高额助推 (Boost热度值: {token.get('totalAmount')})")

        # 条件 D: 1小时爆发暴涨 (24h热点龙头)
        if p_h1 >= 50.0 and v_h1 >= 50000:
            is_triggered = True
            reasons.append(f"📈 1小时爆发涨幅 +{p_h1:.1f}% (1h成交额: ${v_h1:,.0f})")

        if not is_triggered:
            return None

        # 4. 计算综合舆情热度评分 (0-100)
        score = 0
        # 成交量得分 (0-30)
        score += min(30, int((v_m5 / 20000) * 15 + (v_h1 / 100000) * 15))
        # 涨幅与动量得分 (0-30)
        score += min(30, int(max(0, p_m5) * 1.0 + max(0, p_h1) * 0.3))
        # 资金争抢比得分 (0-25)
        if total_txns_m5 > 0:
            buy_pct = buys_m5 / total_txns_m5
            score += int(buy_pct * 25)
        # 流动性健康度 (0-15)
        score += min(15, int((liquidity_usd / 50000) * 15))

        final_score = min(99, max(10, score))

        # 5. 安全与风险标签
        risk_flags = []
        if liquidity_usd < 15000:
            risk_flags.append("⚠️ 池子流动性较浅")
        if fdv > 0 and (liquidity_usd / fdv) < 0.03:
            risk_flags.append("⚠️ FDV相对池子过大")
        if sells_m5 == 0 and buys_m5 > 10:
            risk_flags.append("🚨 疑似无卖单 (需警惕貔貅/Honeypot)")

        return {
            "type": "TOKEN",
            "name": name,
            "symbol": symbol,
            "chain": chain,
            "tokenAddress": token_addr,
            "pairAddress": pair_addr,
            "priceUsd": price_usd,
            "fdv": fdv,
            "liquidityUsd": liquidity_usd,
            "volumeM5": v_m5,
            "volumeH1": v_h1,
            "priceChangeM5": p_m5,
            "priceChangeH1": p_h1,
            "priceChangeH24": p_h24,
            "buysM5": buys_m5,
            "sellsM5": sells_m5,
            "score": final_score,
            "reasons": reasons,
            "riskFlags": risk_flags,
            "url": token.get("url") or f"https://dexscreener.com/{chain.lower()}/{pair_addr or token_addr}",
        }

    def analyze_nft(self, nft: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        分析 NFT 集合异动
        """
        name = nft.get("name", "")
        slug = nft.get("slug", "")
        chain = nft.get("chain", "").upper()
        volume_24h = float(nft.get("volume24h") or 0)
        floor_price = float(nft.get("floorPrice") or 0)
        owners = int(nft.get("owners") or 0)

        reasons = []
        is_triggered = False

        if slug == "niulais":
            # 重点跟踪标的
            is_triggered = True
            reasons.append(f"🎯 现象级热点《牛来》Meme NFT 重点追踪 (地板价: {floor_price} {chain})")
        elif volume_24h >= config.NFT_MIN_24H_VOLUME_BNB:
            is_triggered = True
            reasons.append(f"🔥 Element 24h成交量活跃: {volume_24h:.2f} {chain} (持有人: {owners})")

        if not is_triggered:
            return None

        return {
            "type": "NFT",
            "name": name,
            "slug": slug,
            "chain": chain,
            "contractAddress": nft.get("contractAddress", ""),
            "floorPrice": floor_price,
            "volume24h": volume_24h,
            "owners": owners,
            "elementUrl": nft.get("elementUrl", f"https://element.market/collections/{slug}"),
            "reasons": reasons,
            "score": 88 if slug == "niulais" else 75,
            "description": nft.get("description", ""),
        }
