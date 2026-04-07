import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from './layout/AppShell'
import { navigationItems } from './layout/navigation'
import { AskAiPage } from './pages/AskAiPage'
import { DashboardPage } from './pages/DashboardPage'
import { LandingPage } from './pages/LandingPage'
import { FlashcardsPage } from './pages/FlashcardsPage'
import { HistoryPage } from './pages/HistoryPage'
import { NotesPage } from './pages/NotesPage'
import { PricingPage } from './pages/PricingPage'
import { QuizPage } from './pages/QuizPage'
import { SettingsPage } from './pages/SettingsPage'
import { SummarizePage } from './pages/SummarizePage'

function ShellLayout() {
  const { pathname } = useLocation()
  const currentItem =
    navigationItems.find((item) => item.path === pathname) ?? navigationItems[0]

  return (
    <AppShell currentItem={currentItem}>
      <Outlet />
    </AppShell>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route element={<ShellLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/summarize" element={<SummarizePage />} />
        <Route path="/ask-ai" element={<AskAiPage />} />
        <Route path="/notes" element={<NotesPage />} />
        <Route path="/quiz" element={<QuizPage />} />
        <Route path="/flashcards" element={<FlashcardsPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
