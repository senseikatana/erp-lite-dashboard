<script setup lang="ts">
const { locale, locales, setLocale } = useI18n()

const available = computed(() => locales.value as { code: string; name?: string }[])

function selectLocale(code: string) {
  setLocale(code as Parameters<typeof setLocale>[0])
}
</script>

<template>
  <div>
    <span class="label-text">{{ $t('common.language') }}</span>
    <div
      class="flex gap-0.5 rounded-lg border border-sunken bg-surface p-0.5"
      role="group"
      :aria-label="$t('common.language')"
    >
      <button
        v-for="entry in available"
        :key="entry.code"
        class="btn btn-xs flex-1"
        :class="entry.code === locale ? 'btn-primary' : 'btn-text'"
        type="button"
        :aria-pressed="entry.code === locale"
        @click="selectLocale(entry.code)"
      >
        {{ entry.code.toUpperCase() }}
      </button>
    </div>
  </div>
</template>
