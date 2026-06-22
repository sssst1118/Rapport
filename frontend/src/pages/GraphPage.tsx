/*
 * 关系图 Graph（M3，产品方案 §10.5）—— 人际上下文层的可视落点。
 *
 * 把「同一段对话同时在场 → 推断彼此认识」的共现关系画成一张力导向网络：
 *   - 节点是人（personColor 实心圆 + 首字母），半径随说话量，「我」作 ego 锚更突出；
 *   - 连线是共现（粗细随 weight），低反差暖色，属事实层（不是模型脑补）；
 *   - 群组按 relation 粗分（家人 / 同事·工作 / 其他）做描边着色，拿不准退回 personColor；
 *   - 聚焦模式（防蜘蛛网）：点节点只看它 + 直接邻居，点空白 / 按返回键恢复全网。
 *
 * 数据走 getGraph()，loading/空/失败用统一状态件优雅降级；力仿真在子 hook 里建好、
 * 卸载时停掉；尊重 prefers-reduced-motion（静态出图，不做 tick 动画）。
 *
 * 文件所有权：本页与 pages/graph/** 是本次新增的全部代码。
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getGraph } from '../api/client'
import { PageHeader } from '../components/PageHeader'
import { EmptyState, ErrorState, LoadingBlock } from '../components/states'
import { useAsync } from '../lib/useAsync'
import { GraphCanvas } from './graph/GraphCanvas'
import { LEGEND_GROUPS, groupStyle } from './graph/groups'
import { useForceLayout } from './graph/useForceLayout'

/** 画布高度：固定一个舒展的值，宽度自适应容器。 */
const CANVAS_HEIGHT = 520

export function GraphPage() {
  const navigate = useNavigate()
  const { data, loading, error, reload } = useAsync((s) => getGraph(s), [])

  // 容器宽度（自适应）：用 ResizeObserver 量，喂给 SVG viewBox 与力中心。
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)

  // 依赖 data：容器只在数据到位（else 分支）后才挂载，effect 必须在那时重跑才能
  // 量到真实宽度——否则首次渲染时容器还是 null，width 永远停在 0、画布画不出来。
  useLayoutEffect(() => {
    const el = containerRef.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth)
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [data])

  // 力导向布局（坐标写进节点对象，version 驱动重渲）。
  const { nodes, edges, version } = useForceLayout(data, width, CANVAS_HEIGHT)

  // 聚焦节点（防蜘蛛网）+ hover 提示。
  const [focusId, setFocusId] = useState<number | null>(null)
  const [hoverId, setHoverId] = useState<number | null>(null)

  // 数据变更 / 重载后清空聚焦，回到全网。
  useEffect(() => {
    setFocusId(null)
  }, [data])

  // 返回键 / ESC：先退出聚焦，再交还给浏览器历史。
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && focusId != null) {
        setFocusId(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [focusId])

  // 点节点：未聚焦 → 进入聚焦；已聚焦该节点 → 进人物页；聚焦别的 → 切换聚焦。
  const handleNodeClick = useCallback(
    (id: number) => {
      if (focusId === id) {
        navigate(`/people/${id}`)
      } else {
        setFocusId(id)
      }
    },
    [focusId, navigate],
  )

  const handleBackground = useCallback(() => {
    if (focusId != null) setFocusId(null)
  }, [focusId])

  // —— 三态优雅降级 ——
  let body: React.ReactNode
  if (loading) {
    body = <LoadingBlock label="正在加载关系网络…" />
  } else if (error) {
    body = (
      <ErrorState
        message="关系图加载失败，请稍后再试。"
        onRetry={reload}
      />
    )
  } else if (!data || data.nodes.length === 0) {
    body = (
      <EmptyState
        title="还没有可画的关系"
        hint="多录几段有他人在场的对话，这里就会长出一张网。"
      />
    )
  } else {
    body = (
      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-card border border-line bg-card"
      >
        {width > 0 && (
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            width={width}
            height={CANVAS_HEIGHT}
            focusId={focusId}
            hoverId={hoverId}
            onHover={setHoverId}
            onNodeClick={handleNodeClick}
            onBackground={handleBackground}
            version={version}
          />
        )}

        {/* 聚焦时的返回提示条 */}
        {focusId != null && (
          <button
            type="button"
            onClick={() => setFocusId(null)}
            className="absolute left-3 top-3 rounded-sm border border-line bg-paper/90 px-3 py-1.5 font-ui text-sm text-ink-soft backdrop-blur hover:text-pine"
          >
            ← 返回全网
          </button>
        )}

        {/* 群组图例 */}
        <div className="pointer-events-none absolute bottom-3 right-3 flex flex-col gap-1.5 rounded-sm border border-line bg-paper/85 px-3 py-2 backdrop-blur">
          {LEGEND_GROUPS.map((g) => {
            const s = groupStyle(g)
            return (
              <span
                key={g}
                className="flex items-center gap-2 font-ui text-xs text-ink-soft"
              >
                <span
                  aria-hidden
                  className="inline-block h-2.5 w-2.5 rounded-full border-2"
                  style={{ borderColor: s.stroke, background: 'transparent' }}
                />
                {s.label}
              </span>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <section>
      <PageHeader
        title="关系图"
        description="谁和谁在同一段对话里出现过，就连一条线 —— 这是你身边人际结构的事实快照。点一个人只看他的圈子，点空白返回全网。"
      />
      {body}
    </section>
  )
}
