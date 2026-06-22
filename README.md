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

> 🚧 **Status: early development / design stage.** The design is settled (architecture, privacy model, roadmap); the code is just getting started. Star the repo to follow along.

## What is Rapport?

So much daily stress comes from *rumination* after talking to people — *what did they mean by that? did I say the wrong thing?* Memory is fuzzy, so we fill the gaps with worry, and the worry feeds itself.

Rapport gives that an exit. It quietly records and transcribes your **face-to-face conversations**, organizes everything around the **people** in your life, and — **only when you ask** — helps you replay the facts, understand the other person, switch perspective, and let it go.

It's a tool to help you **think more clearly, so you ruminate less.** A companion, not a watchdog.

## Why Rapport?

|  | Rapport | Limitless / Rewind | screenpipe |
|---|---|---|---|
| Captures | **Audio only** (smaller privacy surface) | Screen + audio + wearable | Screen + audio |
| Organized around | **People** | Time | Time |
| Data lives | **100% local by default** | Cloud | Local |
| Open source | **Yes — AGPL-3.0, can't be acquired away** | Closed (acquired by Meta, 2025) | Source-available |
| Works | **On demand — never interrupts** | 24/7 capture | 24/7 capture |
| Hardware | **Your existing mic** | $99 pendant | — |

Rapport is the **open alternative to Limitless / Granola** — but audio-only and person-centric.

## Privacy: 5 promises you can verify in the code

1. **100% local by default** — audio and transcripts live in a SQLite file on your machine; nothing is uploaded.
2. **No account required.**
3. **Your data is yours** — export, delete, or back it up anytime. The database is just a file on your disk.
4. **Sync is optional and end-to-end encrypted** — leave it off and *zero bytes* leave your machine.
5. **Local AI optional** — run your questions through a local model (Ollama) so even the analysis stays on-device.

Because the code is open, you can read exactly what listens to you. That turns *"trust us"* into *"trust the code."*

## How it works

```
Record → local transcription → split & label speakers → encrypted local store
   → you ask a question → RAG retrieves the relevant bits → LLM answers → you
```

Rapport also exposes your data to the AI tools you already use, through a **local REST API + MCP server** — ask Claude Desktop *"remind me what I last talked about with Alex"* and it pulls from your local Rapport store. The data never leaves your machine.

## Tech stack

Python · `faster-whisper` (local ASR) · `pyannote` (speaker diarization) · SQLite + FTS5 · pluggable LLM (local **Ollama** or your own API key) · FastAPI + MCP · Gradio → PyWebview desktop shell. **Windows first, macOS later.**

## Roadmap

- [ ] **M1** — Record + local transcription + simple UI
- [ ] **M2** — Speaker diarization + local storage
- [ ] **M3** — People-centric views + annotations
- [ ] **M4** — On-demand Q&A (RAG)
- [ ] **M5** — Local REST API + MCP server + Windows packaging
- [ ] **M6** — Relationship graph · voiceprint ID · local LLM · macOS

## License

[AGPL-3.0](./LICENSE) — free and open for everyone, forever. Its strong copyleft means no one can quietly close it up or "acquire it away."

**Commercial licenses available** — to use Rapport inside a closed-source / commercial product without AGPL obligations, contact the author at [@sssst1118](https://github.com/sssst1118).

## Star this repo ⭐

Rapport is in early development. If the idea resonates, **star the repo** to follow along — it genuinely helps.
