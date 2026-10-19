// Catalogue des valeurs proposées dans la recherche.
// « tv » = code TradingView (affichage), « eod » = code EODHD (prix côté serveur).
// On peut ajouter des lignes librement ; un symbole TradingView inconnu peut aussi
// être saisi directement (ex. « SIX:SREN »).

export type Market = 'us' | 'ch' | 'eu' | 'crypto'
export type AssetType = 'stock' | 'etf' | 'crypto'

export interface SymbolInfo {
  tv: string
  name: string
  market: Market
  type: AssetType
  currency: string
  eod?: string
}

type Row = [tv: string, name: string, type?: AssetType]

const US: Row[] = [
  ['NASDAQ:AAPL', 'Apple'], ['NASDAQ:MSFT', 'Microsoft'], ['NASDAQ:NVDA', 'NVIDIA'], ['NASDAQ:AMZN', 'Amazon'],
  ['NASDAQ:GOOGL', 'Alphabet (Google)'], ['NASDAQ:META', 'Meta Platforms'], ['NASDAQ:TSLA', 'Tesla'],
  ['NASDAQ:AVGO', 'Broadcom'], ['NASDAQ:COST', 'Costco'], ['NASDAQ:NFLX', 'Netflix'], ['NASDAQ:AMD', 'AMD'],
  ['NASDAQ:INTC', 'Intel'], ['NASDAQ:ADBE', 'Adobe'], ['NASDAQ:CSCO', 'Cisco'], ['NASDAQ:PEP', 'PepsiCo'],
  ['NASDAQ:PYPL', 'PayPal'], ['NASDAQ:COIN', 'Coinbase'], ['NASDAQ:PLTR', 'Palantir'], ['NASDAQ:SBUX', 'Starbucks'],
  ['NYSE:BRK.B', 'Berkshire Hathaway B'], ['NYSE:JPM', 'JPMorgan Chase'], ['NYSE:V', 'Visa'], ['NYSE:MA', 'Mastercard'],
  ['NYSE:JNJ', 'Johnson & Johnson'], ['NYSE:WMT', 'Walmart'], ['NYSE:PG', 'Procter & Gamble'], ['NYSE:XOM', 'Exxon Mobil'],
  ['NYSE:UNH', 'UnitedHealth'], ['NYSE:HD', 'Home Depot'], ['NYSE:KO', 'Coca-Cola'], ['NYSE:DIS', 'Walt Disney'],
  ['NYSE:ORCL', 'Oracle'], ['NYSE:CRM', 'Salesforce'], ['NYSE:PFE', 'Pfizer'], ['NYSE:MRK', 'Merck & Co'],
  ['NYSE:ABBV', 'AbbVie'], ['NYSE:LLY', 'Eli Lilly'], ['NYSE:CVX', 'Chevron'], ['NYSE:NKE', 'Nike'],
  ['NYSE:MCD', 'McDonald’s'], ['NYSE:BA', 'Boeing'], ['NYSE:IBM', 'IBM'], ['NYSE:UBER', 'Uber'],
  ['NYSE:GS', 'Goldman Sachs'], ['NYSE:T', 'AT&T'], ['NYSE:VZ', 'Verizon'],
  ['AMEX:SPY', 'SPDR S&P 500 ETF', 'etf'], ['AMEX:VOO', 'Vanguard S&P 500 ETF', 'etf'], ['AMEX:IVV', 'iShares Core S&P 500 ETF', 'etf'],
  ['NASDAQ:QQQ', 'Invesco QQQ (Nasdaq 100)', 'etf'], ['AMEX:VTI', 'Vanguard Total Stock Market ETF', 'etf'],
  ['AMEX:DIA', 'SPDR Dow Jones ETF', 'etf'], ['AMEX:IWM', 'iShares Russell 2000 ETF', 'etf'], ['AMEX:GLD', 'SPDR Gold Shares', 'etf'],
  ['AMEX:EEM', 'iShares MSCI Emerging Markets ETF', 'etf'], ['AMEX:XLK', 'Technology Select Sector SPDR', 'etf'],
  ['NASDAQ:TLT', 'iShares 20+ Year Treasury Bond ETF', 'etf'], ['AMEX:ARKK', 'ARK Innovation ETF', 'etf'],
]

const CH: Row[] = [
  ['SIX:NESN', 'Nestlé'], ['SIX:NOVN', 'Novartis'], ['SIX:ROG', 'Roche'], ['SIX:UBSG', 'UBS Group'],
  ['SIX:ZURN', 'Zurich Insurance'], ['SIX:ABBN', 'ABB'], ['SIX:CFR', 'Richemont'], ['SIX:SIKA', 'Sika'],
  ['SIX:LONN', 'Lonza'], ['SIX:GIVN', 'Givaudan'], ['SIX:SREN', 'Swiss Re'], ['SIX:ALC', 'Alcon'],
  ['SIX:HOLN', 'Holcim'], ['SIX:GEBN', 'Geberit'], ['SIX:PGHN', 'Partners Group'], ['SIX:SCMN', 'Swisscom'],
  ['SIX:SLHN', 'Swiss Life'], ['SIX:LOGN', 'Logitech'], ['SIX:SOON', 'Sonova'], ['SIX:KNIN', 'Kuehne + Nagel'],
  ['SIX:SGSN', 'SGS'], ['SIX:BAER', 'Julius Bär'], ['SIX:TEMN', 'Temenos'], ['SIX:SCHP', 'Schindler'],
  ['SIX:LISN', 'Lindt & Sprüngli'], ['SIX:SWON', 'SoftwareONE'], ['SIX:UHR', 'Swatch Group'], ['SIX:BALN', 'Bâloise'],
  ['SIX:CSSMI', 'iShares SMI ETF (CH)', 'etf'], ['SIX:CHSPI', 'iShares Core SPI ETF (CH)', 'etf'],
]

// [tv, nom, type, devise, suffixe EODHD]
const EU: [string, string, AssetType, string, string][] = [
  ['XETR:SAP', 'SAP', 'stock', 'EUR', 'XETRA'], ['XETR:SIE', 'Siemens', 'stock', 'EUR', 'XETRA'],
  ['XETR:ALV', 'Allianz', 'stock', 'EUR', 'XETRA'], ['XETR:DTE', 'Deutsche Telekom', 'stock', 'EUR', 'XETRA'],
  ['XETR:BMW', 'BMW', 'stock', 'EUR', 'XETRA'], ['XETR:MBG', 'Mercedes-Benz', 'stock', 'EUR', 'XETRA'],
  ['XETR:VOW3', 'Volkswagen', 'stock', 'EUR', 'XETRA'], ['XETR:BAS', 'BASF', 'stock', 'EUR', 'XETRA'],
  ['XETR:BAYN', 'Bayer', 'stock', 'EUR', 'XETRA'], ['XETR:ADS', 'Adidas', 'stock', 'EUR', 'XETRA'],
  ['XETR:IFX', 'Infineon', 'stock', 'EUR', 'XETRA'], ['XETR:DBK', 'Deutsche Bank', 'stock', 'EUR', 'XETRA'],
  ['XETR:MUV2', 'Munich Re', 'stock', 'EUR', 'XETRA'], ['XETR:RHM', 'Rheinmetall', 'stock', 'EUR', 'XETRA'],
  ['EURONEXT:MC', 'LVMH', 'stock', 'EUR', 'PA'], ['EURONEXT:OR', 'L’Oréal', 'stock', 'EUR', 'PA'],
  ['EURONEXT:TTE', 'TotalEnergies', 'stock', 'EUR', 'PA'], ['EURONEXT:SAN', 'Sanofi', 'stock', 'EUR', 'PA'],
  ['EURONEXT:AIR', 'Airbus', 'stock', 'EUR', 'PA'], ['EURONEXT:BNP', 'BNP Paribas', 'stock', 'EUR', 'PA'],
  ['EURONEXT:SU', 'Schneider Electric', 'stock', 'EUR', 'PA'], ['EURONEXT:AI', 'Air Liquide', 'stock', 'EUR', 'PA'],
  ['EURONEXT:RMS', 'Hermès', 'stock', 'EUR', 'PA'], ['EURONEXT:KER', 'Kering', 'stock', 'EUR', 'PA'],
  ['EURONEXT:ASML', 'ASML', 'stock', 'EUR', 'AS'], ['EURONEXT:INGA', 'ING Groep', 'stock', 'EUR', 'AS'],
  ['EURONEXT:ADYEN', 'Adyen', 'stock', 'EUR', 'AS'], ['EURONEXT:HEIA', 'Heineken', 'stock', 'EUR', 'AS'],
  ['EURONEXT:ABI', 'AB InBev', 'stock', 'EUR', 'BR'],
  ['MIL:ENI', 'Eni', 'stock', 'EUR', 'MI'], ['MIL:ISP', 'Intesa Sanpaolo', 'stock', 'EUR', 'MI'],
  ['MIL:RACE', 'Ferrari', 'stock', 'EUR', 'MI'], ['MIL:UCG', 'UniCredit', 'stock', 'EUR', 'MI'],
  ['BME:SAN', 'Banco Santander', 'stock', 'EUR', 'MC'], ['BME:ITX', 'Inditex', 'stock', 'EUR', 'MC'],
  ['BME:IBE', 'Iberdrola', 'stock', 'EUR', 'MC'],
  ['LSE:SHEL', 'Shell', 'stock', 'GBX', 'LSE'], ['LSE:AZN', 'AstraZeneca', 'stock', 'GBX', 'LSE'],
  ['LSE:HSBA', 'HSBC', 'stock', 'GBX', 'LSE'], ['LSE:ULVR', 'Unilever', 'stock', 'GBX', 'LSE'],
  ['LSE:BP', 'BP', 'stock', 'GBX', 'LSE'],
  ['XETR:EUNL', 'iShares Core MSCI World ETF', 'etf', 'EUR', 'XETRA'],
  ['XETR:VWCE', 'Vanguard FTSE All-World ETF', 'etf', 'EUR', 'XETRA'],
  ['XETR:EXS1', 'iShares Core DAX ETF', 'etf', 'EUR', 'XETRA'],
  ['EURONEXT:CW8', 'Amundi MSCI World ETF', 'etf', 'EUR', 'PA'],
]

const CRYPTO: [string, string][] = [
  ['BTC', 'Bitcoin'], ['ETH', 'Ethereum'], ['SOL', 'Solana'], ['BNB', 'BNB'], ['XRP', 'XRP'],
  ['ADA', 'Cardano'], ['DOGE', 'Dogecoin'], ['DOT', 'Polkadot'], ['AVAX', 'Avalanche'], ['LINK', 'Chainlink'],
  ['LTC', 'Litecoin'], ['TRX', 'TRON'],
]

const ticker = (tv: string) => tv.split(':')[1]

export const CATALOG: SymbolInfo[] = [
  ...US.map(([tv, name, type = 'stock']): SymbolInfo => ({
    tv, name, type, market: 'us', currency: 'USD', eod: `${ticker(tv).replace('.', '-')}.US`,
  })),
  ...CH.map(([tv, name, type = 'stock']): SymbolInfo => ({
    tv, name, type, market: 'ch', currency: 'CHF', eod: `${ticker(tv)}.SW`,
  })),
  ...EU.map(([tv, name, type, currency, suffix]): SymbolInfo => ({
    tv, name, type, market: 'eu', currency, eod: `${ticker(tv)}.${suffix}`,
  })),
  ...CRYPTO.map(([code, name]): SymbolInfo => ({
    tv: `BINANCE:${code}USDT`, name, type: 'crypto', market: 'crypto', currency: 'USD', eod: `${code}-USD.CC`,
  })),
]

const BY_TV = new Map(CATALOG.map((s) => [s.tv, s]))

// Format accepté pour un symbole TradingView saisi à la main : BOURSE:CODE
export const TV_SYMBOL_RE = /^[A-Z0-9_]{1,20}:[A-Z0-9._!-]{1,20}$/

export function isValidTvSymbol(s: string): boolean {
  return TV_SYMBOL_RE.test(s)
}

const EXCHANGE_SUFFIX: Record<string, { suffix: string; market: Market; currency: string }> = {
  NASDAQ: { suffix: 'US', market: 'us', currency: 'USD' },
  NYSE: { suffix: 'US', market: 'us', currency: 'USD' },
  AMEX: { suffix: 'US', market: 'us', currency: 'USD' },
  SIX: { suffix: 'SW', market: 'ch', currency: 'CHF' },
  XETR: { suffix: 'XETRA', market: 'eu', currency: 'EUR' },
  MIL: { suffix: 'MI', market: 'eu', currency: 'EUR' },
  BME: { suffix: 'MC', market: 'eu', currency: 'EUR' },
  LSE: { suffix: 'LSE', market: 'eu', currency: 'GBX' },
}

// Retrouve la fiche d'un symbole ; pour un symbole hors catalogue, on devine
// à partir de la bourse (Euronext est ambigu : pas de prix serveur dans ce cas).
export function getSymbol(tv: string): SymbolInfo | null {
  const known = BY_TV.get(tv)
  if (known) return known
  if (!isValidTvSymbol(tv)) return null
  const [exchange, code] = tv.split(':')
  const crypto = /^(BINANCE|COINBASE|BITSTAMP|KRAKEN):([A-Z0-9]+?)(USDT|USD|USDC)$/.exec(tv)
  if (crypto) {
    return { tv, name: crypto[2], market: 'crypto', type: 'crypto', currency: 'USD', eod: `${crypto[2]}-USD.CC` }
  }
  const ex = EXCHANGE_SUFFIX[exchange]
  if (ex) {
    const eodCode = ex.suffix === 'US' ? code.replace('.', '-') : code
    return { tv, name: code, market: ex.market, type: 'stock', currency: ex.currency, eod: `${eodCode}.${ex.suffix}` }
  }
  return { tv, name: code, market: exchange === 'EURONEXT' ? 'eu' : 'us', type: 'stock', currency: exchange === 'EURONEXT' ? 'EUR' : 'USD' }
}

export function displayTicker(tv: string): string {
  const t = tv.split(':')[1] ?? tv
  return tv.startsWith('BINANCE:') ? t.replace(/USDT$/, '') : t
}

const normalize = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

// Recherche par nom ou symbole, du plus pertinent au moins pertinent.
export function searchSymbols(query: string, market: Market | 'all' = 'all', limit = 12): SymbolInfo[] {
  const q = normalize(query.trim())
  const pool = market === 'all' ? CATALOG : CATALOG.filter((s) => s.market === market)
  if (!q) return pool.slice(0, limit)
  const scored: { s: SymbolInfo; score: number }[] = []
  for (const s of pool) {
    const tick = normalize(displayTicker(s.tv))
    const name = normalize(s.name)
    let score = 0
    if (tick === q) score = 100
    else if (tick.startsWith(q)) score = 80
    else if (name.startsWith(q)) score = 70
    else if (name.split(/[\s().&-]+/).some((w) => w.startsWith(q))) score = 60
    else if (name.includes(q) || normalize(s.tv).includes(q)) score = 40
    if (score) scored.push({ s, score })
  }
  return scored.sort((a, b) => b.score - a.score || a.s.name.localeCompare(b.s.name)).slice(0, limit).map((x) => x.s)
}

export const SUGGESTIONS = ['SIX:NESN', 'NASDAQ:AAPL', 'SIX:NOVN', 'NASDAQ:NVDA', 'XETR:SAP', 'EURONEXT:MC', 'BINANCE:BTCUSDT', 'AMEX:SPY']

export const TICKER_TAPE = ['SIX:NESN', 'SIX:ROG', 'SIX:UBSG', 'NASDAQ:AAPL', 'NASDAQ:NVDA', 'NASDAQ:MSFT', 'XETR:SAP', 'EURONEXT:ASML', 'BINANCE:BTCUSDT', 'BINANCE:ETHUSDT']
