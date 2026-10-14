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
  <div class="stack">
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="canManage" class="card">
      <div class="card-header">
        <h2>{{ t('demand.parameters') }}</h2>
        <button class="btn btn-primary btn-sm" type="button" @click="regenerate">
          {{ t('demand.regenerate') }}
        </button>
      </div>

      <div class="grid grid-2">
        <div class="field">
          <label for="coverage-ratio">Coverage factor</label>
          <input id="coverage-ratio" v-model.number="coverageRatio" type="number" step="0.1" min="0.1" />
          <span class="hint">Multiple of the minimum stock level.</span>
        </div>
        <div class="field">
          <label for="horizon-days">Horizon (days)</label>
          <input id="horizon-days" v-model.number="horizonDays" type="number" step="1" min="1" />
          <span class="hint">Delivery commitments inside this window are counted.</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2>{{ t('demand.title') }}</h2>
        <span class="muted">{{ t('demand.subtitle') }}</span>
      </div>

      <p v-if="pending" class="muted">{{ t('app.loading') }}</p>

      <EmptyState v-else-if="!data?.items.length" :message="t('demand.noLines')" />

      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ t('common.item') }}</th>
              <th class="numeric">{{ t('demand.needed') }}</th>
              <th>{{ t('demand.requiredDate') }}</th>
              <th>{{ t('demand.source') }}</th>
              <th v-if="canManage"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in data.items" :key="line.id">
              <td>
                <span class="mono faint">{{ line.item_code }}</span>
                {{ line.item_description }}
              </td>
              <td class="numeric">{{ number(line.quantity_needed) }}</td>
              <td class="nowrap">{{ date(line.required_date) }}</td>
              <td class="muted">{{ t(`demand.source${line.source === 'MIN_STOCK' ? 'MinStock' : line.source === 'SALES_ORDER' ? 'Sales' : 'Forecast'}`) }}</td>
              <td v-if="canManage" class="text-right">
                <button class="btn btn-sm" type="button" @click="setAction(line, 'ORDERED')">
                  {{ t('demand.markOrdered') }}
                </button>
                <button class="btn btn-sm" type="button" @click="setAction(line, 'IGNORED')">
                  {{ t('demand.markIgnored') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="auth.hasRole('admin', 'logistics')" class="card">
      <div class="card-header">
        <h2>{{ t('demand.simulator') }}</h2>
        <span class="muted">{{ t('demand.simulatorHint') }}</span>
      </div>

      <div class="grid grid-3">
        <div class="field">
          <label for="sim-days">{{ t('demand.coverageDays') }}</label>
          <input
            id="sim-days"
            v-model.number="simulator.coverageDays"
            type="number"
            min="1"
            max="365"
            @input="updateSimulator(simulator.stock)"
          />
        </div>
        <div class="field">
          <label for="sim-consumption">{{ t('demand.dailyConsumption') }}</label>
          <input
            id="sim-consumption"
            v-model.number="simulator.dailyConsumption"
            type="number"
            min="0"
            step="0.5"
            @input="updateSimulator(simulator.stock)"
          />
        </div>
        <div class="field">
          <label for="sim-stock">{{ t('common.stock') }}</label>
          <input
            id="sim-stock"
            type="number"
            :value="simulator.stock"
            min="0"
            @input="updateSimulator(Number(($event.target as HTMLInputElement).value))"
          />
        </div>
      </div>

      <p class="sim-result">
        {{ t('demand.suggested') }}:
        <strong>{{ number(simulator.computed) }}</strong>
      </p>
    </div>
  </div>
</template>

<style scoped>
.notice {
  margin: 0;
  padding: 0.5rem 0.65rem;
  font-size: 0.8125rem;
  color: var(--accent-strong);
  background: var(--accent-soft);
  border-radius: var(--radius-sm);
}

.sim-result {
  margin: 0.5rem 0 0;
  font-size: 0.9375rem;
}

.sim-result strong {
  font-size: 1.25rem;
  font-variant-numeric: tabular-nums;
}

td .btn + .btn { margin-left: 0.25rem; }
</style>