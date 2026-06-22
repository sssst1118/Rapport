/*
 * 人即颜色：由 id 或名字稳定哈希到一个受约束的 HSL，再派生出三个用途色。
 *
 * 为什么约束：随机 HSL 会出来一堆刺眼/打架的颜色。我们把
 *   饱和度 S 与亮度 L 收窄到一个「与信笺底色和谐」的窗口，
 *   只让色相 H 在 0..360 自由走 —— 于是不同的人各有辨识度，
 *   又始终是同一套低调、暖意的语气，不会破坏《记录与旁批》的整体观感。
 *
 * 返回三个色：
 *   block —— 实心色块（Avatar 背景、强标识）
 *   tint  —— 极浅底色（行高亮、标签底）
 *   ink   —— 落在 block 上的可读文字色
 */

export interface PersonColor {
  /** 实心标识色（Avatar 背景等） */
  block: string
  /** 极浅的同色调底色 */
  tint: string
  /** 与 block 搭配、保证可读的文字色 */
  ink: string
  /** 原始色相，便于需要时自行扩展 */
  hue: number
}

/** djb2 字符串哈希，稳定且分布良好；对纯数字 key 也走同一条路径以保证一致。 */
function hashKey(key: string | number): number {
  const str = String(key)
  let h = 5381
  for (let i = 0; i < str.length; i++) {
    h = (h * 33) ^ str.charCodeAt(i)
  }
  // 转成无符号 32 位
  return h >>> 0
}

// 受约束的 HSL 窗口：与暖燕麦信笺协调
const SAT = 42 // 饱和度（%）——收窄，避免荧光感
const LIGHT_BLOCK = 46 // 色块亮度（%）——够深以承载白字
const LIGHT_TINT = 93 // 浅底亮度（%）

/**
 * 由稳定 key（人物 id 或名字）得到一组协调的标识色。
 * 同一个 key 永远得到同一组颜色。
 */
export function personColor(key: string | number): PersonColor {
  const hue = hashKey(key) % 360
  const block = `hsl(${hue} ${SAT}% ${LIGHT_BLOCK}%)`
  const tint = `hsl(${hue} ${Math.round(SAT * 0.55)}% ${LIGHT_TINT}%)`
  // block 亮度固定为 46%，白字始终可读
  const ink = '#ffffff'
  return { block, tint, ink, hue }
}
