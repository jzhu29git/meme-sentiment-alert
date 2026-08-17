# -*- coding: utf-8 -*-
"""
Meme 代币 / 热点 NFT 舆情与异动实时预警系统
主入口文件
"""
import argparse
import logging
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config import config
from src.fetchers.dex_fetcher import DexFetcher
from src.fetchers.nft_fetcher import NFTFetcher
from src.engine.sentiment_analyzer import SentimentAnalyzer
from src.engine.dedup_manager import DedupManager
from src.notifiers.feishu_notifier import FeishuNotifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("MemeAlert")
console = Console()


class MemeAlertSystem:
    """舆情异动监控主控系统"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.dex_fetcher = DexFetcher()
        self.nft_fetcher = NFTFetcher()
        self.analyzer = SentimentAnalyzer()
        self.dedup = DedupManager()
        self.notifier = FeishuNotifier()

    def run_scan(self) -> int:
        """执行单轮全网扫描与异动判定"""
        console.print(Panel.fit("🔍 [bold cyan]正在执行链上 Meme 与 NFT 舆情异动扫描...[/bold cyan]"))
        alert_count = 0

        # 1. 扫描链上 Meme 代币
        try:
            tokens = self.dex_fetcher.collect_hot_candidates()
            for token in tokens:
                alert = self.analyzer.analyze_token(token)
                if alert:
                    token_key = f"TOKEN:{alert['chain']}:{alert['tokenAddress']}"
                    if self.dedup.is_fresh_alert(token_key):
                        alert_count += 1
                        self._handle_token_alert(alert, token_key)
                    else:
                        logger.debug("代币 [%s] 处于冷却期中，跳过推送", token_key)
        except Exception as e:
            logger.error("扫描代币异动时出错: %s", e)

        # 2. 扫描热点 NFT
        try:
            nfts = self.nft_fetcher.scan_monitored_meme_nfts()
            for nft in nfts:
                alert = self.analyzer.analyze_nft(nft)
                if alert:
                    nft_key = f"NFT:{alert['chain']}:{alert['slug']}"
                    if self.dedup.is_fresh_alert(nft_key):
                        alert_count += 1
                        self._handle_nft_alert(alert, nft_key)
                    else:
                        logger.debug("NFT [%s] 处于冷却期中，跳过推送", nft_key)
        except Exception as e:
            logger.error("扫描 NFT 异动时出错: %s", e)

        # 3. 清理过期去重状态
        self.dedup.cleanup_expired()

        console.print(f"[bold green]✓ 本轮扫描完成，共触发 {alert_count} 个新异动预警。[/bold green]")
        return alert_count

    def _handle_token_alert(self, alert: dict, key: str) -> None:
        """处理代币告警"""
        table = Table(title=f"🔥 命中 Meme 异动预警: ${alert['symbol']} ({alert['chain']})", show_header=True)
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="magenta")
        table.add_row("代币名称", alert['name'])
        table.add_row("公链 / 现价", f"{alert['chain']} / ${alert['priceUsd']:,.6f}")
        table.add_row("5m 涨幅 / 1h 涨幅", f"{alert['priceChangeM5']:+.2f}% / {alert['priceChangeH1']:+.2f}%")
        table.add_row("5m 成交额", f"${alert['volumeM5']:,.0f}")
        table.add_row("5m 买卖单比", f"{alert['buysM5']} 买 / {alert['sellsM5']} 卖")
        table.add_row("流动性深度 (Liq)", f"${alert['liquidityUsd']:,.0f}")
        table.add_row("合约地址", alert['tokenAddress'])
        table.add_row("综合热度评分", f"{alert['score']} 分")
        console.print(table)

        card = self.notifier.build_token_card(alert)
        if not self.dry_run:
            success = self.notifier.send_card(card)
            if success:
                self.dedup.mark_alerted(key)
        else:
            console.print("[yellow][DRY-RUN 模式] 仅在控制台预览，不发送飞书消息[/yellow]")
            self.dedup.mark_alerted(key)

    def _handle_nft_alert(self, alert: dict, key: str) -> None:
        """处理 NFT 告警"""
        table = Table(title=f"🎯 命中 NFT 异动: {alert['name']} ({alert['chain']})", show_header=True)
        table.add_column("属性", style="cyan")
        table.add_column("数据", style="magenta")
        table.add_row("集合名称", alert['name'])
        table.add_row("地板价", f"{alert['floorPrice']} {alert['chain']}")
        table.add_row("24h 成交额", f"{alert['volume24h']:.2f} {alert['chain']}")
        table.add_row("持有人数", str(alert['owners']))
        table.add_row("Element 链接", alert['elementUrl'])
        console.print(table)

        card = self.notifier.build_nft_card(alert)
        if not self.dry_run:
            success = self.notifier.send_card(card)
            if success:
                self.dedup.mark_alerted(key)
        else:
            console.print("[yellow][DRY-RUN 模式] 仅在控制台预览，不发送飞书消息[/yellow]")
            self.dedup.mark_alerted(key)

    def test_feishu(self) -> None:
        """发送测试卡片验证飞书机器人连通性"""
        console.print(Panel.fit("🧪 [bold cyan]正在发送测试预警卡片至飞书...[/bold cyan]"))
        test_alert = {
            "type": "TOKEN",
            "name": "Niulai Cow Meme",
            "symbol": "NIULAI",
            "chain": "BSC",
            "tokenAddress": "0x5fd0d8fecf408f61080cea470249026d3e02fb3d",
            "pairAddress": "0x311188be...",
            "priceUsd": 0.00345,
            "fdv": 3450000,
            "liquidityUsd": 128500,
            "volumeM5": 45600,
            "volumeH1": 198000,
            "priceChangeM5": 38.5,
            "priceChangeH1": 125.0,
            "priceChangeH24": 350.0,
            "buysM5": 68,
            "sellsM5": 12,
            "score": 95,
            "reasons": [
                "⚡ 5m成交量突破 $45,600 且短线暴拉 +38.5%",
                "🔥 5m买卖单比高达 5.7:1 (68笔买入/12笔卖出)",
                "🎯 关联现象级热点《牛来》电影社群爆发"
            ],
            "riskFlags": ["✅ 流动性充足", "✅ 社区热度极高"],
            "url": "https://dexscreener.com/bsc/0x5fd0d8fecf408f61080cea470249026d3e02fb3d",
        }
        card = self.notifier.build_token_card(test_alert)
        ok = self.notifier.send_card(card)
        if ok:
            console.print("[bold green]✓ 飞书测试卡片投递成功！请查看飞书对应群聊。[/bold green]")
        else:
            console.print("[bold red]✗ 飞书测试卡片投递失败，请检查配置或网络。[/bold red]")


def main():
    parser = argparse.ArgumentParser(description="Meme 代币 / 热点 NFT 舆情与异动实时预警系统")
    parser.add_argument("--once", action="store_true", help="执行单次全网扫描并退出")
    parser.add_argument("--dry-run", action="store_true", help="测试运行（不投递真实飞书消息）")
    parser.add_argument("--daemon", action="store_true", help="常驻后台守护监控模式")
    parser.add_argument("--test-feishu", action="store_true", help="发送一条飞书测试卡片")
    args = parser.parse_args()

    system = MemeAlertSystem(dry_run=args.dry_run)

    if args.test_feishu:
        system.test_feishu()
        return

    if args.once or not args.daemon:
        system.run_scan()
        return

    # 常驻守护模式
    console.print(Panel.fit(f"🚀 [bold green]Meme 舆情监控守护进程启动，轮询周期: {config.POLL_INTERVAL_SECONDS} 秒[/bold green]"))
    while True:
        try:
            system.run_scan()
            time.sleep(config.POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            console.print("[bold yellow]监控进程已手动停止。[/bold yellow]")
            break
        except Exception as e:
            logger.error("监控循环发生未捕获异常: %s", e)
            time.sleep(10)


if __name__ == "__main__":
    main()
