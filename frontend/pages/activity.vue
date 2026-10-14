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
  <div class="stack">
    <div class="card toolbar">
      <p class="muted grow">{{ t('activity.subtitle') }}</p>

      <div class="row">
        <label class="visually-hidden" for="entity-filter">{{ t('activity.filterEntity') }}</label>
        <select id="entity-filter" v-model="entity">
          <option value="">{{ t('app.all') }}</option>
          <option v-for="option in entities" :key="option" :value="option">{{ option }}</option>
        </select>

        <label class="visually-hidden" for="actor-filter">{{ t('activity.filterActor') }}</label>
        <select id="actor-filter" v-model="actor">
          <option value="">{{ t('app.all') }}</option>
          <option v-for="option in actors" :key="option" :value="option">{{ option }}</option>
        </select>
      </div>
    </div>

    <p class="faint synth-notice">{{ t('activity.syntheticNotice') }}</p>

    <p v-if="pending" class="muted">{{ t('app.loading') }}</p>

    <div v-else-if="!data?.items.length" class="card">
      <EmptyState :message="t('activity.noEntries')" />
    </div>

    <div v-else class="table-wrap">
      <table>
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
          <tr v-for="event in data.items" :key="event.id">
            <td class="nowrap">
              <span :title="dateTime(event.occurred_at)">{{ relative(event.occurred_at) }}</span>
            </td>
            <td class="mono nowrap">{{ event.actor_username }}</td>
            <td class="mono faint nowrap">{{ event.entity }}<span v-if="event.entity_id">#{{ event.entity_id }}</span></td>
            <td class="nowrap">{{ event.action }}</td>
            <td>
              {{ event.summary ?? '—' }}
              <span v-if="isSynthetic(event)" class="synthetic-tag">seed</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.toolbar p { margin: 0; font-size: 0.875rem; }

.synth-notice { margin: 0; font-size: 0.75rem; }

.synthetic-tag {
  display: inline-block;
  margin-left: 0.4rem;
  padding: 0 0.3rem;
  font-size: 0.6875rem;
  font-family: var(--font-mono);
  color: var(--text-faint);
  background: var(--surface-sunken);
  border-radius: 3px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>