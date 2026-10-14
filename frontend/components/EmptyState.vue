<script setup lang="ts">
defineProps<{ message?: string }>()
const { t } = useI18n()
</script>

<template>
  <div class="empty">
    <p class="empty-mark" aria-hidden="true">◍</p>
    <p class="empty-text">{{ message ?? t('app.empty') }}</p>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 2.5rem 1rem;
  text-align: center;
}

.empty-mark {
  margin: 0;
  font-size: 1.75rem;
  color: var(--text-faint);
}

.empty-text {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-muted);
}
</style>