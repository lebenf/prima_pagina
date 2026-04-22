import { createI18n } from 'vue-i18n'

export const SUPPORTED_LOCALES = ['it', 'en', 'fr', 'de', 'es', 'pt'] as const
export type SupportedLocale = typeof SUPPORTED_LOCALES[number]
const DEFAULT_LOCALE: SupportedLocale = 'it'

const dateTimeFormats = {
  it: {
    short: { year: 'numeric', month: 'short', day: 'numeric' } as const,
    long: { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' } as const,
    time: { hour: '2-digit', minute: '2-digit' } as const,
  },
  en: {
    short: { year: 'numeric', month: 'short', day: 'numeric' } as const,
    long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' } as const,
    time: { hour: '2-digit', minute: '2-digit', hour12: true } as const,
  },
  fr: {
    short: { year: 'numeric', month: 'short', day: 'numeric' } as const,
    long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' } as const,
    time: { hour: '2-digit', minute: '2-digit' } as const,
  },
  de: {
    short: { year: 'numeric', month: 'short', day: 'numeric' } as const,
    long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' } as const,
    time: { hour: '2-digit', minute: '2-digit' } as const,
  },
  es: {
    short: { year: 'numeric', month: 'short', day: 'numeric' } as const,
    long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' } as const,
    time: { hour: '2-digit', minute: '2-digit' } as const,
  },
  pt: {
    short: { year: 'numeric', month: 'short', day: 'numeric' } as const,
    long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' } as const,
    time: { hour: '2-digit', minute: '2-digit' } as const,
  },
}

export const i18n = createI18n({
  legacy: false,
  locale: DEFAULT_LOCALE,
  fallbackLocale: 'en',
  messages: {},
  datetimeFormats: dateTimeFormats,
})

async function loadLocaleMessages(locale: string) {
  const messages = await import(`./locales/${locale}.json`)
  return messages.default
}

export async function setLocale(locale: string) {
  const l: SupportedLocale = SUPPORTED_LOCALES.includes(locale as SupportedLocale)
    ? (locale as SupportedLocale)
    : DEFAULT_LOCALE

  if (!i18n.global.availableLocales.includes(l)) {
    const messages = await loadLocaleMessages(l)
    i18n.global.setLocaleMessage(l, messages)
  }
  ;(i18n.global.locale as unknown as { value: string }).value = l
}

export function detectBrowserLocale(): string {
  const lang = (typeof navigator !== 'undefined' ? navigator.language : '').split('-')[0]
  return SUPPORTED_LOCALES.includes(lang as SupportedLocale) ? lang : DEFAULT_LOCALE
}
