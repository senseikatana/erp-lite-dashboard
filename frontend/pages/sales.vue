<script setup lang="ts">
import type { Page, SalesOrder, SalesOrderStatus } from '~/types/api'

const { t } = useI18n()
const api = useApi()
const auth = useAuthStore()
const { money, number, date } = useFormat()

const statusFilter = ref<SalesOrderStatus[]>([])
const notice = ref('')

const { data, pending, refresh } = await useAsyncData<Page<SalesOrder>>(
  'sales-orders',
  () => api.get<Page<SalesOrder>>('/sales/orders', { limit: 100, status: statusFilter.value }),
  { watch: [statusFilter] },
)

const statusOptions: SalesOrderStatus[] = ['OPEN', 'PICKING', 'SHIPPED', 'INVOICED', 'CANCELLED']

const currency = computed(() => {
  return auth.companies.find((c) => c.code === auth.activeCompany)?.currency ?? 'EUR'
})

async function advance(order: SalesOrder, status: SalesOrderStatus) {
  notice.value = ''
  try {
    await api.patch(`/sales/orders/${order.id}/status`, { status })
    notice.value = t('sales.statusChanged', { status: t(`status.${status}`) })
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}

async function cancelOrder(order: SalesOrder) {
  if (!confirm(t('sales.cancelConfirm', { number: order.number }))) return
  try {
    await api.delete(`/sales/orders/${order.id}`)
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}

/** Next action available for an order, given the caller's role. */
function nextAction(order: SalesOrder): { status: SalesOrderStatus; label: string } | null {
  if (order.status === 'OPEN') {
    return auth.hasRole('admin', 'logistics')
      ? { status: 'PICKING', label: t('sales.pick') }
      : null
  }
  if (order.status === 'PICKING') {
    return auth.hasRole('admin', 'logistics')
      ? { status: 'SHIPPED', label: t('sales.ship') }
      : null
  }
  if (order.status === 'SHIPPED') {
    return auth.hasRole('admin') ? { status: 'INVOICED', label: t('sales.invoice') } : null
  }
  return null
}
</script>

<template>
  <div class="stack">
    <div class="card toolbar">
      <div class="row">
        <label for="status-filter" class="faint">{{ t('sales.filterStatus') }}</label>
        <select
          id="status-filter"
          v-model="statusFilter"
          multiple
          size="1"
          class="status-select"
          @change="(e) => { const v = (e.target as HTMLSelectElement).value; statusFilter = v ? [v as SalesOrderStatus] : [] }"
        >
          <option value="">{{ t('app.all') }}</option>
          <option v-for="option in statusOptions" :key="option" :value="option">
            {{ t(`status.${option}`) }}
          </option>
        </select>
      </div>
      <p v-if="notice" class="notice">{{ notice }}</p>
    </div>

    <p v-if="pending" class="muted">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="t('sales.noOrders')" />
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
            <dt class="faint">{{ t('common.customer') }}</dt>
            <dd>{{ order.customer_name ?? `#${order.customer_id}` }}</dd>
          </div>
          <div>
            <dt class="faint">{{ t('common.orderDate') }}</dt>
            <dd>{{ date(order.order_date) }}</dd>
          </div>
          <div>
            <dt class="faint">{{ t('common.deliveryDate') }}</dt>
            <dd>{{ date(order.delivery_date) }}</dd>
          </div>
          <div>
            <dt class="faint">{{ t('sales.lines') }}</dt>
            <dd>{{ order.lines.length }}</dd>
          </div>
        </dl>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.item') }}</th>
                <th class="numeric">{{ t('common.quantity') }}</th>
                <th class="numeric">{{ t('common.price') }}</th>
                <th class="numeric">{{ t('sales.picked') }}</th>
                <th class="numeric">{{ t('sales.shipped') }}</th>
                <th class="numeric">{{ t('common.total') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in order.lines" :key="line.id">
                <td>
                  <span class="mono faint">{{ line.item_code }}</span>
                  {{ line.item_description }}
                </td>
                <td class="numeric">{{ number(line.quantity) }}</td>
                <td class="numeric">{{ money(line.unit_price, currency) }}</td>
                <td class="numeric">{{ number(line.qty_picked) }}</td>
                <td class="numeric">{{ number(line.qty_shipped) }}</td>
                <td class="numeric">{{ money(line.line_total, currency) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="row order-actions">
          <button
            v-if="nextAction(order)"
            class="btn btn-primary btn-sm"
            type="button"
            @click="advance(order, nextAction(order)!.status)"
          >
            {{ nextAction(order)!.label }}
          </button>

          <button
            v-if="order.status === 'PICKING' && auth.hasRole('admin', 'logistics')"
            class="btn btn-sm"
            type="button"
            @click="advance(order, 'OPEN')"
          >
            {{ t('sales.reopen') }}
          </button>

          <button
            v-if="auth.hasRole('admin') && !['INVOICED', 'CANCELLED'].includes(order.status)"
            class="btn btn-danger btn-sm"
            type="button"
            @click="cancelOrder(order)"
          >
            {{ t('sales.cancel') }}
          </button>
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

.status-select { min-width: 12rem; }

.notice {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--accent-strong);
}

.order-head { margin-bottom: 0.75rem; }

.order-number { font-weight: 600; font-size: 0.9375rem; }

.order-total { font-weight: 600; font-size: 1rem; }

.order-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
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

.order-meta dd {
  margin: 0.1rem 0 0;
  font-size: 0.8125rem;
}

.order-actions { margin-top: 0.85rem; }

@media (max-width: 800px) {
  .order-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>