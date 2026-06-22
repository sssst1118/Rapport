/*
 * ReviewOverlay —— 复盘模式（产品方案 §10.6）。
 *
 * 形态：一个覆盖层（modal/overlay），不是新路由。从对话页/人物页的「复盘」
 * 按钮打开。四步引导，分步推进（ReviewStepper）：
 *   ① 事实回放（事实层，真数据，可回放原声）—— FactReplay
 *   ② 你的视角 / ③ 对方可能的视角 / ④ 接下来怎么做（解读层，M4 占位）—— InterpretStep
 * 事实层①（信笺/记录体）与解读层②③④（iris 旁批）视觉一眼区分。
 *
 * 无障碍：
 *   - role="dialog" + aria-modal，aria-labelledby 指向标题。
 *   - 可关闭：Esc / 点遮罩 / 关闭按钮。
 *   - 焦点管理：打开即把焦点移入对话框；关闭还原到触发元素；Tab 在框内循环（焦点陷阱）。
 *   - 键盘可达：步进、关闭、上一步/下一步都是真实 button。
 *   - 尊重 prefers-reduced-motion：进入动画仅在 no-preference 下播放（用全局
 *     约定的 .animate-record-settle，已在 index.css 里对 reduce 关闭）。
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import type { ReviewScope } from '../../api/types'
import { Button } from '../../components/Button'
import { FactReplay } from './FactReplay'
import { InterpretStep } from './InterpretStep'
import { ReviewStepper, REVIEW_STEPS } from './ReviewStepper'

/**
 * ②③④各步的标题与引导文案对应的 i18n key（与 REVIEW_STEPS 对应）。
 * title 复用 stepper 步骤名；hint 走 interpret.*.hint。
 */
const INTERPRET_COPY: Record<number, { titleKey: string; hintKey: string }> = {
  2: {
    titleKey: 'stepper.steps.yourView',
    hintKey: 'interpret.yourView.hint',
  },
  3: {
    titleKey: 'stepper.steps.theirView',
    hintKey: 'interpret.theirView.hint',
  },
  4: {
    titleKey: 'stepper.steps.nextStep',
    hintKey: 'interpret.nextStep.hint',
  },
}

export interface ReviewOverlayProps {
  /** 复盘范围：一段对话 / 一个人 */
  scope: ReviewScope
  /** 对应对话或人物的 id */
  id: number
  /** 覆盖层标题（如对话备注或人名） */
  title: string
  /** 关闭覆盖层 */
  onClose: () => void
}

export function ReviewOverlay({ scope, id, title, onClose }: ReviewOverlayProps) {
  const { t } = useTranslation('review')
  // 当前步（1..4）由覆盖层自管，父页面只控制开/关，改动更小更内聚
  const [step, setStep] = useState(1)
  const onStep = useCallback(
    (index: number) =>
      setStep(Math.min(REVIEW_STEPS.length, Math.max(1, index))),
    [],
  )
  const dialogRef = useRef<HTMLDivElement | null>(null)
  // 记住打开前的焦点元素，关闭时还原（焦点管理）
  const restoreRef = useRef<Element | null>(null)

  // 打开：锁滚动 + 记住并移入焦点；卸载：还原
  useEffect(() => {
    restoreRef.current = document.activeElement
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // 把焦点移进对话框（优先对话框容器本身，它带 tabIndex=-1）
    const t = window.setTimeout(() => dialogRef.current?.focus(), 0)

    return () => {
      window.clearTimeout(t)
      document.body.style.overflow = prevOverflow
      const el = restoreRef.current
      if (el instanceof HTMLElement) el.focus()
    }
  }, [])

  // 键盘：Esc 关闭；Tab 在对话框内循环（焦点陷阱）
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab') return
      const root = dialogRef.current
      if (!root) return
      const focusables = root.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
      )
      if (focusables.length === 0) return
      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      const activeEl = document.activeElement as HTMLElement | null
      if (e.shiftKey) {
        if (activeEl === first || activeEl === root) {
          e.preventDefault()
          last.focus()
        }
      } else if (activeEl === last) {
        e.preventDefault()
        first.focus()
      }
    },
    [onClose],
  )

  const isLast = step >= REVIEW_STEPS.length
  const isFirst = step <= 1
  const copy = INTERPRET_COPY[step]

  const overlay = (
    // 遮罩：点击空白处关闭
    <div
      className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-ink/40 p-4 sm:p-6"
      onMouseDown={(e) => {
        // 仅当按下点正是遮罩自身时关闭（避免框内拖拽误触）
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="review-overlay-title"
        tabIndex={-1}
        onKeyDown={onKeyDown}
        className="animate-record-settle my-4 w-full max-w-2xl rounded-card border border-line bg-paper shadow-xl outline-none"
      >
        {/* 头部：标题 + 关闭 */}
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 pt-4 pb-3 sm:px-6">
          <div className="min-w-0">
            <p className="font-ui text-xs font-medium uppercase tracking-wide text-pine">
              {t('overlay.eyebrow')}
            </p>
            <h2
              id="review-overlay-title"
              className="mt-0.5 truncate font-record text-xl font-semibold text-ink"
            >
              {title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('overlay.close')}
            className="-mr-1.5 -mt-1 inline-grid size-8 shrink-0 place-items-center rounded-sm text-ink-soft transition-colors hover:bg-ink/5 hover:text-ink"
          >
            <CloseGlyph />
          </button>
        </header>

        {/* 分步进度条 */}
        <ReviewStepper current={step} onSelect={onStep} />

        {/* 步骤内容 */}
        <div className="px-5 py-4 sm:px-6">
          {step === 1 ? (
            <FactReplay scope={scope} id={id} />
          ) : copy ? (
            <InterpretStep
              scope={scope}
              id={id}
              title={t(copy.titleKey)}
              hint={t(copy.hintKey)}
            />
          ) : null}
        </div>

        {/* 底部：上一步 / 下一步（分步推进） */}
        <footer className="flex items-center justify-between gap-3 border-t border-line px-5 py-3 sm:px-6">
          <Button
            variant="ghost"
            onClick={() => onStep(step - 1)}
            disabled={isFirst}
          >
            {t('overlay.prev')}
          </Button>
          <span className="font-mono text-xs text-ink-soft">
            {t('overlay.progress', {
              current: step,
              total: REVIEW_STEPS.length,
            })}
          </span>
          {isLast ? (
            <Button variant="primary" onClick={onClose}>
              {t('overlay.finish')}
            </Button>
          ) : (
            <Button variant="primary" onClick={() => onStep(step + 1)}>
              {t('overlay.next')}
            </Button>
          )}
        </footer>
      </div>
    </div>
  )

  return createPortal(overlay, document.body)
}

function CloseGlyph() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  )
}
