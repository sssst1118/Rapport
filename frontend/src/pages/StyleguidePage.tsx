/*
 * 样式手册 /styleguide —— 集中陈列《记录与旁批》设计系统，便于肉眼核对。
 * 色板、三种字体、Avatar、SpeakerStripe、WaveformMark、WaveformPlayer、
 * InterpretationCard、按钮、状态件都在这里有样例。
 *
 * 注意：WaveformPlayer 指向一个示例音频地址；后端没起时它会优雅显示「音频暂不可用」。
 */

import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/PageHeader'
import { WaveformMark } from '../components/WaveformMark'
import { WaveformPlayer } from '../components/WaveformPlayer'
import { PlayLine } from '../components/PlayLine'
import { Avatar } from '../components/Avatar'
import { SpeakerStripe } from '../components/SpeakerStripe'
import { InterpretationCard } from '../components/InterpretationCard'
import { Button } from '../components/Button'
import { EmptyState, ErrorState, LoadingBlock } from '../components/states'
import { audioUrl } from '../api/client'
import type { Interpretation } from '../api/types'

const SWATCHES: { name: string; varName: string; noteKey: string }[] = [
  { name: 'ink', varName: '--ink', noteKey: 'styleguide.swatch.ink' },
  { name: 'ink-soft', varName: '--ink-soft', noteKey: 'styleguide.swatch.inkSoft' },
  { name: 'paper', varName: '--paper', noteKey: 'styleguide.swatch.paper' },
  { name: 'card', varName: '--card', noteKey: 'styleguide.swatch.card' },
  { name: 'line', varName: '--line', noteKey: 'styleguide.swatch.line' },
  { name: 'pine', varName: '--pine', noteKey: 'styleguide.swatch.pine' },
  { name: 'pine-soft', varName: '--pine-soft', noteKey: 'styleguide.swatch.pineSoft' },
  { name: 'iris', varName: '--iris', noteKey: 'styleguide.swatch.iris' },
  { name: 'iris-tint', varName: '--iris-tint', noteKey: 'styleguide.swatch.irisTint' },
  { name: 'live', varName: '--live', noteKey: 'styleguide.swatch.live' },
]

const SAMPLE_PEOPLE = [
  { id: 1, name: '林深' },
  { id: 2, name: '苏婉' },
  { id: 3, name: '陈嘉树' },
  { id: 4, name: 'Avery' },
  { id: 5, name: 'Jonas' },
  { id: 7, name: '周一一' },
]

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="mb-4 font-ui text-sm font-semibold uppercase tracking-wide text-ink-soft">
        {title}
      </h2>
      {children}
    </section>
  )
}

export function StyleguidePage() {
  const { t } = useTranslation('common')

  const pending: Interpretation = {
    kind: 'interpretation',
    status: 'pending',
    message: t('styleguide.sampleInterpretationMessage'),
    data: null,
  }

  return (
    <div>
      <PageHeader
        title={t('styleguide.title')}
        description={t('styleguide.description')}
      />

      {/* 调色板 */}
      <Section title={t('styleguide.section.palette')}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {SWATCHES.map((s) => (
            <div key={s.name} className="rounded-card border border-line bg-card p-2">
              <div
                className="mb-2 h-14 w-full rounded-sm border border-line"
                style={{ backgroundColor: `var(${s.varName})` }}
              />
              <p className="font-mono text-xs text-ink">{s.name}</p>
              <p className="font-ui text-[11px] text-ink-soft">{t(s.noteKey)}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 字体三角色 */}
      <Section title={t('styleguide.section.type')}>
        <div className="space-y-4">
          <div className="rounded-card border border-line bg-card p-4">
            <p className="mb-1 font-ui text-xs text-ink-soft">
              {t('styleguide.type.recordLabel')}
            </p>
            <p className="font-record text-xl text-ink">
              {t('styleguide.type.recordSample')}
            </p>
            <p className="font-record text-base text-ink-soft">
              {t('styleguide.type.recordSampleLatin')}
            </p>
          </div>
          <div className="rounded-card border border-line bg-card p-4">
            <p className="mb-1 font-ui text-xs text-ink-soft">
              {t('styleguide.type.uiLabel')}
            </p>
            <p className="font-ui text-lg text-ink">
              {t('styleguide.type.uiSample')}
            </p>
          </div>
          <div className="rounded-card border border-line bg-card p-4">
            <p className="mb-1 font-ui text-xs text-ink-soft">
              {t('styleguide.type.monoLabel')}
            </p>
            <p className="font-mono text-lg tabular-nums text-ink">
              {t('styleguide.type.monoSample', { count: 128 })}
            </p>
          </div>
        </div>
      </Section>

      {/* 品牌印记 */}
      <Section title={t('styleguide.section.mark')}>
        <div className="flex items-center gap-6 rounded-card border border-line bg-card p-4">
          <div className="flex items-center gap-2.5">
            <WaveformMark height={20} />
            <span className="font-ui text-lg font-semibold text-ink">Rapport</span>
          </div>
          <WaveformMark height={32} />
          <WaveformMark height={44} />
        </div>
      </Section>

      {/* 人即颜色 */}
      <Section title={t('styleguide.section.color')}>
        <div className="rounded-card border border-line bg-card p-4">
          <div className="mb-4 flex flex-wrap gap-3">
            {SAMPLE_PEOPLE.map((p) => (
              <div key={p.id} className="flex flex-col items-center gap-1">
                <Avatar person={p} size={44} />
                <span className="font-mono text-[11px] text-ink-soft">{p.name}</span>
              </div>
            ))}
          </div>
          <div className="space-y-1">
            {SAMPLE_PEOPLE.slice(0, 3).map((p) => (
              <div key={p.id} className="flex gap-3 py-1">
                <SpeakerStripe colorKey={p.id} />
                <p className="font-record text-[15px] text-ink">
                  {t('styleguide.transcriptSample', { name: p.name })}
                </p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* 波形播放器 */}
      <Section title={t('styleguide.section.player')}>
        <div className="space-y-3 rounded-card border border-line bg-card p-4">
          <WaveformPlayer src={audioUrl('demo')} />
          <div className="flex items-center gap-2 border-t border-line pt-3">
            <PlayLine src={audioUrl('demo')} startMs={1000} endMs={4000} />
            <span className="font-ui text-sm text-ink-soft">
              {t('styleguide.playLineHint')}
            </span>
          </div>
        </div>
      </Section>

      {/* 解读卡 */}
      <Section title={t('styleguide.section.interpretation')}>
        <div className="grid gap-3 sm:grid-cols-2">
          <InterpretationCard
            title={t('styleguide.interpretation.conversationTitle')}
            interpretation={pending}
          />
          <InterpretationCard
            title={t('styleguide.interpretation.personTitle')}
            loading
          />
        </div>
      </Section>

      {/* 按钮 */}
      <Section title={t('styleguide.section.button')}>
        <div className="flex flex-wrap items-center gap-3 rounded-card border border-line bg-card p-4">
          <Button variant="primary">{t('styleguide.button.primary')}</Button>
          <Button variant="secondary">{t('styleguide.button.secondary')}</Button>
          <Button variant="ghost">{t('styleguide.button.ghost')}</Button>
          <Button variant="primary" disabled>
            {t('styleguide.button.disabled')}
          </Button>
        </div>
      </Section>

      {/* 状态件 */}
      <Section title={t('styleguide.section.states')}>
        <div className="grid gap-3 lg:grid-cols-3">
          <LoadingBlock />
          <EmptyState
            title={t('styleguide.states.emptyTitle')}
            hint={t('styleguide.states.emptyHint')}
          />
          <ErrorState onRetry={() => {}} />
        </div>
      </Section>
    </div>
  )
}
