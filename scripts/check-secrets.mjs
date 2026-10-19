// Garde-fou : échoue si une clé secrète se retrouve dans le site public (dist/).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const SECRET_VARS = ['SUPABASE_SERVICE_ROLE_KEY', 'EODHD_API_KEY', 'VAPID_PRIVATE_KEY', 'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET']
const PATTERNS = [/sk_(live|test)_[0-9a-zA-Z]{10,}/, /sb_secret_[0-9a-zA-Z_-]{10,}/, /whsec_[0-9a-zA-Z]{10,}/, /"role"\s*:\s*"service_role"/]

const files = []
const walk = (dir) => {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f)
    statSync(p).isDirectory() ? walk(p) : files.push(p)
  }
}
walk(process.argv[2] ?? 'dist')

const secrets = SECRET_VARS.map((k) => [k, process.env[k]]).filter(([, v]) => v && v.length >= 8)
let leaks = 0
for (const file of files) {
  const text = readFileSync(file, 'utf8')
  for (const [name, value] of secrets) if (text.includes(value)) { console.error(`FUITE : ${name} trouvé dans ${file}`); leaks++ }
  for (const re of PATTERNS) if (re.test(text)) { console.error(`FUITE : motif ${re} trouvé dans ${file}`); leaks++ }
  // Les jetons Supabase sont encodés : on décode ceux trouvés pour vérifier leur rôle.
  for (const jwt of text.match(/eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+/g) ?? []) {
    try {
      const payload = JSON.parse(Buffer.from(jwt.split('.')[1], 'base64url').toString())
      if (payload.role === 'service_role') { console.error(`FUITE : clé service_role dans ${file}`); leaks++ }
    } catch { /* pas un jeton */ }
  }
}
if (leaks) { console.error(`${leaks} fuite(s) détectée(s) : mise en ligne bloquée.`); process.exit(1) }
console.log(`Aucune clé secrète dans le site public (${files.length} fichiers vérifiés).`)
