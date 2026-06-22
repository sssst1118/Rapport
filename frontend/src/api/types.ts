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
 * 解读层信封 —— 解读卡（页边旁批）的统一渲染契约。
 * M4 才会真正产出内容，眼下一律是 pending_m4 占位。
 */
export interface Interpretation {
  kind: 'interpretation'
  status: 'pending_m4'
  message: string
  data: null
}

/** PATCH 类端点的通用确认 */
export interface OkResult {
  ok: true
}

/** POST /api/conversations/:id/relabel 的返回 */
export interface RelabelResult {
  updated: number
}
