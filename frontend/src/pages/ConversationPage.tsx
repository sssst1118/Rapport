/*
 * 对话 Conversation —— 单段对话的交互主舞台（M3 事实层即时生效，解读层走 M4 占位）。
 *
 * 「信笺 + 旁批」对照：
 *   - 顶部 WaveformPlayer（真相锚）
 *   - 事实摘要条 SummaryBand（参与者/时间/句数/时长，纯事实）
 *   - 转写正文：每行 UtteranceRow，叠了逐行编辑 / 标注 / 改说话人 / 划选
 *   - 右侧 InterpretationCard（解读层小结，M4 占位）
 *
 * 五项交互：
 *   ① 顶部摘要条（事实）+ 解读小结（InterpretationCard，M4）
 *   ② 逐行展开：编辑文字 / 加标签批注 / 改这一行说话人（UtteranceRow 内）
 *   ③ 说话人快速映射：点行首说话人 → PersonPicker → relabelSpeaker 整段归属
 *   ④ 划选几行 → 浮动「就这段分析」→ analyze(ids) → InterpretationCard（M4）
 *   ⑤ 事实/解读分离：编辑/映射/标注立即写库；摘要/分析只走 stub + InterpretationCard
 *
 * 乐观更新统一靠 reload()（useAsync 提供）。失败抛 ApiError，本页优雅降级，不白屏。
 */

import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  audioUrl,
  getConversation,
  getConversationSummary,
  relabelSpeaker,
  analyze,
} from '../api/client'
import type { Interpretation } from '../api/types'
import { useAsync } from '../lib/useAsync'
import { formatDateTime } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import { WaveformPlayer } from '../components/WaveformPlayer'
import { InterpretationCard } from '../components/InterpretationCard'
import { Button } from '../components/Button'
import { LoadingBlock, EmptyState, ErrorState } from '../components/states'
import { SummaryBand } from './conversation/SummaryBand'
import { UtteranceRow } from './conversation/UtteranceRow'
import { PersonPicker } from './conversation/PersonPicker'
// M3 复盘模式（§10.6）：覆盖层，从本页「复盘」按钮打开
import { ReviewOverlay } from './review/ReviewOverlay'

export function ConversationPage() {
  const { t } = useTranslation('conversation')
  const { id = '' } = useParams()
  const { data, loading, error, reload } = useAsync(
    (s) => getConversation(id, s),
    [id],
  )
  // 解读小结：独立加载，失败也不影响事实层
  const summary = useAsync((s) => getConversationSummary(id, s), [id])

  // —— 划选状态（事实层操作的选区，复选 + shift 连选）——
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [lastClicked, setLastClicked] = useState<number | null>(null)

  // —— 整段说话人映射浮层 ——（点行首说话人时打开）
  const [speakerMap, setSpeakerMap] = useState<
    { label: string; personId: number | null } | null
  >(null)

  // —— 「就这段分析」结果（解读层，走 stub）——
  const [segment, setSegment] = useState<Interpretation | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  // —— M3 复盘模式（§10.6）：覆盖层开关 ——
  const [reviewOpen, setReviewOpen] = useState(false)

  // 当前选中的句子（保持正文顺序）
  const orderedSelectedIds = useMemo(() => {
    if (!data) return []
    return data.utterances.filter((u) => selectedIds.has(u.id)).map((u) => u.id)
  }, [data, selectedIds])

  if (loading) return <LoadingBlock label={t('page.loading')} />
  if (error || !data)
    return <ErrorState message={t('page.openError')} onRetry={reload} />

  const src = audioUrl(data.id)

  // 勾选/取消一行；按住 shift 时从上次点的那行连选一段
  function toggleSelect(uid: number, shiftKey: boolean) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (shiftKey && lastClicked != null && data) {
        const ids = data.utterances.map((u) => u.id)
        const a = ids.indexOf(lastClicked)
        const b = ids.indexOf(uid)
        if (a !== -1 && b !== -1) {
          const [lo, hi] = a < b ? [a, b] : [b, a]
          for (let i = lo; i <= hi; i++) next.add(ids[i])
          return next
        }
      }
      if (next.has(uid)) next.delete(uid)
      else next.add(uid)
      return next
    })
    setLastClicked(uid)
  }

  function clearSelection() {
    setSelectedIds(new Set())
    setLastClicked(null)
    setSegment(null)
  }

  // 整段说话人映射：把该 speaker_label 的所有行一次性归属 → reload
  async function applySpeakerMap(personId: number | null) {
    if (!speakerMap || !data) return
    await relabelSpeaker(data.id, speakerMap.label, personId)
    reload()
  }

  // 就这段分析（解读层，M4 占位 stub）
  async function analyzeSegment() {
    if (orderedSelectedIds.length === 0) return
    setAnalyzing(true)
    setSegment(null)
    try {
      const res = await analyze(orderedSelectedIds)
      setSegment(res)
    } catch {
      // analyze 失败：清空忙碌态，下方解读卡显示默认占位
      setSegment(null)
    } finally {
      setAnalyzing(false)
    }
  }

  const selectedCount = orderedSelectedIds.length

  return (
    <section className="pb-24">
      <PageHeader
        title={data.note?.trim() || t('page.fallbackTitle')}
        description={formatDateTime(data.started_at)}
        actions={
          <Button variant="secondary" onClick={() => setReviewOpen(true)}>
            {t('page.review')}
          </Button>
        }
      />

      {/* 真相锚：整段波形 */}
      {data.has_audio && (
        <div className="mb-4 rounded-card border border-line bg-card p-4">
          <WaveformPlayer src={src} />
        </div>
      )}

      {/* ① 事实摘要条 */}
      <SummaryBand data={data} />

      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        {/* 事实层：转写正文 + 逐行交互 */}
        <div className="min-w-0">
          {data.utterances.length === 0 ? (
            <EmptyState title={t('page.emptyTranscript')} />
          ) : (
            <ol className="space-y-1">
              {data.utterances.map((u, i) => (
                <UtteranceRow
                  key={u.id}
                  u={u}
                  index={i}
                  src={src}
                  hasAudio={data.has_audio}
                  participants={data.participants}
                  selected={selectedIds.has(u.id)}
                  onToggleSelect={toggleSelect}
                  onReload={reload}
                  onOpenSpeakerMap={setSpeakerMap}
                />
              ))}
            </ol>
          )}
        </div>

        {/* 解读层：页边旁批 */}
        <aside className="space-y-4 lg:pt-1">
          <InterpretationCard
            title={t('page.summaryTitle')}
            interpretation={summary.data}
            loading={summary.loading}
          />

          {/* ④ 「就这段分析」结果，单独一张解读卡（仅在发起后出现） */}
          {(analyzing || segment) && (
            <InterpretationCard
              title={t('page.segmentTitle', { count: selectedCount })}
              interpretation={segment}
              loading={analyzing}
            />
          )}
        </aside>
      </div>

      {/* ③ 整段说话人映射浮层：覆盖在正文左上方 */}
      {speakerMap && (
        <div className="fixed inset-0 z-20" aria-hidden={false}>
          <div className="absolute left-1/2 top-1/3 -translate-x-1/2">
            <PersonPicker
              title={t('page.speakerMapTitle', { label: speakerMap.label })}
              currentPersonId={speakerMap.personId}
              allowClear
              onClose={() => setSpeakerMap(null)}
              onPick={applySpeakerMap}
            />
          </div>
        </div>
      )}

      {/* ④ 划选后的浮动操作条 */}
      {selectedCount > 0 && (
        <div className="fixed inset-x-0 bottom-6 z-20 flex justify-center px-4">
          <div className="flex items-center gap-3 rounded-card border border-line bg-paper px-4 py-2.5 shadow-lg">
            <span className="font-ui text-sm text-ink">
              {t('selection.selected', { count: selectedCount })}
            </span>
            <Button
              variant="primary"
              onClick={() => void analyzeSegment()}
              disabled={analyzing}
            >
              {analyzing ? t('selection.analyzing') : t('selection.analyzeSegment')}
            </Button>
            <Button variant="ghost" onClick={clearSelection}>
              {t('selection.clear')}
            </Button>
          </div>
        </div>
      )}

      {/* M3 复盘模式（§10.6）：覆盖层，四步引导，事实回放用本对话真数据 */}
      {reviewOpen && (
        <ReviewOverlay
          scope="conversation"
          id={data.id}
          title={data.note?.trim() || t('page.fallbackTitle')}
          onClose={() => setReviewOpen(false)}
        />
      )}
    </section>
  )
}
