/*
 * AppShell —— 应用骨架：左侧导航 + 常驻顶栏 + 主内容区。
 *
 * 顶栏左上：波形品牌印记（WaveformMark）+ "Rapport" 字样 —— 反复露出的视觉签名。
 * 顶栏右侧：常驻的 RecordingStatus（录制状态指示）。
 * 左侧导航：今日 / 人物 / 关系图，图标 + 中文名；外加一个「样式手册」入口便于核对设计系统。
 *
 * 移动端：左栏收成顶部一行图标导航（窄屏可用），内容区始终可滚动。
 */

import { NavLink, Outlet } from 'react-router-dom'
import { WaveformMark } from './WaveformMark'
import { RecordingStatus } from './RecordingStatus'
import { TodayIcon, PeopleIcon, GraphIcon } from './NavIcons'

interface NavItem {
  to: string
  label: string
  icon: (p: { className?: string }) => React.ReactElement
  end?: boolean
}

const NAV: NavItem[] = [
  { to: '/', label: '今日', icon: TodayIcon, end: true },
  { to: '/people', label: '人物', icon: PeopleIcon },
  { to: '/graph', label: '关系图', icon: GraphIcon },
]

function navClass({ isActive }: { isActive: boolean }): string {
  return [
    'flex items-center gap-3 rounded-sm px-3 py-2 font-ui text-sm transition-colors',
    isActive
      ? 'bg-pine/10 font-medium text-pine'
      : 'text-ink-soft hover:bg-ink/5 hover:text-ink',
  ].join(' ')
}

export function AppShell() {
  return (
    <div className="min-h-dvh bg-paper text-ink">
      {/* 常驻顶栏 */}
      <header className="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2.5" aria-label="Rapport 首页">
            <WaveformMark height={20} />
            <span className="font-ui text-lg font-semibold tracking-tight text-ink">
              Rapport
            </span>
          </NavLink>
          <div className="ml-auto">
            <RecordingStatus />
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl gap-6 px-4 py-6 sm:px-6">
        {/* 左侧导航（窄屏退到顶部横排） */}
        <nav className="hidden w-44 shrink-0 sm:block" aria-label="主导航">
          <div className="sticky top-20 space-y-1">
            {NAV.map((item) => {
              const Icon = item.icon
              return (
                <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
                  <Icon className="shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              )
            })}

            {/* 分隔的「——」与样式手册入口 */}
            <div className="my-2 border-t border-line" />
            <NavLink to="/styleguide" className={navClass}>
              <span
                aria-hidden="true"
                className="grid size-[18px] place-items-center font-mono text-ink-soft"
              >
                §
              </span>
              <span>样式手册</span>
            </NavLink>
          </div>
        </nav>

        {/* 窄屏顶部横排导航 */}
        <nav
          className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t border-line bg-paper/95 px-2 py-1.5 backdrop-blur sm:hidden"
          aria-label="主导航"
        >
          {NAV.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-0.5 rounded-sm px-3 py-1 font-ui text-xs ${
                    isActive ? 'text-pine' : 'text-ink-soft'
                  }`
                }
              >
                <Icon />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* 主内容 */}
        <main className="min-w-0 flex-1 pb-16 sm:pb-0">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
