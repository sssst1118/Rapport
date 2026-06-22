/*
 * 关系图 Graph —— 纯占位。
 * 这里将来放「人 与 人 的关系网络」。现在给一个用了设计系统的安静占位，说明意图即可。
 */

import { PageHeader } from '../components/PageHeader'
import { EmptyState } from '../components/states'

export function GraphPage() {
  return (
    <section>
      <PageHeader
        title="关系图"
        description="把人和人之间的联系画成一张网，看清你身边的人际结构。"
      />
      <EmptyState
        title="关系图即将到来"
        hint="这一屏会在后续阶段实现：以「人即颜色」的节点连成关系网络。"
      />
    </section>
  )
}
