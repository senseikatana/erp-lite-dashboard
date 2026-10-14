<script setup lang="ts">
defineProps<{ label: string; value: string | number; tone?: 'neutral' | 'accent' }>()
</script>

<template>
  <div class="card stat">
    <p class="stat-label">{{ label }}</p>
    <p class="stat-value" :class="tone === 'accent' ? 'accent' : ''">{{ value }}</p>
  </div>
</template>

<style scoped>
.stat { display: flex; flex-direction: column; gap: 0.1rem; }

.stat-label {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
}

.stat-value {
  margin: 0.15rem 0 0;
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.stat-value.accent { color: var(--accent-strong); }
</style>