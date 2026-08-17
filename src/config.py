# -*- coding: utf-8 -*-
"""
全局配置模块
支持环境变量、.env 文件以及本地 OpenClaw 凭证与本地代理自动发现
"""
import json
import logging
import os
import socket
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载 .env 文件（如果存在）
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


def _get_openclaw_feishu_config() -> Dict[str, str]:
    """从本地 OpenClaw 配置自动读取飞书凭证"""
    openclaw_file = Path(r"C:\Users\Administrator\.openclaw\openclaw.json")
    if openclaw_file.is_file():
        try:
            data = json.loads(openclaw_file.read_text(encoding="utf-8"))
            feishu = data.get("channels", {}).get("feishu", {})
            if isinstance(feishu, dict):
                return {
                    "app_id": str(feishu.get("appId") or feishu.get("app_id") or "").strip(),
                    "app_secret": str(feishu.get("appSecret") or feishu.get("app_secret") or "").strip(),
                }
        except Exception as e:
            logger.debug("读取 openclaw.json 失败: %s", e)
    return {}


def _detect_local_proxy() -> Optional[str]:
    """探测本地 Clash / 代理端口 (优先 7897, 7890)"""
    for port in [7897, 7890, 10808, 10809]:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return f"http://127.0.0.1:{port}"
        except Exception:
            continue
    return None


class Config:
    """系统配置类"""

    # 监控链配置 (DexScreener chain id)
    CHAINS: List[str] = [
        c.strip().lower() for c in os.getenv("MONITOR_CHAINS", "solana,bsc,base").split(",") if c.strip()
    ]

    # 轮询与调度
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "180"))  # 3分钟
    DEDUP_COOLDOWN_MINUTES: int = int(os.getenv("DEDUP_COOLDOWN_MINUTES", "45"))  # 45分钟

    # 代币异动告警阈值
    MIN_LIQUIDITY_USD: float = float(os.getenv("MIN_LIQUIDITY_USD", "5000"))       # 最小池子流动性 5,000 USD
    MIN_VOLUME_5M_USD: float = float(os.getenv("MIN_VOLUME_5M_USD", "10000"))      # 5分钟交易量突增 >= 10,000 USD
    MIN_PRICE_CHANGE_5M: float = float(os.getenv("MIN_PRICE_CHANGE_5M", "15.0"))   # 5分钟价格拉升 >= 15%
    MIN_BUYS_5M: int = int(os.getenv("MIN_BUYS_5M", "20"))                         # 5分钟买单数 >= 20 笔
    MIN_BUY_SELL_RATIO: float = float(os.getenv("MIN_BUY_SELL_RATIO", "1.5"))      # 买卖单比率 >= 1.5

    # NFT 异动告警阈值
    NFT_MIN_24H_VOLUME_BNB: float = float(os.getenv("NFT_MIN_24H_VOLUME_BNB", "0.5"))
    NFT_MIN_24H_VOLUME_ETH: float = float(os.getenv("NFT_MIN_24H_VOLUME_ETH", "0.3"))

    # 飞书凭证加载（环境变量优先，其次自动读取 openclaw.json，默认群 fallback）
    _openclaw_feishu = _get_openclaw_feishu_config()
    FEISHU_APP_ID: str = (os.getenv("FEISHU_APP_ID", "") or _openclaw_feishu.get("app_id", "")).strip()
    FEISHU_APP_SECRET: str = (os.getenv("FEISHU_APP_SECRET", "") or _openclaw_feishu.get("app_secret", "")).strip()
    FEISHU_CHAT_ID: str = (os.getenv("FEISHU_CHAT_ID", "") or "oc_68dbbe5b348f3d561040a34e683d94f2").strip()
    FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    FEISHU_WEBHOOK_SECRET: str = os.getenv("FEISHU_WEBHOOK_SECRET", "").strip()

    # 本地代理配置
    _detected_proxy = _detect_local_proxy()
    HTTP_PROXY: str = os.getenv("HTTP_PROXY", "") or _detected_proxy or ""
    HTTPS_PROXY: str = os.getenv("HTTPS_PROXY", "") or _detected_proxy or ""

    # 数据缓存目录
    CACHE_DIR: Path = Path(__file__).parent.parent / "data"

    @classmethod
    def get_overseas_proxies(cls) -> Optional[Dict[str, str]]:
        """获取境外 API (DexScreener 等) 所需的代理字典"""
        proxy = cls.HTTPS_PROXY or cls.HTTP_PROXY or cls._detect_local_proxy()
        if proxy:
            return {"http": proxy, "https": proxy}
        return None

    @classmethod
    def is_feishu_app_bot_ready(cls) -> bool:
        return bool(cls.FEISHU_APP_ID and cls.FEISHU_APP_SECRET and cls.FEISHU_CHAT_ID)

    @classmethod
    def is_feishu_webhook_ready(cls) -> bool:
        return bool(cls.FEISHU_WEBHOOK_URL)


config = Config()
# 确保数据目录存在
config.CACHE_DIR.mkdir(parents=True, exist_ok=True)

