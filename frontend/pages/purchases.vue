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
  <div class="flex flex-col gap-4">
    <div class="card">
      <div class="card-body">
        <div class="tabs tabs-bordered" role="tablist">
          <button
            class="tab"
            :class="{ 'tab-active': tab === 'orders' }"
            role="tab"
            type="button"
            :aria-selected="tab === 'orders'"
            @click="tab = 'orders'"
          >
            {{ t('purchases.orders') }}
          </button>
          <button
            class="tab"
            :class="{ 'tab-active': tab === 'quality' }"
            role="tab"
            type="button"
            :aria-selected="tab === 'quality'"
            @click="tab = 'quality'"
          >
            {{ t('purchases.qualityQueue') }}
          </button>
        </div>
      </div>
    </div>

    <AppNotice v-if="notice" :message="notice" />

    <p v-if="pending" class="text-sm text-ink/60">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="tab === 'quality' ? t('dashboard.noAlerts') : t('purchases.noOrders')" />
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

          <dl class="grid grid-cols-2 gap-3 border-y border-sunken py-3 md:grid-cols-3">
            <div>
              <dt class="text-xs uppercase tracking-wide text-ink/50">{{ t('common.vendor') }}</dt>
              <dd class="text-sm">{{ order.vendor_name ?? `#${order.vendor_id}` }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-ink/50">{{ t('common.orderDate') }}</dt>
              <dd class="text-sm">{{ date(order.order_date) }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-ink/50">{{ t('common.expectedDate') }}</dt>
              <dd class="text-sm">{{ date(order.expected_date) }}</dd>
            </div>
          </dl>

          <div class="overflow-x-auto">
            <table class="table">
              <thead>
                <tr>
                  <th>{{ t('common.item') }}</th>
                  <th class="text-right">{{ t('common.quantity') }}</th>
                  <th class="text-right">{{ t('purchases.received') }}</th>
                  <th class="text-right">{{ t('common.cost') }}</th>
                  <th>{{ t('purchases.qcStatus') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="line in order.lines" :key="line.id" class="hover:bg-surface/60">
                  <td>
                    <span class="font-mono text-xs text-ink/50">{{ line.item_code }}</span>
                    {{ line.item_description }}
                  </td>
                  <td class="text-right tabular-nums">{{ number(line.quantity) }}</td>
                  <td class="text-right tabular-nums">{{ number(line.qty_received) }}</td>
                  <td class="text-right tabular-nums">{{ money(line.unit_cost, currency) }}</td>
                  <td><StatusBadge :value="line.qc_status" /></td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex flex-wrap items-center gap-2">
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
              <button class="btn btn-error btn-sm" type="button" @click="decide(order, false)">
                {{ t('purchases.reject') }}
              </button>
            </template>

            <p
              v-if="order.status === 'QC_PENDING' && !auth.hasRole('admin', 'quality')"
              class="text-xs text-ink/50"
            >
              {{ t('purchases.quality') }}
            </p>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
