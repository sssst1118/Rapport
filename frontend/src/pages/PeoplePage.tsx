/*
 * 人物列表 People（产品方案 §10.4）—— 日常主力导航：「以人为中心」的入口。
 *
 * 取全部人铺成名片网格（色块头像 = 「人即颜色」），点卡片进 /people/:id。
 * 顶部带：搜索（按名字/关系客户端过滤）、排序（最近 / 高频 / 名字）、新建人物。
 *
 * 纪律：「需要跟进」等承诺/话头属于解读，是 M4 的事——这里不伪造。
 * 仅在卡片角落放一个极克制的 iris 小点 + 「M4」微标，表示「此处将由 M4 填」。
 */

import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import type { PersonListItem } from '../api/types'
import { getPeople } from '../api/client'
import { useAsync } from '../lib/useAsync'
import { PageHeader } from '../components/PageHeader'
import { Avatar } from '../components/Avatar'
import { Button } from '../components/Button'
import { LoadingBlock, EmptyState, ErrorState } from '../components/states'
import { PersonCreateDialog } from './people/PersonCreateDialog'

/** 排序方式：最近（人物 id 越大越新）/ 高频（句数）/ 名字（本地序）。 */
type SortKey = 'recent' | 'frequent' | 'name'

/** 排序项：label 走 i18n（people:list.sort.<key>），运行时再翻译 */
const SORTS: { key: SortKey }[] = [
  { key: 'recent' },
  { key: 'frequent' },
  { key: 'name' },
]

function sortPeople(list: PersonListItem[], sort: SortKey): PersonListItem[] {
  const copy = [...list]
  switch (sort) {
    case 'frequent':
      // 句数降序；并列时按名字稳定
      return copy.sort(
        (a, b) =>
          b.utterance_count - a.utterance_count ||
          a.name.localeCompare(b.name, 'zh-CN'),
      )
    case 'name':
      return copy.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
    case 'recent':
    default:
      // 没有显式时间字段，用 id 近似「最近建档/出现」，越大越新
      return copy.sort((a, b) => b.id - a.id)
  }
}

export function PeoplePage() {
  const { t } = useTranslation('people')
  const { data, loading, error, reload } = useAsync((s) => getPeople(s), [])
  const navigate = useNavigate()

  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('recent')
  const [dialogOpen, setDialogOpen] = useState(false)

  // 过滤（名字/关系，大小写不敏感）+ 排序，纯客户端
  const shown = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    const filtered = q
      ? data.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            (p.relation ?? '').toLowerCase().includes(q),
        )
      : data
    return sortPeople(filtered, sort)
  }, [data, query, sort])

  return (
    <section>
      <PageHeader
        title={t('list.title')}
        description={t('list.description')}
        actions={
          <Button variant="primary" onClick={() => setDialogOpen(true)}>
            {t('list.newPerson')}
          </Button>
        }
      />

      {/* 控制条：搜索 + 排序。仅在有数据时显示，空库时不喧宾夺主 */}
      {!loading && !error && data && data.length > 0 && (
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <label className="relative block sm:max-w-xs sm:flex-1">
            <span className="sr-only">{t('list.search.label')}</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('list.search.placeholder')}
              className="w-full rounded-sm border border-line bg-card px-3 py-2 font-ui text-sm text-ink outline-none placeholder:text-ink-soft/50 focus:border-pine-soft"
            />
          </label>

          <div
            role="group"
            aria-label={t('list.sort.groupLabel')}
            className="flex shrink-0 items-center gap-1 rounded-sm border border-line bg-card p-0.5"
          >
            {SORTS.map((s) => {
              const on = s.key === sort
              return (
                <button
                  key={s.key}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setSort(s.key)}
                  className={`rounded-sm px-2.5 py-1 font-ui text-xs font-medium transition-colors ${
                    on
                      ? 'bg-pine text-paper'
                      : 'text-ink-soft hover:text-ink'
                  }`}
                >
                  {t(`list.sort.${s.key}`)}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {loading && <LoadingBlock label={t('list.loading')} />}
      {!loading && error && (
        <ErrorState message={t('list.error')} onRetry={reload} />
      )}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState
          title={t('list.empty.title')}
          hint={t('list.empty.hint')}
        />
      )}

      {/* 有数据、但被搜索过滤为空 */}
      {!loading && !error && data && data.length > 0 && shown.length === 0 && (
        <EmptyState title={t('list.noMatch.title')} hint={t('list.noMatch.hint')} />
      )}

      {!loading && !error && shown.length > 0 && (
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {shown.map((p) => (
            <li key={p.id}>
              <Link
                to={`/people/${p.id}`}
                className="relative flex items-center gap-3 rounded-card border border-line bg-card p-4 transition-colors hover:border-pine-soft"
              >
                <Avatar person={p} size={44} />
                <div className="min-w-0">
                  <p className="truncate font-record text-base text-ink">
                    {p.name}
                  </p>
                  <p className="font-ui text-xs text-ink-soft">
                    {p.relation || t('list.card.noRelation')} ·{' '}
                    <span className="font-mono">{p.utterance_count}</span>{' '}
                    {t('list.card.utteranceCount', {
                      count: p.utterance_count,
                    })}
                  </p>
                </div>

                {/*
                 * 「需要跟进」是承诺/话头解读，属 M4——不伪造。
                 * 仅放一个极克制的 iris 小点 + M4 微标，表示此处将由 M4 填。
                 */}
                <span
                  className="absolute right-3 top-3 flex items-center gap-1"
                  title={t('list.card.m4Title')}
                >
                  <span
                    aria-hidden="true"
                    className="size-1.5 rounded-full bg-iris/60"
                  />
                  <span className="rounded-sm bg-iris/10 px-1 py-px font-mono text-[9px] font-medium uppercase tracking-wide text-iris/80">
                    M4
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <PersonCreateDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(id) => {
          // 建档成功后刷新列表；并直接进入新人的详情页，符合「以人为中心」
          reload()
          navigate(`/people/${id}`)
        }}
      />
    </section>
  )
}
