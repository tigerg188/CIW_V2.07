# CIW 智能办公平台 V2.07

本地知识库挂载 · 混合检索 · 生成可走 **本地 LM Studio** 或 **云端 OpenAI 兼容接口**

## 本版相对 V2.06 的变化

1. **生成后端可切换**
   - `local`：LM Studio 中的对话模型
   - `cloud`：任意 OpenAI 兼容 `chat/completions`（`cloud_base_url` / `cloud_api_key` / `cloud_model`）
2. **关闭本地对话模型**
   - `local_chat_enabled = false` 时生成强制走云端
   - **不会**关闭 LM Studio；**Embedding 仍依赖** LM Studio
3. **检索 / 同步** 始终使用本地 `llm_base_url`（默认 `http://localhost:1234/v1`）

## 快速开始（Windows）

1. 启动 LM Studio，加载 **Embedding**，开启 Local Server（默认 1234）
2. （可选）加载本地对话模型；仅云端生成可不加载 Chat
3. 双击 `start.bat`
4. 设置 → 模型：选择本地/云端，填写云端参数并保存
5. 勾选知识库 → 同步 → 提问

## settings.json 关键键

| 键 | 含义 |
|----|------|
| `llm_base_url` | 本地 LM Studio（Embedding + 可选本地 Chat） |
| `chat_backend` | `local` 或 `cloud` |
| `local_chat_enabled` | `false` 时关闭本地对话 |
| `cloud_base_url` | 云端 API 根路径（含 `/v1`） |
| `cloud_api_key` | 云端密钥（仅本机） |
| `cloud_model` | 云端模型名 |

## 架构

```
知识库 → 本地解析/分块 → Embedding(LM Studio) → 混合检索 → Evidence
                                                          ↓
                                                Chat：本地或云端
```
