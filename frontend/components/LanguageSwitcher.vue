<script setup lang="ts">
const { locale, locales, setLocale } = useI18n()

const available = computed(() => locales.value as { code: string; name?: string }[])
</script>

<template>
  <div class="language-switcher">
    <span class="switcher-label">{{ $t('common.language') }}</span>
    <div class="lang-buttons" role="group" :aria-label="$t('common.language')">
      <button
        v-for="entry in available"
        :key="entry.code"
        class="lang-btn"
        :class="{ active: entry.code === locale }"
        type="button"
        :aria-pressed="entry.code === locale"
        @click="setLocale(entry.code)"
      >
        {{ entry.code.toUpperCase() }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.language-switcher {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.switcher-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-faint);
}

.lang-buttons {
  display: flex;
  gap: 2px;
  padding: 2px;
  background: var(--surface-sunken);
  border-radius: var(--radius-sm);
}

.lang-btn {
  flex: 1 1 0;
  padding: 0.25rem 0;
  font: inherit;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.lang-btn:hover { color: var(--text); }

.lang-btn.active {
  color: var(--text);
  background: var(--surface-raised);
  box-shadow: var(--shadow-sm);
}
</style>