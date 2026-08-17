# -*- coding: utf-8 -*-
"""
全局配置模块
"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Config:
    """系统配置类"""

    # 监控链配置 (DexScreener chain id)
    CHAINS: List[str] = os.getenv("MONITOR_CHAINS", "solana,bsc,base").split(",")

    # 轮询与调度
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "180"))  # 3分钟
    DEDUP_COOLDOWN_MINUTES: int = int(os.getenv("DEDUP_COOLDOWN_MINUTES", "45"))  # 45分钟

    # 代币异动告警阈值
    MIN_LIQUIDITY_USD: float = float(os.getenv("MIN_LIQUIDITY_USD", "5000"))       # 最小池子流动性 5,000 USD (防空池假币)
    MIN_VOLUME_5M_USD: float = float(os.getenv("MIN_VOLUME_5M_USD", "10000"))      # 5分钟交易量突增 >= 10,000 USD
    MIN_PRICE_CHANGE_5M: float = float(os.getenv("MIN_PRICE_CHANGE_5M", "15.0"))   # 5分钟价格拉升 >= 15%
    MIN_BUYS_5M: int = int(os.getenv("MIN_BUYS_5M", "20"))                         # 5分钟买单数 >= 20 笔
    MIN_BUY_SELL_RATIO: float = float(os.getenv("MIN_BUY_SELL_RATIO", "1.5"))      # 买卖单比率 >= 1.5

    # NFT 异动告警阈值
    NFT_MIN_24H_VOLUME_BNB: float = float(os.getenv("NFT_MIN_24H_VOLUME_BNB", "0.5"))
    NFT_MIN_24H_VOLUME_ETH: float = float(os.getenv("NFT_MIN_24H_VOLUME_ETH", "0.3"))
    NFT_MIN_SALES_1H: int = int(os.getenv("NFT_MIN_SALES_1H", "5"))

    # 飞书机器人配置
    FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "").strip()
    FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "").strip()
    FEISHU_CHAT_ID: str = os.getenv("FEISHU_CHAT_ID", "oc_68dbbe5b348f3d561040a34e683d94f2").strip()
    FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    FEISHU_WEBHOOK_SECRET: str = os.getenv("FEISHU_WEBHOOK_SECRET", "").strip()

    # 代理设置 (优先遵循系统或 Clash 代理)
    HTTP_PROXY: str = os.getenv("HTTP_PROXY", "")
    HTTPS_PROXY: str = os.getenv("HTTPS_PROXY", "")

    # 数据缓存目录
    CACHE_DIR: Path = Path(__file__).parent.parent / "data"

    @classmethod
    def is_feishu_app_bot_ready(cls) -> bool:
        return bool(cls.FEISHU_APP_ID and cls.FEISHU_APP_SECRET and cls.FEISHU_CHAT_ID)

    @classmethod
    def is_feishu_webhook_ready(cls) -> bool:
        return bool(cls.FEISHU_WEBHOOK_URL)


config = Config()
# 确保数据目录存在
config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
