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
  <div class="flex flex-col gap-4">
    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap items-center gap-3">
          <label for="status-filter" class="text-sm text-ink/50">{{ t('sales.filterStatus') }}</label>
          <select
            id="status-filter"
            v-model="statusFilter"
            multiple
            size="1"
            class="select select-sm min-w-48"
            @change="(e) => { const v = (e.target as HTMLSelectElement).value; statusFilter = v ? [v as SalesOrderStatus] : [] }"
          >
            <option value="">{{ t('app.all') }}</option>
            <option v-for="option in statusOptions" :key="option" :value="option">
              {{ t(`status.${option}`) }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <AppNotice v-if="notice" :message="notice" />

    <p v-if="pending" class="text-sm text-ink/60">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="t('sales.noOrders')" />
    </div>

    <div v-else class="flex flex-col gap-4">
      <article v-for="order in data.items" :key="order.id" class="card">
        <div class="card-body">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <span class="font-mono text-sm font-semibold">{{ order.number }}</span>
              <StatusBadge :value="order.status" />
            </div>
            <span class="text-base font-semibold tabular-nums">{{ money(order.total, currency) }}</span>
          </div>

          <dl class="grid grid-cols-2 gap-3 border-y border-sunken py-3 md:grid-cols-4">
            <div>
              <dt class="text-xs uppercase tracking-wide text-ink/50">{{ t('common.customer') }}</dt>
              <dd class="text-sm">{{ order.customer_name ?? `#${order.customer_id}` }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-ink/50">{{ t('common.orderDate') }}</dt>
              <dd class="text-sm">{{ date(order.order_date) }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-ink/50">{{ t('common.deliveryDate') }}</dt>
              <dd class="text-sm">{{ date(order.delivery_date) }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-ink/50">{{ t('sales.lines') }}</dt>
              <dd class="text-sm">{{ order.lines.length }}</dd>
            </div>
          </dl>

          <div class="overflow-x-auto">
            <table class="table">
              <thead>
                <tr>
                  <th>{{ t('common.item') }}</th>
                  <th class="text-right">{{ t('common.quantity') }}</th>
                  <th class="text-right">{{ t('common.price') }}</th>
                  <th class="text-right">{{ t('sales.picked') }}</th>
                  <th class="text-right">{{ t('sales.shipped') }}</th>
                  <th class="text-right">{{ t('common.total') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="line in order.lines" :key="line.id" class="hover:bg-surface/60">
                  <td>
                    <span class="font-mono text-xs text-ink/50">{{ line.item_code }}</span>
                    {{ line.item_description }}
                  </td>
                  <td class="text-right tabular-nums">{{ number(line.quantity) }}</td>
                  <td class="text-right tabular-nums">{{ money(line.unit_price, currency) }}</td>
                  <td class="text-right tabular-nums">{{ number(line.qty_picked) }}</td>
                  <td class="text-right tabular-nums">{{ number(line.qty_shipped) }}</td>
                  <td class="text-right tabular-nums">{{ money(line.line_total, currency) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex flex-wrap items-center gap-2">
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
              class="btn btn-error btn-sm"
              type="button"
              @click="cancelOrder(order)"
            >
              {{ t('sales.cancel') }}
            </button>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
