<script setup lang="ts">
const auth = useAuthStore()
</script>

<template>
  <div class="grid min-h-screen place-items-center bg-surface p-6">
    <slot />
  </div>
</template>
