import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { Icon } from './Icon'

export function PremiumGate() {
  const { t } = useI18n()
  return (
    <div className="card glass gate">
      <Icon name="star" size={32} />
      <p>{t('common.premiumOnly')}</p>
      <Link className="btn btn-primary" to="/pricing">{t('common.upgrade')}</Link>
    </div>
  )
}
