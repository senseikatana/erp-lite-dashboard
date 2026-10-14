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
  <div class="stack">
    <p v-if="pending" class="muted">{{ t('app.loading') }}</p>

    <div v-else-if="error" class="card">
      <p class="muted">{{ t('app.error') }}</p>
      <button class="btn btn-sm" type="button" @click="refresh()">{{ t('app.retry') }}</button>
    </div>

    <template v-else-if="data">
      <!-- Measured KPIs. Every value here comes from the activity log. -->
      <section>
        <div class="grid grid-4">
          <KpiCard v-for="kpi in data.kpis" :key="kpi.key" :kpi="kpi" />
        </div>
      </section>

      <section>
        <div class="grid grid-4">
          <StatCard :label="t('dashboard.openSales')" :value="number(data.open_sales_orders)" />
          <StatCard :label="t('dashboard.openPurchases')" :value="number(data.open_purchase_orders)" />
          <StatCard :label="t('dashboard.awaitingQuality')" :value="number(data.orders_awaiting_quality)" />
          <StatCard :label="t('dashboard.pendingDemand')" :value="number(data.pending_demand_lines)" />
        </div>
      </section>

      <section>
        <div class="grid grid-3">
          <StatCard :label="t('dashboard.belowMinimum')" :value="number(data.items_below_minimum)" tone="accent" />
          <StatCard :label="t('dashboard.inventoryValue')" :value="money(data.inventory_value, currency)" />
          <StatCard :label="t('dashboard.routesToday')" :value="number(data.routes_today)" />
        </div>
      </section>

      <section class="grid grid-2">
        <div class="card">
          <div class="card-header">
            <h2>{{ t('dashboard.alerts') }}</h2>
          </div>

          <EmptyState v-if="!alerts?.length" :message="t('dashboard.noAlerts')" />

          <ul v-else class="alert-list">
            <li
              v-for="(alert, index) in alerts"
              :key="index"
              class="alert"
              :class="alert.severity"
            >
              <span class="alert-dot" aria-hidden="true" />
              <span class="alert-text">
                <span class="alert-code">{{ alert.code }}</span>
                {{ alert.message }}
              </span>
            </li>
          </ul>
        </div>

        <div class="card">
          <div class="card-header">
            <h2>{{ t('dashboard.recentActivity') }}</h2>
            <NuxtLink class="btn btn-sm" to="/activity">{{ t('nav.activity') }}</NuxtLink>
          </div>

          <EmptyState v-if="!activity?.length" :message="t('activity.noEntries')" />

          <ul v-else class="feed">
            <li v-for="event in activity" :key="event.id" class="feed-item">
              <div class="row-between">
                <span class="feed-actor">{{ event.actor_username }}</span>
                <span class="faint nowrap">{{ dateTime(event.occurred_at) }}</span>
              </div>
              <p class="feed-summary">
                <span class="mono faint">{{ event.entity }}</span>
                <span class="feed-action">{{ event.action }}</span>
              </p>
              <p v-if="event.summary" class="feed-detail faint">{{ event.summary }}</p>
            </li>
          </ul>
        </div>
      </section>

      <section class="card">
        <div class="card-header">
          <h2>{{ t('dashboard.stockLevels') }}</h2>
        </div>

        <EmptyState v-if="!stock?.length" :message="t('warehouse.noItems')" />

        <div v-else class="stock-list">
          <div v-for="level in stock" :key="level.item_id" class="stock-row">
            <div class="stock-meta">
              <span class="mono">{{ level.code }}</span>
              <span class="grow">{{ level.description }}</span>
              <span class="nowrap numeric">
                {{ number(level.stock) }} / {{ number(level.min_stock) }}
              </span>
            </div>
            <div
              class="stock-bar"
              role="meter"
              :aria-valuenow="stockRatio(level)"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div class="stock-fill" :style="{ width: `${stockRatio(level)}%` }" />
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.alert-list,
.feed,
.stock-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.alert-list { display: flex; flex-direction: column; gap: 0.5rem; }

.alert {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.5rem 0.6rem;
  font-size: 0.8125rem;
  border-radius: var(--radius-sm);
}

.alert.critical { background: var(--danger-soft); color: var(--danger); }
.alert.warning { background: var(--warning-soft); color: var(--warning); }

.alert-dot {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  margin-top: 0.4rem;
  background: currentColor;
  border-radius: 50%;
}

.alert-code { font-weight: 600; font-family: var(--font-mono); }

.feed { display: flex; flex-direction: column; }

.feed-item {
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border);
}

.feed-item:last-child { border-bottom: none; }

.feed-actor { font-size: 0.8125rem; font-weight: 600; }

.feed-summary {
  margin: 0.1rem 0 0;
  font-size: 0.8125rem;
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
}

.feed-action { font-weight: 500; }

.feed-detail { margin: 0.1rem 0 0; font-size: 0.75rem; }

.stock-list { display: flex; flex-direction: column; gap: 0.7rem; }

.stock-meta {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  font-size: 0.8125rem;
  margin-bottom: 0.25rem;
}

.stock-bar {
  height: 6px;
  background: var(--surface-sunken);
  border-radius: 999px;
  overflow: hidden;
}

.stock-fill {
  height: 100%;
  background: var(--danger);
  border-radius: 999px;
}
</style>