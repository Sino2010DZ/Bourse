import { useEffect } from 'react'
import { useI18n } from '../../i18n'
import { LEGAL } from '../../config'
import { LEGAL_CONTENT } from './content'

export function LegalPage({ kind }: { kind: 'terms' | 'privacy' }) {
  const { t, lang, intl } = useI18n()
  useEffect(() => { window.scrollTo(0, 0) }, [kind])
  const content = LEGAL_CONTENT[kind][lang] ?? LEGAL_CONTENT[kind].en
  return (
    <div className="page">
      <article className="card glass legal">
        <h1>{t(`legal.${kind}`)}</h1>
        <p className="muted small">{t('legal.updated', { date: new Date(LEGAL.updated).toLocaleDateString(intl) })}</p>
        {content}
      </article>
    </div>
  )
}
