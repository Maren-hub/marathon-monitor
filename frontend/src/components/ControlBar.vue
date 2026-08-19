<script setup>
defineProps({
  selectedSegment: { type: Object, default: null },
  running: { type: Boolean, default: true },
  busy: { type: Boolean, default: false }
})

defineEmits(['inject', 'control'])
</script>

<template>
  <div class="control-bar">
    <div class="selected-context">
      <span>当前操作赛段</span>
      <strong>{{ selectedSegment?.name ?? '请选择赛段' }}</strong>
      <small v-if="selectedSegment">{{ selectedSegment.focus_label }}</small>
    </div>
    <div class="control-group">
      <button :disabled="busy" class="event-button crowd" @click="$emit('inject', 'crowd')">模拟聚集</button>
      <button :disabled="busy" class="event-button fall" @click="$emit('inject', 'fall')">模拟跌倒</button>
      <button :disabled="busy" class="event-button vital" @click="$emit('inject', 'vital')">模拟体征异常</button>
    </div>
    <div class="control-group system">
      <button :disabled="busy" @click="$emit('control', running ? 'pause' : 'start')">{{ running ? '暂停推演' : '继续推演' }}</button>
      <button :disabled="busy" @click="$emit('control', 'reset')">重置</button>
    </div>
  </div>
</template>

