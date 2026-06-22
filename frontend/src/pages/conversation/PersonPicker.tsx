/*
 * PersonPicker —— 可复用的「选人」浮层。
 *
 * 用在两处「事实层」交互：
 *   1) 给某一行单独改说话人（updateUtterancePerson）
 *   2) 把某说话人整段一次性映射到真人（relabelSpeaker）—— §9.1 / §10.7 的头条交互
 *
 * 自身只负责「列出人 + 搜索 + 新建人物 + 抛出选择」，不直接写库：
 * 选定/新建后把 personId 通过 onPick 交回父组件，由父决定调哪个端点、何时 reload()。
 * 这样同一个浮层既能服务「改一行」也能服务「整段映射」。
 *
 * 纯原生实现（不引依赖）：一个绝对定位的小面板 + Esc/点外关闭 + 键盘可达。
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { getPeople, createPerson } from '../../api/client'
import type { PersonListItem } from '../../api/types'
import { useAsync } from '../../lib/useAsync'
import { Avatar } from '../../components/Avatar'

export interface PersonPickerProps {
  /** 关闭浮层（点外、Esc、选定后都会调用） */
  onClose: () => void
  /**
   * 选定一个人（已存在或刚新建）。personId 为 null 表示「清除归属 / 设为未知」。
   * 父组件据此调用 updateUtterancePerson 或 relabelSpeaker，并自行 reload()。
   * 返回 Promise 时浮层会显示忙碌态直到落库完成。
   */
  onPick: (personId: number | null) => void | Promise<void>
  /** 当前已归属的人物 id（高亮显示），未归属传 null */
  currentPersonId?: number | null
  /** 标题，例如「这一行是谁说的？」或「把 A 映射到…」 */
  title?: string
  /** 是否显示「设为未知 / 清除归属」项，默认 false */
  allowClear?: boolean
}

export function PersonPicker({
  onClose,
  onPick,
  currentPersonId = null,
  title = '归属到谁？',
  allowClear = false,
}: PersonPickerProps) {
  const people = useAsync((s) => getPeople(s), [])
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [createErr, setCreateErr] = useState<string | null>(null)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  // 打开即聚焦搜索框，键盘用户可立刻输入
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // 点浮层外 / 按 Esc 关闭
  useEffect(() => {
    function onDocPointer(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    document.addEventListener('mousedown', onDocPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  const q = query.trim().toLowerCase()
  const filtered = useMemo(() => {
    const list = people.data ?? []
    if (!q) return list
    return list.filter((p) => p.name.toLowerCase().includes(q))
  }, [people.data, q])

  // 搜索词没命中任何已存在的人 -> 允许一键新建
  const exactExists = (people.data ?? []).some(
    (p) => p.name.trim().toLowerCase() === q,
  )
  const canCreate = q.length > 0 && !exactExists

  async function pick(personId: number | null) {
    if (busy) return
    setBusy(true)
    try {
      await onPick(personId)
      onClose()
    } catch {
      // 落库失败：父组件可能已弹错；这里只解除忙碌，让用户重试
      setBusy(false)
    }
  }

  async function handleCreate() {
    if (busy || !canCreate) return
    setBusy(true)
    setCreateErr(null)
    try {
      const created = await createPerson({ name: query.trim() })
      await onPick(created.id)
      onClose()
    } catch {
      setCreateErr('新建失败，请重试')
      setBusy(false)
    }
  }

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== 'Enter') return
    e.preventDefault()
    // 回车：优先选中唯一过滤结果，否则若可新建就新建
    if (filtered.length === 1) {
      void pick(filtered[0].id)
    } else if (canCreate) {
      void handleCreate()
    }
  }

  return (
    <div
      ref={rootRef}
      role="dialog"
      aria-label={title}
      className="absolute z-30 mt-1 w-64 rounded-card border border-line bg-paper p-2 shadow-lg"
      // 浮层属于「事实层 chrome」：用 paper/line，不沾 iris（那是解读层）
      onClick={(e) => e.stopPropagation()}
    >
      <p className="mb-1.5 px-1 font-ui text-xs font-medium text-ink-soft">
        {title}
      </p>

      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={onInputKeyDown}
        placeholder="搜索或输入新名字…"
        disabled={busy}
        className="mb-1.5 w-full rounded-sm border border-line bg-card px-2 py-1.5 font-ui text-sm text-ink outline-none placeholder:text-ink-soft/60 focus:border-pine disabled:opacity-50"
      />

      <div className="max-h-56 overflow-y-auto">
        {people.loading && (
          <p className="px-1 py-2 font-ui text-xs text-ink-soft">正在加载人物…</p>
        )}
        {people.error && (
          <p className="px-1 py-2 font-ui text-xs text-ink-soft">
            取不到人物列表。
          </p>
        )}

        {allowClear && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void pick(null)}
            className={`flex w-full items-center gap-2 rounded-sm px-1.5 py-1.5 text-left font-ui text-sm transition-colors hover:bg-ink/5 disabled:opacity-50 ${
              currentPersonId === null ? 'text-ink' : 'text-ink-soft'
            }`}
          >
            <span className="inline-grid size-7 shrink-0 place-items-center rounded-full border border-dashed border-line text-ink-soft">
              ?
            </span>
            设为未知（清除归属）
          </button>
        )}

        {!people.loading &&
          filtered.map((p: PersonListItem) => {
            const active = p.id === currentPersonId
            return (
              <button
                key={p.id}
                type="button"
                disabled={busy}
                onClick={() => void pick(p.id)}
                className={`flex w-full items-center gap-2 rounded-sm px-1.5 py-1.5 text-left transition-colors hover:bg-ink/5 disabled:opacity-50 ${
                  active ? 'bg-ink/5' : ''
                }`}
              >
                <Avatar person={p} size={28} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-record text-sm text-ink">
                    {p.name}
                  </span>
                  <span className="block font-mono text-[11px] text-ink-soft">
                    {p.utterance_count} 句
                    {p.relation ? ` · ${p.relation}` : ''}
                  </span>
                </span>
                {active && (
                  <span className="font-mono text-xs text-pine">当前</span>
                )}
              </button>
            )
          })}

        {!people.loading && !people.error && filtered.length === 0 && !canCreate && (
          <p className="px-1 py-2 font-ui text-xs text-ink-soft">没有匹配的人。</p>
        )}
      </div>

      {canCreate && (
        <button
          type="button"
          disabled={busy}
          onClick={() => void handleCreate()}
          className="mt-1 flex w-full items-center gap-2 rounded-sm border border-dashed border-pine/40 px-1.5 py-1.5 text-left font-ui text-sm text-pine transition-colors hover:bg-pine/10 disabled:opacity-50"
        >
          <span className="inline-grid size-7 shrink-0 place-items-center rounded-full bg-pine/10 text-base leading-none">
            +
          </span>
          新建「{query.trim()}」
        </button>
      )}

      {createErr && (
        <p className="mt-1 px-1 font-ui text-xs text-ink-soft">{createErr}</p>
      )}
      {busy && (
        <p className="mt-1 px-1 font-ui text-xs text-ink-soft" aria-live="polite">
          正在保存…
        </p>
      )}
    </div>
  )
}
