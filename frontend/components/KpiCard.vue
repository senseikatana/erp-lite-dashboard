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
  <div class="card">
    <div class="card-body gap-1 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-ink/60">{{ label }}</p>

      <template v-if="hasValue">
        <p class="text-2xl font-semibold leading-tight tabular-nums">
          {{ number(kpi.value, 1) }}
          <span v-if="kpi.unit" class="text-sm font-medium text-ink/60">{{ kpi.unit }}</span>
        </p>
        <p
          v-if="kpi.delta !== null"
          class="text-xs"
          :class="kpi.delta >= 0 ? 'text-ok' : 'text-danger'"
        >
          {{ kpi.delta >= 0 ? '▲' : '▼' }} {{ number(Math.abs(kpi.delta), 1) }}
        </p>
      </template>

      <template v-else>
        <p class="text-base font-medium text-ink/50">{{ t('kpi.noData') }}</p>
        <p class="text-xs text-ink/50">{{ t('kpi.noDataHint') }}</p>
      </template>
    </div>
  </div>
</template>
