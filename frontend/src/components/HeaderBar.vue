<script setup>
import { computed } from 'vue'

const props = defineProps({
  snapshot: { type: Object, default: null },
  connectionStatus: { type: String, default: 'connecting' }
})
defineEmits(['open-review'])

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
    <div class="brand">
      <div class="brand-mark">M</div>
      <div>
        <h1>马拉松智能监控平台</h1>
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
      <button class="review-entry" @click="$emit('open-review')">赛事复盘</button>
      <div class="connection-pill" :class="connectionStatus">
        <i></i>{{ statusLabel }}
      </div>
    </div>
  </header>
</template>
