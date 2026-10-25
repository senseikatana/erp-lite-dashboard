<script setup lang="ts">
const props = defineProps<{ value: string }>()
const { t, te } = useI18n()

const tones: Record<string, string> = {
  // Sales
  OPEN: 'neutral',
  PICKING: 'info',
  SHIPPED: 'success',
  INVOICED: 'success',
  CANCELLED: 'danger',
  // Purchasing
  RECEIVED: 'info',
  QC_PENDING: 'warning',
  QC_APPROVED: 'success',
  REJECTED: 'danger',
  CLOSED: 'neutral',
  // Quality
  PENDING: 'neutral',
  PASSED: 'success',
  FAILED: 'danger',
  // Demand
  ORDERED: 'success',
  IGNORED: 'neutral',
  // Routes
  PLANNED: 'neutral',
  IN_TRANSIT: 'info',
  DELIVERED: 'success',
}

// Static class strings so Tailwind can detect every badge variant at build time.
const toneClasses: Record<string, string> = {
  neutral: 'badge badge-soft',
  info: 'badge badge-soft badge-info',
  success: 'badge badge-soft badge-success',
  warning: 'badge badge-soft badge-warning',
  danger: 'badge badge-soft badge-error',
}

const toneClass = computed(() => toneClasses[tones[props.value] ?? 'neutral'])

const label = computed(() =>
  te(`status.${props.value}`) ? t(`status.${props.value}`) : props.value,
)
</script>

<template>
  <span :class="toneClass">{{ label }}</span>
</template>
