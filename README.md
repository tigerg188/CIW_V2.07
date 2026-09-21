# CIW 智能办公平台 V2.07

本地知识库挂载 · 混合检索（BM25 + Dense + RRF）· 任务规划 · 本地 / 云端双后端生成

## 版本定位

在 **V2.06** 稳定逻辑上增量：

- 保留：Hybrid RAG、TaskPlan、EvidencePack、工作流、知识库资产
- 新增：**OpenAI 兼容云端生成**（如 Groq / 中转）
- 新增：本地对话可关闭；**Embedding 仍走 LM Studio**（可选）
- 新增：云端设置本地记忆、联通性测试、云端 `max_tokens` 独立抬升

## 快速开始（Windows）

1. 解压本仓库中的 `CIW_v2.07` 目录到任意盘（建议非 C 盘）
2. 双击 `start.bat`（可自配置 embeddable Python 与依赖）
3. （可选）启动 LM Studio，加载 **Embedding** 模型并开启 Local Server → `http://localhost:1234/v1`
4. 在 **环境 → 大模型底座**：
   - 生成后端选「云端 OpenAI 兼容」
   - 填写 `base_url` / `api_key` / `model`
   - 点 **测试云端连接** → **保存生成设置**
5. 挂载知识库后，使用「知识库检索」等工作流

### Groq 示例

- base_url：`https://api.groq.com/openai/v1`
- model：以控制台可用模型名为准

### 配置文件

- 运行时写入程序目录 `settings.json`（含云端记忆，请勿把真实 key 提交到公开仓库）
- 模板：`settings.example.json`

## 架构要点

```
用户任务
  → TaskUnderstand / TaskPlan（规则为主）
  → Hybrid 检索（BM25；Embedding 可用时 + Dense + RRF）
  → EvidencePack
  → 生成：本地 LM Studio Chat  或  云端 OpenAI 兼容 API
```

- **Embedding** 与 **Chat** 路径分离：云端只负责生成，不替代本地向量索引
- 云端生成默认提高 `max_tokens`（可用 `cloud_max_tokens` 配置）

## 目录结构（摘要）

- `main.py` / `start.bat` — 入口
- `office/` — RAG、规划、预算、LLM 路由
- `retrieval/` — BM25 / RRF / 路由
- `ui/` — PySide6 界面
- `workflow/` — 工作流提示词
- `themes/` — 外观

## 日志

会话日志：`ciw_YYYYMMDD_HHMMSS.log`、`latest.log`（反馈问题时请一并提供）

## 许可与使用

个人 / 办公本地使用。第三方开源依赖遵循各自许可证。请勿将 API Key 提交到版本库。
