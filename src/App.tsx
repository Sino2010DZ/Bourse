import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { premiumModeActive } from './config'
import { I18nProvider } from './i18n'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import { DataProvider } from './context/DataContext'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { SymbolPage } from './pages/SymbolPage'
import { NotFound } from './pages/NotFound'

// Pages secondaires chargées à la demande : l'accueil s'affiche plus vite.
const Portfolio = lazy(() => import('./pages/Portfolio').then((m) => ({ default: m.Portfolio })))
const Alerts = lazy(() => import('./pages/Alerts').then((m) => ({ default: m.Alerts })))
const Account = lazy(() => import('./pages/Account').then((m) => ({ default: m.Account })))
const Pricing = lazy(() => import('./pages/Pricing').then((m) => ({ default: m.Pricing })))
const Login = lazy(() => import('./pages/Auth').then((m) => ({ default: m.Login })))
const Signup = lazy(() => import('./pages/Auth').then((m) => ({ default: m.Signup })))
const ForgotPassword = lazy(() => import('./pages/Auth').then((m) => ({ default: m.ForgotPassword })))
const ResetPassword = lazy(() => import('./pages/Auth').then((m) => ({ default: m.ResetPassword })))
const LegalPage = lazy(() => import('./pages/legal/LegalPage').then((m) => ({ default: m.LegalPage })))

export default function App() {
  return (
    <I18nProvider>
      <ThemeProvider>
        <AuthProvider>
          <DataProvider>
            <BrowserRouter>
              <Suspense fallback={null}>
              <Routes>
                <Route element={<Layout />}>
                  <Route index element={<Home />} />
                  <Route path="s/:symbol" element={<SymbolPage />} />
                  <Route path="portfolio" element={<Portfolio />} />
                  <Route path="alerts" element={<Alerts />} />
                  <Route path="account" element={<Account />} />
                  <Route path="pricing" element={premiumModeActive() ? <Pricing /> : <Navigate to="/" replace />} />
                  <Route path="login" element={<Login />} />
                  <Route path="signup" element={<Signup />} />
                  <Route path="forgot-password" element={<ForgotPassword />} />
                  <Route path="reset-password" element={<ResetPassword />} />
                  <Route path="legal/terms" element={<LegalPage kind="terms" />} />
                  <Route path="legal/privacy" element={<LegalPage kind="privacy" />} />
                  <Route path="*" element={<NotFound />} />
                </Route>
              </Routes>
              </Suspense>
            </BrowserRouter>
          </DataProvider>
        </AuthProvider>
      </ThemeProvider>
    </I18nProvider>
  )
}
