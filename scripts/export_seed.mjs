/**
 * Frontenddagi demo ma'lumotni backend uchun JSON ga chiqaradi.
 *
 * Bu skript ixtiyoriy: `seed/demo_seed.json` allaqachon repozitoriyda bor.
 * U faqat frontenddagi `src/data/mock.js` o'zgarganda qayta ishlatiladi.
 *
 * Ishga tushirish (backend ildizidan):
 *   node scripts/export_seed.mjs
 *   node scripts/export_seed.mjs ../migrant-dashboard/src/data/mock.js
 *
 * Manba ko'rsatilmasa yonma-yon turgan `../migrant-dashboard/src/data/mock.js`
 * qidiriladi. Uni MOCK_SOURCE muhit o'zgaruvchisi bilan ham berish mumkin.
 */
import { writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const projectRoot = resolve(here, '..')

const DEFAULT_SOURCES = [
  resolve(projectRoot, '..', 'migrant-dashboard', 'src', 'data', 'mock.js'),
  resolve(projectRoot, '..', 'frontend', 'src', 'data', 'mock.js'),
]

/** Manba faylni topadi: argument -> muhit o'zgaruvchisi -> odatiy joylar */
function resolveSource() {
  const explicit = process.argv[2] || process.env.MOCK_SOURCE
  if (explicit) {
    const path = resolve(process.cwd(), explicit)
    if (!existsSync(path)) {
      throw new Error(`Manba topilmadi: ${path}`)
    }
    return path
  }
  const found = DEFAULT_SOURCES.find(existsSync)
  if (!found) {
    throw new Error(
      'Frontenddagi mock.js topilmadi.\n' +
      'Yo‘lni argument sifatida bering:\n' +
      '  node scripts/export_seed.mjs ../migrant-dashboard/src/data/mock.js',
    )
  }
  return found
}

const sourceFile = resolveSource()
const mock = await import(pathToFileURL(sourceFile).href)

/** Tumanlar viloyatga bog'lanadi — hozircha barchasi Toshkent viloyatiniki */
const DISTRICT_REGION = 'Toshkent viloyati'

const payload = {
  generatedFrom: sourceFile.replace(/\\/g, '/'),
  roles: mock.roles,
  users: mock.users,
  settings: mock.settings,

  countries: mock.countries,
  regions: mock.regions,
  districts: mock.districts.map((d) => ({ ...d, region: DISTRICT_REGION })),
  borderPoints: mock.borderPoints,
  borderSources: mock.borderSources,

  migrants: mock.migrants,
  employers: mock.employers,

  violations: mock.violations,
  sosEvents: mock.sosEvents,
  sosChannels: mock.sosChannels,
  consulateServices: mock.consulateServices,
  returnPrograms: mock.returnPrograms,

  metrics: {
    dashboard: mock.kpis,
    consulate: mock.consulate,
    return: mock.returnStats,
    border: mock.borderStats,
    sos: mock.sosStats,
    audit: mock.auditStats,
  },
  shares: {
    composition: mock.composition,
    purpose: mock.purposes,
    risk: mock.riskDistribution,
  },
  series: mock.series,
  aiInsights: mock.aiInsights,
  aiSuggestions: mock.aiSuggestions,
  integrations: mock.integrations,
  riskWeights: mock.riskWeights,
  reportTemplates: mock.reportTemplates,
  reportArchive: mock.reportArchive,
}

const outFile = resolve(projectRoot, 'seed', 'demo_seed.json')
mkdirSync(dirname(outFile), { recursive: true })
writeFileSync(outFile, JSON.stringify(payload, null, 2), 'utf8')

const counts = Object.entries(payload)
  .filter(([, value]) => Array.isArray(value))
  .map(([key, value]) => `${key}=${value.length}`)

console.log('manba :', sourceFile)
console.log('yozildi:', outFile)
console.log(counts.join(' '))
