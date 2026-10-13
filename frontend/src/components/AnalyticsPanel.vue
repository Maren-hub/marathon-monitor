<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])
const props = defineProps({ snapshot: { type: Object, required: true }, analytics: { type: Object, default: null }, dataMode: { type: String, default: 'simulation' } })
defineEmits(['close'])
const chartNodes = ref([])
const charts = []

const colors = ['#f5b54b', '#ff6688', '#46d9ce', '#5db9ff']
const base = {
  backgroundColor: 'transparent',
  textStyle: { color: '#a9c3d0', fontFamily: 'Microsoft YaHei, sans-serif', fontSize: 11 },
  legend: { textStyle: { color: '#a9c3d0' }, top: 3 },
  tooltip: { trigger: 'axis', backgroundColor: '#0b2737', borderColor: '#2b6879', textStyle: { color: '#effcff' } },
  grid: { top: 45, left: 48, right: 18, bottom: 42 },
  xAxis: { axisLine: { lineStyle: { color: '#486b79' } }, axisLabel: { color: '#8aaebd' }, splitLine: { show: false } },
  yAxis: { axisLine: { show: false }, axisLabel: { color: '#8aaebd' }, splitLine: { lineStyle: { color: '#183847' } } } }

function options() {
  const segments = props.snapshot?.segments ?? []
  const alerts = props.analytics?.alerts ?? []
  const history = props.analytics?.health_history ?? []
  const drones = props.snapshot?.drones ?? []
  const timeBins = new Map()
  for (const alert of alerts) {
    const date = new Date(alert.created_at)
    if (Number.isNaN(date.getTime())) continue
    const key = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    if (!timeBins.has(key)) timeBins.set(key, { crowd: 0, fall: 0, vital: 0 })
    if (alert.event_type in timeBins.get(key)) timeBins.get(key)[alert.event_type]++
  }
  const times = Array.from(timeBins.keys()).slice(-12)
  if (!times.length) times.push('暂无事件')
  const taskCounts = segments.map((segment) => drones.filter((item) => item.target_segment_id === segment.id).length)
  return [
    {
      ...base, legend: { ...base.legend, data: ['聚集风险', '健康风险'] },
      xAxis: { ...base.xAxis, type: 'category', data: segments.map((item) => item.id) },
      yAxis: { ...base.yAxis, type: 'value', min: 0, max: 100, name: '%' },
      series: [
        { name: '聚集风险', type: 'bar', data: segments.map((item) => Math.round(item.crowd_risk * 100)), itemStyle: { color: colors[0], borderRadius: [4, 4, 0, 0] } },
        { name: '健康风险', type: 'bar', data: segments.map((item) => Math.round(item.health_risk * 100)), itemStyle: { color: colors[1], borderRadius: [4, 4, 0, 0] } }
      ]
    },
    {
      ...base, legend: { ...base.legend, data: ['聚集', '跌倒', '体征异常'] },
      xAxis: { ...base.xAxis, type: 'category', data: times },
      yAxis: { ...base.yAxis, type: 'value', minInterval: 1, name: '件' },
      series: [['crowd', '聚集', colors[0]], ['fall', '跌倒', colors[1]], ['vital', '体征异常', colors[2]]].map(([key, name, color]) => ({
        name, type: 'bar', stack: 'events', data: times.map((time) => timeBins.get(time)?.[key] ?? 0), itemStyle: { color }
      }))
    },
    {
      ...base, legend: { ...base.legend, data: ['平均心率 bpm', '平均疲劳度 %'] },
      xAxis: { ...base.xAxis, type: 'category', data: history.map((item) => `${Math.floor(item.elapsed_seconds / 60)}′`) },
      yAxis: [
        { ...base.yAxis, type: 'value', name: 'bpm', min: 0 },
        { ...base.yAxis, type: 'value', name: '%', min: 0, max: 100 }
      ],
      series: [
        { name: '平均心率 bpm', type: 'line', smooth: true, showSymbol: false, data: history.map((item) => item.heart_rate_bpm), lineStyle: { color: colors[1], width: 2 }, itemStyle: { color: colors[1] } },
        { name: '平均疲劳度 %', type: 'line', yAxisIndex: 1, smooth: true, showSymbol: false, data: history.map((item) => item.fatigue_percent), lineStyle: { color: colors[2], width: 2 }, itemStyle: { color: colors[2] } }
      ]
    },
    {
      ...base, legend: { show: false },
      xAxis: { ...base.xAxis, type: 'category', data: segments.map((item) => item.id) },
      yAxis: { ...base.yAxis, type: 'value', minInterval: 1, name: '架' },
      series: [{ name: '当前任务目标', type: 'bar', data: taskCounts, barMaxWidth: 35, itemStyle: { color: colors[3], borderRadius: [4, 4, 0, 0] } }]
    }
  ]
}

function updateCharts() {
  const configs = options()
  charts.forEach((chart, index) => chart?.setOption(configs[index], true))
}

function resizeCharts() { charts.forEach((chart) => chart?.resize()) }
onMounted(async () => {
  await nextTick()
  chartNodes.value.forEach((node, index) => { if (node) charts[index] = echarts.init(node) })
  updateCharts()
  window.addEventListener('resize', resizeCharts)
})
watch(() => [props.snapshot, props.analytics, props.dataMode], updateCharts, { deep: true })
onBeforeUnmount(() => { window.removeEventListener('resize', resizeCharts); charts.forEach((chart) => chart?.dispose()) })
</script>

<template>
  <div class="analytics-overlay" @click.self="$emit('close')">
    <section class="analytics-sheet" role="dialog" aria-modal="true" aria-label="赛事统计图表">
      <header><div><small>RACE ANALYTICS</small><h2>赛事统计图表</h2><p>当前赛段风险与任务实时刷新；事件和健康曲线来自本次模拟运行记录。</p></div><button type="button" @click="$emit('close')">关闭 ×</button></header>
      <div class="analytics-grid">
        <article><h3>赛段风险分布</h3><p>{{ dataMode === 'pipeline' ? '有可用接入结果的赛段采用管道风险，其他赛段为模拟值。' : '聚集和健康风险均为 0–1 原型规则值。' }}</p><div :ref="(node) => chartNodes[0] = node" class="chart-box"></div></article>
        <article><h3>事件类型 / 发生时段</h3><p>按报警创建的实际时钟分钟归类；不包括系统提示。</p><div :ref="(node) => chartNodes[1] = node" class="chart-box"></div></article>
        <article><h3>运动员健康趋势</h3><p>模拟运动员平均心率和疲劳度，横轴为模拟赛时；最多保留最近 360 个采样点。</p><div :ref="(node) => chartNodes[2] = node" class="chart-box"></div></article>
        <article><h3>无人机任务分布</h3><p>当前各赛段被指向的无人机数；累计调度 {{ analytics?.drone_dispatches ?? 0 }} 次。不是实测航拍覆盖面积。</p><div :ref="(node) => chartNodes[3] = node" class="chart-box"></div></article>
      </div>
      <footer>数据边界：当前赛事为模拟推演；校园三维模型与逻辑赛道风险尚未完成空间配准。</footer>
    </section>
  </div>
</template>

<style scoped>
.analytics-overlay { position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center; padding: 20px; background: rgba(2, 11, 19, .88); }
.analytics-sheet { width: min(1120px, 98vw); max-height: 95vh; overflow: auto; padding: 25px; border: 1px solid #29546a; border-radius: 18px; background: #081b2a; box-shadow: 0 20px 80px #000a; }
header { display: flex; justify-content: space-between; align-items: start; gap: 20px; } header small { color: #4fdacb; letter-spacing: .2em; } h2 { margin: 5px 0; font-size: 27px; } header p, article p, footer { color: #90acba; font-size: 12px; line-height: 1.6; } button { padding: 9px 15px; border: 1px solid #39718a; border-radius: 8px; color: #d7f8fa; background: #0e3041; cursor: pointer; }
.analytics-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 20px; } article { min-width: 0; padding: 15px; border: 1px solid #204255; border-radius: 12px; background: #0c2635; } article h3 { margin: 0; font-size: 15px; } article p { min-height: 37px; margin: 7px 0 0; } .chart-box { width: 100%; height: 230px; } footer { margin-top: 15px; }
@media (max-width: 750px) { .analytics-grid { grid-template-columns: 1fr; } .analytics-sheet { padding: 14px; } }
</style>
