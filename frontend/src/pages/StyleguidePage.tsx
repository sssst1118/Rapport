/*
 * 样式手册 /styleguide —— 集中陈列《记录与旁批》设计系统，便于肉眼核对。
 * 色板、三种字体、Avatar、SpeakerStripe、WaveformMark、WaveformPlayer、
 * InterpretationCard、按钮、状态件都在这里有样例。
 *
 * 注意：WaveformPlayer 指向一个示例音频地址；后端没起时它会优雅显示「音频暂不可用」。
 */

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

const SWATCHES: { name: string; varName: string; note: string }[] = [
  { name: 'ink', varName: '--ink', note: '正文（事实）' },
  { name: 'ink-soft', varName: '--ink-soft', note: '次级文字 / 标签' },
  { name: 'paper', varName: '--paper', note: '应用底色 燕麦' },
  { name: 'card', varName: '--card', note: '抬升表面 卡片' },
  { name: 'line', varName: '--line', note: '细分隔线' },
  { name: 'pine', varName: '--pine', note: '品牌 / 真相锚' },
  { name: 'pine-soft', varName: '--pine-soft', note: 'pine 次级 / hover' },
  { name: 'iris', varName: '--iris', note: '解读层 专用' },
  { name: 'iris-tint', varName: '--iris-tint', note: '解读卡背景' },
  { name: 'live', varName: '--live', note: '仅录制指示点' },
]

const SAMPLE_PEOPLE = [
  { id: 1, name: '林深' },
  { id: 2, name: '苏婉' },
  { id: 3, name: '陈嘉树' },
  { id: 4, name: 'Avery' },
  { id: 5, name: 'Jonas' },
  { id: 7, name: '周一一' },
]

const PENDING: Interpretation = {
  kind: 'interpretation',
  status: 'pending_m4',
  message: '（示例）这里将显示对这段对话的解读与小结。',
  data: null,
}

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
  return (
    <div>
      <PageHeader
        title="样式手册"
        description="《记录与旁批》设计系统的可视基准 —— 色、字、件。"
      />

      {/* 调色板 */}
      <Section title="调色板">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {SWATCHES.map((s) => (
            <div key={s.name} className="rounded-card border border-line bg-card p-2">
              <div
                className="mb-2 h-14 w-full rounded-sm border border-line"
                style={{ backgroundColor: `var(${s.varName})` }}
              />
              <p className="font-mono text-xs text-ink">{s.name}</p>
              <p className="font-ui text-[11px] text-ink-soft">{s.note}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 字体三角色 */}
      <Section title="字体 · 三角色">
        <div className="space-y-4">
          <div className="rounded-card border border-line bg-card p-4">
            <p className="mb-1 font-ui text-xs text-ink-soft">
              记录体 · 人说的话（霞鹜文楷 / Literata）
            </p>
            <p className="font-record text-xl text-ink">
              “我们那天聊到很晚，他说他其实一直想换一种活法。”
            </p>
            <p className="font-record text-base text-ink-soft">
              The quiet things that no one ever knows.
            </p>
          </div>
          <div className="rounded-card border border-line bg-card p-4">
            <p className="mb-1 font-ui text-xs text-ink-soft">
              界面体 · chrome（Noto Sans SC / Hanken Grotesk）
            </p>
            <p className="font-ui text-lg text-ink">
              今日 · 人物 · 关系图 — 安静、现代、退到后面
            </p>
          </div>
          <div className="rounded-card border border-line bg-card p-4">
            <p className="mb-1 font-ui text-xs text-ink-soft">
              记录时刻体 · 数据（IBM Plex Mono）
            </p>
            <p className="font-mono text-lg tabular-nums text-ink">
              0:42 / 3:17 · A · B · 128 句
            </p>
          </div>
        </div>
      </Section>

      {/* 品牌印记 */}
      <Section title="波形品牌印记 WaveformMark">
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
      <Section title="人即颜色 · Avatar / SpeakerStripe">
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
                  {p.name}：这是带行首色条的一行转写示例。
                </p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* 波形播放器 */}
      <Section title="波形播放器 WaveformPlayer / PlayLine">
        <div className="space-y-3 rounded-card border border-line bg-card p-4">
          <WaveformPlayer src={audioUrl('demo')} />
          <div className="flex items-center gap-2 border-t border-line pt-3">
            <PlayLine src={audioUrl('demo')} startMs={1000} endMs={4000} />
            <span className="font-ui text-sm text-ink-soft">
              行内 PlayLine：点一下跳播某句区间（后端未起时静默不报错）
            </span>
          </div>
        </div>
      </Section>

      {/* 解读卡 */}
      <Section title="解读卡 InterpretationCard · 页边旁批">
        <div className="grid gap-3 sm:grid-cols-2">
          <InterpretationCard title="这次对话的小结" interpretation={PENDING} />
          <InterpretationCard title="关于这个人" loading />
        </div>
      </Section>

      {/* 按钮 */}
      <Section title="按钮 Button">
        <div className="flex flex-wrap items-center gap-3 rounded-card border border-line bg-card p-4">
          <Button variant="primary">主操作</Button>
          <Button variant="secondary">次操作</Button>
          <Button variant="ghost">低强度</Button>
          <Button variant="primary" disabled>
            禁用
          </Button>
        </div>
      </Section>

      {/* 状态件 */}
      <Section title="状态件 · loading / 空 / 错误">
        <div className="grid gap-3 lg:grid-cols-3">
          <LoadingBlock />
          <EmptyState title="什么也没有" hint="这是空态示例。" />
          <ErrorState onRetry={() => {}} />
        </div>
      </Section>
    </div>
  )
}
