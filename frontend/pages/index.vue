<script setup lang="ts">
import type { ActivityEvent, Alert, DashboardSummary, StockLevel } from '~/types/api'

const { t } = useI18n()
const api = useApi()
const { money, number, dateTime } = useFormat()

const { data, pending, error, refresh } = await useAsyncData<DashboardSummary>(
  'dashboard-summary',
  () => api.get<DashboardSummary>('/dashboard/summary'),
)

const { data: alerts } = await useAsyncData<Alert[]>('dashboard-alerts', () =>
  api.get<Alert[]>('/dashboard/alerts'),
)

const { data: stock } = await useAsyncData<StockLevel[]>('dashboard-stock', () =>
  api.get<StockLevel[]>('/dashboard/stock-levels'),
)

const { data: activity } = await useAsyncData<ActivityEvent[]>('dashboard-activity', () =>
  api.get<ActivityEvent[]>('/dashboard/activity', { limit: 12 }),
)

const currency = computed(() => {
  const auth = useAuthStore()
  return auth.companies.find((c) => c.code === auth.activeCompany)?.currency ?? 'EUR'
})

function stockRatio(level: StockLevel): number {
  if (!level.min_stock) return 100
  return Math.min(100, Math.round((level.stock / level.min_stock) * 100))
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <p v-if="pending" class="text-sm text-ink/60">{{ t('app.loading') }}</p>

    <div v-else-if="error" class="card">
      <div class="card-body items-start gap-3">
        <p class="text-sm text-ink/60">{{ t('app.error') }}</p>
        <button class="btn btn-sm" type="button" @click="refresh()">{{ t('app.retry') }}</button>
      </div>
    </div>

    <template v-else-if="data">
      <!-- Measured KPIs. Every value here comes from the activity log. -->
      <section class="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard v-for="kpi in data.kpis" :key="kpi.key" :kpi="kpi" />
      </section>

      <section class="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard :label="t('dashboard.openSales')" :value="number(data.open_sales_orders)" />
        <StatCard :label="t('dashboard.openPurchases')" :value="number(data.open_purchase_orders)" />
        <StatCard :label="t('dashboard.awaitingQuality')" :value="number(data.orders_awaiting_quality)" />
        <StatCard :label="t('dashboard.pendingDemand')" :value="number(data.pending_demand_lines)" />
      </section>

      <section class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard :label="t('dashboard.belowMinimum')" :value="number(data.items_below_minimum)" tone="accent" />
        <StatCard :label="t('dashboard.inventoryValue')" :value="money(data.inventory_value, currency)" />
        <StatCard :label="t('dashboard.routesToday')" :value="number(data.routes_today)" />
      </section>

      <section class="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div class="card">
          <div class="card-body">
            <h2 class="text-lg font-semibold">{{ t('dashboard.alerts') }}</h2>

            <EmptyState v-if="!alerts?.length" :message="t('dashboard.noAlerts')" />

            <ul v-else class="flex flex-col gap-2">
              <li v-for="(alert, index) in alerts" :key="index">
                <div
                  class="alert alert-soft text-sm"
                  :class="alert.severity === 'critical' ? 'alert-error' : 'alert-warning'"
                >
                  <span class="font-mono font-semibold">{{ alert.code }}</span>
                  <span>{{ alert.message }}</span>
                </div>
              </li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-lg font-semibold">{{ t('dashboard.recentActivity') }}</h2>
              <NuxtLink class="btn btn-sm" to="/activity">{{ t('nav.activity') }}</NuxtLink>
            </div>

            <EmptyState v-if="!activity?.length" :message="t('activity.noEntries')" />

            <ul v-else class="divide-y divide-sunken">
              <li v-for="event in activity" :key="event.id" class="py-2 first:pt-0 last:pb-0">
                <div class="flex items-center justify-between gap-3">
                  <span class="text-sm font-semibold">{{ event.actor_username }}</span>
                  <span class="text-xs whitespace-nowrap text-ink/50">{{ dateTime(event.occurred_at) }}</span>
                </div>
                <p class="mt-0.5 flex items-baseline gap-1.5 text-sm">
                  <span class="font-mono text-xs text-ink/50">{{ event.entity }}</span>
                  <span class="font-medium">{{ event.action }}</span>
                </p>
                <p v-if="event.summary" class="mt-0.5 text-xs text-ink/50">{{ event.summary }}</p>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card-body">
          <h2 class="text-lg font-semibold">{{ t('dashboard.stockLevels') }}</h2>

          <EmptyState v-if="!stock?.length" :message="t('warehouse.noItems')" />

          <div v-else class="flex flex-col gap-3">
            <div v-for="level in stock" :key="level.item_id">
              <div class="mb-1 flex items-baseline gap-2.5 text-sm">
                <span class="font-mono text-xs">{{ level.code }}</span>
                <span class="flex-1">{{ level.description }}</span>
                <span class="tabular-nums whitespace-nowrap">
                  {{ number(level.stock) }} / {{ number(level.min_stock) }}
                </span>
              </div>
              <div
                class="progress"
                role="meter"
                :aria-valuenow="stockRatio(level)"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <div class="progress-bar progress-error" :style="{ width: `${stockRatio(level)}%` }" />
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
