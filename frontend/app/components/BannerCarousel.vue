<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import type { BannerItem } from '~/composables/useCatalog'

const props = defineProps<{ banners: BannerItem[] }>()

const current = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const stop = () => {
  if (timer) clearInterval(timer)
  timer = null
}
const start = () => {
  stop()
  if (props.banners.length > 1) timer = setInterval(next, 7000)
}

function go(i: number) {
  current.value = (i + props.banners.length) % props.banners.length
  start() // reinicia o relógio após navegação manual
}
const next = () => go(current.value + 1)
const prev = () => go(current.value - 1)

// banners podem mudar (refresh): mantém o índice válido
watch(() => props.banners.length, (len) => {
  if (current.value >= len) current.value = 0
  start()
})

onMounted(start)
onBeforeUnmount(stop)
</script>

<template>
  <div
    v-if="banners.length"
    class="relative aspect-[4/1]"
    @mouseenter="stop"
    @mouseleave="start"
  >
    <a
      v-for="(b, i) in banners"
      :key="b.id"
      :href="b.url"
      target="_blank"
      rel="noopener noreferrer"
      class="absolute inset-0 rounded-xl overflow-hidden border border-white/10 transition-opacity duration-500"
      :class="i === current ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'"
    >
      <img v-if="b.image" :src="b.image" :alt="b.title" class="w-full h-full object-cover">
    </a>

    <template v-if="banners.length > 1">
      <button
        type="button"
        aria-label="Anterior"
        class="absolute left-3 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-black/50 hover:bg-black/70 text-white backdrop-blur-sm transition-colors"
        @click.prevent="prev"
      >
        <ChevronLeft class="w-5 h-5" />
      </button>
      <button
        type="button"
        aria-label="Próximo"
        class="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-black/50 hover:bg-black/70 text-white backdrop-blur-sm transition-colors"
        @click.prevent="next"
      >
        <ChevronRight class="w-5 h-5" />
      </button>

      <div class="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
        <button
          v-for="(b, i) in banners"
          :key="b.id"
          type="button"
          :aria-label="`Banner ${i + 1}`"
          class="w-2 h-2 rounded-full transition-colors"
          :class="i === current ? 'bg-white' : 'bg-white/40 hover:bg-white/70'"
          @click="go(i)"
        />
      </div>
    </template>
  </div>
</template>
