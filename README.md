<div align="center">

# Rapport

**Open-source, local-first memory for the people in your life.**

Record your real-world conversations, organize them around *people* — not time — and, when you need it, replay the facts, understand the other side, and think it through.

**English** · [简体中文](./README.zh-CN.md)

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](./LICENSE)
![Status](https://img.shields.io/badge/status-early%20development-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![Stars](https://img.shields.io/github/stars/sssst1118/Rapport?style=social)](https://github.com/sssst1118/Rapport)

</div>

---

> 🚧 **Status: early development.** **M1–M4 work today** — record → transcribe → local SQLite + full-text search, a people-centric **bilingual (EN/中)** desktop app (Today · conversation · people · relationship graph · review), and on-demand AI readings that run **100% locally via Ollama (no API key)** and **cite the original audio** behind every judgment. Star the repo to follow along.

## Stop guessing where you stand

- What does your **boss** really think of you?
- Do the **people you lead** actually respect you?
- Is the **person you're seeing** into it — or just being polite?

You guess. Everyone guesses. Rapport means you don't have to.

It keeps the **real record** of what was actually said — so you can replay the facts, see the moment from the other side, and get a straight answer to the question you couldn't crack. **Not mind-reading; just the truth, kept.**

## What is Rapport?

Memory is fuzzy. After a conversation you keep an *impression* — and impressions drift: they fill in gaps, soften or sharpen, and quietly rewrite themselves over time.

Rapport keeps the **real record** instead. It records and transcribes your face-to-face conversations, organized around the **people** in your life, so you can go back to **what was actually said** — review it honestly, understand the other person, and see a moment from their side.

One idea underneath it all: **the truth of what happened beats whatever you happened to remember.**

## What makes it different

- **Always-on by design** — it keeps the *real* record, not just the moments you remembered to hit record.
- **Audio, not screen** — your real-world, face-to-face conversations. Smaller footprint, sharper purpose.
- **Organized around people, not time** — profiles, relationships, and perspective-switching, instead of an endless timeline.
- **100% local & open source** — the only kind of always-on recorder worth trusting: the data never leaves your machine, and the code is yours to read.

## Privacy: 5 promises you can verify in the code

1. **100% local by default** — audio and transcripts live in a SQLite file on your machine; nothing is uploaded.
2. **No account required.**
3. **Your data is yours** — export, delete, or back it up anytime. The database is just a file on your disk.
4. **Sync is optional and end-to-end encrypted** — leave it off and *zero bytes* leave your machine.
5. **Local AI optional** — run your questions through a local model (Ollama) so even the analysis stays on-device.

Because the code is open, you can read exactly what listens to you. That turns *"trust us"* into *"trust the code."*

> Rapport records real people. Recording-consent laws vary by region — everything stays on your device, but using it lawfully is on you.

## How it works

```
Record → local transcription → split & label speakers → encrypted local store
   → you ask a question → RAG retrieves the relevant bits → LLM answers → you
```

Rapport also exposes your data to the AI tools you already use, through a **local REST API + MCP server** — ask Claude Desktop *"remind me what I last talked about with Alex"* and it pulls from your local Rapport store. The data never leaves your machine.

## The bigger idea: a human-context layer for your AI

An AI becomes a *real* assistant not by talking well, but by two things: **knowing your real context**, and **being able to act on it**.

Rapport owns the most private, hardest-to-get slice of that context — **your real relationships and conversations with the people around you** — and hands it, safely and on-device, to the AI tools you already use. So Claude or Cursor stop being clever strangers and start giving answers that actually fit your situation with the people in your life.

Others built memory search for your *digital* life. **Rapport is the understanding layer for your *human* one.**

## Tech stack

Python · `faster-whisper` (local ASR) · `pyannote` (speaker diarization) · SQLite + FTS5 · pluggable LLM (local **Ollama** or your own API key) · FastAPI + MCP · React (Vite) SPA + system-tray desktop app (pystray, `rapport app`). **Windows first, macOS later.**

## Quick start

> **Prerequisites:** Python 3.10+ (3.12 recommended) · **Node.js 20+** (to build the web UI). Runs on **CPU by default — no GPU or CUDA required.** Windows first (macOS later).
>
> Windows users who just want to try it without setting up a toolchain can grab the packaged `RapportSetup.exe` installer (Start-menu + system tray; no Python / Node needed). To run from source, follow below.

### 1. Install

```bash
git clone https://github.com/sssst1118/Rapport.git
cd Rapport

python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -e .                       # or:  uv pip install -e .

# Build the web UI (serve / app both serve it — don't skip, or the UI is blank)
npm --prefix frontend install
npm --prefix frontend run build
```

### 2. Pick how to run it

```bash
rapport app        # [recommended, full experience] system-tray resident: local UI + continuous background recording, all in one
rapport serve      # web UI only → open http://127.0.0.1:8000
rapport watch      # background always-on recording daemon only (no window)
rapport mcp        # MCP server — expose your local data to Claude Desktop / Cursor (stdio)
```

> `rapport app` starts recording on launch (red tray dot = recording); use `rapport app --no-record` to start idle. It's a tray app with **no main window** — right-click the tray icon to pause / open the UI / quit.

### 3. Want to see it first? Load demo data (no microphone needed)

```bash
python seed_demo.py                                  # writes data/demo.db (leaves your rapport.db alone)
# Windows PowerShell:
$env:RAPPORT_DB_PATH="data/demo.db"; rapport serve
# macOS / Linux:
RAPPORT_DB_PATH=data/demo.db rapport serve
```

### 4. Configure the language model (enable AI readings · optional)

Works without it: the UI, recording, search and annotations all run — only the AI readings show "not configured." Configure one to unlock on-demand readings (M4), where **every reading separates fact from interpretation and cites the original quote + replayable audio.**

**Three ways to configure — pick the one that fits:**

| Method | Best for | How |
| --- | --- | --- |
| **① In-app Settings page** (gear icon in the top/side bar) | Packaged app (`.exe`), zero env vars | Open the UI → click the gear icon → fill in provider / model / API key → Save. Written to `%LOCALAPPDATA%\Rapport\config.json` and takes effect immediately. |
| **② Edit `%LOCALAPPDATA%\Rapport\config.json`** | Manual / scripted setup | Edit the JSON file directly; Rapport reads it on next launch. |
| **③ Environment variables** | CLI, automation, highest priority | See below — these override `config.json`. |

Priority: **environment variables > `config.json` > defaults.**

**A. Local Ollama (recommended · fully local, no API key, data never leaves the device)**

```bash
# 1) Install Ollama (https://ollama.com) and pull a chat model:
ollama pull qwen2.5:7b-instruct        # any chat model works; size it to your machine
# 2) Point Rapport at it via env vars (readings follow the UI language EN/中):
# Windows PowerShell:
$env:RAPPORT_LLM_PROVIDER="ollama"; $env:RAPPORT_LLM_MODEL="qwen2.5:7b-instruct"; rapport serve
# macOS / Linux:
RAPPORT_LLM_PROVIDER=ollama RAPPORT_LLM_MODEL=qwen2.5:7b-instruct rapport serve
```

**B. Bring your own API key (Anthropic)**

```bash
pip install -e ".[anthropic]"          # install the optional dependency
# Windows PowerShell:
$env:RAPPORT_LLM_PROVIDER="anthropic"; $env:ANTHROPIC_API_KEY="sk-ant-..."; $env:RAPPORT_LLM_MODEL="claude-opus-4-8"; rapport serve
# macOS / Linux:
RAPPORT_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... RAPPORT_LLM_MODEL=claude-opus-4-8 rapport serve
```

| Env var | Purpose | Values |
| --- | --- | --- |
| `RAPPORT_LLM_PROVIDER` | choose the LLM backend | `none` (default, no readings) · `ollama` · `anthropic` |
| `RAPPORT_LLM_MODEL` | model name | e.g. `qwen2.5:7b-instruct` / `claude-opus-4-8` |
| `ANTHROPIC_API_KEY` | your Anthropic key | only when `provider=anthropic` |

> Env vars override `config.json` and apply to both `rapport serve` and `rapport app`.

### CLI utilities

```bash
rapport transcribe path/to/audio.wav    # transcribe an audio file
rapport ingest audio.wav                # transcribe → store as a conversation
rapport show 1                          # print a conversation's lines
rapport search "project"                # full-text search across everything
rapport devices                         # list microphones (record --device N to pick one)
```

First transcription downloads a small Whisper model. Choose a model size or enable GPU via env vars:

```bash
RAPPORT_WHISPER_MODEL=small rapport transcribe audio.wav   # tiny | base | small | medium | large-v3
RAPPORT_WHISPER_DEVICE=cuda  rapport transcribe audio.wav   # GPU (needs CUDA runtime libs)
```

### Speaker diarization (multi-speaker, optional)

By default Rapport labels every line as speaker **`A`** (single-speaker placeholder). To
tell speakers apart (**`A` / `B` / `C` …**) within a recording, enable the optional
`pyannote` diarizer:

```bash
pip install -e ".[diarize]"   # installs pyannote.audio + torch (~GB)
```

Pyannote's pretrained models are gated on Hugging Face — accept the model license once and
provide a token:

```bash
RAPPORT_DIARIZER=pyannote HUGGINGFACE_TOKEN=hf_... rapport ingest audio.wav
```

| Variable | Purpose | Default |
| --- | --- | --- |
| `RAPPORT_DIARIZER` | `single` (placeholder, all `A`) or `pyannote` | `single` |
| `RAPPORT_PYANNOTE_MODEL` | model name or local checkpoint path (point to a downloaded checkpoint to run offline) | `pyannote/speaker-diarization-3.1` |
| `HUGGINGFACE_TOKEN` / `HF_TOKEN` | Hugging Face access token (accept the model license first) | — |

**Known limitation — labels are consistent only within one diarize call.** `A` / `B` / `C`
are stable across a single `rapport ingest <file>` (or one always-on batch), but **not**
across different recordings/days: pyannote independently emits `SPEAKER_xx` each run, so the
same person may be `B` today and `A` tomorrow. Recognizing the same person across
conversations requires voice-embedding (a later milestone) and is **not** done here. Use the
relabel-speaker feature to map labels to people per conversation.

### Known limitations (M5 packaging, current state)

- **In-app settings page is live**: click the gear icon (top/side bar) to configure the language model provider, model name, and API key directly in the UI — no env vars needed. Settings persist to `%LOCALAPPDATA%\Rapport\config.json`. Environment variables still work and take priority over the config file.
- **`rapport app` opens the UI automatically on launch**: your default browser opens `http://127.0.0.1:8000` at startup (pass `--no-open` to skip). Quit = right-click the tray icon → "Quit" (reliably terminates the process); if the icon is collapsed under "^", use `taskkill /F /IM Rapport.exe` as a fallback.
- First transcription downloads a Whisper model (needs network); the binary isn't code-signed, so SmartScreen may prompt on first run.

## Roadmap

- [x] **M1** — Record + local transcription + simple UI ✅
- [x] **M2** — Local SQLite storage + full-text search + ingest ✅ *(diarization seam ready; pyannote optional)*
- [ ] **Always-on capture** — continuous background recording (the real record, not just manual clips)
- [x] **M3** — People-centric desktop app + annotations ✅ *(FastAPI + React, bilingual EN/中: Today · conversation · people · relationship graph · review)*
- [x] **M4** — On-demand AI readings ✅ *(pluggable LLM — local **Ollama**, no API key, or bring your own; every reading separates fact from interpretation and **cites the original quote + audio**)*
- [x] **M5** — Human-context layer for your AI ✅
  - [x] **MCP server** ✅ — built on the official Python MCP SDK (FastMCP), stdio transport; exposes 7 read-only structured tools (`list_people` / `search_people` / `get_person` / `get_conversation` / `list_conversations` / `relationship_graph` / `search_utterances`); pure data, zero AI, zero API key; reuses the existing local DB layer, no web server required; every returned utterance carries a replayable citation (utterance_id + conversation_id + timestamp)
  - [x] **Always-on background recording** ✅ — `rapport watch` runs as a standalone daemon: continuously captures the microphone → splits on silence into utterances → transcribes → diarizes → stores; conversations are **bucketed by calendar day** (time-axis only, no semantic segmentation); audio is written to a rolling day-WAV with per-utterance byte offsets so every line is 🔊 replayable; `/api/status` honestly reflects recording/paused state (the frontend red dot is real); pause = capture fully stops (privacy-first — no hidden recording); all data stays on-device
  - [x] **Windows `.exe` packaging** ✅ — PyInstaller onedir build + NSIS installer (`RapportSetup.exe`); system-tray resident app (tray menu: start/pause recording, open UI, quit; icon color = always-visible recording indicator); single process orchestrates the local web UI (serve) + always-on recording Engine; frozen-mode user data lands in `%LOCALAPPDATA%\Rapport`; optional launch-at-startup (unchecked by default — privacy-respecting); uninstall preserves user data. *Note: Whisper model not bundled — first transcription downloads it on demand; binary not code-signed — SmartScreen may prompt on first run.*
- [ ] **M6** — Voiceprint ID · macOS

## License

[AGPL-3.0](./LICENSE) — free and open for everyone, forever. Its strong copyleft means no one can quietly close it up or "acquire it away."

**Commercial licenses available** — to use Rapport inside a closed-source / commercial product without AGPL obligations, contact the author at [@sssst1118](https://github.com/sssst1118).

## Star this repo ⭐

Rapport is in early development. If the idea resonates, **star the repo** to follow along — it genuinely helps.
