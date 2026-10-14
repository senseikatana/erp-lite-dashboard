<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()

const { t } = useI18n()

useHead({ title: `${t('app.error')} · ERP-Lite` })

function goHome() {
  clearError({ redirect: '/' })
}
</script>

<template>
  <main class="error-page">
    <div class="error-card">
      <p class="error-code">{{ props.error.statusCode }}</p>
      <h1 class="error-title">
        {{ props.error.statusCode === 404 ? 'Page not found' : t('app.error') }}
      </h1>
      <p class="error-detail">
        {{ props.error.statusCode === 404 ? 'The page you requested does not exist.' : props.error.message }}
      </p>
      <button class="btn btn-primary" type="button" @click="goHome">
        {{ t('common.name') }}
      </button>
    </div>
  </main>
</template>

<style scoped>
.error-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem;
  background: var(--surface);
}

.error-card {
  text-align: center;
  max-width: 32rem;
}

.error-code {
  font-size: 4rem;
  font-weight: 700;
  color: var(--accent);
  margin: 0;
  line-height: 1;
}

.error-title {
  font-size: 1.5rem;
  margin: 1rem 0 0.5rem;
  color: var(--text);
}

.error-detail {
  color: var(--text-muted);
  margin-bottom: 1.5rem;
}
</style>