<div align="center">

# Rapport

**开源、本地优先的「人际记忆」助手——为你生命里的人而记。**

把你线下面对面的真实对话记录、转写下来，以**「人」**（而非时间）为中心组织起来；在你需要时，帮你回看事实、理解对方、切换视角，把事情想通。

[**English**](./README.md) · 简体中文

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](./LICENSE)
![Status](https://img.shields.io/badge/status-早期开发中-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![Stars](https://img.shields.io/github/stars/sssst1118/Rapport?style=social)](https://github.com/sssst1118/Rapport)

</div>

---

> 🚧 **状态：早期开发。** **M1–M4 已经能跑**——录音 → 转写 → 本地 SQLite + 全文检索，一个以人为中心的**中英双语**桌面应用（今日 · 对话 · 人物 · 关系图 · 复盘），以及按需 AI 解读——**100% 本地跑（Ollama，零 API key）**、每条判断都**挂着可回放的原话出处**。点个 Star 跟进进展。

## 别再猜了

- 你的**老板**，到底怎么看你？
- 你**带的团队**，私下里服不服你？
- 你正在处的**那个人**，是真上心，还是在客气？

你在猜，谁都在猜。而 Rapport 让你不用猜。

它把你和 TA **真实说过的每一句话**完整留下来——想不通的时候，回放事实、切到对方的角度看一遍、把那个难回答的问题直接问出来。**不是读心术，是被留住的真相。**

## Rapport 是什么？

记忆是模糊的。一段对话结束，你留下的只是个*印象*——而印象会漂移：它自动填补空白、把细节放大或抹平，悄悄地随时间改写自己。

Rapport 替你留住**真实的记录**：它记录、转写你面对面的对话，以你生命里的**「人」**为中心组织起来，让你随时能回到**当时到底说了什么**——诚实地复盘、理解对方、也站到对方的角度看一次。

底下只有一个信念：**真实发生过的，胜过你恰好记住的。**

## 有什么不同

- **生而常驻** —— 它留住的是*真实*记录，而不只是你恰好想起来按下录音的那几下。
- **只录音频，不录屏** —— 你真实世界里面对面的对话。更轻、更纯粹。
- **以人为中心，不是时间轴** —— 人物画像、关系、视角切换，而不是一条没尽头的时间线。
- **100% 本地 + 开源** —— 一个常驻录音工具唯一值得信任的形态：数据不出你的机器，代码你能亲自读。

## 隐私：5 条你能在代码里核对的承诺

1. **默认 100% 本地** —— 音频和转写都落在你机器上的 SQLite 文件里，不上传任何东西。
2. **无需账号。**
3. **数据归你** —— 随时导出、删除、备份。数据库就是你磁盘上的一个文件。
4. **同步可选且端到端加密** —— 不开同步，就是**零字节**出本机。
5. **本地 AI 可选** —— 用本地模型（Ollama）做问答，连分析都可以不出设备。

因为代码开源，你能**亲眼读到到底是哪段代码在听你说话**——这把「相信某家公司」换成了「相信可被检验的代码」。

> Rapport 录的是真实的人。录音与取得同意的法律因地区而异——数据全留在你设备上，但合法使用是你自己的责任。

## 它怎么工作

```
录音 → 本地转写 → 切句并标说话人 → 加密本地库
   → 你提问 → RAG 检索相关片段 → 大模型作答 → 给你
```

Rapport 还通过**本地 REST API + MCP server**，把你的数据开放给你**已经在用的 AI 工具**——在 Claude Desktop 里问一句*「我和老王上次聊了啥，提醒我下」*，它就从你本地的 Rapport 库里取数作答。**数据始终不出本机。**

## 更大的图景：做你 AI 的「人际上下文层」

一个 AI 能从"会聊天"变成"真正的助手"，靠的不是话术，而是两件事：**握着你的真实上下文**，以及**能据此替你办事**。

Rapport 握住其中最私密、最难获取的那一块——**你和身边人的真实关系与对话**——并在本机内、安全地交给你已经在用的 AI 工具。于是 Claude、Cursor 不再是"聪明的陌生人"，而能给出真正贴合你人际处境的回应。

别人为你的*数字*生活做记忆检索；**Rapport 为你的*人际*生活做理解底座。**

## 技术栈

Python · `faster-whisper`（本地转写）· `pyannote`（说话人分离）· SQLite + FTS5 · 可插拔大模型（本地 **Ollama** 或自带 API key）· FastAPI + MCP · React (Vite) SPA + 系统托盘桌面应用（pystray，`rapport app`）。**Windows 先行，后续 macOS。**

## 快速开始

> **前置**：Python 3.10+（推荐 3.12）· **Node.js 20+**（构建网页界面用）。**默认 CPU 运行，无需 GPU 或 CUDA。** Windows 先行（macOS 后续）。
>
> Windows 用户想直接体验、不装环境，可下载打包好的安装器 `RapportSetup.exe`（开始菜单 + 系统托盘，免装 Python / Node）。从源码跑则按下面来。

### 1. 安装

```bash
git clone https://github.com/sssst1118/Rapport.git
cd Rapport

python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -e .                       # 或： uv pip install -e .

# 构建网页界面（serve / app 都要服务它，这步不能省，否则界面是空白）
npm --prefix frontend install
npm --prefix frontend run build
```

### 2. 选一种方式跑起来

```bash
rapport app        # 【推荐·最完整】系统托盘常驻：本地界面 + 后台持续录音，一体启动
rapport serve      # 只开网页界面 → 浏览器访问 http://127.0.0.1:8000
rapport watch      # 只开后台常驻录音守护（无窗口）
rapport mcp        # 开 MCP server，把本地数据接给 Claude Desktop / Cursor（stdio）
```

> `rapport app` 启动即录音（托盘图标红点 = 正在录音）；想先不录用 `rapport app --no-record`。它是托盘应用、**没有主窗口**——右键托盘图标即可暂停 / 打开界面 / 退出。

### 3. 想先看效果？灌一份演示数据（不用麦克风）

```bash
python seed_demo.py                                  # 写入 data/demo.db（不碰你的 rapport.db）
# Windows PowerShell:
$env:RAPPORT_DB_PATH="data/demo.db"; rapport serve
# macOS / Linux:
RAPPORT_DB_PATH=data/demo.db rapport serve
```

### 4. 配置语言模型（开启 AI 解读 · 可选）

不配也能用：界面、录音、检索、标注全都正常，只是每条 AI 解读会显示「未配置」。配上才有「按需解读」（M4），且**每条解读都事实与解读分离、挂原话出处 + 可回放原声**。

**三种配置方式，按需选一种：**

| 方式 | 适合场景 | 操作 |
| --- | --- | --- |
| **① 界面内「设置」页**（顶栏/侧栏齿轮图标） | 打包应用（`.exe`）首选，零环境变量 | 打开界面 → 点齿轮 → 填写后端 / 模型名 / API Key → 保存。立即生效，持久化到 `%LOCALAPPDATA%\Rapport\config.json`。 |
| **② 手动编辑 `%LOCALAPPDATA%\Rapport\config.json`** | 脚本/批量部署 | 直接编辑 JSON 文件，下次启动生效。 |
| **③ 环境变量**（优先级最高） | CLI、自动化 | 见下方示例，会覆盖 config.json 的配置。 |

优先级：**环境变量 > config.json > 默认值**。

**A. 本地 Ollama（推荐 · 全本地、零 API key、数据不出设备）**

```bash
# 1) 装 Ollama（https://ollama.com），拉一个对话模型：
ollama pull qwen2.5:7b-instruct        # 任意 chat 模型皆可，按机器配置选大小
# 2) 用环境变量指定后端（解读语言跟随界面 EN/中）：
# Windows PowerShell:
$env:RAPPORT_LLM_PROVIDER="ollama"; $env:RAPPORT_LLM_MODEL="qwen2.5:7b-instruct"; rapport serve
# macOS / Linux:
RAPPORT_LLM_PROVIDER=ollama RAPPORT_LLM_MODEL=qwen2.5:7b-instruct rapport serve
```

**B. 自带 API key（Anthropic）**

```bash
pip install -e ".[anthropic]"          # 装可选依赖
# Windows PowerShell:
$env:RAPPORT_LLM_PROVIDER="anthropic"; $env:ANTHROPIC_API_KEY="sk-ant-..."; $env:RAPPORT_LLM_MODEL="claude-opus-4-8"; rapport serve
# macOS / Linux:
RAPPORT_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... RAPPORT_LLM_MODEL=claude-opus-4-8 rapport serve
```

| 环境变量 | 作用 | 取值 |
| --- | --- | --- |
| `RAPPORT_LLM_PROVIDER` | 选语言模型后端 | `none`（默认，不解读）· `ollama` · `anthropic` |
| `RAPPORT_LLM_MODEL` | 模型名 | 如 `qwen2.5:7b-instruct` / `claude-opus-4-8` |
| `ANTHROPIC_API_KEY` | Anthropic 的 key | 仅 `provider=anthropic` 时需要 |

> 环境变量会覆盖 config.json，对 `rapport serve` / `rapport app` 同样生效。

### 命令行小工具

```bash
rapport transcribe 路径/音频.wav    # 转写一个音频文件
rapport ingest audio.wav            # 转写 → 作为一段对话入库
rapport show 1                      # 打印某段对话
rapport search "项目进度"            # 全文检索（中文需 ≥3 字）
rapport devices                     # 列出麦克风（record --device N 选设备）
```

首次转写会下载一个小的 Whisper 模型。用环境变量选模型大小或启用 GPU：

```bash
RAPPORT_WHISPER_MODEL=small rapport transcribe audio.wav   # tiny | base | small | medium | large-v3
RAPPORT_WHISPER_DEVICE=cuda  rapport transcribe audio.wav   # GPU（需 CUDA 运行库）
```

### 已知限制（M5 打包现状）

- **打包应用已内置「设置」页**：点顶栏/侧栏齿轮图标，直接在界面内配语言模型后端、模型名和 API Key，保存即生效，持久化到 `%LOCALAPPDATA%\Rapport\config.json`。环境变量仍可使用，且优先级高于 config.json。
- **`rapport app` 启动后自动打开界面**：默认浏览器会自动打开 `http://127.0.0.1:8000`（加 `--no-open` 可关闭）。退出 = 右键托盘图标 →「退出」（已可靠终止进程）；图标折叠到「^」找不到时，用 `taskkill /F /IM Rapport.exe` 兜底。
- 首次转写需联网下载 Whisper 模型；未代码签名，首次运行 SmartScreen 可能提示。

## 路线图

- [x] **M1** —— 录音 + 本地转写 + 简易界面 ✅
- [x] **M2** —— SQLite 本地存储 + 全文检索 + 入库 ✅ *(说话人分离 seam 已留；pyannote 可选)*
- [ ] **常驻采集** —— 持续后台录音（真实记录，而不只是手动片段）
- [x] **M3** —— 以人为中心的桌面应用 + 标注 ✅ *（FastAPI + React，中英双语：今日 · 对话 · 人物 · 关系图 · 复盘）*
- [x] **M4** —— 按需 AI 解读 ✅ *（可插拔大模型——本地 **Ollama**，零 API key，或自带 key；每条解读都事实与解读分离、**挂原话出处 + 可回放原声**）*
- [x] **M5** —— 做你 AI 的「人际上下文层」✅
  - [x] **MCP server** ✅ —— 基于官方 Python MCP SDK（FastMCP）、stdio transport；对外暴露 7 个只读结构化工具（`list_people` / `search_people` / `get_person` / `get_conversation` / `list_conversations` / `relationship_graph` / `search_utterances`）；纯数据、零 AI、零 API key；复用现有本地 DB 层、不依赖 web 服务器；每条返回话语都带可回放出处（utterance_id + conversation_id + 时间戳）
  - [x] **常驻 always-on 后台录音** ✅ —— `rapport watch` 作为独立守护进程运行：持续采集麦克风 → 按静音切句（utterance）→ 转写 → 说话人分离 → 入库；**按自然日分桶成对话**（纯时间轴组织，不做语义对话切分）；音频写滚动 day-WAV、每句带 day-WAV 内字节偏移以保 🔊 可回放；`/api/status` 诚实反映录制/暂停状态（前端红点变真）；暂停 = 完全停止采集（隐私优先、绝不隐蔽采集）；数据全程本地
  - [x] **Windows `.exe` 打包** ✅ —— PyInstaller onedir 产物 + NSIS 安装器（`RapportSetup.exe`）；系统托盘常驻应用（托盘菜单：开始/暂停录音、打开界面、退出；图标颜色 = 持续可见的录制指示）；单进程内编排本地 web 界面（serve）+ 常驻录音 Engine；冻结态用户数据落 `%LOCALAPPDATA%\Rapport`；可选开机自启（默认不勾，尊重隐私）；卸载保留用户数据。*注：未打包 whisper 模型，首次转写需联网下载；未代码签名，首次运行 SmartScreen 可能提示。*
- [ ] **M6** —— 声纹识别 · macOS

## 许可证

[AGPL-3.0](./LICENSE) —— 对所有人永久免费且开源。它的强 copyleft 意味着没人能悄悄把它闭源、或「收购了事」。

**提供商业授权** —— 若想在闭源 / 商业产品里使用 Rapport 而不承担 AGPL 义务，请联系作者 [@sssst1118](https://github.com/sssst1118)。

## 给个 Star ⭐

Rapport 还在早期开发。如果这个想法打动了你，**点个 Star 跟进**——这真的很有帮助。
