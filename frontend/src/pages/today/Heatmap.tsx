/*
 * 日历热力图 —— 最近约 12 周，每个自然日一格，按当天对话数着色（pine 的深浅）。
 *
 * 纯 CSS grid + 内联 color-mix，无第三方库。
 * 颜色思路：从「信笺底」(paper) 到 pine 之间按强度插值，
 *   空数据是一格极浅描边的空格，越密越接近实心 pine —— 与品牌「真相锚」同色。
 * 紧凑一条放页顶，未来日期渲染成幽灵格（不参与计数、低存在感）。
 */

import type { HeatCell } from './dateUtils'
import { buildHeatmap } from './dateUtils'
import type { ConversationListItem } from '../../api/types'

interface HeatmapProps {
  conversations: ConversationListItem[]
  weeks?: number
}

/** 把「计数/最大值」映射成一段 pine 着色（0=空格底；>0 在 paper..pine 间插值）。 */
function cellStyle(cell: HeatCell, maxCount: number): React.CSSProperties {
  if (cell.future) {
    // 未来日期：几乎隐形的幽灵格，仅留极淡描边，保持网格完整
    return { backgroundColor: 'transparent', opacity: 0.25 }
  }
  if (cell.count === 0) {
    // 有记录的日子之外的空白：极浅的同底色块
    return { backgroundColor: 'color-mix(in srgb, var(--pine) 6%, var(--card))' }
  }
  // 1..max 映射到 28%..100% 的 pine 浓度，保证「有一条就看得见」
  const t = maxCount <= 1 ? 1 : cell.count / maxCount
  const pct = Math.round(28 + t * 72)
  return { backgroundColor: `color-mix(in srgb, var(--pine) ${pct}%, var(--card))` }
}

// 星期标签（只显式标 周一/周三/周五，避免拥挤）
const WEEKDAY_MARKS: Record<number, string> = { 1: '一', 3: '三', 5: '五' }

export function Heatmap({ conversations, weeks = 12 }: HeatmapProps) {
  const { columns, maxCount } = buildHeatmap(conversations, weeks)
  const hasAny = maxCount > 0

  return (
    <div className="rounded-card border border-line bg-card/60 px-4 py-3.5">
      <div className="mb-2.5 flex items-baseline justify-between gap-3">
        <span className="font-ui text-xs font-medium text-ink-soft">
          最近 {weeks} 周
        </span>
        <span className="font-ui text-xs text-ink-soft">
          {hasAny ? '颜色越深，那天对话越多' : '还没有记录，开始录音后这里会亮起来'}
        </span>
      </div>

      <div className="flex gap-1.5">
        {/* 左侧星期轴：与右边 7 行对齐 */}
        <div
          className="grid shrink-0 gap-[3px] pr-0.5"
          style={{ gridTemplateRows: 'repeat(7, 1fr)' }}
          aria-hidden="true"
        >
          {Array.from({ length: 7 }, (_, d) => (
            <span
              key={d}
              className="flex h-3 items-center font-mono text-[9px] leading-none text-ink-soft/70"
            >
              {WEEKDAY_MARKS[d] ?? ''}
            </span>
          ))}
        </div>

        {/* 周列：横向滚动兜底，窄屏不挤压 */}
        <div className="flex gap-[3px] overflow-x-auto">
          {columns.map((col, ci) => (
            <div key={ci} className="grid gap-[3px]" style={{ gridTemplateRows: 'repeat(7, 1fr)' }}>
              {col.map((cell) => (
                <div
                  key={cell.key}
                  title={
                    cell.future
                      ? undefined
                      : `${cell.label} · ${cell.count} 段对话`
                  }
                  style={cellStyle(cell, maxCount)}
                  className="h-3 w-3 rounded-[3px] ring-1 ring-inset ring-line/40"
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
