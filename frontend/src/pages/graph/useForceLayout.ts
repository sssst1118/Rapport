/*
 * useForceLayout —— 把 GraphData 跑成一张稳定的力导向布局。
 *
 * 设计：
 *   - 节点用 forceManyBody 互斥 + forceCollide 防重叠；连线用 forceLink（距离随
 *     weight 收紧：越熟越近）；forceX/forceY 轻轻拉回中心，避免孤立节点飘走。
 *   - 「我」(ego) 用 fx/fy 钉在画布中心当锚，整张网围着它长 —— 呼应「人际上下文层」。
 *   - 尊重 prefers-reduced-motion：reduced 时不挂 tick 动画，直接同步 tick 到收敛，
 *     一次性给出静态坐标；非 reduced 时用 tick 计数触发 React 重渲，做平滑收敛动画。
 *   - 卸载时 simulation.stop()，避免后台定时器泄漏。
 *
 * 返回 nodes/edges（带上 d3 注入的 x/y）+ version（坐标版本号，驱动外层重渲）。
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
} from 'd3-force'
import type { Simulation } from 'd3-force'
import type { GraphData } from '../../api/types'
import { buildSimData } from './layout'
import type { SimEdge, SimNode } from './types'

export interface ForceLayout {
  nodes: SimNode[]
  edges: SimEdge[]
  /** 坐标版本号：每次坐标更新自增，供外层依赖以重渲。 */
  version: number
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function useForceLayout(
  data: GraphData | null,
  width: number,
  height: number,
): ForceLayout {
  // 把契约数据编译成仿真节点/连线；data 变才重建。
  const built = useMemo(() => (data ? buildSimData(data) : null), [data])

  const simRef = useRef<Simulation<SimNode, SimEdge> | null>(null)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    if (!built || width <= 0 || height <= 0) return

    const { nodes, edges } = built
    const cx = width / 2
    const cy = height / 2

    // 把 ego 钉在中心，作为整张网的锚。
    for (const n of nodes) {
      if (n.isEgo) {
        n.fx = cx
        n.fy = cy
      }
      // 初始撒在中心附近，收敛更快、更对称。
      if (n.x == null) n.x = cx + (Math.random() - 0.5) * 40
      if (n.y == null) n.y = cy + (Math.random() - 0.5) * 40
    }

    const linkForce = forceLink<SimNode, SimEdge>(edges)
      .id((d) => d.id)
      // 越熟（weight 越大）距离越短，但给下限避免贴死。
      .distance((e) => 120 - Math.min(e.weight, 4) * 12)
      .strength(0.5)

    const sim = forceSimulation<SimNode>(nodes)
      .force('link', linkForce)
      .force('charge', forceManyBody<SimNode>().strength(-340))
      .force('center', forceCenter<SimNode>(cx, cy).strength(0.05))
      .force('collide', forceCollide<SimNode>().radius((d) => d.radius + 8))
      // 轻拉回中心，兜住孤立节点（如小李）不飘出视野。
      .force('x', forceX<SimNode>(cx).strength(0.06))
      .force('y', forceY<SimNode>(cy).strength(0.06))

    simRef.current = sim

    if (prefersReducedMotion()) {
      // 静态：同步 tick 到（近）收敛，一次性出图，不做动画。
      sim.stop()
      const ticks = Math.ceil(
        Math.log(sim.alphaMin()) / Math.log(1 - sim.alphaDecay()),
      )
      sim.tick(ticks)
      setVersion((v) => v + 1)
    } else {
      sim.on('tick', () => setVersion((v) => v + 1))
    }

    return () => {
      sim.on('tick', null)
      sim.stop()
      simRef.current = null
    }
  }, [built, width, height])

  return {
    nodes: built?.nodes ?? [],
    edges: built?.edges ?? [],
    version,
  }
}
