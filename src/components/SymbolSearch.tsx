import { useId, useMemo, useState, type KeyboardEvent } from 'react'
import { useI18n } from '../i18n'
import { displayTicker, getSymbol, isValidTvSymbol, searchSymbols, type Market, type SymbolInfo } from '../lib/symbols'
import { Icon } from './Icon'

const MARKETS: (Market | 'all')[] = ['all', 'us', 'ch', 'eu', 'crypto']

interface Props {
  onSelect: (s: SymbolInfo) => void
  // Si fourni : un bouton « + » par résultat pour l'ajouter directement.
  onAdd?: (s: SymbolInfo) => void
  isAdded?: (tv: string) => boolean
  autoFocus?: boolean
}

export function SymbolSearch({ onSelect, onAdd, isAdded, autoFocus }: Props) {
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const [market, setMarket] = useState<Market | 'all'>('all')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const listId = useId()

  const results = useMemo(() => {
    const found = searchSymbols(query, market, 10).map((info) => ({ info, custom: false }))
    const typed = query.trim().toUpperCase()
    if (isValidTvSymbol(typed) && !found.some((r) => r.info.tv === typed)) {
      const info = getSymbol(typed)
      if (info) found.push({ info, custom: true })
    }
    return found
  }, [query, market])

  const pick = (s: SymbolInfo) => {
    onSelect(s)
    setQuery('')
    setOpen(false)
  }

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter' && results[active]) { e.preventDefault(); pick(results[active].info) }
    else if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div className="search">
      <div className="search-box glass">
        <Icon name="search" />
        <input
          type="search"
          role="combobox"
          aria-label={t('search.label')}
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          placeholder={t('search.placeholder')}
          value={query}
          autoFocus={autoFocus}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); setActive(0) }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={onKey}
        />
      </div>
      {open && (
        <div className="search-pop glass">
          <div className="chips" role="group">
            {MARKETS.map((m) => (
              <button key={m} type="button" className={`chip ${market === m ? 'on' : ''}`}
                onMouseDown={(e) => e.preventDefault()} onClick={() => { setMarket(m); setActive(0) }}>
                {t(`search.filters.${m}`)}
              </button>
            ))}
          </div>
          <ul id={listId} role="listbox" className={`search-list ${onAdd ? 'with-add' : ''}`}>
            {results.length === 0 && <li className="muted empty-row">{t('search.noResults')}</li>}
            {results.map(({ info: s, custom }, i) => (
              <li key={s.tv} role="option" aria-selected={i === active} className={i === active ? 'active' : ''}
                onMouseDown={(e) => e.preventDefault()} onClick={() => pick(s)} onMouseEnter={() => setActive(i)}>
                <span className="sym">{displayTicker(s.tv)}</span>
                <span className="name">
                  {custom ? t('search.custom', { symbol: s.tv }) : s.name}
                </span>
                <span className="tag">{t(`search.types.${s.type}`)} · {s.tv.split(':')[0]}</span>
                {onAdd && (
                  <button type="button" className="icon-btn add-btn" disabled={isAdded?.(s.tv)}
                    aria-label={`${t('watchlist.add')} ${displayTicker(s.tv)}`}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={(e) => { e.stopPropagation(); onAdd(s); setQuery(''); setOpen(false) }}>
                    <Icon name={isAdded?.(s.tv) ? 'check' : 'plus'} size={18} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
