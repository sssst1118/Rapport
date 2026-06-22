/*
 * WaveformMark —— 品牌印记：一段定格的波形。
 *
 * 这是「真相锚」的徽标形态：一组高低起伏的 pine 色竖条，像一句话被定格成波形。
 * 它在顶栏左上角与 "Rapport" 字样并排出现，是全应用反复露出的视觉签名。
 * 纯 SVG、无依赖、可任意缩放。条形高度是一组手挑的「自然语音包络」，
 * 不对称、有节奏，避免机械等高。
 */

export interface WaveformMarkProps {
  /** 高度（px），默认 22；宽度自适应 */
  height?: number
  className?: string
  title?: string
}

// 一段「自然语音包络」：归一化到 0..1 的条高（手调，含起伏与停顿）
const BARS = [0.28, 0.55, 0.9, 0.62, 1, 0.4, 0.72, 0.34, 0.85, 0.5, 0.66, 0.22]

export function WaveformMark({
  height = 22,
  className = '',
  title = 'Rapport',
}: WaveformMarkProps) {
  const barW = 3
  const gap = 2.4
  const width = BARS.length * barW + (BARS.length - 1) * gap

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      {BARS.map((h, i) => {
        const barH = Math.max(2, h * height)
        const x = i * (barW + gap)
        const y = (height - barH) / 2
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barW}
            height={barH}
            rx={barW / 2}
            fill="var(--pine)"
          />
        )
      })}
    </svg>
  )
}
