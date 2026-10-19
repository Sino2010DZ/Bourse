import { memo, useEffect, useRef } from 'react'

// Intègre un widget gratuit de TradingView. Les données et leur licence sont
// gérées par TradingView ; le lien « TradingView » doit rester visible.
interface Props {
  widget: 'advanced-chart' | 'single-quote' | 'timeline' | 'ticker-tape' | 'symbol-info'
  config: Record<string, unknown>
  className?: string
  height?: number | string
  attribution?: boolean
}

function TradingViewWidgetBase({ widget, config, className, height, attribution = true }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const json = JSON.stringify(config)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.innerHTML = ''
    const inner = document.createElement('div')
    inner.className = 'tradingview-widget-container__widget'
    el.appendChild(inner)
    const script = document.createElement('script')
    script.src = `https://s3.tradingview.com/external-embedding/embed-widget-${widget}.js`
    script.async = true
    script.type = 'text/javascript'
    script.innerHTML = json
    el.appendChild(script)
    return () => { el.innerHTML = '' }
  }, [widget, json])

  return (
    <div className={`tv-wrap ${className ?? ''}`} style={{ height }}>
      <div className="tradingview-widget-container" ref={ref} style={{ height: '100%', width: '100%' }} />
      {attribution && (
        <a className="tv-credit" href="https://www.tradingview.com/" target="_blank" rel="noopener nofollow">
          TradingView
        </a>
      )}
    </div>
  )
}

export const TradingViewWidget = memo(TradingViewWidgetBase)
