<script setup lang="ts">
const auth = useAuthStore()
const { t } = useI18n()
const route = useRoute()

const sidebarOpen = useCookie<boolean>('erp_sidebar_open', {
  default: () => true,
  sameSite: 'lax',
  maxAge: 60 * 60 * 24 * 365,
})

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

const companyName = computed(() => {
  const code = auth.activeCompany
  return auth.companies.find((c) => c.code === code)?.name ?? code ?? ''
})

const currency = computed(() => {
  const code = auth.activeCompany
  return auth.companies.find((c) => c.code === code)?.currency ?? 'EUR'
})

const routeLabel = computed(() => {
  const path = route.path
  if (path === '/') return 'dashboard'
  return path.split('/')[1] ?? 'dashboard'
})
</script>

<template>
  <div
    class="grid min-h-screen grid-cols-1"
    :class="sidebarOpen ? 'lg:grid-cols-[248px_minmax(0,1fr)]' : ''"
  >
    <aside
      v-show="sidebarOpen"
      id="app-sidebar"
      class="flex flex-col gap-4 border-b border-sunken bg-panel p-4 lg:border-b-0 lg:border-r"
    >
      <div class="flex items-center gap-2.5 px-1">
        <span
          class="text-bg-primary grid size-9 place-items-center rounded-lg text-sm"
          aria-hidden="true"
        >
          ▤
        </span>
        <div>
          <p class="text-sm font-semibold leading-tight">ERP-Lite</p>
          <p class="text-xs text-ink/60">{{ t('app.subtitle') }}</p>
        </div>
      </div>

      <CompanySwitcher />

      <nav class="flex-1" :aria-label="t('nav.dashboard')">
        <ul
          class="menu menu-horizontal w-full flex-nowrap overflow-x-auto p-0 lg:menu-vertical lg:overflow-visible"
        >
          <li v-for="entry in auth.navigation" :key="entry.to">
            <NuxtLink :to="entry.to" active-class="menu-active" class="text-sm">
              {{ t(`nav.${entry.key}`) }}
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <div class="flex flex-col gap-3 border-t border-sunken pt-3">
        <div class="grid grid-cols-2 gap-2">
          <LanguageSwitcher />
          <ThemeSwitcher />
        </div>
      </div>
    </aside>

    <main class="flex min-w-0 flex-col">
      <header
        class="flex items-center justify-between gap-4 border-b border-sunken bg-panel px-4 py-2.5 lg:px-6"
      >
        <div class="flex min-w-0 items-center gap-2">
          <button
            id="sidebar-toggle"
            class="btn btn-sm btn-square btn-text"
            type="button"
            :aria-expanded="sidebarOpen"
            aria-controls="app-sidebar"
            :aria-label="sidebarOpen ? t('nav.hideSidebar') : t('nav.showSidebar')"
            @click="toggleSidebar"
          >
            <span aria-hidden="true">☰</span>
          </button>
          <h1 class="truncate text-xl font-semibold">{{ t(`nav.${routeLabel}`) }}</h1>
        </div>
        <div class="flex items-center gap-2 text-sm">
          <span class="hidden text-ink/60 sm:inline">{{ companyName }}</span>
          <span class="badge badge-soft font-mono text-xs">{{ currency }}</span>
          <ThemeToggle />
          <UserMenu />
        </div>
      </header>

      <div class="p-4 lg:p-6">
        <slot />
      </div>
    </main>
  </div>
</template>
