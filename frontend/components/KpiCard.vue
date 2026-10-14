<script setup lang="ts">
import type { Kpi } from '~/types/api'

const props = defineProps<{ kpi: Kpi }>()

const { t, te } = useI18n()
const { number } = useFormat()

const label = computed(() =>
  te(`kpi.${props.kpi.key}`) ? t(`kpi.${props.kpi.key}`) : props.kpi.key,
)

// A null value is not a zero. It means the metric could not be measured, which
// is a different statement from "performance is zero", and rendering it as 0
// would be a lie.
const hasValue = computed(() => props.kpi.value !== null && props.kpi.value !== undefined)
</script>

<template>
  <div class="card kpi">
    <p class="kpi-label">{{ label }}</p>

    <template v-if="hasValue">
      <p class="kpi-value">
        {{ number(kpi.value, kpi.unit === '%' ? 1 : 1) }}
        <span v-if="kpi.unit" class="kpi-unit">{{ kpi.unit }}</span>
      </p>
      <p v-if="kpi.delta !== null" class="kpi-delta" :class="kpi.delta >= 0 ? 'up' : 'down'">
        {{ kpi.delta >= 0 ? '▲' : '▼' }} {{ number(Math.abs(kpi.delta), 1) }}
      </p>
    </template>

    <template v-else>
      <p class="kpi-value kpi-empty">{{ t('kpi.noData') }}</p>
      <p class="kpi-hint">{{ t('kpi.noDataHint') }}</p>
    </template>
  </div>
</template>

<style scoped>
.kpi { display: flex; flex-direction: column; gap: 0.15rem; }

.kpi-label {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
}

.kpi-value {
  margin: 0.15rem 0 0;
  font-size: 1.75rem;
  font-weight: 600;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

.kpi-unit {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-muted);
}

.kpi-empty {
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--text-faint);
}

.kpi-hint,
.kpi-delta {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-faint);
}

.kpi-delta.up { color: var(--success); }
.kpi-delta.down { color: var(--danger); }
</style>