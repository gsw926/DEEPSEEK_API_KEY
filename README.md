# Daily Industry News Push - Cloud Edition

Mac 关机也能推送。基于 GitHub Actions + DeepSeek AI + Google News RSS，每日自动搜索行业新闻，AI 总结后推送到微信。

## 支持的行业推送

| 主题 | TOPIC | 推送标题 | 四个方向 |
|------|-------|---------|---------|
| 📺 电视行业 | `tv` | 每日电视行业趋势 | 产品功能、用户体验、最新科技、行业趋势 |
| 🎨 设计行业 | `design` | 每日设计行业趋势 | 设计工具、用户体验、创意趋势、行业动态 |
| 🤖 AI行业 | `ai` | 每日AI行业趋势 | 模型与技术、产品应用、行业动态、前沿研究 |

## 架构

```
Google News RSS (免费搜索) → DeepSeek AI (筛选+总结) → PushPlus → 微信
                    ↑                                          ↑
            GitHub Actions 定时触发 (免费)              每日 08:30 自动推送
```

## 费用

| 组件 | 费用 | 说明 |
|------|------|------|
| GitHub Actions | 免费 | 公开仓库无限分钟 |
| DeepSeek API | 约 ¥0.03/天 | 3个主题各约¥0.01，注册送¥10可用约300天 |
| Google News RSS | 免费 | 无需 API Key |
| PushPlus | 免费 | 已配置 |

## 部署步骤

### 第一步：注册 DeepSeek 获取 API Key

1. 打开 https://platform.deepseek.com/
2. 注册 → API Keys → 创建 API Key
3. 复制 API Key（格式 `sk-xxxx`）

### 第二步：配置 GitHub Secrets

仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Name | Value |
|------|-------|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key |
| `PUSHPLUS_TOKEN` | `001ebed82a144517a912aab762f7135f` |

### 第三步：测试运行

1. 进入仓库 Actions 标签页
2. 选择「Daily Industry News Push」
3. 点 Run workflow → 可选择运行 `all`（三个主题）或单个主题
4. 等待 2-3 分钟，微信收到推送

### 第四步：完成

以后每天 08:30 自动推送三个行业的新闻，Mac 开不开机都行。

## 自定义

### 修改搜索关键词

编辑 `main.py` 中 `TOPICS` 字典对应主题的 `queries` 列表。

### 修改推送时间

编辑 `.github/workflows/daily-push.yml` 中的 cron：

```yaml
cron: '30 0 * * *'  # 08:30 北京时间 = 00:30 UTC
```

### 添加新行业

在 `main.py` 的 `TOPICS` 字典中添加新条目，然后在 workflow 的 matrix 中加入对应 topic 名。

## 注意事项

- GitHub Actions cron 可能有几分钟延迟
- DeepSeek 余额用完后推送会失败，注意定期检查
- 三个主题并行运行，总耗时约 3-5 分钟
