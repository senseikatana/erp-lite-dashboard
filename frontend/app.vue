<script setup lang="ts">
const { locale } = useI18n()
const { theme } = useTheme()

// Keep the document language attribute in sync so screen readers and the
// browser's own hyphenation match the active locale. The theme attribute is
// resolved from the cookie during SSR, so the first paint is already correct.
useHead(() => ({
  htmlAttrs: { lang: locale.value, 'data-theme': theme.value },
}))
</script>

<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>