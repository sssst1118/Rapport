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

> 🚧 **Status: early development.** **M1–M2 work today** — record → transcribe → store in a local SQLite DB → full-text search. Building outward (see the roadmap). Star the repo to follow along.

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

Python · `faster-whisper` (local ASR) · `pyannote` (speaker diarization) · SQLite + FTS5 · pluggable LLM (local **Ollama** or your own API key) · FastAPI + MCP · Gradio → PyWebview desktop shell. **Windows first, macOS later.**

## Quick start

> **Python 3.10+** (3.12 recommended for the widest prebuilt-wheel coverage). Runs on **CPU by default — no GPU or CUDA required.**

```bash
git clone https://github.com/sssst1118/Rapport.git
cd Rapport
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -e .            # or:  uv pip install -e .

rapport transcribe path/to/audio.wav    # transcribe an audio file
rapport ui                              # or launch the web UI
```

First run downloads a small Whisper model. Choose a model size or enable GPU via env vars:

```bash
RAPPORT_WHISPER_MODEL=small rapport transcribe audio.wav   # tiny | base | small | medium | large-v3
RAPPORT_WHISPER_DEVICE=cuda  rapport transcribe audio.wav   # GPU (needs CUDA runtime libs)
```

Store a recording in your local database, then browse and search it:

```bash
rapport ingest audio.wav   # transcribe → store as a conversation
rapport show 1             # print a conversation's lines
rapport search "project"   # full-text search across everything
rapport devices            # list microphones (record --device N to pick one)
```

## Roadmap

- [x] **M1** — Record + local transcription + simple UI ✅
- [x] **M2** — Local SQLite storage + full-text search + ingest ✅ *(diarization seam ready; pyannote optional)*
- [ ] **Always-on capture** — continuous background recording (the real record, not just manual clips)
- [ ] **M3** — People-centric views + annotations
- [ ] **M4** — On-demand Q&A (RAG)
- [ ] **M5** — Local REST API + MCP server + Windows packaging
- [ ] **M6** — Relationship graph · voiceprint ID · local LLM · macOS

## License

[AGPL-3.0](./LICENSE) — free and open for everyone, forever. Its strong copyleft means no one can quietly close it up or "acquire it away."

**Commercial licenses available** — to use Rapport inside a closed-source / commercial product without AGPL obligations, contact the author at [@sssst1118](https://github.com/sssst1118).

## Star this repo ⭐

Rapport is in early development. If the idea resonates, **star the repo** to follow along — it genuinely helps.
