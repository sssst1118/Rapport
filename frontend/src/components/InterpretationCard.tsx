/*
 * InterpretationCard —— 解读层（AI 分析）的载体，即「页边旁批」register。
 *
 * 视觉上必须和事实层（信笺）一眼区分：
 *   - iris 配色 + iris-tint 背景（事实层是 paper/card 的暖燕麦）
 *   - 左侧一道虚线/括注边，像在页边写批注
 *   - 右上角「M4」角标，明示这是后续 M4 才会真正产出的解读
 *
 * 渲染契约：接收 Interpretation 信封 {kind:'interpretation', status:'pending_m4', message}。
 * 现阶段一律是占位信封，组件据此显示「等待 M4」的安静状态。
 */

import type { Interpretation } from '../api/types'

export interface InterpretationCardProps {
  /** 卡片标题，如「这次对话的小结」「关于这个人」 */
  title: string
  /** 解读信封；为空表示尚未发起/加载中 */
  interpretation?: Interpretation | null
  /** 加载态 */
  loading?: boolean
  className?: string
}

export function InterpretationCard({
  title,
  interpretation,
  loading = false,
  className = '',
}: InterpretationCardProps) {
  const message = interpretation?.message
  const isPending = interpretation?.status === 'pending_m4'

  return (
    <aside
      // 用 aside 语义：这确实是正文旁边的补充批注
      style={{ backgroundColor: 'var(--iris-tint)' }}
      className={`relative rounded-card border border-iris/25 border-l-[3px] border-l-dashed border-l-iris/70 p-4 ${className}`}
    >
      {/* 右上角 M4 角标 */}
      <span className="absolute right-3 top-3 rounded-sm bg-iris/12 px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wide text-iris">
        M4
      </span>

      <h3 className="mb-1.5 pr-10 font-ui text-sm font-semibold text-iris">
        {title}
      </h3>

      {loading ? (
        <div className="space-y-2" aria-hidden="true">
          <div className="h-3 w-4/5 animate-pulse rounded bg-iris/15" />
          <div className="h-3 w-3/5 animate-pulse rounded bg-iris/15" />
        </div>
      ) : (
        <p className="font-record text-sm leading-relaxed text-ink/85">
          {message ?? '解读尚未生成。'}
        </p>
      )}

      {isPending && !loading && (
        <p className="mt-2 font-ui text-xs text-iris/70">
          解读功能将在 M4 阶段接入。
        </p>
      )}
    </aside>
  )
}
