// Cloudflare Pages : /api/billing/checkout et /api/billing/portal.
import handler from '../../../netlify/functions/billing.mts'

export const onRequest = ({ request }: { request: Request }) => handler(request)
