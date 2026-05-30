# 微信公众号每日自动发文系统

每天早上9点，自动生成文章并推送到你的邮箱和微信。你只需花2分钟手动发布到公众号。

## 功能

- **每日荐书**：AI 书评人每天推荐一本好书——专业视角、幽默而不失趣味
  - 十个类别轮替：文学、历史、哲学、心理、商业、科技、传记、社会、艺术、科幻
  - 结构：引语 → 内容概括 → 三个理由 → 金句摘录 → 保留意见 → 明日预告
- **毛选附文**：AI 从 25 篇毛泽东选集经典中随机选一篇撰写现代读书笔记
- **自动配图**：Unsplash 现代图库自动匹配，每篇文章 5 张高清大图
- **双通道推送**：邮件 HTML（精美排版）+ PushPlus 微信消息
- **完全自动化**：GitHub Actions 每天早上 9:00（北京时间）定时运行

## 收到的是什么样

<img alt="email-example" src="https://via.placeholder.com/600x400/f7f6f4/333?text=邮件示例（现代白卡片排版）" />

## 快速开始（3 步）

### 1. Fork 本仓库

点右上角 Fork → 选择你的账号

### 2. 获取 4 个免费 Key

| 服务 | 用途 | 获取方式 |
|------|------|----------|
| DeepSeek | AI 写文章 | [platform.deepseek.com](https://platform.deepseek.com) 注册充值（极便宜，约 0.3 元/天） |
| QQ 邮箱 SMTP | 邮件推送 | QQ邮箱 → 设置 → 账户 → 开启 SMTP → 获取授权码 |
| PushPlus | 微信推送 | [pushplus.plus](http://www.pushplus.plus) 微信扫码 → 复制 Token |
| Unsplash | 文章配图 | [unsplash.com/developers](https://unsplash.com/developers) 注册 → 创建应用 → 获取 Access Key |

### 3. 设置 GitHub Secret

进入你的 Fork → Settings → Secrets and variables → Actions → New repository secret

- **Name**：`CONFIG_JSON`
- **Value**：复制以下内容，替换成你的 Key

```json
{
  "deepseek": {
    "api_key": "sk-你的DeepSeek-Key",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com"
  },
  "email": {
    "smtp_host": "smtp.qq.com",
    "smtp_port": 587,
    "sender": "你的QQ号@qq.com",
    "password": "QQ邮箱SMTP授权码",
    "receiver": "接收邮箱"
  },
  "wechat_notify": {
    "enabled": true,
    "type": "pushplus",
    "token": "你的PushPlus-Token"
  },
  "unsplash": {
    "api_key": "你的Unsplash-Access-Key"
  },
  "schedule": {
    "cron": "0 1 * * *",
    "comment": "UTC 1:00 = 北京时间 9:00"
  }
}
```

搞定！每天早上 9 点自动生成文章，发到你的邮箱和微信。

## 手动测试

进入仓库 Actions → Daily Article Generator → Run workflow → 等 2 分钟 → 查邮箱和微信

## 自定义

- **修改定时时间**：编辑 `.github/workflows/daily.yml` 里的 cron 表达式（UTC 时间）
- **调整文章风格**：编辑 `writer/prompts.py` 里的提示词
- **更换图片来源**：编辑 `images/fetcher.py`，支持 Unsplash / Pexels
- **增删书籍类别**：编辑 `mao_data/book_categories.json`
- **增删毛选篇目**：编辑 `mao_data/essays.json`

## 项目结构

```
├── .github/workflows/daily.yml   # GitHub Actions 定时任务
├── main.py                        # 主入口，串联全流程
├── config.example.json             # 配置模板
├── requirements.txt
│
├── writer/                        # AI 写作模块
│   ├── client.py                  # DeepSeek API 封装
│   └── prompts.py                 # 提示词模板
│
├── images/                        # 配图模块
│   └── fetcher.py                 # Unsplash 搜图下载
│
├── output/                        # 输出推送模块
│   ├── formatter.py               # 排版（邮件 HTML / 微信 Markdown）
│   └── notifier.py                # 邮件 + PushPlus 双通道
│
└── mao_data/                      # 内容数据
    ├── essays.json                 # 毛选 25 篇索引
    └── book_categories.json        # 荐书类别轮替
```

## 费用

| 项目 | 每月花费 |
|------|----------|
| DeepSeek API | 约 10-25 元 |
| GitHub Actions | 免费 |
| Unsplash 图库 | 免费 |
| PushPlus 通知 | 免费 |
| QQ 邮箱 SMTP | 免费 |
| **合计** | **约 10-25 元/月** |

## License

MIT
