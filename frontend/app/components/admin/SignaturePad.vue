<script setup lang="ts">
import { onMounted, ref } from 'vue'

// Área de desenho da assinatura. Gera um PNG TRANSPARENTE (nunca pinta o fundo),
// mesmo formato que o upload → reaproveita o endpoint/validação do backend.
const W = 1200
const H = 400 // 3:1, mesma proporção recomendada pro upload

type Pt = { x: number; y: number }

const canvas = ref<HTMLCanvasElement | null>(null)
const dirty = ref(false)
let ctx: CanvasRenderingContext2D | null = null
let drawing = false
let lastPoint: Pt | null = null // último ponto cru
let lastMid: Pt | null = null // último ponto médio (junção contínua entre segmentos)

const setup = () => {
  const c = canvas.value
  if (!c) return
  ctx = c.getContext('2d')
  if (!ctx) return
  ctx.lineWidth = 5
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = '#1a1a1e'
  ctx.fillStyle = '#1a1a1e'
}
onMounted(setup)

// clientX/Y → coordenadas internas do canvas (independe do tamanho exibido)
const pos = (e: PointerEvent): Pt => {
  const c = canvas.value!
  const r = c.getBoundingClientRect()
  return { x: ((e.clientX - r.left) / r.width) * W, y: ((e.clientY - r.top) / r.height) * H }
}

const onDown = (e: PointerEvent) => {
  if (!ctx) return
  drawing = true
  const p = pos(e)
  lastPoint = p
  lastMid = p
  // pinga um ponto (cobre o clique simples, sem mover)
  ctx.beginPath()
  ctx.arc(p.x, p.y, ctx.lineWidth / 2, 0, Math.PI * 2)
  ctx.fill()
  dirty.value = true
  canvas.value?.setPointerCapture(e.pointerId)
}

const onMove = (e: PointerEvent) => {
  if (!drawing || !ctx || !lastPoint || !lastMid) return
  const p = pos(e)
  const mid = { x: (lastPoint.x + p.x) / 2, y: (lastPoint.y + p.y) / 2 }
  // liga o mid anterior ao novo mid usando o ponto cru como controle → curva contínua
  ctx.beginPath()
  ctx.moveTo(lastMid.x, lastMid.y)
  ctx.quadraticCurveTo(lastPoint.x, lastPoint.y, mid.x, mid.y)
  ctx.stroke()
  lastPoint = p
  lastMid = mid
  dirty.value = true
}

const onUp = () => {
  drawing = false
  lastPoint = null
  lastMid = null
}

const clear = () => {
  ctx?.clearRect(0, 0, W, H)
  dirty.value = false
}

const isEmpty = () => !dirty.value

const toBlob = (): Promise<Blob | null> =>
  new Promise((resolve) => {
    if (!canvas.value || !dirty.value) return resolve(null)
    canvas.value.toBlob((b) => resolve(b), 'image/png')
  })

defineExpose({ clear, isEmpty, toBlob })
</script>

<template>
  <div>
    <canvas
      ref="canvas"
      :width="W"
      :height="H"
      class="w-full max-w-[480px] rounded-lg border border-white/15 bg-white cursor-crosshair touch-none select-none"
      style="aspect-ratio: 3 / 1"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointerleave="onUp"
      @pointercancel="onUp"
    />
  </div>
</template>
