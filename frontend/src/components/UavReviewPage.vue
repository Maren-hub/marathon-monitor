<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ alert: { type: Object, default: null } })
defineEmits(['return-dashboard'])

const files = [
  { name: 'main.py', label: '程序入口', description: '读取视频，逐帧调用识别，再用 OpenCV 弹窗显示。' },
  { name: 'api.py', label: '处理入口', description: '把视频帧交给姿态识别模块。' },
  { name: 'yolo_pose.py', label: '姿态与跌倒判断', description: '使用 YOLO 姿态关键点与规则判断疑似摔倒。' },
  { name: 'yolo_detector.py', label: '人员检测', description: '单帧目标检测封装。' },
  { name: 'yolo_tracker.py', label: '人员跟踪', description: '调用 YOLO 跟踪接口。' },
  { name: 'config.py', label: '参数配置', description: '视频路径、置信度、姿态判断阈值等。' },
  { name: 'utils.py', label: '辅助方法', description: '截图保存、输出视频写入工具。' }
]
const selectedFile = ref(files[0].name)
const sourceText = ref('正在读取代码…')

watch(selectedFile, async (filename) => {
  sourceText.value = '正在读取代码…'
  try {
    const response = await fetch(`/uav-review/marathon_detect/${filename}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    sourceText.value = await response.text()
  } catch {
    sourceText.value = '代码文件暂时无法读取。请确认前端服务已经启动，并刷新页面。'
  }
}, { immediate: true })
</script>

<template>
  <div class="uav-review-page">
    <header class="uav-review-header">
      <div>
        <span class="uav-review-kicker">UAV REVIEW / 无人机复核资料</span>
        <h1>无人机动态监测</h1>
        <p>查看团队提供的 YOLO 研究代码与示例素材，了解从视频帧到疑似跌倒提示的处理流程。</p>
      </div>
      <button type="button" @click="$emit('return-dashboard')">← 返回监控平台</button>
    </header>

    <main class="uav-review-main">
      <section v-if="alert" class="uav-review-context">
        <span>当前复核事件</span>
        <strong>{{ alert.title }}</strong>
        <span>{{ alert.segment_id }} · {{ alert.athlete_id || '未关联运动员' }}</span>
        <small>平台已记录“无人机复核”处置动作；下方视频是独立示例素材，并非该事件的实时画面。</small>
      </section>

      <div class="uav-review-grid">
        <section class="uav-review-card uav-review-video">
          <div class="uav-review-card-heading"><span>01 / 示例素材</span><h2>无人机视频预览</h2></div>
          <video controls muted playsinline preload="metadata" src="/uav-review/marathon_detect/videos/drone3.mp4">
            当前浏览器不支持视频播放。
          </video>
          <p>团队提供的无人机动态监测演示视频。该素材用于展示视频监测效果，并非当前报警事件的实时画面。</p>
        </section>

        <section class="uav-review-card uav-review-method">
          <div class="uav-review-card-heading"><span>02 / 代码逻辑</span><h2>这套代码做什么</h2></div>
          <ol>
            <li><b>读入视频</b><span><code>main.py</code> 用 OpenCV 逐帧读取。</span></li>
            <li><b>提取姿态</b><span><code>yolo_pose.py</code> 调用 YOLO 姿态模型定位人体关键点。</span></li>
            <li><b>判断异常</b><span>结合人体框比例和肩髋位置，给疑似跌倒者画框。</span></li>
            <li><b>本地显示</b><span>结果通过电脑上的 OpenCV 窗口显示，而非网页视频流。</span></li>
          </ol>
          <div class="uav-review-notice"><b>目前的接入边界</b><span>平台按钮已连接到此资料页，但尚未调用 YOLO 实时推理；下方源码也是研究原版，运行需要额外安装 OpenCV、Ultralytics 等依赖，并提供原压缩包中的模型权重。</span></div>
        </section>
      </div>

      <section class="uav-review-card uav-review-code">
        <div class="uav-review-card-heading"><span>03 / 源代码</span><h2>查看压缩包中的 Python 文件</h2></div>
        <div class="uav-review-code-layout">
          <nav aria-label="源代码文件">
            <button v-for="file in files" :key="file.name" type="button" :class="{ active: selectedFile === file.name }" @click="selectedFile = file.name">
              <strong>{{ file.name }}</strong><small>{{ file.label }}</small>
            </button>
          </nav>
          <div class="uav-review-source">
            <div class="uav-review-source-head"><span>{{ selectedFile }} · {{ files.find((item) => item.name === selectedFile)?.description }}</span><a :href="`/uav-review/marathon_detect/${selectedFile}`" :download="selectedFile">下载此文件 ↓</a></div>
            <pre><code>{{ sourceText }}</code></pre>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
