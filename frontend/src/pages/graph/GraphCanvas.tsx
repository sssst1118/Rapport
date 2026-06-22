/*
 * GraphCanvas —— 自定义 SVG 渲染层。不用图表库，手画圆与线，保持《记录与旁批》观感。
 *
 * 职责：
 *   - 画连线（粗细随 weight，低反差暖色 --line / pine）。
 *   - 画节点（personColor 实心圆 + 首字母；半径随说话量；ego 更大更突出 + 群组描边）。
 *   - 聚焦模式（§10.5 防蜘蛛网）：focusId 非空时只亮「它 + 直接邻居」的 ego 子图，
 *     其余淡出（仍在 DOM，平滑过渡）。
 *   - 点节点 → onNodeClick(id)；点空白 → onBackground()。
 *
 * 坐标由 useForceLayout 写进每个 SimNode 的 x/y；本组件只读不算。
 */

import { useMemo } from 'react'
import { personColor } from '../../lib/personColor'
import { groupStyle } from './groups'
import { endpointId } from './layout'
import type { SimEdge, SimNode } from './types'

export interface GraphCanvasProps {
  nodes: SimNode[]
  edges: SimEdge[]
  width: number
  height: number
  /** 当前聚焦的节点 id；null = 全网 */
  focusId: number | null
  /** 用于 hover/选中态的轻提示 */
  hoverId: number | null
  onHover: (id: number | null) => void
  onNodeClick: (id: number) => void
  onBackground: () => void
  /** 坐标版本号，变了就重渲（坐标在可变对象里，需显式依赖） */
  version: number
}

export function GraphCanvas({
  nodes,
  edges,
  width,
  height,
  focusId,
  hoverId,
  onHover,
  onNodeClick,
  onBackground,
  version,
}: GraphCanvasProps) {
  // 聚焦子图：focus 节点 + 其直接邻居的 id 集合。focusId 为空则全亮。
  const visibleIds = useMemo<Set<number> | null>(() => {
    if (focusId == null) return null
    const set = new Set<number>([focusId])
    for (const e of edges) {
      const s = endpointId(e.source)
      const t = endpointId(e.target)
      if (s === focusId) set.add(t)
      if (t === focusId) set.add(s)
    }
    return set
    // version 进依赖只是为了与坐标更新同步（其实 edges 引用稳定时不必，但无害且明确）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusId, edges, version])

  const isDim = (id: number): boolean =>
    visibleIds != null && !visibleIds.has(id)

  // 边可见：两端都在子图里（聚焦时），否则全可见。
  const edgeVisible = (e: SimEdge): boolean => {
    if (!visibleIds) return true
    return visibleIds.has(endpointId(e.source)) && visibleIds.has(endpointId(e.target))
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label="关系网络图"
      className="block touch-none select-none"
      onClick={onBackground}
    >
      {/* —— 连线层 —— */}
      <g stroke="var(--line)" fill="none">
        {edges.map((e) => {
          const s = e.source as SimNode
          const t = e.target as SimNode
          if (s?.x == null || s?.y == null || t?.x == null || t?.y == null)
            return null
          const visible = edgeVisible(e)
          // 聚焦时，连到 focus 的边用 pine 提一档反差。
          const touchesFocus =
            focusId != null &&
            (endpointId(e.source) === focusId || endpointId(e.target) === focusId)
          return (
            <line
              key={`${endpointId(e.source)}-${endpointId(e.target)}`}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke={touchesFocus ? 'var(--pine-soft)' : 'var(--line)'}
              strokeWidth={1 + Math.min(e.weight, 5) * 1.1}
              strokeLinecap="round"
              opacity={visible ? 0.75 : 0.08}
              style={{ transition: 'opacity 240ms ease' }}
            />
          )
        })}
      </g>

      {/* —— 节点层 —— */}
      <g>
        {nodes.map((n) => {
          if (n.x == null || n.y == null) return null
          const { block, ink } = personColor(n.id)
          const dim = isDim(n.id)
          const hovered = hoverId === n.id
          const stroke = groupStyle(n.group).stroke
          // ego 与 hover 给更明显的描边；其余群组色细描边。
          const strokeWidth = n.isEgo ? 3 : hovered ? 2.5 : 1.5
          const r = n.radius

          return (
            <g
              key={n.id}
              transform={`translate(${n.x} ${n.y})`}
              opacity={dim ? 0.18 : 1}
              style={{
                transition: 'opacity 240ms ease',
                cursor: 'pointer',
              }}
              onMouseEnter={() => onHover(n.id)}
              onMouseLeave={() => onHover(null)}
              onClick={(ev) => {
                ev.stopPropagation()
                onNodeClick(n.id)
              }}
              role="button"
              aria-label={`${n.name}${n.relation ? `（${n.relation}）` : ''}`}
              tabIndex={dim ? -1 : 0}
              onKeyDown={(ev) => {
                if (ev.key === 'Enter' || ev.key === ' ') {
                  ev.preventDefault()
                  onNodeClick(n.id)
                }
              }}
            >
              {/* hover 光晕 */}
              {hovered && !dim && (
                <circle r={r + 6} fill={block} opacity={0.16} />
              )}
              <circle
                r={r}
                fill={block}
                stroke={stroke}
                strokeWidth={strokeWidth}
              />
              {/* 首字母 */}
              <text
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={Math.round(r * 0.82)}
                fill={ink}
                className="font-ui"
                fontWeight={500}
                style={{ pointerEvents: 'none' }}
              >
                {n.initial}
              </text>
              {/* 名字标签（聚焦或 hover 时显示，避免全网拥挤） */}
              {(focusId != null || hovered) && !dim && (
                <text
                  y={r + 14}
                  textAnchor="middle"
                  fontSize={12}
                  fill="var(--ink)"
                  className="font-record"
                  style={{ pointerEvents: 'none' }}
                >
                  {n.name}
                </text>
              )}
            </g>
          )
        })}
      </g>
    </svg>
  )
}
