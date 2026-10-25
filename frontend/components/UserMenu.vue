<script setup lang="ts">
const auth = useAuthStore()
const api = useApi()
const { t } = useI18n()

const menu = ref<HTMLDetailsElement | null>(null)
const purging = ref(false)
const error = ref('')

const initials = computed(() => {
  const name = auth.user?.full_name?.trim()
  if (!name) return '?'
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
})

const roleLabel = computed(() => (auth.user ? t(`role.${auth.user.role}`) : ''))

const companyName = computed(
  () =>
    auth.companies.find((company) => company.code === auth.activeCompany)?.name ??
    auth.activeCompany ??
    '',
)

function close() {
  if (menu.value) menu.value.open = false
}

function onPointerDown(event: MouseEvent) {
  if (menu.value?.open && !menu.value.contains(event.target as Node)) close()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
}

async function purgeContent() {
  if (!confirm(t('user.purgeConfirm', { company: companyName.value }))) return

  purging.value = true
  error.value = ''
  try {
    await api.post('/admin/purge')
    close()
    await refreshNuxtData()
    await navigateTo('/')
  } catch (err: any) {
    error.value = err?.statusMessage ?? t('app.error')
  } finally {
    purging.value = false
  }
}

async function signOut() {
  close()
  // `clear()` expires the erp_token and erp_company cookies, so a reload
  // cannot restore the session.
  auth.clear()
  await navigateTo('/login')
}

onMounted(() => {
  document.addEventListener('click', onPointerDown)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onPointerDown)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <details ref="menu" class="relative">
    <summary class="btn btn-sm btn-text gap-2" :aria-label="t('user.menu')">
      <span
        class="text-bg-primary grid size-7 place-items-center rounded-full text-xs"
        aria-hidden="true"
      >
        {{ initials }}
      </span>
      <span class="hidden text-left leading-tight sm:block">
        <span class="block text-xs font-semibold">{{ auth.user?.full_name }}</span>
        <span class="block text-xs text-ink/50">{{ roleLabel }}</span>
      </span>
      <span class="text-xs text-ink/40" aria-hidden="true">▾</span>
    </summary>

    <div
      class="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-sunken bg-panel p-1.5 shadow-lg"
    >
      <div class="border-b border-sunken px-2.5 pb-2 pt-1.5">
        <p class="truncate text-sm font-semibold">{{ auth.user?.full_name }}</p>
        <p class="truncate text-xs text-ink/50">{{ auth.user?.email }}</p>
        <p class="text-xs text-ink/50">{{ roleLabel }}</p>
      </div>

      <ul class="menu w-full p-0 pt-1">
        <li v-if="auth.hasRole('admin')">
          <button
            type="button"
            class="text-left text-sm text-danger"
            :disabled="purging"
            @click="purgeContent"
          >
            {{ purging ? t('app.loading') : t('user.purge') }}
          </button>
        </li>
        <li>
          <button type="button" class="text-left text-sm" @click="signOut">
            {{ t('nav.signOut') }}
          </button>
        </li>
      </ul>

      <p v-if="error" class="px-2.5 pb-1.5 text-xs text-danger">{{ error }}</p>
    </div>
  </details>
</template>

<style scoped>
summary {
  list-style: none;
  cursor: pointer;
}

summary::-webkit-details-marker {
  display: none;
}
</style>
