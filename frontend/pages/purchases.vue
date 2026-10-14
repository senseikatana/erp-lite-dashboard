<script setup lang="ts">
import type { Page, PurchaseOrder } from '~/types/api'

const { t } = useI18n()
const api = useApi()
const auth = useAuthStore()
const { money, number, date } = useFormat()

const tab = ref<'orders' | 'quality'>('orders')
const notice = ref('')

const { data, pending, refresh } = await useAsyncData<Page<PurchaseOrder>>(
  'purchase-orders',
  () =>
    tab.value === 'quality'
      ? api.get<Page<PurchaseOrder>>('/purchases/orders/awaiting-quality', { limit: 100 })
      : api.get<Page<PurchaseOrder>>('/purchases/orders', { limit: 100 }),
  { watch: [tab] },
)

const currency = computed(
  () => auth.companies.find((c) => c.code === auth.activeCompany)?.currency ?? 'EUR',
)

async function receive(order: PurchaseOrder) {
  notice.value = ''
  try {
    // Omitting `lines` receives the full ordered quantity in one pass.
    await api.post(`/purchases/orders/${order.id}/receive`, {})
    notice.value = t('purchases.receivedOk')
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}

async function decide(order: PurchaseOrder, passed: boolean) {
  notice.value = ''
  const note = passed ? '' : prompt(t('purchases.qualityNote')) ?? ''
  try {
    await api.post(`/purchases/orders/${order.id}/quality`, { passed, note })
    notice.value = passed ? t('purchases.approvedOk') : t('purchases.rejectedOk')
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}
</script>

<template>
  <div class="stack">
    <div class="card toolbar">
      <div class="tabs" role="tablist">
        <button
          class="tab"
          :class="{ active: tab === 'orders' }"
          role="tab"
          type="button"
          :aria-selected="tab === 'orders'"
          @click="tab = 'orders'"
        >
          {{ t('purchases.orders') }}
        </button>
        <button
          class="tab"
          :class="{ active: tab === 'quality' }"
          role="tab"
          type="button"
          :aria-selected="tab === 'quality'"
          @click="tab = 'quality'"
        >
          {{ t('purchases.qualityQueue') }}
        </button>
      </div>
      <p v-if="notice" class="notice">{{ notice }}</p>
    </div>

    <p v-if="pending" class="muted">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="tab === 'quality' ? t('dashboard.noAlerts') : t('purchases.noOrders')" />
    </div>

    <div v-else class="stack">
      <article v-for="order in data.items" :key="order.id" class="card order">
        <div class="row-between order-head">
          <div class="row">
            <span class="mono order-number">{{ order.number }}</span>
            <StatusBadge :value="order.status" />
          </div>
          <span class="order-total numeric">{{ money(order.total, currency) }}</span>
        </div>

        <dl class="order-meta">
          <div>
            <dt class="faint">{{ t('common.vendor') }}</dt>
            <dd>{{ order.vendor_name ?? `#${order.vendor_id}` }}</dd>
          </div>
          <div>
            <dt class="faint">{{ t('common.orderDate') }}</dt>
            <dd>{{ date(order.order_date) }}</dd>
          </div>
          <div>
            <dt class="faint">{{ t('common.expectedDate') }}</dt>
            <dd>{{ date(order.expected_date) }}</dd>
          </div>
        </dl>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.item') }}</th>
                <th class="numeric">{{ t('common.quantity') }}</th>
                <th class="numeric">{{ t('purchases.received') }}</th>
                <th class="numeric">{{ t('common.cost') }}</th>
                <th>{{ t('purchases.qcStatus') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in order.lines" :key="line.id">
                <td>
                  <span class="mono faint">{{ line.item_code }}</span>
                  {{ line.item_description }}
                </td>
                <td class="numeric">{{ number(line.quantity) }}</td>
                <td class="numeric">{{ number(line.qty_received) }}</td>
                <td class="numeric">{{ money(line.unit_cost, currency) }}</td>
                <td><StatusBadge :value="line.qc_status" /></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="row order-actions">
          <button
            v-if="auth.hasRole('admin', 'logistics') && ['OPEN', 'RECEIVED'].includes(order.status)"
            class="btn btn-primary btn-sm"
            type="button"
            @click="receive(order)"
          >
            {{ t('purchases.receive') }}
          </button>

          <template v-if="auth.hasRole('admin', 'quality') && order.status === 'QC_PENDING'">
            <button class="btn btn-primary btn-sm" type="button" @click="decide(order, true)">
              {{ t('purchases.approve') }}
            </button>
            <button class="btn btn-danger btn-sm" type="button" @click="decide(order, false)">
              {{ t('purchases.reject') }}
            </button>
          </template>

          <p v-if="order.status === 'QC_PENDING' && !auth.hasRole('admin', 'quality')" class="faint hint">
            {{ t('purchases.quality') }}
          </p>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.tabs { display: flex; gap: 0.25rem; }

.tab {
  padding: 0.35rem 0.75rem;
  font: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.tab:hover { background: var(--surface-sunken); }

.tab.active {
  color: var(--accent-strong);
  background: var(--accent-soft);
  border-color: #b8d8e6;
}

.notice { margin: 0; font-size: 0.8125rem; color: var(--accent-strong); }

.order-head { margin-bottom: 0.75rem; }

.order-number { font-weight: 600; font-size: 0.9375rem; }

.order-total { font-weight: 600; font-size: 1rem; }

.order-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0 0 0.85rem;
  padding: 0.65rem 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.order-meta dt {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.order-meta dd { margin: 0.1rem 0 0; font-size: 0.8125rem; }

.order-actions { margin-top: 0.85rem; }

.hint { margin: 0; font-size: 0.75rem; }

@media (max-width: 800px) {
  .order-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>