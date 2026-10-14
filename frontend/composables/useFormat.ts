/**
 * Locale-aware formatters.
 *
 * Every number and date the user sees goes through here, so a company
 * operating in Catalonia gets Catalan formatting without any component
 * knowing which locale is active.
 */
export function useFormat() {
  const { locale } = useI18n()

  // Map our locale codes onto the ones Intl expects.
  const intlLocale = computed(() => (locale.value === 'en' ? 'en-GB' : locale.value === 'ca' ? 'ca-ES' : 'es-ES'))

  function number(value: number | null | undefined, digits = 0): string {
    if (value === null || value === undefined || Number.isNaN(value)) return '—'
    return new Intl.NumberFormat(intlLocale.value, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(value)
  }

  function money(value: number | null | undefined, currency = 'EUR'): string {
    if (value === null || value === undefined || Number.isNaN(value)) return '—'
    return new Intl.NumberFormat(intlLocale.value, {
      style: 'currency',
      currency,
    }).format(value)
  }

  function quantity(value: number | null | undefined): string {
    return number(value, 0)
  }

  function date(value: string | null | undefined): string {
    if (!value) return '—'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return '—'
    return new Intl.DateTimeFormat(intlLocale.value, { dateStyle: 'medium' }).format(parsed)
  }

  function dateTime(value: string | null | undefined): string {
    if (!value) return '—'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return '—'
    return new Intl.DateTimeFormat(intlLocale.value, {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(parsed)
  }

  function relative(value: string | null | undefined): string {
    if (!value) return '—'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return '—'

    const seconds = Math.round((parsed.getTime() - Date.now()) / 1000)
    const formatter = new Intl.RelativeTimeFormat(intlLocale.value, { numeric: 'auto' })

    const thresholds: [number, Intl.RelativeTimeFormatUnit][] = [
      [60, 'second'],
      [3600, 'minute'],
      [86400, 'hour'],
      [604800, 'day'],
      [2629800, 'week'],
      [31557600, 'month'],
    ]

    const divisors: Record<string, number> = {
      second: 1,
      minute: 60,
      hour: 3600,
      day: 86400,
      week: 604800,
      month: 2629800,
      year: 31557600,
    }

    const abs = Math.abs(seconds)
    for (const [limit, unit] of thresholds) {
      if (abs < limit) {
        return formatter.format(Math.round(seconds / divisors[unit]), unit)
      }
    }
    return formatter.format(Math.round(seconds / divisors.year), 'year')
  }

  return { number, money, quantity, date, dateTime, relative }
}