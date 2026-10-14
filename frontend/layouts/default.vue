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
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">▤</span>
        <div>
          <p class="brand-name">ERP-Lite</p>
          <p class="brand-sub">{{ t('app.subtitle') }}</p>
        </div>
      </div>

      <CompanySwitcher />

      <nav class="nav" :aria-label="t('nav.dashboard')">
        <NuxtLink
          v-for="entry in auth.navigation"
          :key="entry.to"
          :to="entry.to"
          class="nav-link"
          active-class="nav-link-active"
        >
          {{ t(`nav.${entry.key}`) }}
        </NuxtLink>
      </nav>

      <div class="sidebar-footer">
        <LanguageSwitcher />
        <div class="user">
          <p class="user-name">{{ auth.user?.full_name }}</p>
          <p class="user-role">{{ auth.user ? t(`role.${auth.user.role}`) : '' }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="signOut">
          {{ t('nav.signOut') }}
        </button>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h1>{{ t(`nav.${routeLabel}`) }}</h1>
        </div>
        <div class="topbar-meta">
          <span class="muted">{{ companyName }}</span>
          <span class="faint mono">{{ currency }}</span>
        </div>
      </header>

      <div class="content">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.15rem 0.9rem;
  background: var(--surface-raised);
  border-right: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0 0.25rem;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  font-size: 1rem;
  color: #fff;
  background: var(--accent);
  border-radius: var(--radius-sm);
}

.brand-name {
  margin: 0;
  font-weight: 600;
  line-height: 1.2;
}

.brand-sub {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1 1 auto;
}

.nav-link {
  padding: 0.45rem 0.6rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-muted);
  border-radius: var(--radius-sm);
  text-decoration: none;
}

.nav-link:hover {
  color: var(--text);
  background: var(--surface-sunken);
  text-decoration: none;
}

.nav-link-active,
.nav-link-active:hover {
  color: var(--accent-strong);
  background: var(--accent-soft);
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--border);
}

.user-name {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 500;
}

.user-role {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border);
}

.topbar h1 {
  margin: 0;
  font-size: 1.25rem;
}

.topbar-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.8125rem;
}

.content {
  padding: 1.5rem;
}

@media (max-width: 860px) {
  .shell { grid-template-columns: minmax(0, 1fr); }
  .sidebar { border-right: none; border-bottom: 1px solid var(--border); }
  .nav { flex-direction: row; overflow-x: auto; }
  .content { padding: 1rem; }
}
</style>