/*
 * ReviewStepper —— 复盘四步的进度指示与分段推进（产品方案 §10.6）。
 *
 * 四步：① 事实回放（事实层）/ ② 你的视角 / ③ 对方可能的视角 / ④ 接下来怎么做（解读层）。
 * 视觉上把「事实层①」与「解读层②③④」一眼区分：
 *   - 第①步用 pine（真相锚同色），代表「真数据、可回放」。
 *   - ②③④用 iris（解读层专色），代表「AI 旁批、M4 占位」。
 * 每一步都是可点的按钮，键盘可达；当前步用实心点 + 加粗标签强调。
 *
 * 注意：Tailwind v4 靠静态扫描源码收集类名，禁止用模板字符串拼类名
 * （如 `text-${x}`）。这里全部用预写好的静态类名映射。
 */

import { useTranslation } from 'react-i18next'

export interface ReviewStep {
  /** 步骤序号（1..4） */
  index: number
  /** 步骤短标题的 i18n key（review 命名空间下 stepper.steps.*） */
  labelKey: string
  /** 是否属于解读层（②③④）。事实层①为 false。 */
  interpret: boolean
}

/** 复盘四步定义，整套复盘共用。标题文案走 i18n（labelKey）。 */
export const REVIEW_STEPS: ReviewStep[] = [
  { index: 1, labelKey: 'stepper.steps.fact', interpret: false },
  { index: 2, labelKey: 'stepper.steps.yourView', interpret: true },
  { index: 3, labelKey: 'stepper.steps.theirView', interpret: true },
  { index: 4, labelKey: 'stepper.steps.nextStep', interpret: true },
]

/** 当前步（激活）配色：事实层 pine / 解读层 iris。全静态，供 Tailwind 扫描。 */
const ACTIVE_TEXT = { pine: 'text-pine', iris: 'text-iris' } as const
/** 已完成 / 激活的序号小圆：实心。 */
const DOT_SOLID = {
  pine: 'bg-pine text-paper',
  iris: 'bg-iris text-paper',
} as const
/** 未到达的序号小圆：描边。 */
const DOT_HOLLOW = {
  pine: 'border border-pine/40 text-pine/70',
  iris: 'border border-iris/40 text-iris/70',
} as const

export interface ReviewStepperProps {
  /** 当前激活的步骤序号（1..4） */
  current: number
  /** 切到某一步 */
  onSelect: (index: number) => void
}

export function ReviewStepper({ current, onSelect }: ReviewStepperProps) {
  const { t } = useTranslation('review')
  return (
    <nav aria-label={t('stepper.navLabel')} className="px-5 pt-4 sm:px-6">
      <ol className="flex flex-wrap items-center gap-1.5">
        {REVIEW_STEPS.map((step, i) => {
          const active = step.index === current
          const done = step.index < current
          const tone = step.interpret ? 'iris' : 'pine'
          return (
            <li key={step.index} className="flex items-center">
              <button
                type="button"
                onClick={() => onSelect(step.index)}
                aria-current={active ? 'step' : undefined}
                className={[
                  'flex items-center gap-2 rounded-sm px-2.5 py-1.5 font-ui text-sm transition-colors',
                  active
                    ? ACTIVE_TEXT[tone]
                    : 'text-ink-soft hover:bg-ink/5 hover:text-ink',
                ].join(' ')}
              >
                <span
                  aria-hidden="true"
                  className={[
                    'inline-grid size-5 place-items-center rounded-full font-mono text-[11px] leading-none',
                    active || done ? DOT_SOLID[tone] : DOT_HOLLOW[tone],
                  ].join(' ')}
                >
                  {step.index}
                </span>
                <span
                  className={[
                    'whitespace-nowrap',
                    active ? 'font-semibold' : 'font-medium',
                  ].join(' ')}
                >
                  {t(step.labelKey)}
                </span>
              </button>
              {i < REVIEW_STEPS.length - 1 && (
                <span
                  aria-hidden="true"
                  className="mx-0.5 hidden h-px w-4 bg-line sm:inline-block"
                />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
