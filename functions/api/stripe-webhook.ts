// Cloudflare Pages : /api/stripe-webhook → même code que la version Netlify.
import handler from '../../netlify/functions/stripe-webhook.mts'

export const onRequest = ({ request }: { request: Request }) => handler(request)
