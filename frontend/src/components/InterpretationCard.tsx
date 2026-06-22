/*
 * InterpretationCard —— 解读层（AI 分析）的载体，即「页边旁批」register。
 *
 * 视觉上必须和事实层（信笺）一眼区分：
 *   - iris 配色 + iris-tint 背景（事实层是 paper/card 的暖燕麦）
 *   - 左侧一道虚线/括注边，像在页边写批注
 *   - 右上角「解读」角标，明示这是 AI 的「读」、不是事实
 *
 * 渲染契约：接收 Interpretation 信封 {kind, status, message, data}，按 status 分支：
 *   - ready       渲染 data.overview（小结，若有）+ data.findings 列表；
 *                 每条 Finding 是一个判断，下面挂着它依据的真话原话（可回放原声）。
 *   - needs_setup 安静地显示 message（怎么配置 LLM），不用报错样式。
 *   - pending     加载骨架（与 props.loading 同处理）。
 *   - error       用 message 克制地说明失败原因（非红色大字）。
 *
 * 原话出处是事实锚：每条判断都让用户一眼看出「这条读，依据的是这几句真话」。
 */

import type { Interpretation } from '../api/types'
import { FindingItem } from './FindingItem'

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
  // pending 与外部 loading 同等对待：都进加载骨架。
  const isLoading = loading || interpretation?.status === 'pending'
  const status = interpretation?.status

  return (
    <aside
      // 用 aside 语义：这确实是正文旁边的补充批注
      style={{ backgroundColor: 'var(--iris-tint)' }}
      className={`relative rounded-card border border-iris/25 border-l-[3px] border-l-dashed border-l-iris/70 p-4 ${className}`}
    >
      {/* 右上角「解读」角标：明示这是 AI 的「读」、非事实 */}
      <span className="absolute right-3 top-3 rounded-sm bg-iris/12 px-1.5 py-0.5 font-ui text-[10px] font-medium tracking-wide text-iris">
        解读
      </span>

      <h3 className="mb-1.5 pr-12 font-ui text-sm font-semibold text-iris">
        {title}
      </h3>

      {renderBody({ isLoading, status, interpretation })}
    </aside>
  )
}

/** 按 status / loading 分支渲染卡片正文。 */
function renderBody({
  isLoading,
  status,
  interpretation,
}: {
  isLoading: boolean
  status: Interpretation['status'] | undefined
  interpretation: Interpretation | null | undefined
}) {
  // 1) 加载态（props.loading 或 status==='pending'）：沿用原骨架
  if (isLoading) {
    return <LoadingSkeleton />
  }

  // 2) 无信封：尚未发起 —— 给一句安静的占位
  if (!interpretation) {
    return <QuietLine>暂无可呈现的解读。</QuietLine>
  }

  // 3) needs_setup：诚实告知如何配置，不用报错样式
  if (status === 'needs_setup') {
    return (
      <QuietLine>
        {interpretation.message || '需要先配置才能生成解读。'}
      </QuietLine>
    )
  }

  // 4) error：克制地说明失败原因（非红色大字）
  if (status === 'error') {
    return (
      <QuietLine>
        {interpretation.message || '这次没能生成解读，待会儿再试。'}
      </QuietLine>
    )
  }

  // 5) ready：真实解读 —— overview 小结 + findings 列表（每条挂原话出处）
  if (status === 'ready') {
    const findings = interpretation.data?.findings ?? []
    const overview = interpretation.data?.overview

    if (!overview && findings.length === 0) {
      return <QuietLine>暂无可呈现的解读。</QuietLine>
    }

    return (
      <div className="space-y-3">
        {overview && (
          // 小结：解读的总览，记录体 + ink/85，作为列表前的引子
          <p className="font-record text-sm leading-relaxed text-ink/85">
            {overview}
          </p>
        )}
        {findings.length > 0 && (
          <ul className="space-y-3 border-t border-iris/15 pt-3">
            {findings.map((finding, i) => (
              <FindingItem key={i} finding={finding} />
            ))}
          </ul>
        )}
      </div>
    )
  }

  // 兜底：未知 status —— 用 message，再不济给占位
  return (
    <QuietLine>{interpretation.message || '暂无可呈现的解读。'}</QuietLine>
  )
}

/** 加载骨架（与原实现一致，尊重 prefers-reduced-motion——动画类在该模式下不生效）。 */
function LoadingSkeleton() {
  return (
    <div className="space-y-2" aria-hidden="true">
      <div className="h-3 w-4/5 animate-pulse rounded bg-iris/15" />
      <div className="h-3 w-3/5 animate-pulse rounded bg-iris/15" />
    </div>
  )
}

/** 安静的单行文案：用于 needs_setup / error / 空态，克制、不喧哗。 */
function QuietLine({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-record text-sm leading-relaxed text-ink-soft">
      {children}
    </p>
  )
}
