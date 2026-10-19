import { Component, type ReactNode } from 'react'
import { useI18n } from '../i18n'

function CrashScreen() {
  const { t } = useI18n()
  return (
    <div className="page"><div className="card glass gate">
      <p>{t('crash.title')}</p>
      <button className="btn btn-primary" onClick={() => window.location.reload()}>{t('crash.reload')}</button>
    </div></div>
  )
}

// Si une page plante, on affiche un message propre au lieu d'un écran blanc.
export class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { failed: boolean; key?: string }> {
  state = { failed: false, key: this.props.resetKey }
  static getDerivedStateFromError() { return { failed: true } }
  static getDerivedStateFromProps(props: { resetKey?: string }, state: { failed: boolean; key?: string }) {
    return props.resetKey !== state.key ? { failed: false, key: props.resetKey } : null
  }
  componentDidCatch(error: unknown) { console.error(error) }
  render() { return this.state.failed ? <CrashScreen /> : this.props.children }
}
