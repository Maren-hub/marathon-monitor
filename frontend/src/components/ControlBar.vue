<script setup>
const props = defineProps({
  selectedSegment: { type: Object, default: null },
  running: { type: Boolean, default: true },
  busy: { type: Boolean, default: false },
  demo: { type: Object, default: null }
})

defineEmits(['inject', 'control'])

function formatDemoTime(totalSeconds = 0) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0')
  const seconds = String(totalSeconds % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
}
</script>

<template>
  <div class="control-bar">
    <div v-if="demo?.enabled || demo?.completed || demo?.elapsed_seconds" class="selected-context demo-context">
      <div class="demo-title-row">
        <span>AUTO DEMO</span>
        <b>{{ formatDemoTime(demo.elapsed_seconds) }} / {{ formatDemoTime(demo.duration_seconds) }}</b>
      </div>
      <strong>{{ demo.current_title }}</strong>
      <div class="demo-progress"><i :style="{ width: `${demo.progress_percent}%` }"></i></div>
      <small v-if="demo.next_event_title">下一事件：{{ demo.next_event_title }} · {{ demo.next_event_in_seconds }}秒</small>
      <small v-else-if="demo.completed">演示已完成，可重新播放</small>
    </div>
    <div v-else class="selected-context">
      <span>当前操作赛段</span>
      <strong>{{ selectedSegment?.name ?? '请选择赛段' }}</strong>
      <small v-if="selectedSegment">{{ selectedSegment.focus_label }}</small>
    </div>
    <div class="control-group">
      <button :disabled="busy || demo?.enabled" class="event-button crowd" @click="$emit('inject', 'crowd')">模拟聚集</button>
      <button :disabled="busy || demo?.enabled" class="event-button fall" @click="$emit('inject', 'fall')">模拟跌倒</button>
      <button :disabled="busy || demo?.enabled" class="event-button vital" @click="$emit('inject', 'vital')">模拟体征异常</button>
    </div>
    <div class="control-group system">
      <button
        :disabled="busy || demo?.enabled"
        class="auto-demo-button"
        :class="{ active: demo?.enabled }"
        @click="$emit('control', 'auto_start')"
      >{{ demo?.completed ? '重新自动演示' : '开始自动演示' }}</button>
      <button :disabled="busy" @click="$emit('control', running ? 'pause' : 'start')">{{ running ? '暂停推演' : '继续推演' }}</button>
      <button :disabled="busy" @click="$emit('control', 'reset')">重置</button>
    </div>
  </div>
</template>
