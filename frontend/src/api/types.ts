/*
 * API 契约的 TypeScript 类型。
 * 与后端（跑在 :8000）同一份契约并行实现；改契约时两边同步改。
 * 注意：本仓库开启了 verbatimModuleSyntax，引用这些类型时请用 `import type`。
 */

/** GET /api/status */
export interface Status {
  recording: boolean
  paused: boolean
}

/** 参与者的最小引用（出现在对话列表/详情里） */
export interface ParticipantRef {
  id: number
  name: string
}

/** GET /api/people 列表项 */
export interface PersonListItem {
  id: number
  name: string
  avatar: string | null
  relation: string | null
  utterance_count: number
}

/** POST /api/people 的返回 */
export interface PersonCreated {
  id: number
  name: string
  relation: string | null
  avatar: string | null
}

/** GET /api/people/:id 详情 */
export interface PersonDetail {
  id: number
  name: string
  avatar: string | null
  relation: string | null
  created_at: string
  updated_at: string
  conversation_count: number
  utterance_count: number
}

/** GET /api/people/:id/utterances 列表项（某人说过的话，跨对话） */
export interface PersonUtterance {
  id: number
  conversation_id: number
  conversation_note: string | null
  started_at: string
  speaker_label: string
  text: string
  start_ms: number
  end_ms: number
}

/** GET /api/conversations 列表项 */
export interface ConversationListItem {
  id: number
  started_at: string
  note: string | null
  has_audio: boolean
  utterance_count: number
  participants: ParticipantRef[]
}

/** 一句话上的标注（标签或批注） */
export interface Annotation {
  id: number
  type: 'tag' | 'note'
  value: string
}

/** 对话详情里的一句话 */
export interface Utterance {
  id: number
  person_id: number | null
  speaker_label: string
  text: string
  start_ms: number
  end_ms: number
  annotations: Annotation[]
}

/** GET /api/conversations/:id 详情 */
export interface ConversationDetail {
  id: number
  started_at: string
  note: string | null
  has_audio: boolean
  participants: ParticipantRef[]
  speakers: string[]
  utterances: Utterance[]
}

/**
 * 原话出处（一条解读所依据的真实话语）—— 事实锚，点击可回放原声。
 * 由后端把 LLM 引用的 utterance_id 解析成完整引语，前端无需再查。
 */
export interface Citation {
  utterance_id: number
  conversation_id: number
  text: string
  start_ms: number
  end_ms: number
  speaker_label: string
  person_name: string | null
}

/** 一条解读：一个判断 + 它所依据的原话（可为空，但应尽量挂出处）。 */
export interface Finding {
  /** 解读判断本身（AI 的「读」，非事实） */
  point: string
  /** 依据的原话出处（点击回放原声） */
  quotes: Citation[]
}

/**
 * 解读层信封 —— 解读卡（页边旁批）的统一渲染契约。事实与解读分离的数据落点：
 * 事实端点直接返回数据；解读端点返回本信封，每条判断都挂着真实原话出处。
 *
 * status：
 *   - ready       已生成解读，data.findings 有内容（每条挂 quotes 原话）
 *   - needs_setup 未配置 LLM（没设 ANTHROPIC_API_KEY 等）——诚实告知，不编造
 *   - pending     正在生成（占位/加载，可选用）
 *   - error       生成失败（message 说明），不抛 500
 */
export interface Interpretation {
  kind: 'interpretation'
  status: 'ready' | 'needs_setup' | 'pending' | 'error'
  message: string
  data: { findings: Finding[]; overview?: string } | null
}

/** PATCH 类端点的通用确认 */
export interface OkResult {
  ok: true
}

/** POST /api/conversations/:id/relabel 的返回 */
export interface RelabelResult {
  updated: number
}

/** GET /api/graph 的节点（一个人） */
export interface GraphNode {
  id: number
  name: string
  relation: string | null
  utterance_count: number
  conversation_count: number
}

/** GET /api/graph 的连线（两人共同在场推断的关系） */
export interface GraphEdge {
  source: number
  target: number
  /** 共同在场的对话数，越大关系越近/越新 */
  weight: number
}

/** GET /api/graph 关系网络 */
export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

/** 复盘范围：一段对话 / 一个人 / 某一天 */
export type ReviewScope = 'conversation' | 'person' | 'day'
