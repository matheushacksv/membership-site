<script setup lang="ts">
import { Video } from 'lucide-vue-next'

const props = defineProps<{
  provider: string | null
  videoId: string | null
}>()

const emit = defineEmits<{
  progress: [seconds: number, duration: number]
  ended: []
}>()

const extractId = (provider: string, raw: string): string | null => {
  const v = raw.trim()
  if (!v) return null

  if (provider === 'youtube') {
    // youtu.be/ID, youtube.com/watch?v=ID, youtube.com/embed/ID, youtube.com/shorts/ID
    const patterns = [
      /youtu\.be\/([\w-]{6,})/,
      /[?&]v=([\w-]{6,})/,
      /\/embed\/([\w-]{6,})/,
      /\/shorts\/([\w-]{6,})/,
    ]
    for (const re of patterns) {
      const m = v.match(re)
      if (m) return m[1]!
    }
    // bare ID
    if (/^[\w-]{6,}$/.test(v)) return v
    return null
  }

  if (provider === 'vimeo') {
    // vimeo.com/ID or player.vimeo.com/video/ID
    const m = v.match(/vimeo\.com\/(?:video\/)?(\d+)/)
    if (m) return m[1]!
    if (/^\d+$/.test(v)) return v
    return null
  }

  if (provider === 'panda') {
    // pandavideo player URL: ...?v=ID  OR  /embed/?v=ID
    const m = v.match(/[?&]v=([\w-]+)/)
    if (m) return m[1]!
    // sometimes Panda IDs come as UUID
    if (/^[\w-]+$/.test(v)) return v
    return null
  }

  return null
}

const embedUrl = computed(() => {
  if (!props.provider || !props.videoId) return null
  const raw = props.videoId.trim()

  // Panda: subdomain varies per tenant — use full URL if provided
  if (props.provider === 'panda') {
    if (/^https?:\/\//.test(raw)) return raw
    return null
  }

  if (props.provider === 'youtube') {
    // youtube.com/embed already → use direct
    if (/youtube\.com\/embed\//.test(raw))
      return raw.includes('enablejsapi') ? raw : `${raw}${raw.includes('?') ? '&' : '?'}enablejsapi=1&rel=0`
    const id = extractId('youtube', raw)
    return id ? `https://www.youtube.com/embed/${id}?enablejsapi=1&rel=0` : null
  }

  if (props.provider === 'vimeo') {
    if (/player\.vimeo\.com\/video\//.test(raw)) return raw
    const id = extractId('vimeo', raw)
    return id ? `https://player.vimeo.com/video/${id}` : null
  }

  return null
})

const iframeRef = ref<HTMLIFrameElement | null>(null)
let ytPlayer: any = null
let pollTimer: ReturnType<typeof setInterval> | null = null

const loadYouTubeApi = (): Promise<any> => {
  return new Promise((resolve) => {
    if ((window as any).YT && (window as any).YT.Player) {
      resolve((window as any).YT)
      return
    }
    const existing = document.getElementById('yt-iframe-api')
    if (!existing) {
      const s = document.createElement('script')
      s.id = 'yt-iframe-api'
      s.src = 'https://www.youtube.com/iframe_api'
      document.head.appendChild(s)
    }
    ;(window as any).onYouTubeIframeAPIReady = () => resolve((window as any).YT)
  })
}

const initYouTube = async () => {
  if (props.provider !== 'youtube' || !iframeRef.value) return
  const YT = await loadYouTubeApi()
  ytPlayer = new YT.Player(iframeRef.value, {
    events: {
      onStateChange: (e: any) => {
        if (e.data === YT.PlayerState.ENDED) emit('ended')
      },
    },
  })
  pollTimer = setInterval(() => {
    if (!ytPlayer?.getCurrentTime) return
    try {
      const seconds = ytPlayer.getCurrentTime() || 0
      const duration = ytPlayer.getDuration() || 0
      if (duration > 0) emit('progress', seconds, duration)
    } catch { /* not ready */ }
  }, 5000)
}

onMounted(() => {
  if (props.provider === 'youtube') initYouTube()
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (ytPlayer?.destroy) try { ytPlayer.destroy() } catch { /* noop */ }
})

watch(() => props.videoId, () => {
  if (pollTimer) clearInterval(pollTimer)
  if (ytPlayer?.destroy) try { ytPlayer.destroy() } catch { /* noop */ }
  ytPlayer = null
  nextTick(() => {
    if (props.provider === 'youtube') initYouTube()
  })
})
</script>

<template>
  <div
    v-if="embedUrl"
    class="relative w-full aspect-video bg-black rounded-xl overflow-hidden border border-white/5"
  >
    <iframe
      ref="iframeRef"
      :src="embedUrl"
      class="absolute inset-0 w-full h-full"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
    />
  </div>

  <div
    v-else
    class="w-full aspect-video bg-white/[0.02] border border-dashed border-white/10 rounded-xl flex flex-col items-center justify-center text-neutral-600"
  >
    <Video class="w-10 h-10 mb-2" />
    <p class="text-xs">Aula sem vídeo</p>
  </div>
</template>
