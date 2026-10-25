<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()

const { t } = useI18n()
const { theme } = useTheme()

// Error pages bypass app.vue, so the theme attribute is applied here too.
useHead(() => ({
  title: `${t('app.error')} · ERP-Lite`,
  htmlAttrs: { 'data-theme': theme.value },
}))

function goHome() {
  clearError({ redirect: '/' })
}
</script>

<template>
  <main class="grid min-h-screen place-items-center bg-surface p-8">
    <div class="card max-w-lg text-center">
      <div class="card-body items-center gap-3">
        <p class="text-6xl font-bold leading-none text-brand">{{ props.error.statusCode }}</p>
        <h1 class="text-2xl font-semibold">
          {{ props.error.statusCode === 404 ? 'Page not found' : t('app.error') }}
        </h1>
        <p class="text-sm text-ink/60">
          {{ props.error.statusCode === 404 ? 'The page you requested does not exist.' : props.error.message }}
        </p>
        <button class="btn btn-primary" type="button" @click="goHome">
          {{ t('common.name') }}
        </button>
      </div>
    </div>
  </main>
</template>
