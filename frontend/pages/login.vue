<script setup lang="ts">
import type { Token } from '~/types/api'

definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const auth = useAuthStore()
const config = useRuntimeConfig()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true

  try {
    const payload = await $fetch<Token>(`${config.public.apiBase}/auth/login`, {
      method: 'POST',
      body: { username: username.value, password: password.value },
    })

    auth.setSession(payload)
    // Load the company list up front so the switcher is populated immediately.
    auth.setCompanies(await $fetch(`${config.public.apiBase}/companies`, {
      headers: { Authorization: `Bearer ${payload.access_token}` },
    }))

    await navigateTo((route.query.redirect as string) || '/')
  } catch (err: any) {
    error.value = err?.data?.detail ?? t('login.invalid')
  } finally {
    busy.value = false
  }
}

const demoAccounts = ['admin', 'buyer', 'logistics', 'quality']
</script>

<template>
  <div class="w-full max-w-sm">
    <div class="card">
      <div class="card-body">
        <div class="mb-2 text-center">
          <span
            class="text-bg-primary mx-auto mb-2 grid size-11 place-items-center rounded-lg text-lg"
            aria-hidden="true"
          >
            ▤
          </span>
          <p class="text-xs font-semibold tracking-wide text-ink/60">{{ t('app.title') }}</p>
          <h1 class="text-xl font-semibold">{{ t('login.title') }}</h1>
          <p class="text-sm text-ink/60">{{ t('login.subtitle') }}</p>
        </div>

        <form class="flex flex-col gap-3" @submit.prevent="submit">
          <div>
            <label class="label-text" for="username">{{ t('login.username') }}</label>
            <input
              id="username"
              v-model="username"
              class="input w-full"
              type="text"
              autocomplete="username"
              required
              autofocus
            />
          </div>

          <div>
            <label class="label-text" for="password">{{ t('login.password') }}</label>
            <input
              id="password"
              v-model="password"
              class="input w-full"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>

          <AppNotice v-if="error" :message="error" tone="error" />

          <button class="btn btn-primary w-full" type="submit" :disabled="busy">
            {{ busy ? t('app.loading') : t('login.submit') }}
          </button>
        </form>

        <div class="mt-2 border-t border-sunken pt-4">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink/60">
            {{ t('login.demoAccounts') }}
          </p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="account in demoAccounts"
              :key="account"
              class="btn btn-xs btn-soft"
              type="button"
              @click="username = account; password = 'demo1234'"
            >
              {{ account }}
            </button>
          </div>
          <p class="mt-2 text-xs text-ink/50">
            {{ t('login.password') }}:
            <code class="rounded bg-sunken px-1 py-0.5 font-mono">demo1234</code>
          </p>
          <p class="mt-1 text-xs text-ink/50">{{ t('login.hint') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
