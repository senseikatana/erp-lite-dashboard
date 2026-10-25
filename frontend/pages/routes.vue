<script setup lang="ts">
import type { Page, Route } from '~/types/api'

const { t } = useI18n()
const api = useApi()
const auth = useAuthStore()
const { number, date } = useFormat()

const notice = ref('')

const { data, pending, refresh } = await useAsyncData<Page<Route>>('routes', () =>
  api.get<Page<Route>>('/routes', { limit: 200 }),
)

const canManage = computed(() => auth.hasRole('admin', 'logistics'))

async function setStatus(route: Route, status: 'IN_TRANSIT' | 'DELIVERED') {
  notice.value = ''
  try {
    await api.patch(`/routes/${route.id}`, { status })
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <AppNotice v-if="notice" :message="notice" />

    <p v-if="pending" class="text-sm text-ink/60">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="t('routes.noRoutes')" />
    </div>

    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr>
              <th>{{ t('routes.code') }}</th>
              <th>{{ t('routes.carrier') }}</th>
              <th>{{ t('routes.date') }}</th>
              <th class="text-right">{{ t('routes.stops') }}</th>
              <th>{{ t('common.status') }}</th>
              <th v-if="canManage"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="route in data.items" :key="route.id" class="hover:bg-surface/60">
              <td class="font-mono text-xs whitespace-nowrap">{{ route.code }}</td>
              <td>{{ route.carrier }}</td>
              <td class="whitespace-nowrap">{{ date(route.date) }}</td>
              <td class="text-right tabular-nums">{{ number(route.stops) }}</td>
              <td><StatusBadge :value="route.status" /></td>
              <td v-if="canManage" class="text-right whitespace-nowrap">
                <button
                  v-if="route.status === 'PLANNED'"
                  class="btn btn-sm"
                  type="button"
                  @click="setStatus(route, 'IN_TRANSIT')"
                >
                  {{ t('routes.markInTransit') }}
                </button>
                <button
                  v-if="route.status === 'IN_TRANSIT'"
                  class="btn btn-primary btn-sm"
                  type="button"
                  @click="setStatus(route, 'DELIVERED')"
                >
                  {{ t('routes.markDelivered') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
