import { describe, expect, it } from 'vitest'
import { CATALOG, displayTicker, getSymbol, isValidTvSymbol, searchSymbols, SUGGESTIONS, TICKER_TAPE } from '../../src/lib/symbols'

describe('catalogue', () => {
  it('chaque symbole est unique, valide et a un code de prix', () => {
    const tvs = CATALOG.map((s) => s.tv)
    expect(new Set(tvs).size).toBe(tvs.length)
    for (const s of CATALOG) {
      expect(isValidTvSymbol(s.tv), s.tv).toBe(true)
      expect(s.eod, s.tv).toMatch(/^[A-Z0-9-]+\.[A-Z]+$/)
    }
  })
  it('couvre les 4 marchés', () => {
    for (const m of ['us', 'ch', 'eu', 'crypto']) expect(CATALOG.some((s) => s.market === m)).toBe(true)
  })
  it('suggestions et bandeau pointent vers le catalogue', () => {
    for (const s of [...SUGGESTIONS, ...TICKER_TAPE]) expect(CATALOG.some((c) => c.tv === s), s).toBe(true)
  })
})

describe('recherche', () => {
  it('trouve par symbole exact en premier', () => {
    expect(searchSymbols('aapl')[0].tv).toBe('NASDAQ:AAPL')
  })
  it('trouve par nom, sans tenir compte des accents', () => {
    expect(searchSymbols('nestle')[0].tv).toBe('SIX:NESN')
    expect(searchSymbols('Hermes')[0].tv).toBe('EURONEXT:RMS')
  })
  it('filtre par marché', () => {
    const r = searchSymbols('', 'crypto')
    expect(r.length).toBeGreaterThan(0)
    expect(r.every((s) => s.market === 'crypto')).toBe(true)
  })
  it('trouve un mot au milieu du nom', () => {
    expect(searchSymbols('world').some((s) => s.tv === 'XETR:EUNL')).toBe(true)
  })
})

describe('symboles hors catalogue', () => {
  it('devine le code de prix selon la bourse', () => {
    expect(getSymbol('SIX:EMSN')?.eod).toBe('EMSN.SW')
    expect(getSymbol('NYSE:BRK.A')?.eod).toBe('BRK-A.US')
    expect(getSymbol('XETR:HEN3')?.eod).toBe('HEN3.XETRA')
    expect(getSymbol('BINANCE:PEPEUSDT')?.eod).toBe('PEPE-USD.CC')
  })
  it('Euronext hors catalogue : pas de prix serveur (bourse ambiguë)', () => {
    expect(getSymbol('EURONEXT:XYZ')?.eod).toBeUndefined()
  })
  it('refuse les saisies invalides', () => {
    expect(getSymbol('<script>')).toBeNull()
    expect(isValidTvSymbol('AAPL')).toBe(false)
  })
  it('affiche un ticker lisible', () => {
    expect(displayTicker('BINANCE:BTCUSDT')).toBe('BTC')
    expect(displayTicker('SIX:NESN')).toBe('NESN')
  })
})
