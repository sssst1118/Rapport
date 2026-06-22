/*
 * 今日视图的日期工具：把对话按「发生的那一天」聚合、推算相对日标题、聚合每日计数。
 *
 * 设计原则（与 §10.1 一致）：
 *   - 首页讲的是「今天你和谁说过话」，所以一切以「本地自然日」为单位，而非一锅时间流。
 *   - formatDateTime 只负责把 ISO 格式化成时间；「今天 / 昨天 / 更早」这类相对语义由这里自行推算。
 *   - 全程用本地时区（用户感知的「今天」），不碰 UTC。
 */

import type { TFunction } from 'i18next'
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
 * 相对日标题的「语义描述」——纯数据，不含文案。
 * 由调用方（拿得到 t() 与当前语言）翻译成最终字符串，工具层保持无 i18n 依赖。
 *   - kind=unknown/today/yesterday/beforeYesterday：直接对应一条 i18n key
 *   - kind=weekday：本周内，day=0..6（周日..周六），调用方查 relativeDay.weekday.<day>
 *   - kind=date：更早，调用方用 Intl 按当前 locale 格式化；sameYear 决定是否带年份
 */
export type RelativeDay =
  | { kind: 'unknown' }
  | { kind: 'today' }
  | { kind: 'yesterday' }
  | { kind: 'beforeYesterday' }
  | { kind: 'weekday'; day: number }
  | { kind: 'date'; timestamp: number; sameYear: boolean }

/**
 * 把某天的 0 点时间戳归类成相对日语义：今天 / 昨天 / 前天 / 周几（本周内）/ 具体日期。
 * 仅用 Date 推算，不依赖 formatDateTime，也不产出可见文案（交给调用方 i18n）。
 */
export function relativeDay(dayStart: number, now: Date = new Date()): RelativeDay {
  if (Number.isNaN(dayStart)) return { kind: 'unknown' }
  const today = startOfLocalDay(now)
  const delta = diffDays(dayStart, today) // 0=今天, 1=昨天, ...
  if (delta === 0) return { kind: 'today' }
  if (delta === 1) return { kind: 'yesterday' }
  if (delta === 2) return { kind: 'beforeYesterday' }

  const d = new Date(dayStart)
  // 本周内（3~6 天前）用「周几」，更亲切
  if (delta >= 3 && delta <= 6) {
    return { kind: 'weekday', day: d.getDay() }
  }

  // 更早：同年只到「月日」，跨年带上年份
  return {
    kind: 'date',
    timestamp: dayStart,
    sameYear: d.getFullYear() === now.getFullYear(),
  }
}

/** ISO -> 仅「时:分」（卡片上对话发生在几点）。按 locale 本地化；失败时退回原串。 */
export function formatClock(iso: string, locale?: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
}

export interface DayGroup {
  /** 当天 0 点时间戳，作为稳定 key */
  key: number
  /** 相对日语义（今天 / 昨天 / …）—— 文案由调用方按 i18n 翻译 */
  relative: RelativeDay
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
    relative: relativeDay(k, now),
    isToday: k === today,
    items: map.get(k)!,
  }))
}

export interface HeatCell {
  /** 当天 0 点时间戳（既是稳定 key，也供 tooltip 按 locale 格式化日期） */
  key: number
  /** 当天对话数 */
  count: number
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
        future: ts > today,
      })
    }
    columns.push(col)
  }

  return { columns, maxCount }
}

/** i18n 语言码 -> Intl 可用的 BCP-47 locale（zh -> zh-CN，其余原样）。 */
function intlLocale(lang: string): string {
  return lang.startsWith('zh') ? 'zh-CN' : lang
}

/** 把时间戳按当前语言格式化成「月日」（withYear 时带年份），用于更早日期 / 热力图 tooltip。 */
export function formatCalendarDate(
  timestamp: number,
  lang: string,
  withYear = false,
): string {
  return new Date(timestamp).toLocaleDateString(intlLocale(lang), {
    year: withYear ? 'numeric' : undefined,
    month: 'long',
    day: 'numeric',
  })
}

/**
 * 把 relativeDay() 的语义结果翻成可见标题。
 * 接收页面的 t（命名空间 today）与当前语言：weekday 查表、date 按 locale 格式化。
 */
export function relativeDayLabel(
  rel: RelativeDay,
  t: TFunction<'today'>,
  lang: string,
): string {
  switch (rel.kind) {
    case 'unknown':
      return t('relativeDay.unknown')
    case 'today':
      return t('relativeDay.today')
    case 'yesterday':
      return t('relativeDay.yesterday')
    case 'beforeYesterday':
      return t('relativeDay.beforeYesterday')
    case 'weekday':
      return t(`relativeDay.weekday.${rel.day}` as const)
    case 'date':
      return formatCalendarDate(rel.timestamp, lang, !rel.sameYear)
  }
}
