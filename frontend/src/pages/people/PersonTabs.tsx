/*
 * PersonTabs —— 人物详情页的 Tab 切换条（界面体 chrome）。
 *
 * 三个 Tab：对话历史（事实）/ 人物分析（解读·M4）/ 你和TA的关系（解读·M4）。
 * 解读类 Tab 带一个极克制的 iris 小点 + 「M4」微标，暗示「此处由 M4 填」，
 * 不伪造任何内容；事实 Tab 不带标记，与解读一眼区分。
 *
 * 无障碍：role=tablist/tab，方向键左右切换，aria-selected 同步。
 */

import { useRef } from 'react'

export interface PersonTab {
  key: string
  label: string
  /** 该 Tab 是否属于解读层（M4）—— 决定是否渲染 iris 小点 + M4 微标 */
  interpretation?: boolean
}

export interface PersonTabsProps {
  tabs: PersonTab[]
  active: string
  onChange: (key: string) => void
}

export function PersonTabs({ tabs, active, onChange }: PersonTabsProps) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})

  function onKeyDown(e: React.KeyboardEvent, idx: number) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    e.preventDefault()
    const dir = e.key === 'ArrowRight' ? 1 : -1
    const next = (idx + dir + tabs.length) % tabs.length
    const key = tabs[next].key
    onChange(key)
    refs.current[key]?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label="人物视图"
      className="mb-5 flex gap-1 border-b border-line"
    >
      {tabs.map((t, idx) => {
        const selected = t.key === active
        return (
          <button
            key={t.key}
            ref={(el) => {
              refs.current[t.key] = el
            }}
            role="tab"
            type="button"
            id={`person-tab-${t.key}`}
            aria-selected={selected}
            aria-controls={`person-panel-${t.key}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.key)}
            onKeyDown={(e) => onKeyDown(e, idx)}
            className={`relative -mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 font-ui text-sm font-medium transition-colors ${
              selected
                ? 'border-pine text-ink'
                : 'border-transparent text-ink-soft hover:text-ink'
            }`}
          >
            {t.label}
            {t.interpretation && (
              <>
                {/* 极克制的 iris 小点：暗示该 Tab 是解读层，将由 M4 填 */}
                <span
                  aria-hidden="true"
                  className="size-1.5 rounded-full bg-iris/70"
                />
                <span className="rounded-sm bg-iris/12 px-1 py-px font-mono text-[9px] font-medium uppercase tracking-wide text-iris">
                  M4
                </span>
              </>
            )}
          </button>
        )
      })}
    </div>
  )
}
