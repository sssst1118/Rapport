/*
 * InterpretStep —— 复盘第②③④步「你的视角 / 对方可能的视角 / 接下来怎么做」。
 *
 * 这三步是解读层（产品方案 §10.6）：调 review(scope, id) 取 Interpretation 信封，
 * 用 InterpretationCard 渲染（iris 旁批 + 右上角 M4 角标）。现阶段后端一律返回
 * pending_m4 占位——我们如实呈现「解读将在 M4 接入」，绝不自己编 AI 文案冒充事实。
 *
 * 按需加载：仅当用户切到该步时才发起 review 请求（lazy=进入即拉一次）。
 */

import { useEffect, useState } from 'react'
import type { Interpretation, ReviewScope } from '../../api/types'
import { review } from '../../api/client'
import { InterpretationCard } from '../../components/InterpretationCard'

export interface InterpretStepProps {
  scope: ReviewScope
  id: number
  /** 卡片标题，对应当前步（如「你的视角」） */
  title: string
  /** 这一步对用户的引导说明 */
  hint: string
}

export function InterpretStep({ scope, id, title, hint }: InterpretStepProps) {
  const [data, setData] = useState<Interpretation | null>(null)
  const [loading, setLoading] = useState(true)

  // 进入这一步即拉一次 review。失败时静默降级为占位卡（不白屏）。
  // review() 不接受 AbortSignal，这里用 alive 标志防止卸载后 setState 的竞态。
  useEffect(() => {
    let alive = true
    setLoading(true)
    setData(null)
    review(scope, id)
      .then((res) => {
        if (alive) setData(res)
      })
      .catch(() => {
        // review 失败：InterpretationCard 用默认占位文案兜底
        if (alive) setData(null)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [scope, id, title])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 font-ui text-sm text-iris">
        <span
          aria-hidden="true"
          className="inline-block size-1.5 rounded-full bg-iris"
        />
        <span className="font-medium">解读</span>
        <span className="text-ink-soft">·会带原话出处、可回放，不凭空生成</span>
      </div>
      <p className="font-ui text-sm text-ink-soft">{hint}</p>
      <InterpretationCard title={title} interpretation={data} loading={loading} />
    </div>
  )
}
