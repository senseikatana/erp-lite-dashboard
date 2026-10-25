<script setup lang="ts">
defineProps<{ message?: string }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col items-center gap-1.5 px-4 py-10 text-center">
    <p class="text-2xl text-ink/30" aria-hidden="true">◍</p>
    <p class="text-sm text-ink/60">{{ message ?? t('app.empty') }}</p>
  </div>
</template>
