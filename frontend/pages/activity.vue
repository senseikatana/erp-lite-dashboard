<script setup lang="ts">
import type { ActivityEvent, Page } from '~/types/api'

const { t } = useI18n()
const api = useApi()
const { dateTime, relative } = useFormat()

const entity = ref('')
const actor = ref('')

const { data, pending } = await useAsyncData<Page<ActivityEvent>>(
  'activity-log',
  () =>
    api.get<Page<ActivityEvent>>('/activity', {
      limit: 200,
      entity: entity.value || undefined,
      actor: actor.value || undefined,
    }),
  { watch: [entity, actor] },
)

const entities = ['sales_order', 'purchase_order', 'item', 'demand', 'route', 'customer', 'vendor', 'user']
const actors = ['admin', 'buyer', 'logistics', 'quality', 'seed']

function isSynthetic(event: ActivityEvent): boolean {
  return event.actor_username === 'seed' || event.payload?.synthetic === true
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-ink/60">{{ t('activity.subtitle') }}</p>

          <div class="flex items-center gap-2">
            <label class="sr-only" for="entity-filter">{{ t('activity.filterEntity') }}</label>
            <select id="entity-filter" v-model="entity" class="select select-sm">
              <option value="">{{ t('app.all') }}</option>
              <option v-for="option in entities" :key="option" :value="option">{{ option }}</option>
            </select>

            <label class="sr-only" for="actor-filter">{{ t('activity.filterActor') }}</label>
            <select id="actor-filter" v-model="actor" class="select select-sm">
              <option value="">{{ t('app.all') }}</option>
              <option v-for="option in actors" :key="option" :value="option">{{ option }}</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <p class="text-xs text-ink/50">{{ t('activity.syntheticNotice') }}</p>

    <p v-if="pending" class="text-sm text-ink/60">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="t('activity.noEntries')" />
    </div>

    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr>
              <th>{{ t('activity.when') }}</th>
              <th>{{ t('activity.who') }}</th>
              <th>{{ t('activity.entity') }}</th>
              <th>{{ t('activity.action') }}</th>
              <th>{{ t('activity.summary') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in data.items" :key="event.id" class="hover:bg-surface/60">
              <td class="whitespace-nowrap">
                <span :title="dateTime(event.occurred_at)">{{ relative(event.occurred_at) }}</span>
              </td>
              <td class="font-mono text-xs whitespace-nowrap">{{ event.actor_username }}</td>
              <td class="font-mono text-xs whitespace-nowrap text-ink/50">
                {{ event.entity }}<span v-if="event.entity_id">#{{ event.entity_id }}</span>
              </td>
              <td class="whitespace-nowrap">{{ event.action }}</td>
              <td>
                {{ event.summary ?? '—' }}
                <span v-if="isSynthetic(event)" class="badge badge-soft badge-xs ml-1 font-mono">seed</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
