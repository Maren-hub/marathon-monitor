<script setup>
defineProps({ alerts: { type: Array, default: () => [] } })
defineEmits(['acknowledge', 'locate'])

const levelLabel = { critical: '紧急', warning: '关注', info: '信息' }

function formatTime(value) {
  return new Date(value).toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <section class="panel alert-panel">
    <div class="panel-heading">
      <div>
        <span class="eyebrow">EVENT CENTER</span>
        <h2>实时事件</h2>
      </div>
      <span class="live-mark"><i></i> LIVE</span>
    </div>

    <div class="alert-list">
      <article
        v-for="alert in alerts"
        :key="alert.id"
        class="alert-card"
        :class="[alert.level, { handled: alert.status !== 'new' }]"
        @click="$emit('locate', alert.segment_id)"
      >
        <div class="alert-topline">
          <span class="level-badge">{{ levelLabel[alert.level] }}</span>
          <time>{{ formatTime(alert.created_at) }}</time>
        </div>
        <h3>{{ alert.title }}</h3>
        <p>{{ alert.message }}</p>
        <div class="alert-footer">
          <span>{{ alert.segment_id }}<template v-if="alert.athlete_id"> · {{ alert.athlete_id }}</template></span>
          <button
            v-if="alert.status === 'new'"
            @click.stop="$emit('acknowledge', alert.id)"
          >确认处置</button>
          <span v-else class="handled-label">已确认</span>
        </div>
      </article>
    </div>
  </section>
</template>

