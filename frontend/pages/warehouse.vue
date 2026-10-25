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

// Static class strings so Tailwind detects every badge variant at build time.
const toneClasses: Record<'ok' | 'near' | 'low', string> = {
  ok: 'badge badge-soft badge-success',
  near: 'badge badge-soft badge-warning',
  low: 'badge badge-soft badge-error',
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap items-center gap-3">
          <label class="sr-only" for="item-search">{{ t('app.search') }}</label>
          <input
            id="item-search"
            v-model="search"
            type="search"
            class="input w-full sm:w-64"
            :placeholder="t('app.search')"
          />
          <label class="flex cursor-pointer items-center gap-2 text-sm">
            <input v-model="belowMinimum" type="checkbox" class="checkbox checkbox-sm" />
            {{ t('warehouse.belowMinimumOnly') }}
          </label>
        </div>
      </div>
    </div>

    <AppNotice v-if="notice" :message="notice" />

    <p v-if="pending" class="text-sm text-ink/60">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="t('warehouse.noItems')" />
    </div>

    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr>
              <th>{{ t('common.code') }}</th>
              <th>{{ t('common.name') }}</th>
              <th>{{ t('common.category') }}</th>
              <th>{{ t('common.location') }}</th>
              <th class="text-right">{{ t('common.stock') }}</th>
              <th class="text-right">{{ t('common.minimum') }}</th>
              <th class="text-right">{{ t('common.cost') }}</th>
              <th>{{ t('warehouse.stockStatus') }}</th>
              <th v-if="auth.hasRole('admin', 'logistics')"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in data.items" :key="item.id" class="hover:bg-surface/60">
              <td class="font-mono text-xs whitespace-nowrap">{{ item.code }}</td>
              <td>{{ item.description }}</td>
              <td class="text-ink/60">{{ item.category ?? '—' }}</td>
              <td class="font-mono text-xs">{{ item.location }}</td>
              <td class="text-right tabular-nums">{{ number(item.stock) }}</td>
              <td class="text-right tabular-nums">{{ number(item.min_stock) }}</td>
              <td class="text-right tabular-nums">{{ money(item.unit_cost, currency) }}</td>
              <td>
                <span :class="toneClasses[stockTone(item)]">
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
    </div>

    <!-- Stock adjustment dialog -->
    <div
      v-if="adjusting"
      class="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4"
      @click.self="adjusting = null"
    >
      <div
        class="modal-content w-full max-w-md"
        role="dialog"
        aria-modal="true"
        :aria-label="t('warehouse.adjustTitle')"
      >
        <div class="modal-header">
          <h2 class="text-lg font-semibold">{{ t('warehouse.adjustTitle') }}</h2>
          <button class="btn btn-sm btn-text" type="button" @click="adjusting = null">✕</button>
        </div>

        <div class="modal-body flex flex-col gap-3">
          <p class="font-mono text-sm text-ink/60">
            {{ adjusting.item.code }} · {{ adjusting.item.description }}
          </p>
          <p class="text-sm">
            {{ t('common.stock') }}: <strong class="tabular-nums">{{ number(adjusting.item.stock) }}</strong>
          </p>

          <div>
            <label class="label-text" for="adjust-qty">{{ t('warehouse.adjustQuantity') }}</label>
            <input id="adjust-qty" v-model.number="adjusting.quantity" class="input w-full" type="number" step="1" />
            <span class="helper-text">Negative values reduce stock.</span>
          </div>

          <div>
            <label class="label-text" for="adjust-reason">{{ t('warehouse.adjustReason') }}</label>
            <input id="adjust-reason" v-model="adjusting.reason" class="input w-full" type="text" />
            <span class="helper-text">{{ t('warehouse.adjustReasonHint') }}</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn" type="button" @click="adjusting = null">{{ t('app.cancel') }}</button>
          <button class="btn btn-primary" type="button" @click="submitAdjustment">
            {{ t('app.save') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
