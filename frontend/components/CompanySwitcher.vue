<script setup lang="ts">
const auth = useAuthStore()
const { t } = useI18n()

async function onChange(event: Event) {
  const target = event.target as HTMLSelectElement
  auth.activeCompany = target.value
  // Company-scoped data differs per tenant, so every cached list is stale now.
  await refreshNuxtData()
}
</script>

<template>
  <div class="company-switcher">
    <label class="switcher-label" for="company-switcher">{{ t('common.company') }}</label>
    <select
      id="company-switcher"
      class="switcher-select"
      :value="auth.activeCompany ?? ''"
      @change="onChange"
    >
      <option v-for="company in auth.companies" :key="company.code" :value="company.code">
        {{ company.name }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.company-switcher {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.switcher-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-faint);
}

.switcher-select {
  font-size: 0.8125rem;
}
</style>