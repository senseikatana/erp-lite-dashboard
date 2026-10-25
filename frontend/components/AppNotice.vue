<script setup lang="ts">
withDefaults(defineProps<{ message?: string; tone?: 'neutral' | 'error' }>(), {
  tone: 'neutral',
})
</script>

<template>
  <p
    v-if="message"
    class="alert alert-soft text-sm"
    :class="tone === 'error' ? 'alert-error' : ''"
    role="status"
  >
    {{ message }}
  </p>
</template>
