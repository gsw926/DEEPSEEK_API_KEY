# 📺 TV Industry Daily News Push - Cloud Edition

Mac 关机也能推送。基于 GitHub Actions + DeepSeek AI + Google News RSS，每日自动搜索电视行业新闻，AI 总结后推送到微信。

## 架构

```
Google News RSS (免费搜索) → DeepSeek AI (筛选+总结) → PushPlus → 微信
                    ↑                                          ↑
            GitHub Actions 定时触发 (免费)              每日 08:30 自动推送
```

## 费用

| 组件 | 费用 | 说明 |
|------|------|------|
| GitHub Actions | 免费 | 公开仓库无限分钟，私有仓库 2000 分钟/月 |
| DeepSeek API | 约 ¥0.01/天 | 注册送 ¥10，可用约 1000 天 |
| Google News RSS | 免费 | 无需 API Key |
| PushPlus | 免费 | 已配置 |

## 部署步骤

### 第一步：注册 DeepSeek 获取 API Key

1. 打开 https://platform.deepseek.com/
2. 注册账号（支持手机号/邮箱）
3. 进入「API Keys」页面，点击「创建 API Key」
4. 复制 API Key（格式类似 `sk-xxxxxxxxxxxxxxxx`）
5. 新用户赠送 ¥10 余额，足够用 1000 天

### 第二步：创建 GitHub 仓库

1. 打开 https://github.com/new
2. 仓库名填 `tv-daily-push`（或任意名称）
3. 选择 **Public**（免费无限分钟）或 **Private**（每月 2000 分钟）
4. 点击「Create repository」
5. 把本项目所有文件上传到仓库（或用 git push）

### 第三步：配置 Secrets

进入仓库页面 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，添加两个：

| Name | Value |
|------|-------|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key（`sk-xxxx`） |
| `PUSHPLUS_TOKEN` | `001ebed82a144517a912aab762f7135f` |

### 第四步：测试运行

1. 进入仓库 **Actions** 标签页
2. 左侧选择「TV Industry Daily Push」
3. 点击「Run workflow」→ 绿色按钮确认
4. 等待 2-3 分钟，微信应收到推送

### 第五步：完成

以后每天北京时间 08:30 自动推送，Mac 开不开机都行。

## 自定义

### 修改搜索关键词

编辑 `main.py` 中的 `SEARCH_QUERIES` 列表：

```python
SEARCH_QUERIES = [
    ("产品功能", "你的搜索词", "zh-CN"),
    ...
]
```

### 修改推送时间

编辑 `.github/workflows/daily-push.yml` 中的 cron 表达式（UTC 时间）：

```yaml
cron: '30 0 * * *'  # 08:30 北京时间 = 00:30 UTC
```

常用时间对照：

| 北京时间 | UTC |
|----------|-----|
| 07:00 | 23:00 (前一天) |
| 08:00 | 00:00 |
| 08:30 | 00:30 |
| 09:00 | 01:00 |
| 12:00 | 04:00 |

### 修改 AI 模型

编辑 `main.py` 中的 `MODEL` 变量：

```python
MODEL = "deepseek-chat"      # 标准模型，便宜
# MODEL = "deepseek-reasoner"  # 推理模型，更贵但更强
```

## 注意事项

- GitHub Actions 的 cron 不保证精确到秒，可能有几分钟延迟
- 如果当天 GitHub 服务故障，推送会跳过（不会补发）
- DeepSeek 余额用完后推送会失败，注意定期检查余额
- 建议同时保留 WorkBuddy 本地自动化作为备份（错开时间推送）

## 文件说明

```
tv-daily-cloud/
├── main.py                          # 主脚本：RSS搜索 → AI总结 → HTML生成 → 微信推送
├── requirements.txt                 # Python依赖（仅 requests）
├── .github/workflows/daily-push.yml # GitHub Actions 定时任务配置
├── .gitignore
└── README.md                        # 本文件
```
