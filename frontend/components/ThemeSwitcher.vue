<script setup lang="ts">
import type { ThemeName } from '~/composables/useTheme'

const { theme, setTheme, themes } = useTheme()
const { t } = useI18n()

function onChange(event: Event) {
  setTheme((event.target as HTMLSelectElement).value as ThemeName)
}
</script>

<template>
  <div>
    <label class="label-text" for="theme-switcher">{{ t('common.theme') }}</label>
    <select
      id="theme-switcher"
      class="select select-sm w-full capitalize"
      :value="theme"
      @change="onChange"
    >
      <option v-for="name in themes" :key="name" :value="name">{{ name }}</option>
    </select>
  </div>
</template>
