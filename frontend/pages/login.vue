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
  <div class="login">
    <div class="login-card">
      <div class="login-head">
        <span class="login-mark" aria-hidden="true">▤</span>
        <p class="login-brand">{{ t('app.title') }}</p>
        <h1>{{ t('login.title') }}</h1>
        <p class="muted">{{ t('login.subtitle') }}</p>
      </div>

      <form @submit.prevent="submit">
        <div class="field">
          <label for="username">{{ t('login.username') }}</label>
          <input
            id="username"
            v-model="username"
            type="text"
            autocomplete="username"
            required
            autofocus
          />
        </div>

        <div class="field">
          <label for="password">{{ t('login.password') }}</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </div>

        <p v-if="error" class="login-error" role="alert">{{ error }}</p>

        <button class="btn btn-primary login-submit" type="submit" :disabled="busy">
          {{ busy ? t('app.loading') : t('login.submit') }}
        </button>
      </form>

      <div class="login-demo">
        <p class="demo-title">{{ t('login.demoAccounts') }}</p>
        <div class="demo-accounts">
          <button
            v-for="account in demoAccounts"
            :key="account"
            class="demo-chip"
            type="button"
            @click="username = account; password = 'demo1234'"
          >
            {{ account }}
          </button>
        </div>
        <p class="demo-hint faint">{{ t('login.password') }}: <code>demo1234</code></p>
        <p class="demo-hint faint">{{ t('login.hint') }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login { width: 100%; max-width: 25rem; }

.login-card {
  padding: 1.75rem 1.6rem;
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

.login-head {
  text-align: center;
  margin-bottom: 1.5rem;
}

.login-mark {
  display: inline-grid;
  place-items: center;
  width: 42px;
  height: 42px;
  margin-bottom: 0.6rem;
  font-size: 1.15rem;
  color: #fff;
  background: var(--accent);
  border-radius: var(--radius);
}

.login-brand {
  margin: 0 0 0.3rem;
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-muted);
}

.login-head h1 { margin: 0 0 0.15rem; font-size: 1.35rem; }
.login-head p { margin: 0; font-size: 0.8125rem; }

.login-submit { width: 100%; margin-top: 0.25rem; }

.login-error {
  margin: 0 0 0.75rem;
  padding: 0.5rem 0.65rem;
  font-size: 0.8125rem;
  color: var(--danger);
  background: var(--danger-soft);
  border: 1px solid #f0c1ba;
  border-radius: var(--radius-sm);
}

.login-demo {
  margin-top: 1.5rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--border);
}

.demo-title {
  margin: 0 0 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.demo-accounts { display: flex; flex-wrap: wrap; gap: 0.35rem; }

.demo-chip {
  padding: 0.2rem 0.55rem;
  font: inherit;
  font-size: 0.8125rem;
  color: var(--text);
  background: var(--surface-sunken);
  border: 1px solid var(--border);
  border-radius: 999px;
  cursor: pointer;
}

.demo-chip:hover {
  background: var(--accent-soft);
  border-color: #b8d8e6;
  color: var(--accent-strong);
}

.demo-hint {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
}

.demo-hint code {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.05rem 0.25rem;
  background: var(--surface-sunken);
  border-radius: 3px;
}
</style>