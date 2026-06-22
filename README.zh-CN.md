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

> 🚧 **状态：早期开发。** **M1–M3 已经能跑**——录音 → 转写 → 本地 SQLite + 全文检索，外加一个以人为中心的桌面应用（今日 · 对话 · 人物 · 关系图 · 复盘）。下一步是按需 AI 问答（M4）。点个 Star 跟进进展。

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

Python · `faster-whisper`（本地转写）· `pyannote`（说话人分离）· SQLite + FTS5 · 可插拔大模型（本地 **Ollama** 或自带 API key）· FastAPI + MCP · React (Vite) SPA → PyWebview 桌面壳。**Windows 先行，后续 macOS。**

## 快速开始

> **Python 3.10+**（推荐 3.12，预编译 wheel 覆盖最全）。**默认 CPU 运行，无需 GPU 或 CUDA。**

```bash
git clone https://github.com/sssst1118/Rapport.git
cd Rapport
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -e .            # 或： uv pip install -e .

rapport transcribe 路径/音频.wav    # 转写一个音频文件
rapport ui                          # 或启动网页界面
```

首次运行会下载一个小的 Whisper 模型。用环境变量选模型大小或启用 GPU：

```bash
RAPPORT_WHISPER_MODEL=small rapport transcribe audio.wav   # tiny | base | small | medium | large-v3
RAPPORT_WHISPER_DEVICE=cuda  rapport transcribe audio.wav   # GPU（需 CUDA 运行库）
```

把录音存进本地数据库，再浏览 / 检索：

```bash
rapport ingest audio.wav   # 转写 → 作为一段对话入库
rapport show 1             # 打印某段对话
rapport search "项目进度"   # 全文检索（中文需 ≥3 字）
rapport devices            # 列出麦克风（record --device N 选设备）
```

## 路线图

- [x] **M1** —— 录音 + 本地转写 + 简易界面 ✅
- [x] **M2** —— SQLite 本地存储 + 全文检索 + 入库 ✅ *(说话人分离 seam 已留；pyannote 可选)*
- [ ] **常驻采集** —— 持续后台录音（真实记录，而不只是手动片段）
- [x] **M3** —— 以人为中心的桌面应用 + 标注 ✅ *（FastAPI + React：今日 · 对话 · 人物 · 关系图 · 复盘；事实层已真，AI 解读留待 M4）*
- [ ] **M4** —— 按需问答（RAG）——摘要 / 画像 / 视角切换背后的 AI 解读
- [ ] **M5** —— 本地 REST API + MCP server + Windows 打包
- [ ] **M6** —— 声纹识别 · 本地大模型 · macOS

## 许可证

[AGPL-3.0](./LICENSE) —— 对所有人永久免费且开源。它的强 copyleft 意味着没人能悄悄把它闭源、或「收购了事」。

**提供商业授权** —— 若想在闭源 / 商业产品里使用 Rapport 而不承担 AGPL 义务，请联系作者 [@sssst1118](https://github.com/sssst1118)。

## 给个 Star ⭐

Rapport 还在早期开发。如果这个想法打动了你，**点个 Star 跟进**——这真的很有帮助。
