/**
 * Theme selection.
 *
 * The active theme lives in a cookie so the server renders the right
 * `data-theme` on <html> and the first paint never flashes the wrong palette.
 */
export const THEMES = ['light', 'dark', 'corporate', 'soft', 'luxury'] as const

export type ThemeName = (typeof THEMES)[number]

const THEME_COOKIE = 'erp_theme'

function isThemeName(value: string): value is ThemeName {
  return (THEMES as readonly string[]).includes(value)
}

export function useTheme() {
  const cookie = useCookie<string>(THEME_COOKIE, {
    default: () => 'light',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365,
  })

  const theme = computed<ThemeName>(() =>
    isThemeName(cookie.value) ? cookie.value : 'light',
  )

  function setTheme(value: ThemeName) {
    cookie.value = value
  }

  return { theme, setTheme, themes: THEMES }
}
