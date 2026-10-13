<script setup>
import { computed } from 'vue'

const props = defineProps({
  snapshot: { type: Object, default: null },
  connectionStatus: { type: String, default: 'connecting' },
  dataMode: { type: String, default: 'simulation' },
  pipelineAvailable: { type: Boolean, default: false }
})
defineEmits(['open-review', 'open-analytics', 'open-help', 'open-data', 'export-results', 'change-data-mode', 'return-home'])

const statusLabel = computed(() => ({ online: '实时连接', offline: '连接中断', connecting: '正在连接' })[props.connectionStatus])

function formatElapsed(totalSeconds = 0) {
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, '0')
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0')
  const seconds = String(totalSeconds % 60).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}
</script>

<template>
  <header class="topbar">
    <div class="topbar-primary">
      <div class="brand">
        <div class="brand-mark">智</div>
        <div class="brand-copy">
          <h1>智跑慧巡</h1>
          <p>
            <strong class="active-race">{{ snapshot?.race?.name ?? '赛事载入中' }}</strong>
            <span> · 三维赛道 · 空地协同 · 分段任务自适应编排</span>
          </p>
        </div>
      </div>
      <div class="race-meta" v-if="snapshot">
        <div class="meta-item"><span>模拟赛时</span><strong>{{ formatElapsed(snapshot.race.elapsed_seconds) }}</strong></div>
        <div class="meta-item"><span>天气</span><strong>{{ snapshot.race.temperature_c }}℃ / {{ snapshot.race.humidity_percent }}%</strong></div>
        <div class="meta-item"><span>未完赛运动员</span><strong>{{ snapshot.stats.online_athletes }}</strong></div>
        <div class="meta-item"><span>活动无人机</span><strong>{{ snapshot.stats.active_drones }}</strong></div>
        <div class="connection-pill" :class="connectionStatus">
          <i></i>{{ statusLabel }}
        </div>
      </div>
    </div>
    <nav class="topbar-actions" aria-label="平台操作">
      <div class="topbar-actions-main">
        <button class="review-entry" @click="$emit('return-home')">返回首页</button>
        <div class="data-mode-switch" v-if="snapshot">
          <button :class="{ active: dataMode === 'simulation' }" @click="$emit('change-data-mode', 'simulation')">模拟推演</button>
          <button :class="{ active: dataMode === 'pipeline' }" @click="$emit('change-data-mode', 'pipeline')">
            <i :class="{ available: pipelineAvailable }"></i>接入数据
          </button>
        </div>
      </div>
      <div class="topbar-actions-secondary" v-if="snapshot">
        <button class="review-entry" @click="$emit('open-data')">数据管理</button>
        <button class="review-entry" @click="$emit('open-review')">赛事复盘</button>
        <button class="review-entry" @click="$emit('open-analytics')">统计图表</button>
        <button class="review-entry" @click="$emit('export-results')">导出成果</button>
        <button class="review-entry" @click="$emit('open-help')">帮助中心</button>
      </div>
    </nav>
  </header>
</template>
