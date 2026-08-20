<script setup>
defineProps({ alerts: { type: Array, default: () => [] } })
defineEmits(['action', 'locate'])

const levelLabel = { critical: '紧急', warning: '关注', info: '信息' }
const actionLabel = {
  acknowledge: '指挥中心确认',
  uav_review: '无人机复核',
  medical_dispatch: '医疗救援',
  staff_dispatch: '现场疏导'
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDuration(seconds) {
  if (seconds == null) return '--'
  if (seconds < 60) return `${seconds}秒`
  return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
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
        :class="[alert.level, { processing: alert.status === 'acknowledged', handled: alert.status === 'resolved' }]"
        @click="$emit('locate', alert.segment_id)"
      >
        <div class="alert-topline">
          <span class="level-badge">{{ levelLabel[alert.level] }}</span>
          <time>{{ formatTime(alert.created_at) }}</time>
        </div>
        <h3>{{ alert.title }}</h3>
        <p>{{ alert.message }}</p>
        <div v-if="alert.event_type !== 'system'" class="event-flow">
          <span class="done">发现</span><i></i>
          <span :class="{ done: alert.status !== 'new' }">响应</span><i></i>
          <span :class="{ done: alert.status === 'resolved' }">完成</span>
        </div>
        <div v-if="alert.status !== 'new' && alert.event_type !== 'system'" class="handling-record">
          <div><span>处置方式</span><b>{{ actionLabel[alert.handling_action] ?? '事件处置' }}</b></div>
          <div><span>负责单位</span><b>{{ alert.assigned_unit ?? '赛事指挥中心' }}</b></div>
          <div><span>响应时间</span><b>{{ formatDuration(alert.response_seconds) }}</b></div>
          <p>{{ alert.handling_note }}</p>
        </div>
        <div class="alert-footer">
          <span>{{ alert.segment_id }}<template v-if="alert.athlete_id"> · {{ alert.athlete_id }}</template></span>
          <span v-if="alert.status === 'acknowledged'" class="processing-label">处置中</span>
          <span v-else-if="alert.status === 'resolved'" class="handled-label">已完成 · {{ formatDuration(alert.resolution_seconds) }}</span>
        </div>
        <div v-if="alert.status === 'new'" class="alert-actions">
          <button v-if="alert.event_type !== 'system'" @click.stop="$emit('action', { alertId: alert.id, action: 'uav_review' })">无人机复核</button>
          <button v-if="alert.event_type === 'fall' || alert.event_type === 'vital'" class="primary medical" @click.stop="$emit('action', { alertId: alert.id, action: 'medical_dispatch' })">派遣医疗</button>
          <button v-else-if="alert.event_type === 'crowd'" class="primary" @click.stop="$emit('action', { alertId: alert.id, action: 'staff_dispatch' })">现场疏导</button>
          <button v-else class="primary" @click.stop="$emit('action', { alertId: alert.id, action: 'acknowledge' })">确认信息</button>
        </div>
        <div v-else-if="alert.status === 'acknowledged'" class="alert-actions">
          <button class="primary resolve" @click.stop="$emit('action', { alertId: alert.id, action: 'resolve' })">完成处置</button>
        </div>
      </article>
    </div>
  </section>
</template>
