/*
 * PersonCreateDialog —— 「新建人物」轻量对话框。
 *
 * 线下认识的人（还没在任何对话里出现过）需要手动建档，这里用一个
 * 原生 <dialog> 收名字 + 关系，提交走 createPerson，成功后回调让列表 reload。
 *
 * 设计：界面体（chrome），安静地退到后面；事实层（信笺）才是主角。
 * 无障碍：原生 <dialog> 自带焦点陷阱与 Esc 关闭；首个输入框自动聚焦。
 */

import { useEffect, useRef, useState } from 'react'
import { createPerson } from '../../api/client'
import { Button } from '../../components/Button'

export interface PersonCreateDialogProps {
  open: boolean
  onClose: () => void
  /** 成功创建后回调（携带新建人物 id，便于上层决定跳转/刷新） */
  onCreated: (id: number) => void
}

export function PersonCreateDialog({
  open,
  onClose,
  onCreated,
}: PersonCreateDialogProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null)
  const nameRef = useRef<HTMLInputElement | null>(null)
  const [name, setName] = useState('')
  const [relation, setRelation] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // open 状态与原生 <dialog> 的 showModal/close 同步
  useEffect(() => {
    const dlg = dialogRef.current
    if (!dlg) return
    if (open && !dlg.open) {
      dlg.showModal()
      // 进场时清空残留并聚焦名字输入
      setName('')
      setRelation('')
      setError(null)
      // 等 dialog 真正打开后再聚焦
      requestAnimationFrame(() => nameRef.current?.focus())
    } else if (!open && dlg.open) {
      dlg.close()
    }
  }, [open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('名字不能为空。')
      nameRef.current?.focus()
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const created = await createPerson({
        name: trimmed,
        relation: relation.trim() || undefined,
      })
      onCreated(created.id)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败，请重试。')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <dialog
      ref={dialogRef}
      // 点击遮罩（dialog 本体）关闭；内容区域阻止冒泡
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose()
      }}
      onCancel={(e) => {
        // 拦截原生 Esc 的默认 close，统一走 onClose 让 open 状态收敛
        e.preventDefault()
        onClose()
      }}
      className="m-auto w-[min(26rem,calc(100vw-2rem))] rounded-card border border-line bg-card p-0 text-ink backdrop:bg-ink/30"
    >
      <form onSubmit={handleSubmit} className="p-5">
        <h2 className="mb-1 font-record text-lg font-semibold text-ink">
          新建人物
        </h2>
        <p className="mb-4 font-ui text-sm text-ink-soft">
          线下认识、还没在对话里出现过的人，可以先在这里建档。
        </p>

        <label className="mb-3 block">
          <span className="mb-1 block font-ui text-xs font-medium text-ink-soft">
            名字
          </span>
          <input
            ref={nameRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：老王"
            className="w-full rounded-sm border border-line bg-paper px-3 py-2 font-record text-[15px] text-ink outline-none placeholder:text-ink-soft/50 focus:border-pine-soft"
          />
        </label>

        <label className="mb-4 block">
          <span className="mb-1 block font-ui text-xs font-medium text-ink-soft">
            关系 <span className="text-ink-soft/60">（可选）</span>
          </span>
          <input
            value={relation}
            onChange={(e) => setRelation(e.target.value)}
            placeholder="例如：同事 / 朋友 / 客户"
            className="w-full rounded-sm border border-line bg-paper px-3 py-2 font-ui text-sm text-ink outline-none placeholder:text-ink-soft/50 focus:border-pine-soft"
          />
        </label>

        {error && (
          <p className="mb-3 font-ui text-sm text-live" role="alert">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button type="submit" variant="primary" disabled={submitting}>
            {submitting ? '创建中…' : '创建'}
          </Button>
        </div>
      </form>
    </dialog>
  )
}
