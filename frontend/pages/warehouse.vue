<script setup lang="ts">
import type { Item, Page } from '~/types/api'

const { t } = useI18n()
const api = useApi()
const auth = useAuthStore()
const { money, number } = useFormat()

const search = ref('')
const belowMinimum = ref(false)
const notice = ref('')

const { data, pending, refresh } = await useAsyncData<Page<Item>>(
  'warehouse-items',
  () =>
    api.get<Page<Item>>('/warehouse/items', {
      limit: 200,
      search: search.value || undefined,
      below_minimum: belowMinimum.value || undefined,
    }),
  { watch: [search, belowMinimum] },
)

const currency = computed(
  () => auth.companies.find((c) => c.code === auth.activeCompany)?.currency ?? 'EUR',
)

type Adjustment = { item: Item; quantity: number; reason: string } | null
const adjusting = ref<Adjustment>(null)

function openAdjustment(item: Item) {
  adjusting.value = { item, quantity: 0, reason: '' }
}

async function submitAdjustment() {
  if (!adjusting.value) return
  const { item, quantity, reason } = adjusting.value

  if (!reason.trim()) {
    notice.value = t('warehouse.adjustReasonHint')
    return
  }

  notice.value = ''
  try {
    await api.post(`/warehouse/items/${item.id}/adjust`, {
      quantity,
      reason: reason.trim(),
    })
    notice.value = t('warehouse.adjusted')
    adjusting.value = null
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}

function stockTone(item: Item): 'ok' | 'near' | 'low' {
  if (item.stock < item.min_stock) return 'low'
  if (item.min_stock > 0 && item.stock < item.min_stock * 1.5) return 'near'
  return 'ok'
}
</script>

<template>
  <div class="stack">
    <div class="card toolbar">
      <div class="row grow">
        <label class="visually-hidden" for="item-search">{{ t('app.search') }}</label>
        <input
          id="item-search"
          v-model="search"
          type="search"
          class="grow"
          :placeholder="t('app.search')"
        />
        <label class="checkbox">
          <input v-model="belowMinimum" type="checkbox" />
          {{ t('warehouse.belowMinimumOnly') }}
        </label>
      </div>
      <p v-if="notice" class="notice">{{ notice }}</p>
    </div>

    <p v-if="pending" class="muted">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="t('warehouse.noItems')" />
    </div>

    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('common.code') }}</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('common.category') }}</th>
            <th>{{ t('common.location') }}</th>
            <th class="numeric">{{ t('common.stock') }}</th>
            <th class="numeric">{{ t('common.minimum') }}</th>
            <th class="numeric">{{ t('common.cost') }}</th>
            <th>{{ t('warehouse.stockStatus') }}</th>
            <th v-if="auth.hasRole('admin', 'logistics')"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in data.items" :key="item.id">
            <td class="mono nowrap">{{ item.code }}</td>
            <td>{{ item.description }}</td>
            <td class="muted">{{ item.category ?? '—' }}</td>
            <td class="mono">{{ item.location }}</td>
            <td class="numeric">{{ number(item.stock) }}</td>
            <td class="numeric">{{ number(item.min_stock) }}</td>
            <td class="numeric">{{ money(item.unit_cost, currency) }}</td>
            <td>
              <span class="tone" :class="`tone-${stockTone(item)}`">
                {{ t(`warehouse.${stockTone(item)}`) }}
              </span>
            </td>
            <td v-if="auth.hasRole('admin', 'logistics')" class="text-right">
              <button class="btn btn-sm" type="button" @click="openAdjustment(item)">
                {{ t('warehouse.adjust') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Stock adjustment modal -->
    <div v-if="adjusting" class="modal-backdrop" @click.self="adjusting = null">
      <div class="modal card" role="dialog" aria-modal="true" :aria-label="t('warehouse.adjustTitle')">
        <div class="card-header">
          <h2>{{ t('warehouse.adjustTitle') }}</h2>
        </div>

        <p class="muted mono">
          {{ adjusting.item.code }} · {{ adjusting.item.description }}
        </p>
        <p class="muted">
          {{ t('common.stock') }}: <strong>{{ number(adjusting.item.stock) }}</strong>
        </p>

        <div class="field">
          <label for="adjust-qty">{{ t('warehouse.adjustQuantity') }}</label>
          <input id="adjust-qty" v-model.number="adjusting.quantity" type="number" step="1" />
          <span class="hint">Negative values reduce stock.</span>
        </div>

        <div class="field">
          <label for="adjust-reason">{{ t('warehouse.adjustReason') }}</label>
          <input id="adjust-reason" v-model="adjusting.reason" type="text" />
          <span class="hint">{{ t('warehouse.adjustReasonHint') }}</span>
        </div>

        <div class="row">
          <button class="btn btn-primary" type="button" @click="submitAdjustment">
            {{ t('app.save') }}
          </button>
          <button class="btn" type="button" @click="adjusting = null">{{ t('app.cancel') }}</button>
        </div>
      </div>
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

.notice { margin: 0; font-size: 0.8125rem; color: var(--accent-strong); }

.tone {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 999px;
}

.tone-ok { color: var(--success); background: var(--success-soft); }
.tone-near { color: var(--warning); background: var(--warning-soft); }
.tone-low { color: var(--danger); background: var(--danger-soft); }

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgb(16 24 40 / 45%);
  z-index: 50;
}

.modal {
  width: 100%;
  max-width: 26rem;
  margin: 0;
  box-shadow: var(--shadow);
}
</style>