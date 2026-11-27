// Cloudflare Pages : /api/billing → même code que la version Netlify.
import handler from '../../netlify/functions/billing.mts'

export const onRequest = ({ request }: { request: Request }) => handler(request)
