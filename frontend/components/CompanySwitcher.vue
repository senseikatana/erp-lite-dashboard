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
  <div>
    <label class="label-text" for="company-switcher">{{ t('common.company') }}</label>
    <select
      id="company-switcher"
      class="select select-sm w-full"
      :value="auth.activeCompany ?? ''"
      @change="onChange"
    >
      <option v-for="company in auth.companies" :key="company.code" :value="company.code">
        {{ company.name }}
      </option>
    </select>
  </div>
</template>
