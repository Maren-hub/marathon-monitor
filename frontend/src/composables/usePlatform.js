import { onBeforeUnmount, onMounted, ref } from 'vue'
import { liveSocketUrl, platformApi } from '../services/api'

export function usePlatform() {
  const snapshot = ref(null)
  const connectionStatus = ref('connecting')
  const errorMessage = ref('')
  let socket = null
  let reconnectTimer = null
  let heartbeatTimer = null

  async function refresh() {
    try {
      snapshot.value = await platformApi.snapshot()
      errorMessage.value = ''
    } catch (error) {
      errorMessage.value = error.message
    }
  }

  function connect() {
    clearTimeout(reconnectTimer)
    connectionStatus.value = 'connecting'
    socket = new WebSocket(liveSocketUrl())
    socket.onopen = () => {
      connectionStatus.value = 'online'
      errorMessage.value = ''
      heartbeatTimer = window.setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) socket.send('ping')
      }, 15000)
    }
    socket.onmessage = (event) => {
      snapshot.value = JSON.parse(event.data)
    }
    socket.onerror = () => {
      errorMessage.value = '实时连接暂时不可用，正在重试。'
    }
    socket.onclose = () => {
      connectionStatus.value = 'offline'
      clearInterval(heartbeatTimer)
      reconnectTimer = window.setTimeout(connect, 2500)
    }
  }

  onMounted(async () => {
    await refresh()
    connect()
  })

  onBeforeUnmount(() => {
    clearTimeout(reconnectTimer)
    clearInterval(heartbeatTimer)
    if (socket) {
      socket.onclose = null
      socket.close()
    }
  })

  return { snapshot, connectionStatus, errorMessage, refresh }
}

