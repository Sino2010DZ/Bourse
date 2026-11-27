// Cloudflare Pages : /api/quotes → même code que la version Netlify.
import handler from '../../netlify/functions/quotes.mts'

export const onRequest = ({ request }: { request: Request }) => handler(request)
