<script setup lang="ts">
import type { DemandLine, Page } from '~/types/api'

const { t } = useI18n()
const api = useApi()
const auth = useAuthStore()
const { number, date } = useFormat()

const notice = ref('')

const { data, pending, refresh } = await useAsyncData<Page<DemandLine>>('demand-lines', () =>
  api.get<Page<DemandLine>>('/demand', { limit: 200, action: 'PENDING' }),
)

const coverageRatio = ref(1.5)
const horizonDays = ref(30)

const canManage = computed(() => auth.hasRole('admin', 'buyer'))

async function regenerate() {
  if (!confirm(t('demand.regenerateConfirm'))) return

  notice.value = ''
  try {
    const lines = await api.post<DemandLine[]>('/demand/generate', {
      coverage_ratio: coverageRatio.value,
      horizon_days: horizonDays.value,
    })
    notice.value = t('demand.regenerated', { count: lines.length })
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}

async function setAction(line: DemandLine, action: 'ORDERED' | 'IGNORED') {
  notice.value = ''
  try {
    await api.patch(`/demand/${line.id}`, { action })
    await refresh()
  } catch (error: any) {
    notice.value = error?.statusMessage ?? t('app.error')
  }
}

/**
 * Replenishment simulator.
 *
 * Same formula the backend worksheet uses, so the two cannot disagree about
 * what a reorder quantity is.
 */
const simulator = reactive({
  coverageDays: 15,
  dailyConsumption: 10,
  stock: 0,
  computed: 0,
})

function updateSimulator(stock: number) {
  simulator.stock = stock
  const target = simulator.dailyConsumption * simulator.coverageDays
  simulator.computed = Math.max(0, target - stock)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <AppNotice v-if="notice" :message="notice" />

    <div v-if="canManage" class="card">
      <div class="card-body">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-semibold">{{ t('demand.parameters') }}</h2>
          <button class="btn btn-primary btn-sm" type="button" @click="regenerate">
            {{ t('demand.regenerate') }}
          </button>
        </div>

        <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label class="label-text" for="coverage-ratio">Coverage factor</label>
            <input
              id="coverage-ratio"
              v-model.number="coverageRatio"
              class="input w-full"
              type="number"
              step="0.1"
              min="0.1"
            />
            <span class="helper-text">Multiple of the minimum stock level.</span>
          </div>
          <div>
            <label class="label-text" for="horizon-days">Horizon (days)</label>
            <input
              id="horizon-days"
              v-model.number="horizonDays"
              class="input w-full"
              type="number"
              step="1"
              min="1"
            />
            <span class="helper-text">Delivery commitments inside this window are counted.</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-semibold">{{ t('demand.title') }}</h2>
          <span class="text-sm text-ink/60">{{ t('demand.subtitle') }}</span>
        </div>

        <p v-if="pending" class="text-sm text-ink/60">{{ t('app.loading') }}</p>

        <EmptyState v-else-if="!data?.items.length" :message="t('demand.noLines')" />

        <div v-else class="overflow-x-auto">
          <table class="table">
            <thead>
              <tr>
                <th>{{ t('common.item') }}</th>
                <th class="text-right">{{ t('demand.needed') }}</th>
                <th>{{ t('demand.requiredDate') }}</th>
                <th>{{ t('demand.source') }}</th>
                <th v-if="canManage"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in data.items" :key="line.id" class="hover:bg-surface/60">
                <td>
                  <span class="font-mono text-xs text-ink/50">{{ line.item_code }}</span>
                  {{ line.item_description }}
                </td>
                <td class="text-right tabular-nums">{{ number(line.quantity_needed) }}</td>
                <td class="whitespace-nowrap">{{ date(line.required_date) }}</td>
                <td class="text-ink/60">{{ t(`demand.source${line.source === 'MIN_STOCK' ? 'MinStock' : line.source === 'SALES_ORDER' ? 'Sales' : 'Forecast'}`) }}</td>
                <td v-if="canManage" class="text-right whitespace-nowrap">
                  <button class="btn btn-sm" type="button" @click="setAction(line, 'ORDERED')">
                    {{ t('demand.markOrdered') }}
                  </button>
                  <button class="btn btn-sm ml-1" type="button" @click="setAction(line, 'IGNORED')">
                    {{ t('demand.markIgnored') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="auth.hasRole('admin', 'logistics')" class="card">
      <div class="card-body">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-semibold">{{ t('demand.simulator') }}</h2>
          <span class="text-sm text-ink/60">{{ t('demand.simulatorHint') }}</span>
        </div>

        <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div>
            <label class="label-text" for="sim-days">{{ t('demand.coverageDays') }}</label>
            <input
              id="sim-days"
              v-model.number="simulator.coverageDays"
              class="input w-full"
              type="number"
              min="1"
              max="365"
              @input="updateSimulator(simulator.stock)"
            />
          </div>
          <div>
            <label class="label-text" for="sim-consumption">{{ t('demand.dailyConsumption') }}</label>
            <input
              id="sim-consumption"
              v-model.number="simulator.dailyConsumption"
              class="input w-full"
              type="number"
              min="0"
              step="0.5"
              @input="updateSimulator(simulator.stock)"
            />
          </div>
          <div>
            <label class="label-text" for="sim-stock">{{ t('common.stock') }}</label>
            <input
              id="sim-stock"
              class="input w-full"
              type="number"
              :value="simulator.stock"
              min="0"
              @input="updateSimulator(Number(($event.target as HTMLInputElement).value))"
            />
          </div>
        </div>

        <p class="mt-2 text-base">
          {{ t('demand.suggested') }}:
          <strong class="text-xl tabular-nums">{{ number(simulator.computed) }}</strong>
        </p>
      </div>
    </div>
  </div>
</template>
