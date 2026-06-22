# Rapport 前端

本地优先、以人为中心的「真实世界人际对话」助手的前端。视觉基准为设计系统《记录与旁批》(Margin & Record)。技术栈：Vite + React + TypeScript + Tailwind CSS v4 + react-router-dom + wavesurfer.js。

## 三件事

- **开发**：`npm install` 然后 `npm run dev`（默认 http://localhost:5173 ，被占用时自动顺延端口）。
- **构建**：`npm run build`，干净产出到 `frontend/dist`（由 Python 后端托管）。
- **代理**：开发时 `/api` 经 Vite proxy 转发到 `http://127.0.0.1:8000`（FastAPI 后端）。后端没起时，所有 API 调用会优雅降级到 loading/空态，不会白屏。

## 目录约定

- `src/styles/tokens.css` — 设计令牌（CSS 变量 + Tailwind v4 `@theme` 双向暴露）。
- `src/api/` — `types.ts`（契约类型）、`client.ts`（每个端点一个函数，指向 `/api`）。
- `src/lib/` — 工具：`personColor`（人即颜色）、`format`（时间码）、`useAsync`（三态数据 hook）。
- `src/components/` — 共享件：AppShell、RecordingStatus、WaveformMark、WaveformPlayer、PlayLine、Avatar、SpeakerStripe、InterpretationCard、Button、PageHeader、状态件等。
- `src/pages/` — 各屏占位页（今日 / 对话 / 人物列表 / 人物 / 关系图 / 样式手册）。
- `/styleguide` 路由集中陈列设计系统，便于核对。
