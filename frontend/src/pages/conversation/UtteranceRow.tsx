/*
 * UtteranceRow —— 转写正文里的一行，叠了「逐行展开操作」的交互层。
 *
 * 事实层（立即真实写库 + reload）：
 *   - 编辑文字：行内 textarea -> updateUtteranceText
 *   - 加标签 / 加批注：addAnnotation；已有标注可 deleteAnnotation
 *   - 改这一行说话人：PersonPicker -> updateUtterancePerson
 *
 * 视觉纪律：本行属信笺（paper/card + 记录体），与解读层 InterpretationCard 一眼区分。
 * 展开面板是安静的 chrome（界面体 + line/card），不抢正文。
 *
 * 划选：本行只负责「显示选中态 + 把点击/勾选回调上抛」，选区状态由页面统一持有。
 */

import { useEffect, useRef, useState } from 'react'
import type { Utterance, ParticipantRef } from '../../api/types'
import {
  updateUtteranceText,
  updateUtterancePerson,
  addAnnotation,
  deleteAnnotation,
} from '../../api/client'
import { formatTimecode } from '../../lib/format'
import { SpeakerStripe } from '../../components/SpeakerStripe'
import { PlayLine } from '../../components/PlayLine'
import { Button } from '../../components/Button'
import { PersonPicker } from './PersonPicker'

export interface UtteranceRowProps {
  u: Utterance
  index: number
  src: string
  hasAudio: boolean
  /** 当前对话的参与者，用来把 person_id 显示成真名 */
  participants: ParticipantRef[]
  /** 是否被划选 */
  selected: boolean
  /** 勾选/取消勾选本行（支持 shift 连选：第二个参数是原始事件） */
  onToggleSelect: (id: number, shiftKey: boolean) => void
  /** 任一事实写库成功后调用，触发页面 reload() */
  onReload: () => void
  /** 打开「整段说话人映射」浮层（点行首说话人标签时） */
  onOpenSpeakerMap: (anchor: { label: string; personId: number | null }) => void
}

export function UtteranceRow({
  u,
  index,
  src,
  hasAudio,
  participants,
  selected,
  onToggleSelect,
  onReload,
  onOpenSpeakerMap,
}: UtteranceRowProps) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(u.text)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // 内联表单：加标签/批注
  const [tagInput, setTagInput] = useState('')
  const [noteInput, setNoteInput] = useState('')

  // 行尾「改这一行说话人」的 PersonPicker 开关
  const [rowPicker, setRowPicker] = useState(false)

  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const person = u.person_id != null
    ? participants.find((p) => p.id === u.person_id) ?? null
    : null
  const unmapped = u.person_id == null
  // 色条/头像的颜色 key：已归属用人物 id，未归属退回说话人标签（仍稳定出色）
  const stripeKey = u.person_id ?? u.speaker_label

  useEffect(() => {
    if (editing) {
      const ta = textareaRef.current
      if (ta) {
        ta.focus()
        ta.setSelectionRange(ta.value.length, ta.value.length)
      }
    }
  }, [editing])

  function startEdit() {
    setDraft(u.text)
    setErr(null)
    setEditing(true)
    setExpanded(true)
  }

  async function saveText() {
    const next = draft.trim()
    if (!next || next === u.text) {
      setEditing(false)
      return
    }
    setSaving(true)
    setErr(null)
    try {
      await updateUtteranceText(u.id, next)
      setEditing(false)
      onReload()
    } catch {
      setErr('保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  async function addTag() {
    const v = tagInput.trim()
    if (!v) return
    setSaving(true)
    setErr(null)
    try {
      await addAnnotation(u.id, 'tag', v)
      setTagInput('')
      onReload()
    } catch {
      setErr('添加标签失败')
    } finally {
      setSaving(false)
    }
  }

  async function addNote() {
    const v = noteInput.trim()
    if (!v) return
    setSaving(true)
    setErr(null)
    try {
      await addAnnotation(u.id, 'note', v)
      setNoteInput('')
      onReload()
    } catch {
      setErr('添加批注失败')
    } finally {
      setSaving(false)
    }
  }

  async function removeAnnotation(aid: number) {
    setSaving(true)
    setErr(null)
    try {
      await deleteAnnotation(aid)
      onReload()
    } catch {
      setErr('删除标注失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <li
      className={`group relative flex gap-3 rounded-sm px-2 py-2 transition-colors ${
        selected ? 'bg-pine/5 ring-1 ring-pine/30' : 'hover:bg-card'
      }`}
    >
      {/* 划选复选框：默认隐身，hover/选中时显形，不抢正文 */}
      <label
        className={`flex shrink-0 items-start pt-1.5 transition-opacity ${
          selected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 focus-within:opacity-100'
        }`}
        title="选中这一行"
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) =>
            onToggleSelect(u.id, (e.nativeEvent as MouseEvent).shiftKey)
          }
          className="size-3.5 accent-pine"
          aria-label={`选中第 ${index + 1} 句`}
        />
      </label>

      {/* 色条头部：点它打开「整段说话人映射」 */}
      <button
        type="button"
        onClick={() => onOpenSpeakerMap({ label: u.speaker_label, personId: u.person_id })}
        title="把这个说话人整段归属到某人"
        className="flex shrink-0 self-stretch rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-pine/50"
      >
        <SpeakerStripe colorKey={stripeKey} width={4} title={u.speaker_label} />
      </button>

      <div className="min-w-0 flex-1">
        <div className="mb-0.5 flex flex-wrap items-center gap-2">
          {/* 说话人标签：点开整段映射浮层；未映射时高亮提示「这是谁？」 */}
          <button
            type="button"
            onClick={() => onOpenSpeakerMap({ label: u.speaker_label, personId: u.person_id })}
            className={`rounded-sm px-1 font-mono text-xs font-medium transition-colors ${
              unmapped
                ? 'bg-pine/10 text-pine ring-1 ring-pine/40 hover:bg-pine/20'
                : 'text-ink-soft hover:bg-ink/5 hover:text-ink'
            }`}
            title={unmapped ? '这是谁？点一下认人，整段一起归属' : '改这个说话人的归属'}
          >
            {person ? person.name : u.speaker_label}
            {unmapped && <span className="ml-1">· 这是谁？</span>}
          </button>

          <span className="font-mono text-[11px] text-ink-soft/70">
            {formatTimecode(u.start_ms)}
          </span>

          {hasAudio && (
            <PlayLine src={src} startMs={u.start_ms} endMs={u.end_ms} className="ml-0.5" />
          )}

          {/* 行尾「⋯」：展开/收起逐行操作面板 */}
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            title={expanded ? '收起' : '更多操作'}
            className="ml-auto inline-grid size-7 place-items-center rounded-full text-ink-soft opacity-0 transition-colors hover:bg-ink/5 hover:text-ink group-hover:opacity-100 focus-visible:opacity-100 aria-expanded:opacity-100"
          >
            <span className="text-lg leading-none">⋯</span>
          </button>
        </div>

        {/* 正文：编辑态切 textarea，否则点一下进入编辑 */}
        {editing ? (
          <div className="mt-1">
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  void saveText()
                }
                if (e.key === 'Escape') {
                  e.preventDefault()
                  setEditing(false)
                  setDraft(u.text)
                }
              }}
              rows={Math.max(2, Math.ceil(draft.length / 40))}
              disabled={saving}
              className="w-full resize-y rounded-sm border border-pine/40 bg-card px-2 py-1.5 font-record text-[15px] leading-relaxed text-ink outline-none focus:border-pine disabled:opacity-50"
            />
            <div className="mt-1.5 flex items-center gap-2">
              <Button variant="primary" onClick={() => void saveText()} disabled={saving}>
                {saving ? '保存中…' : '保存'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setEditing(false)
                  setDraft(u.text)
                }}
                disabled={saving}
              >
                取消
              </Button>
              <span className="font-ui text-xs text-ink-soft/70">⌘/Ctrl+Enter 保存 · Esc 取消</span>
            </div>
          </div>
        ) : (
          <p
            onClick={startEdit}
            title="点一下编辑这句话"
            className="cursor-text font-record text-[15px] leading-relaxed text-ink"
          >
            {u.text}
          </p>
        )}

        {/* 已有标注：可点 × 删除 */}
        {u.annotations.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {u.annotations.map((a) => (
              <span
                key={a.id}
                className="inline-flex items-center gap-1 rounded-sm bg-ink/5 px-1.5 py-0.5 font-ui text-xs text-ink-soft"
              >
                <span className="font-mono">{a.type === 'tag' ? '#' : '✎'}</span>
                {a.value}
                <button
                  type="button"
                  onClick={() => void removeAnnotation(a.id)}
                  disabled={saving}
                  aria-label={`删除标注 ${a.value}`}
                  className="ml-0.5 rounded-full px-0.5 text-ink-soft/60 hover:text-ink disabled:opacity-50"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        {/* 展开的逐行操作面板 */}
        {expanded && (
          <div className="mt-2 rounded-sm border border-line bg-card/70 p-2.5">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-2">
              {!editing && (
                <Button variant="secondary" onClick={startEdit}>
                  编辑文字
                </Button>
              )}

              {/* 改这一行的说话人 —— 单行 PersonPicker */}
              <div className="relative">
                <Button variant="secondary" onClick={() => setRowPicker((v) => !v)}>
                  改这一行说话人
                </Button>
                {rowPicker && (
                  <PersonPicker
                    title="这一行是谁说的？"
                    currentPersonId={u.person_id}
                    allowClear
                    onClose={() => setRowPicker(false)}
                    onPick={async (pid) => {
                      await updateUtterancePerson(u.id, pid)
                      onReload()
                    }}
                  />
                )}
              </div>
            </div>

            {/* 加标签 / 加批注 */}
            <div className="mt-2.5 flex flex-col gap-2 sm:flex-row">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  void addTag()
                }}
                className="flex flex-1 items-center gap-1.5"
              >
                <span className="font-mono text-xs text-ink-soft">#</span>
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  placeholder="加标签"
                  disabled={saving}
                  className="min-w-0 flex-1 rounded-sm border border-line bg-paper px-2 py-1 font-ui text-xs text-ink outline-none placeholder:text-ink-soft/60 focus:border-pine disabled:opacity-50"
                />
                <Button variant="ghost" type="submit" disabled={saving || !tagInput.trim()}>
                  加
                </Button>
              </form>

              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  void addNote()
                }}
                className="flex flex-1 items-center gap-1.5"
              >
                <span className="font-mono text-xs text-ink-soft">✎</span>
                <input
                  type="text"
                  value={noteInput}
                  onChange={(e) => setNoteInput(e.target.value)}
                  placeholder="加批注"
                  disabled={saving}
                  className="min-w-0 flex-1 rounded-sm border border-line bg-paper px-2 py-1 font-ui text-xs text-ink outline-none placeholder:text-ink-soft/60 focus:border-pine disabled:opacity-50"
                />
                <Button variant="ghost" type="submit" disabled={saving || !noteInput.trim()}>
                  加
                </Button>
              </form>
            </div>

            {err && <p className="mt-2 font-ui text-xs text-ink-soft">{err}</p>}
          </div>
        )}
      </div>
    </li>
  )
}
