/*
 * 路由表。所有页面都套在 AppShell 内（共享顶栏 + 导航）。
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { TodayPage } from './pages/TodayPage'
import { ConversationPage } from './pages/ConversationPage'
import { PeoplePage } from './pages/PeoplePage'
import { PersonPage } from './pages/PersonPage'
import { GraphPage } from './pages/GraphPage'
import { StyleguidePage } from './pages/StyleguidePage'
import { NotFoundPage } from './pages/NotFoundPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<TodayPage />} />
          <Route path="/conversations/:id" element={<ConversationPage />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/people/:id" element={<PersonPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/styleguide" element={<StyleguidePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
