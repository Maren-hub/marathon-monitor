<script setup>
import { computed } from 'vue'

const props = defineProps({ snapshot: { type: Object, required: true } })
defineEmits(['close'])

const review = computed(() => props.snapshot.review)
const highestRiskSegment = computed(() => review.value?.segments.find((item) => item.id === review.value.highest_risk_segment_id))
const busiestSegment = computed(() => review.value?.segments.find((item) => item.id === review.value.busiest_segment_id))

const eventItems = computed(() => [
  { key: 'crowd', label: '人员聚集', value: review.value?.event_counts.crowd ?? 0, className: 'crowd' },
  { key: 'fall', label: '人员跌倒', value: review.value?.event_counts.fall ?? 0, className: 'fall' },
  { key: 'vital', label: '体征异常', value: review.value?.event_counts.vital ?? 0, className: 'vital' }
])

function formatDuration(seconds) {
  if (seconds == null) return '暂无数据'
  if (seconds < 60) return `${seconds} 秒`
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

function formatRaceTime(totalSeconds = 0) {
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, '0')
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0')
  const seconds = String(totalSeconds % 60).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

function printReport() {
  window.print()
}
</script>

<template>
  <div class="review-overlay">
    <section class="review-sheet">
      <header class="review-header">
        <div>
          <span>RACE INTELLIGENCE REVIEW</span>
          <h2>{{ snapshot.race.name }} · 智能监测复盘</h2>
          <p>模拟赛时 {{ formatRaceTime(snapshot.race.elapsed_seconds) }} · 报告生成于 {{ new Date(snapshot.generated_at).toLocaleString('zh-CN') }}</p>
        </div>
        <div class="review-actions">
          <button @click="printReport">打印 / 保存PDF</button>
          <button class="close" @click="$emit('close')">关闭</button>
        </div>
      </header>

      <div class="report-notice">本报告由原型系统根据模拟赛事、模拟穿戴设备和模拟无人机数据自动生成，仅用于方案验证。</div>

      <div class="review-kpis">
        <article><span>监测事件</span><strong>{{ review.total_events }}</strong><small>件</small></article>
        <article><span>完成处置</span><strong>{{ review.resolved_events }}</strong><small>完成率 {{ review.completion_rate_percent }}%</small></article>
        <article><span>平均响应</span><strong>{{ review.average_response_seconds ?? '--' }}</strong><small>秒</small></article>
        <article><span>无人机调度</span><strong>{{ review.drone_dispatches }}</strong><small>次</small></article>
      </div>

      <div class="review-main-grid">
        <section class="review-block event-summary">
          <div class="review-block-title"><span>01</span><h3>事件构成</h3></div>
          <div class="event-summary-list">
            <div v-for="item in eventItems" :key="item.key" :class="item.className">
              <span>{{ item.label }}</span><strong>{{ item.value }}</strong><i :style="{ width: `${review.total_events ? item.value / review.total_events * 100 : 0}%` }"></i>
            </div>
          </div>
          <div class="response-summary">
            <span>平均完整处置时间</span>
            <strong>{{ formatDuration(review.average_resolution_seconds) }}</strong>
          </div>
        </section>

        <section class="review-block insight-summary">
          <div class="review-block-title"><span>02</span><h3>系统结论</h3></div>
          <div class="insight-card critical"><span>历史最高风险赛段</span><strong>{{ highestRiskSegment?.name ?? '--' }}</strong><b>{{ highestRiskSegment?.peak_risk_percent ?? 0 }}%</b></div>
          <div class="insight-card"><span>历史人员峰值赛段</span><strong>{{ busiestSegment?.name ?? '--' }}</strong><b>{{ busiestSegment?.peak_athletes ?? 0 }} 人</b></div>
          <p>系统依据赛段位置、实时人员密度与个体安全状态动态调整监测权重，并联动无人机与现场保障力量完成处置。</p>
        </section>
      </div>

      <section class="review-block segment-review">
        <div class="review-block-title"><span>03</span><h3>分赛段监测表现</h3></div>
        <div class="segment-review-head"><span>赛段</span><span>峰值人数</span><span>最高风险</span><span>事件数量</span><span>风险态势</span></div>
        <div v-for="segment in review.segments" :key="segment.id" class="segment-review-row">
          <strong>{{ segment.id }} · {{ segment.name }}</strong>
          <span>{{ segment.peak_athletes }} 人</span>
          <span>{{ segment.peak_risk_percent }}%</span>
          <span>{{ segment.event_count }} 件</span>
          <div><i :class="{ warning: segment.peak_risk_percent >= 55, critical: segment.peak_risk_percent >= 75 }" :style="{ width: `${segment.peak_risk_percent}%` }"></i></div>
        </div>
      </section>

      <footer class="review-footer">
        <span>马拉松智能监控平台 · 数字孪生原型</span>
        <b>分段任务自适应编排 · 空地协同 · 处置闭环</b>
      </footer>
    </section>
  </div>
</template>
