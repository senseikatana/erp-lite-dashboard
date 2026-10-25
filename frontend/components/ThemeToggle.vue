<script setup lang="ts">
const { theme, setTheme } = useTheme()
const { t } = useI18n()

const isDark = computed(() => theme.value === 'dark')

function toggle() {
  setTheme(isDark.value ? 'light' : 'dark')
}
</script>

<template>
  <button
    id="theme-toggle"
    class="btn btn-sm btn-square btn-text"
    type="button"
    :aria-pressed="isDark"
    :aria-label="t('user.themeToggle')"
    :title="t('user.themeToggle')"
    @click="toggle"
  >
    <span aria-hidden="true">{{ isDark ? '☀' : '☾' }}</span>
  </button>
</template>
