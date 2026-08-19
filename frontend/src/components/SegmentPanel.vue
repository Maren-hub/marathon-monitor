<script setup>
defineProps({
  segments: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' }
})

defineEmits(['select'])

const focusClass = (focus) => `focus-${focus}`
const riskPercent = (value) => `${Math.round(value * 100)}%`
</script>

<template>
  <section class="panel segment-panel">
    <div class="panel-heading">
      <div>
        <span class="eyebrow">COURSE INTELLIGENCE</span>
        <h2>赛段监测任务</h2>
      </div>
      <span class="count-badge">{{ segments.length }} 段</span>
    </div>

    <div class="segment-list">
      <button
        v-for="segment in segments"
        :key="segment.id"
        class="segment-card"
        :class="[{ selected: selectedId === segment.id }, focusClass(segment.focus)]"
        @click="$emit('select', segment.id)"
      >
        <div class="segment-title-row">
          <span class="segment-index">{{ segment.id }}</span>
          <div>
            <strong>{{ segment.name }}</strong>
            <small>{{ segment.start_km }}–{{ segment.end_km }} km · {{ segment.athlete_count }} 人</small>
          </div>
          <span class="focus-tag">{{ segment.focus_label }}</span>
        </div>

        <div class="risk-row">
          <span>聚集</span>
          <div class="risk-track"><i class="crowd" :style="{ width: riskPercent(segment.crowd_risk) }"></i></div>
          <b>{{ riskPercent(segment.crowd_risk) }}</b>
        </div>
        <div class="risk-row">
          <span>健康</span>
          <div class="risk-track"><i class="health" :style="{ width: riskPercent(segment.health_risk) }"></i></div>
          <b>{{ riskPercent(segment.health_risk) }}</b>
        </div>

        <div class="task-chips">
          <span v-for="task in segment.monitoring_tasks" :key="task">{{ task }}</span>
        </div>
      </button>
    </div>
  </section>
</template>

