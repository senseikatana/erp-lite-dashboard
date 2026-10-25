<script setup lang="ts">
defineProps<{ label: string; value: string | number; tone?: 'neutral' | 'accent' }>()
</script>

<template>
  <div class="card">
    <div class="card-body gap-1 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-ink/60">{{ label }}</p>
      <p
        class="text-xl font-semibold leading-tight tabular-nums"
        :class="tone === 'accent' ? 'text-brand' : ''"
      >
        {{ value }}
      </p>
    </div>
  </div>
</template>
