/*
 * 力导向布局用的内部类型 —— 把契约的 GraphNode/GraphEdge 包成 d3-force 能跑的
 * SimulationNodeDatum / SimulationLinkDatum，并预算好渲染需要的派生量（半径、群组）。
 */

import type { SimulationLinkDatum, SimulationNodeDatum } from 'd3-force'
import type { GraphNode } from '../../api/types'
import type { GroupKey } from './groups'

/** 进入仿真的节点：原始数据 + d3 注入的 x/y/vx/vy + 我们预算的渲染派生量。 */
export interface SimNode extends SimulationNodeDatum {
  id: number
  name: string
  relation: string | null
  utterance_count: number
  conversation_count: number
  /** 渲染半径（由说话量/对话数派生） */
  radius: number
  /** 是否「我」—— ego 锚点 */
  isEgo: boolean
  /** 群组粗分 */
  group: GroupKey
  /** 首字母标识（中文取首字，拉丁取首字母大写） */
  initial: string
}

/** 进入仿真的连线：source/target 在初始化后会被 d3 替换为 SimNode 引用。 */
export interface SimEdge extends SimulationLinkDatum<SimNode> {
  weight: number
}

/** 原始 GraphNode（来自 api/types），别名导出以便子模块少写路径。 */
export type RawNode = GraphNode
