/*
 * 今日视图的日期工具：把对话按「发生的那一天」聚合、推算相对日标题、聚合每日计数。
 *
 * 设计原则（与 §10.1 一致）：
 *   - 首页讲的是「今天你和谁说过话」，所以一切以「本地自然日」为单位，而非一锅时间流。
 *   - formatDateTime 只负责把 ISO 格式化成时间；「今天 / 昨天 / 更早」这类相对语义由这里自行推算。
 *   - 全程用本地时区（用户感知的「今天」），不碰 UTC。
 */

import type { ConversationListItem } from '../../api/types'

/** 把一个 Date 折叠成「当天 0 点」的本地时间戳，作为分组键。 */
function startOfLocalDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

/** ISO 串 -> 本地自然日的 0 点时间戳；非法时间返回 NaN。 */
export function dayKey(iso: string): number {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return NaN
  return startOfLocalDay(d)
}

/** 两个「当天 0 点」时间戳相差多少个自然日（a 比 b 早多少天，正数=更早）。 */
function diffDays(dayStart: number, base: number): number {
  return Math.round((base - dayStart) / 86_400_000)
}

/**
 * 把某天的 0 点时间戳渲染成组标题：今天 / 昨天 / 前天 / 周几（本周内）/ 具体日期。
 * 仅用 Date 推算，不依赖 formatDateTime。
 */
export function relativeDayLabel(dayStart: number, now: Date = new Date()): string {
  if (Number.isNaN(dayStart)) return '未知日期'
  const today = startOfLocalDay(now)
  const delta = diffDays(dayStart, today) // 0=今天, 1=昨天, ...
  if (delta === 0) return '今天'
  if (delta === 1) return '昨天'
  if (delta === 2) return '前天'

  const d = new Date(dayStart)
  // 本周内（3~6 天前）用「周几」，更亲切
  if (delta >= 3 && delta <= 6) {
    const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    return week[d.getDay()]
  }

  // 更早：同年只到「月日」，跨年带上年份
  const sameYear = d.getFullYear() === now.getFullYear()
  return d.toLocaleDateString('zh-CN', {
    year: sameYear ? undefined : 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

/** ISO -> 仅「时:分」（卡片上对话发生在几点）。失败时退回原串。 */
export function formatClock(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export interface DayGroup {
  /** 当天 0 点时间戳，作为稳定 key */
  key: number
  /** 相对日标题（今天 / 昨天 / …） */
  label: string
  /** 是否为「今天」——首页要把它排最前最醒目 */
  isToday: boolean
  /** 该天的对话，保持入参的「最近优先」顺序 */
  items: ConversationListItem[]
}

/**
 * 按自然日把对话分组。入参假定已「最近优先」（后端契约如此），
 * 因此天与天之间、天内条目都天然保持由新到旧。
 */
export function groupByDay(
  conversations: ConversationListItem[],
  now: Date = new Date(),
): DayGroup[] {
  const today = startOfLocalDay(now)
  const map = new Map<number, ConversationListItem[]>()
  // 用数组记录首次出现顺序 = 由新到旧
  const order: number[] = []

  for (const c of conversations) {
    const k = dayKey(c.started_at)
    if (!map.has(k)) {
      map.set(k, [])
      order.push(k)
    }
    map.get(k)!.push(c)
  }

  return order.map((k) => ({
    key: k,
    label: relativeDayLabel(k, now),
    isToday: k === today,
    items: map.get(k)!,
  }))
}

export interface HeatCell {
  /** 当天 0 点时间戳 */
  key: number
  /** 当天对话数 */
  count: number
  /** 该天的可读日期（tooltip 用） */
  label: string
  /** 是否未来（用于占位末尾，渲染成空格） */
  future: boolean
}

/**
 * 生成最近 weeks 周（含本周）的日历热力图数据，按「列=周、行=星期」排布。
 * 返回二维数组：columns[周][星期0..6]，每格是 HeatCell（未来日期标 future）。
 */
export function buildHeatmap(
  conversations: ConversationListItem[],
  weeks = 12,
  now: Date = new Date(),
): { columns: HeatCell[][]; maxCount: number } {
  // 先把对话聚合成「天 -> 计数」
  const counts = new Map<number, number>()
  for (const c of conversations) {
    const k = dayKey(c.started_at)
    if (Number.isNaN(k)) continue
    counts.set(k, (counts.get(k) ?? 0) + 1)
  }

  const today = startOfLocalDay(now)
  // 网格末列是「本周」，把右下角对齐到本周的周六，左上角回退 weeks 周
  const dow = new Date(today).getDay() // 0=周日 .. 6=周六
  const lastSaturday = today + (6 - dow) * 86_400_000
  const firstSunday = lastSaturday - (weeks * 7 - 1) * 86_400_000

  let maxCount = 0
  const columns: HeatCell[][] = []
  for (let w = 0; w < weeks; w++) {
    const col: HeatCell[] = []
    for (let d = 0; d < 7; d++) {
      const ts = firstSunday + (w * 7 + d) * 86_400_000
      const count = counts.get(ts) ?? 0
      if (count > maxCount) maxCount = count
      col.push({
        key: ts,
        count,
        label: new Date(ts).toLocaleDateString('zh-CN', {
          month: 'long',
          day: 'numeric',
        }),
        future: ts > today,
      })
    }
    columns.push(col)
  }

  return { columns, maxCount }
}
