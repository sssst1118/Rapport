/*
 * 404 —— 走错页时的安静占位。
 */

import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'

export function NotFoundPage() {
  return (
    <section>
      <PageHeader title="这里什么也没有" description="你要找的页面不存在。" />
      <Link to="/" className="font-ui text-sm font-medium text-pine hover:underline">
        回到今日
      </Link>
    </section>
  )
}
