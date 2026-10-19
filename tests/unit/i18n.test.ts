import { describe, expect, it } from 'vitest'
import { fr } from '../../src/i18n/messages/fr'
import { en } from '../../src/i18n/messages/en'
import { translate } from '../../src/i18n'

function keys(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) => (typeof v === 'string' ? [`${prefix}${k}`] : keys(v, `${prefix}${k}.`)))
}
function values(obj: object): string[] {
  return Object.values(obj).flatMap((v) => (typeof v === 'string' ? [v] : values(v)))
}

describe('traductions', () => {
  it('le français et l’anglais ont exactement les mêmes clés', () => {
    expect(keys(en).sort()).toEqual(keys(fr).sort())
  })
  it('aucun texte vide', () => {
    for (const v of [...values(fr), ...values(en)]) expect(v.trim()).not.toBe('')
  })
  it('les variables {x} sont les mêmes dans chaque langue', () => {
    const vars = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join()
    for (const k of keys(fr)) expect(vars(translate(en, k as never)), k).toBe(vars(translate(fr, k as never)))
  })
  it('remplace les variables', () => {
    expect(translate(fr, 'watchlist.count', { count: 3, limit: 5 })).toBe('3 / 5')
  })
  it('contient le message obligatoire', () => {
    expect(fr.disclaimer).toBe('Informations non contractuelles, ceci n’est pas un conseil en investissement.')
  })
})
