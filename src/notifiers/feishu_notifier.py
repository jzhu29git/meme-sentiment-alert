# -*- coding: utf-8 -*-
"""
飞书富文本互动卡片预警投递器
支持 Feishu App-Bot (优先) 与 Webhook 投递
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional
import requests

from src.config import config

logger = logging.getLogger(__name__)


class FeishuNotifier:
    """飞书预警通知器"""

    def __init__(self):
        self.session = requests.Session()
        self._tenant_token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取飞书应用机器人的 tenant_access_token"""
        now = time.time()
        if self._tenant_token and now < self._token_expires_at - 60:
            return self._tenant_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": config.FEISHU_APP_ID,
            "app_secret": config.FEISHU_APP_SECRET,
        }
        try:
            resp = self.session.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    self._tenant_token = data.get("tenant_access_token")
                    expire_in = data.get("expire", 7200)
                    self._token_expires_at = now + expire_in
                    return self._tenant_token
                else:
                    logger.error("获取飞书 Tenant Token 失败: %s", data)
            else:
                logger.error("获取飞书 Tenant Token 状态码异常: %s", resp.status_code)
        except Exception as e:
            logger.error("请求飞书 Token 发生网络异常: %s", e)
        return None

    def build_token_card(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """构造代币异动飞书交互卡片"""
        symbol = alert_data.get("symbol", "TOKEN")
        name = alert_data.get("name", "Unknown")
        chain = alert_data.get("chain", "SOL")
        score = alert_data.get("score", 80)
        p_m5 = alert_data.get("priceChangeM5", 0)
        p_h1 = alert_data.get("priceChangeH1", 0)
        v_m5 = alert_data.get("volumeM5", 0)
        buys = alert_data.get("buysM5", 0)
        sells = alert_data.get("sellsM5", 0)
        liq = alert_data.get("liquidityUsd", 0)
        fdv = alert_data.get("fdv", 0)
        price_usd = alert_data.get("priceUsd", 0)
        addr = alert_data.get("tokenAddress", "")
        reasons = alert_data.get("reasons", [])
        risks = alert_data.get("riskFlags", [])
        dex_url = alert_data.get("url", f"https://dexscreener.com/{chain.lower()}/{addr}")

        # 卡片主题颜色：涨幅极大用 red (红涨)，中等用 carmine/orange
        template = "carmine" if p_m5 >= 30 else "orange"

        reasons_text = "\n".join([f"• {r}" for r in reasons]) or "• 链上买单与交易量异动"
        risks_text = " | ".join(risks) if risks else "✅ 基础流动性与交易指标正常"

        gmgn_url = f"https://gmgn.ai/{chain.lower()}/token/{addr}"

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔥【Meme异动预警】${symbol} ({chain}) 舆情热度 {score}分"
                },
                "template": template
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": (
                        f"**代币全称**: `{name}`  |  **公链**: **{chain}**\n"
                        f"**现价**: `${price_usd:,.6f}`  |  **FDV/市值**: `${fdv:,.0f}`\n"
                        f"**5m 涨幅**: **{'+' if p_m5>0 else ''}{p_m5:.2f}%**  |  **1h 涨幅**: **{'+' if p_h1>0 else ''}{p_h1:.2f}%**\n"
                        f"**5m 成交额**: `${v_m5:,.0f}`  |  **5m 买卖笔数**: `{buys}买 / {sells}卖`\n"
                        f"**流动性池 (Liq)**: `${liq:,.0f}`\n"
                        f"**合约地址**: `{addr}`\n\n"
                        f"**【异动触发原因】**\n{reasons_text}\n\n"
                        f"**【安全与风险提示】**\n`{risks_text}`"
                    )
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📊 打开 DexScreener 查看 K 线"},
                            "type": "primary",
                            "url": dex_url
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🕵️‍♂️ GMGN 聪明钱持仓分析"},
                            "type": "default",
                            "url": gmgn_url
                        }
                    ]
                }
            ]
        }
        return card

    def build_nft_card(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """构造 NFT 异动飞书交互卡片"""
        name = alert_data.get("name", "NFT Collection")
        slug = alert_data.get("slug", "")
        chain = alert_data.get("chain", "BSC")
        floor_price = alert_data.get("floorPrice", 0)
        vol_24h = alert_data.get("volume24h", 0)
        owners = alert_data.get("owners", 0)
        addr = alert_data.get("contractAddress", "")
        reasons = alert_data.get("reasons", [])
        element_url = alert_data.get("elementUrl", f"https://element.market/collections/{slug}")

        reasons_text = "\n".join([f"• {r}" for r in reasons])

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🎯【NFT 热点异动】{name} ({chain})"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": (
                        f"**集合名称**: `{name}`  |  **公链**: **{chain}**\n"
                        f"**地板价**: `{floor_price} {chain}`  |  **24h 成交额**: `{vol_24h:.2f} {chain}`\n"
                        f"**持有人数**: `{owners}`\n"
                        f"**合约地址**: `{addr or '暂未公开/多合约'}`\n\n"
                        f"**【热度分析与异动】**\n{reasons_text}\n\n"
                        f"💡 *提示：遇热点项目早期 Mint，请通过 BscScan / 合约官方入口或独立小号钱包操作，切勿主钱包盲目授权。*"
                    )
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🛒 前往 Element Market 查看"},
                            "type": "primary",
                            "url": element_url
                        }
                    ]
                }
            ]
        }
        return card

    def build_digest_card(self, token_alerts: List[Dict[str, Any]], nft_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构造聚合型 Meme & NFT 舆情异动精选简报 (Digest Card)
        """
        now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        total_count = len(token_alerts) + len(nft_alerts)

        md_sections = []
        md_sections.append(f"⏱ **扫描时间**: `{now_str}`  |  **全网异动捕获**: **{total_count}** 个")

        if token_alerts:
            md_sections.append("\n### 🚀 **链上热门 Meme 币异动**")
            for idx, item in enumerate(token_alerts[:6], start=1):
                sym = item.get("symbol", "TOKEN")
                name = item.get("name", "")
                chain = item.get("chain", "")
                p_m5 = item.get("priceChangeM5", 0)
                p_h1 = item.get("priceChangeH1", 0)
                v_m5 = item.get("volumeM5", 0)
                liq = item.get("liquidityUsd", 0)
                score = item.get("score", 0)
                addr = item.get("tokenAddress", "")
                url = item.get("url", "")
                gmgn_url = f"https://gmgn.ai/{chain.lower()}/token/{addr}"

                p_m5_str = f"+{p_m5:.1f}%" if p_m5 > 0 else f"{p_m5:.1f}%"
                p_h1_str = f"+{p_h1:.1f}%" if p_h1 > 0 else f"{p_h1:.1f}%"

                md_sections.append(
                    f"**{idx}. [${sym}]({url})** (`{chain}`) - **热度 {score}分**\n"
                    f"• 5m: **{p_m5_str}** (${v_m5:,.0f}) | 1h: **{p_h1_str}** | 池深: `${liq:,.0f}`\n"
                    f"• 合约: `{addr}` | [GMGN持仓]({gmgn_url})"
                )

        if nft_alerts:
            md_sections.append("\n### 🎯 **热点 NFT 市场异动**")
            for idx, item in enumerate(nft_alerts[:4], start=1):
                name = item.get("name", "NFT")
                chain = item.get("chain", "")
                floor = item.get("floorPrice", 0)
                vol24 = item.get("volume24h", 0)
                url = item.get("elementUrl", "")
                reasons = " | ".join(item.get("reasons", []))

                md_sections.append(
                    f"**{idx}. [{name}]({url})** (`{chain}`)\n"
                    f"• 地板价: `{floor} {chain}` | 24h额: `{vol24:.2f} {chain}`\n"
                    f"• 说明: {reasons}"
                )

        content = "\n".join(md_sections)

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"⚡【Meme & NFT 链上舆情精选简报】命中 {total_count} 个异动"
                },
                "template": "carmine" if any(t.get("priceChangeM5", 0) >= 30 for t in token_alerts) else "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "💡 提示：点击代币名称直达 DexScreener K线，点击 [GMGN持仓] 检查聪明钱持仓与貔貅风险。"
                        }
                    ]
                }
            ]
        }
        return card

    def send_card(self, card_dict: Dict[str, Any]) -> bool:

        """投递飞书卡片"""
        # 1. 优先使用 App-Bot 模式投递到指定群聊
        if config.is_feishu_app_bot_ready():
            token = self._get_tenant_access_token()
            if token:
                url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                }
                payload = {
                    "receive_id": config.FEISHU_CHAT_ID,
                    "msg_type": "interactive",
                    "content": json.dumps(card_dict, ensure_ascii=False),
                }
                try:
                    resp = self.session.post(url, headers=headers, json=payload, timeout=10)
                    res = resp.json()
                    if res.get("code") == 0:
                        logger.info("飞书 App-Bot 卡片发送成功 [chat_id: %s]", config.FEISHU_CHAT_ID)
                        return True
                    else:
                        logger.error("飞书 App-Bot 发送失败: %s", res)
                except Exception as e:
                    logger.error("飞书 App-Bot 请求异常: %s", e)

        # 2. 回退到 Webhook 模式
        if config.is_feishu_webhook_ready():
            try:
                payload = {
                    "msg_type": "interactive",
                    "card": card_dict,
                }
                resp = self.session.post(config.FEISHU_WEBHOOK_URL, json=payload, timeout=10)
                res = resp.json()
                if res.get("StatusCode") == 0 or res.get("code") == 0:
                    logger.info("飞书 Webhook 卡片发送成功")
                    return True
                else:
                    logger.error("飞书 Webhook 发送失败: %s", res)
            except Exception as e:
                logger.error("飞书 Webhook 异常: %s", e)

        logger.warning("未配置有效的飞书 App-Bot 或 Webhook，卡片仅在本地记录")
        return False
