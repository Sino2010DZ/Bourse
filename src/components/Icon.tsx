// Petites icônes en SVG (aucune dépendance externe).
const PATHS = {
  markets: 'M3 17l5-5 4 4 8-8M15 8h5v5',
  portfolio: 'M4 7h16v12H4zM9 7V5h6v2',
  alerts: 'M6 16V11a6 6 0 1112 0v5l2 2H4zM10 20h4',
  account: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 20a8 8 0 0116 0',
  pricing: 'M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z',
  search: 'M11 18a7 7 0 100-14 7 7 0 000 14zM20 20l-4-4',
  plus: 'M12 5v14M5 12h14',
  close: 'M6 6l12 12M18 6L6 18',
  trash: 'M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13',
  back: 'M15 5l-7 7 7 7',
  check: 'M5 13l4 4L19 7',
  bell: 'M6 16V11a6 6 0 1112 0v5l2 2H4zM10 20h4',
  star: 'M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z',
  sun: 'M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6L4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4M12 17a5 5 0 100-10 5 5 0 000 10z',
  info: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 11v6M12 7h.01',
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name, size = 20, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name]} />
    </svg>
  )
}
