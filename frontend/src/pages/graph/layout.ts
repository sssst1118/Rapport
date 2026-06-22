/*
 * 纯函数：把契约数据转成仿真节点/连线，计算半径与首字母。
 * 抽出来便于 useForceLayout 与（未来的）测试复用，也让 hook 体保持轻。
 */

import type { GraphData } from '../../api/types'
import { classifyGroup } from './groups'
import type { SimEdge, SimNode } from './types'

/** 取姓名首字：中文取第 1 个字，拉丁取首字母大写（与 components/Avatar.tsx 一致）。 */
export function initialOf(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return '?'
  const first = Array.from(trimmed)[0]
  return /[a-z]/i.test(first) ? first.toUpperCase() : first
}

/**
 * 节点半径：随「说话量 + 对话数」缓增，再对「我」加权放大。
 * 用 sqrt 压住长尾，避免话痨节点撑爆画面；给一个体面的下限保证可点。
 */
export function radiusOf(
  utteranceCount: number,
  conversationCount: number,
  isEgo: boolean,
): number {
  const base = 14
  const mass = utteranceCount + conversationCount * 2
  const r = base + Math.sqrt(mass) * 2.4
  const clamped = Math.min(r, 34)
  return isEgo ? clamped * 1.55 : clamped
}

/** 把 GraphData 编译成仿真用的节点与连线（深拷贝，不动入参）。 */
export function buildSimData(data: GraphData): {
  nodes: SimNode[]
  edges: SimEdge[]
} {
  const nodes: SimNode[] = data.nodes.map((n) => {
    const isEgo = n.relation === '自己'
    return {
      id: n.id,
      name: n.name,
      relation: n.relation,
      utterance_count: n.utterance_count,
      conversation_count: n.conversation_count,
      radius: radiusOf(n.utterance_count, n.conversation_count, isEgo),
      isEgo,
      group: classifyGroup(n.relation),
      initial: initialOf(n.name),
    }
  })

  // 用 source/target id 建连线；d3 在初始化时会把 id 换成节点引用。
  const edges: SimEdge[] = data.edges.map((e) => ({
    source: e.source,
    target: e.target,
    weight: e.weight,
  }))

  return { nodes, edges }
}

/** 边端点取 id —— 初始化前是数字，初始化后是 SimNode；两种都收敛成 id。 */
export function endpointId(end: SimEdge['source']): number {
  return typeof end === 'object' ? (end as SimNode).id : (end as number)
}
