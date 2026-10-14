<script setup lang="ts">
const { locale } = useI18n()

// Keep the document language attribute in sync so screen readers and the
// browser's own hyphenation match the active locale.
useHead(() => ({
  htmlAttrs: { lang: locale.value },
}))
</script>

<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>