/*
 * 404 —— 走错页时的安静占位。
 */

import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/PageHeader'

export function NotFoundPage() {
  const { t } = useTranslation('common')
  return (
    <section>
      <PageHeader title={t('notFound.title')} description={t('notFound.description')} />
      <Link to="/" className="font-ui text-sm font-medium text-pine hover:underline">
        {t('notFound.backToToday')}
      </Link>
    </section>
  )
}
