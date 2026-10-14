<script setup lang="ts">
const props = defineProps<{ value: string }>()
const { t, te } = useI18n()

const tone = computed(() => {
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
  return tones[props.value] ?? 'neutral'
})

const label = computed(() =>
  te(`status.${props.value}`) ? t(`status.${props.value}`) : props.value,
)
</script>

<template>
  <span class="badge" :class="`badge-${tone}`">{{ label }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.5;
  white-space: nowrap;
  border-radius: 999px;
  border: 1px solid transparent;
}

.badge-neutral { color: var(--text-muted); background: var(--surface-sunken); border-color: var(--border); }
.badge-info { color: var(--accent-strong); background: var(--accent-soft); border-color: #b8d8e6; }
.badge-success { color: var(--success); background: var(--success-soft); border-color: #b7e0cd; }
.badge-warning { color: var(--warning); background: var(--warning-soft); border-color: #edd6ab; }
.badge-danger { color: var(--danger); background: var(--danger-soft); border-color: #f0c1ba; }
</style>