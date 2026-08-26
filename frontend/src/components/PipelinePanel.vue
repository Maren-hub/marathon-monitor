<script setup>
defineProps({
  results: { type: Array, default: () => [] },
  selectedSegmentId: { type: String, default: '' }
})

defineEmits(['select'])

const percent = (value) => value == null ? '—' : `${Math.round(value * 100)}%`
const timeLabel = (value) => value ? value.slice(11, 19) : '—'
</script>

<template>
  <section class="panel pipeline-result-panel">
    <div class="panel-heading">
      <div>
        <span class="eyebrow">AUTOMATIC PIPELINE</span>
        <h2>接入数据结果</h2>
      </div>
      <span class="live-mark"><i></i> AUTO</span>
    </div>

    <div v-if="results.length" class="pipeline-result-list">
      <button
        v-for="item in results"
        :key="`${item.window_start}-${item.segment_id}`"
        class="pipeline-result-card"
        :class="{ selected: selectedSegmentId === item.segment_id }"
        @click="$emit('select', item.segment_id)"
      >
        <div class="pipeline-result-title">
          <strong>{{ item.segment_id }} · {{ item.focus_label }}</strong>
          <span>{{ timeLabel(item.window_start) }}</span>
        </div>
        <div class="pipeline-risk-pair">
          <span>聚集 <b class="crowd-value">{{ percent(item.crowd_risk) }}</b></span>
          <span>健康 <b class="health-value">{{ percent(item.health_risk) }}</b></span>
          <span>置信度 <b>{{ percent(item.data_confidence) }}</b></span>
        </div>
        <div class="pipeline-units">
          <span v-for="unit in item.recommended_units" :key="unit">{{ unit }}</span>
        </div>
      </button>
    </div>

    <div v-else class="pipeline-empty">
      <strong>尚未收到完整数据</strong>
      <span>先运行批量发送脚本，系统会自动生成赛段风险与任务建议。</span>
    </div>
  </section>
</template>
