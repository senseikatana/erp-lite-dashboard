<script setup lang="ts">
const auth = useAuthStore()
const { t } = useI18n()
const route = useRoute()

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

async function signOut() {
  auth.clear()
  await navigateTo('/login')
}
</script>

<template>
  <div class="grid min-h-screen grid-cols-1 lg:grid-cols-[248px_minmax(0,1fr)]">
    <aside class="flex flex-col gap-4 border-b border-sunken bg-panel p-4 lg:border-b-0 lg:border-r">
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

        <div>
          <p class="text-sm font-medium">{{ auth.user?.full_name }}</p>
          <p class="text-xs text-ink/60">{{ auth.user ? t(`role.${auth.user.role}`) : '' }}</p>
        </div>

        <button class="btn btn-sm btn-text justify-start" type="button" @click="signOut">
          {{ t('nav.signOut') }}
        </button>
      </div>
    </aside>

    <main class="flex min-w-0 flex-col">
      <header
        class="flex items-center justify-between gap-4 border-b border-sunken bg-panel px-4 py-3 lg:px-6"
      >
        <h1 class="text-xl font-semibold">{{ t(`nav.${routeLabel}`) }}</h1>
        <div class="flex items-center gap-3 text-sm">
          <span class="text-ink/60">{{ companyName }}</span>
          <span class="badge badge-soft font-mono text-xs">{{ currency }}</span>
        </div>
      </header>

      <div class="p-4 lg:p-6">
        <slot />
      </div>
    </main>
  </div>
</template>
