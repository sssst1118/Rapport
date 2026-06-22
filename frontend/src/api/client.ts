/*
 * API 客户端。所有后端调用都从这里走，统一指向 /api（开发时由 Vite proxy 转到 :8000）。
 * 设计要点：
 *   - 失败时抛 ApiError，调用方负责优雅降级（loading/空态），别白屏。
 *   - 仅做 JSON 序列化 + 错误归一化，不做缓存/状态管理（留给上层）。
 */

import type {
  Annotation,
  ConversationDetail,
  ConversationListItem,
  GraphData,
  Interpretation,
  OkResult,
  PersonCreated,
  PersonDetail,
  PersonListItem,
  PersonUtterance,
  RelabelResult,
  ReviewScope,
  Status,
} from './types'

const BASE = '/api'

/** 统一的 API 错误类型，带上 HTTP 状态码方便上层区分。 */
export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  signal?: AbortSignal
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal } = opts
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (e) {
    // 网络层失败（后端没起、断网等）
    throw new ApiError((e as Error)?.message ?? '网络请求失败', 0)
  }

  if (!res.ok) {
    let detail = `请求失败（${res.status}）`
    try {
      const data = await res.json()
      if (data && typeof data.detail === 'string') detail = data.detail
    } catch {
      /* 响应体非 JSON，沿用默认文案 */
    }
    throw new ApiError(detail, res.status)
  }

  // 204 / 空响应体的兜底
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** 拼出某段对话的音频流地址（供 <audio>/wavesurfer 直接用，支持 Range）。 */
export function audioUrl(conversationId: number | string): string {
  return `${BASE}/conversations/${conversationId}/audio`
}

/* —— 录制状态 —— */
export const getStatus = (signal?: AbortSignal) =>
  request<Status>('/status', { signal })

/* —— 人物 —— */
export const getPeople = (signal?: AbortSignal) =>
  request<PersonListItem[]>('/people', { signal })

export const createPerson = (input: { name: string; relation?: string }) =>
  request<PersonCreated>('/people', { method: 'POST', body: input })

export const getPerson = (id: number | string, signal?: AbortSignal) =>
  request<PersonDetail>(`/people/${id}`, { signal })

export const getPersonUtterances = (id: number | string, signal?: AbortSignal) =>
  request<PersonUtterance[]>(`/people/${id}/utterances`, { signal })

/* —— 对话 —— */
export const getConversations = (signal?: AbortSignal) =>
  request<ConversationListItem[]>('/conversations', { signal })

export const getConversation = (id: number | string, signal?: AbortSignal) =>
  request<ConversationDetail>(`/conversations/${id}`, { signal })

/* —— 编辑：转写文本 / 归属说话人 —— */
export const updateUtteranceText = (id: number | string, text: string) =>
  request<OkResult>(`/utterances/${id}`, { method: 'PATCH', body: { text } })

export const updateUtterancePerson = (
  id: number | string,
  personId: number | null,
) =>
  request<OkResult>(`/utterances/${id}/person`, {
    method: 'PATCH',
    body: { person_id: personId },
  })

/** 把整段对话里某个 speaker_label 一次性归到某人（或清空）。 */
export const relabelSpeaker = (
  conversationId: number | string,
  speakerLabel: string,
  personId: number | null,
) =>
  request<RelabelResult>(`/conversations/${conversationId}/relabel`, {
    method: 'POST',
    body: { speaker_label: speakerLabel, person_id: personId },
  })

/* —— 标注（标签 / 批注）—— */
export const addAnnotation = (
  utteranceId: number | string,
  type: 'tag' | 'note',
  value: string,
) =>
  request<Annotation>(`/utterances/${utteranceId}/annotations`, {
    method: 'POST',
    body: { type, value },
  })

export const deleteAnnotation = (id: number | string) =>
  request<OkResult>(`/annotations/${id}`, { method: 'DELETE' })

/** 当前界面语言：读 i18n 写入 localStorage 的 rapport-lang（回退浏览器语言/英文）。
 *  解读类请求据此带 ?lang=，让模型用与界面一致的语言产出解读。 */
function langParam(): string {
  try {
    const saved = localStorage.getItem('rapport-lang')
    if (saved === 'en' || saved === 'zh') return saved
  } catch {
    /* localStorage 不可用：回退到浏览器语言 */
  }
  return typeof navigator !== 'undefined' &&
    navigator.language?.startsWith('zh')
    ? 'zh'
    : 'en'
}

/* —— 解读层（解读输出语言跟随界面 ?lang=）—— */
export const getConversationSummary = (
  id: number | string,
  signal?: AbortSignal,
) =>
  request<Interpretation>(
    `/conversations/${id}/summary?lang=${langParam()}`,
    { signal },
  )

export const getPersonAnalysis = (id: number | string, signal?: AbortSignal) =>
  request<Interpretation>(`/people/${id}/analysis?lang=${langParam()}`, {
    signal,
  })

export const getPersonBrief = (id: number | string, signal?: AbortSignal) =>
  request<Interpretation>(`/people/${id}/brief?lang=${langParam()}`, { signal })

export const analyze = (utteranceIds: number[]) =>
  request<Interpretation>(`/analyze?lang=${langParam()}`, {
    method: 'POST',
    body: { utterance_ids: utteranceIds },
  })

/* —— 关系图（事实：共现推断的关系网络）—— */
export const getGraph = (signal?: AbortSignal) =>
  request<GraphData>('/graph', { signal })

/* —— 复盘（②你的视角/③对方视角/④接下来怎么做 = 解读，M4 占位）—— */
export const review = (scope: ReviewScope, id?: number) =>
  request<Interpretation>(`/review?lang=${langParam()}`, {
    method: 'POST',
    body: { scope, id },
  })
