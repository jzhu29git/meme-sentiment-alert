# -*- coding: utf-8 -*-
"""
去重与状态管理模块
保证同一标的在冷却期内不重复推送，防止刷屏骚扰
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict
from src.config import config

logger = logging.getLogger(__name__)


class DedupManager:
    """去重状态管理器"""

    def __init__(self, state_file: Path = None):
        self.state_file = state_file or (config.CACHE_DIR / "dedup_state.json")
        self.cooldown_seconds = config.DEDUP_COOLDOWN_MINUTES * 60
        self.state: Dict[str, float] = self._load_state()

    def _load_state(self) -> Dict[str, float]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("读取去重状态文件失败: %s", e)
        return {}

    def _save_state(self) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存去重状态失败: %s", e)

    def is_fresh_alert(self, item_key: str) -> bool:
        """检查该标的是否处于可推送状态（已过冷却期或从未推送）"""
        now = time.time()
        last_alert_time = self.state.get(item_key, 0)
        if (now - last_alert_time) > self.cooldown_seconds:
            return True
        return False

    def mark_alerted(self, item_key: str) -> None:
        """记录已推送时间戳"""
        self.state[item_key] = time.time()
        self._save_state()

    def cleanup_expired(self) -> None:
        """清理超过 24 小时的过期旧记录"""
        now = time.time()
        expired_keys = [k for k, t in self.state.items() if (now - t) > 86400]
        for k in expired_keys:
            del self.state[k]
        if expired_keys:
            self._save_state()
