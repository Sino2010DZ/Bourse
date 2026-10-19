import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'

export function NotFound() {
  const { t } = useI18n()
  return <div className="page"><div className="card glass"><p>{t('notFound')}</p><Link className="btn" to="/">{t('nav.markets')}</Link></div></div>
}
