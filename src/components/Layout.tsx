import { NavLink, Outlet, Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { Icon, type IconName } from './Icon'
import { Logo } from './Logo'
import { LangButton, ThemeButton } from './Toggles'
import { CookieBanner } from './CookieBanner'
import { InstallBanner } from './InstallBanner'
import { openConsentSettings } from '../lib/consent'
import { APP_NAME } from '../config'
import type { MessageKey } from '../i18n'

const NAV: { to: string; icon: IconName; label: MessageKey }[] = [
  { to: '/', icon: 'markets', label: 'nav.markets' },
  { to: '/portfolio', icon: 'portfolio', label: 'nav.portfolio' },
  { to: '/alerts', icon: 'alerts', label: 'nav.alerts' },
  { to: '/pricing', icon: 'pricing', label: 'nav.pricing' },
  { to: '/account', icon: 'account', label: 'nav.account' },
]

export function Layout() {
  const { t } = useI18n()
  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true"><span /><span /><span /></div>

      <aside className="sidebar glass">
        <Link to="/" className="sidebar-logo"><Logo /></Link>
        <nav className="side-nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'} className="side-link">
              <Icon name={n.icon} /> <span>{t(n.label)}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-tools"><LangButton /><ThemeButton /></div>
      </aside>

      <header className="topbar glass">
        <Link to="/"><Logo size={26} /></Link>
        <div className="topbar-tools"><LangButton /><ThemeButton /></div>
      </header>

      <div className="disclaimer glass" role="note">
        <Icon name="info" size={16} /> <span>{t('disclaimer')}</span>
      </div>

      <main className="main">
        <InstallBanner />
        <Outlet />
        <footer className="footer">
          <p className="footer-warn">{t('disclaimer')}</p>
          <p>{t('footer.data')} {t('watchlist.delayed')}.</p>
          <p className="footer-links">
            <Link to="/legal/terms">{t('legal.terms')}</Link>
            <Link to="/legal/privacy">{t('legal.privacy')}</Link>
            <button className="link-btn" onClick={openConsentSettings}>{t('account.cookieSettings')}</button>
          </p>
          <p>© {new Date().getFullYear()} {APP_NAME}</p>
        </footer>
      </main>

      <nav className="tabbar glass" aria-label="Navigation">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className="tab-link">
            <Icon name={n.icon} size={22} />
            <span>{t(n.label)}</span>
          </NavLink>
        ))}
      </nav>

      <CookieBanner />
    </div>
  )
}
