// Cloudflare Pages : /api/delete-account → même code que la version Netlify.
import handler from '../../netlify/functions/delete-account.mts'

export const onRequest = ({ request }: { request: Request }) => handler(request)
