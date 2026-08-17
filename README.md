# Meme 代币 & 热点 NFT 舆情与异动实时预警系统 (`meme-sentiment-alert`)

针对 **Solana / BSC / Base 链上爆发性 Meme 代币** 与 **Element / OpenSea 热点 NFT**（如《牛来》NIULAI 等突发热梗）的全天候链上量价异常与社交舆情监控工具。

---

## 🌟 核心功能

1. **多链实时异动捕获**：
   - 自动轮询 DexScreener（Solana / BSC / Base）的 Top Boosted 社区助推榜单、新上架宣发 Profiles 及放量新池。
   - 实时计算 5 分钟与 1 小时级别的交易量加速度、短线暴拉涨幅、买卖单笔数比（Buy/Sell Ratio）与资金抢筹强度。
2. **NFT 热点与热梗追踪**：
   - 聚合 Element Market 热门排行榜与现象级 Meme 集合（如 `niulais` 牛来）。
   - 追踪地板价、24h 成交额异动与持有人增减。
3. **安全风控与防貔貅过滤**：
   - 自动过滤流动性过小（<$5,000）的空池骗局。
   - 标注流动性浅度、无卖单疑似貔貅（Honeypot）等风险预警。
4. **飞书交互式卡片推送 (Feishu Interactive Card)**：
   - 投递富文本卡片，包含标的合约、现价、涨跌幅、异动原因与一键跳转 DexScreener / GMGN / Element 按钮。
5. **智能去重与防轰炸**：
   - 同一标的触发后进入 45 分钟冷却期，支持历史记录自动淘汰。

---

## 🚀 快速使用

### 1. 安装依赖
```powershell
& 'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe' -m pip install -r requirements.txt
```

### 2. 配置环境变量（可选）
复制 `.env.example` 为 `.env`：
```env
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxx
FEISHU_CHAT_ID=oc_68dbbe5b348f3d561040a34e683d94f2
```

### 3. 运行命令

- **单次扫描（本地控制台预览，不推飞书）**：
  ```powershell
  & 'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe' main.py --once --dry-run
  ```

- **单次扫描并发送飞书卡片**：
  ```powershell
  & 'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe' main.py --once
  ```

- **常驻后台守护监控（每 3 分钟轮询一次）**：
  ```powershell
  & 'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe' main.py --daemon
  ```

- **测试飞书机器人卡片连通性**：
  ```powershell
  & 'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe' main.py --test-feishu
  ```

---

## 📁 目录结构

```text
meme-sentiment-alert/
├── data/                       # 状态与去重缓存
│   └── dedup_state.json
├── src/
│   ├── config.py               # 全局配置中心
│   ├── fetchers/               # 数据采集模块
│   │   ├── dex_fetcher.py      # 链上 DexScreener 数据源
│   │   └── nft_fetcher.py      # Element/NFT 市场数据源
│   ├── engine/                 # 舆情与风控判定引擎
│   │   ├── sentiment_analyzer.py # 评分与异动触发器
│   │   └── dedup_manager.py    # 状态去重器
│   └── notifiers/              # 飞书互动卡片投递器
│       └── feishu_notifier.py
├── tests/                      # 单元测试集
│   └── test_alert_system.py
├── .env.example
├── main.py                     # CLI 主入口
├── README.md
└── requirements.txt
```
