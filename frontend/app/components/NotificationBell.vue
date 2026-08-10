<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { AlertTriangle, Bell, CheckCheck, Info, Sparkles, Wrench, X } from 'lucide-vue-next'
import type { Announcement } from '~/composables/useAnnouncements'

const { list, unreadCount, markRead } = useAnnouncements()

const open = ref(false)
const items = ref<Announcement[]>([])
const unread = ref(0)
const selected = ref<Announcement | null>(null)
const zoomSrc = ref<string | null>(null)
const showAll = ref(false)
const menuRef = ref<HTMLElement | null>(null)

// ponytail: mostra 3, botão revela o resto que já veio (API traz até 20). Passar de 20 =
// paginação por offset no backend.
const visible = computed(() => (showAll.value ? items.value : items.value.slice(0, 3)))

// ponytail: busca no mount e ao abrir, sem realtime. Poll/websocket só se necessário.
const refreshCount = async () => {
  try { unread.value = (await unreadCount()).count } catch { /* silencioso */ }
}
const loadList = async () => {
  try { items.value = await list() } catch { /* silencioso */ }
}

const toggle = async () => {
  open.value = !open.value
  if (open.value) {
    showAll.value = false
    await loadList()
  }
}

const markAllRead = async () => {
  try {
    await markRead()
    unread.value = 0
  } catch { /* silencioso */ }
}

// Click num item = abre modal expandido pra leitura confortável (fecha o dropdown).
const expand = (a: Announcement) => {
  selected.value = a
  open.value = false
}

// ícone + cor por tipo (só visual)
const KIND: Record<string, { icon: any, color: string }> = {
  downtime: { icon: AlertTriangle, color: 'text-red-400' },
  change: { icon: Wrench, color: 'text-sky-400' },
  feature: { icon: Sparkles, color: 'text-emerald-400' },
  info: { icon: Info, color: 'text-neutral-400' },
}
const kindOf = (k: string) => KIND[k] || KIND.info
const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('pt-BR') : '')
// body é HTML rico → tira tags pro preview de 2 linhas na lista.
const stripHtml = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()

// Zoom: delega o click no body; se veio de uma <img>, abre em tela cheia (lightbox).
const onBodyClick = (e: MouseEvent) => {
  const el = e.target as HTMLElement
  if (el.tagName === 'IMG') zoomSrc.value = (el as HTMLImageElement).src
}

const onDocClick = (e: MouseEvent) => {
  if (open.value && menuRef.value && !menuRef.value.contains(e.target as Node)) open.value = false
}
const onKey = (e: KeyboardEvent) => {
  if (e.key !== 'Escape') return
  if (zoomSrc.value) zoomSrc.value = null
  else if (selected.value) selected.value = null
  else open.value = false
}
onMounted(() => {
  refreshCount()
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="menuRef" class="relative">
    <button
      type="button"
      aria-label="Novidades"
      class="relative inline-flex items-center justify-center w-9 h-9 rounded-full border border-white/10 hover:border-white/20 bg-white/5 hover:bg-white/10 text-neutral-300 hover:text-white transition-colors"
      :aria-expanded="open"
      @click="toggle"
    >
      <Bell class="w-4 h-4" />
      <span
        v-if="unread > 0"
        class="absolute -top-1 -right-1 min-w-4 h-4 px-1 inline-flex items-center justify-center rounded-full bg-orange-500 text-white text-[9px] font-bold"
      >{{ unread > 9 ? '9+' : unread }}</span>
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div
        v-if="open"
        class="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-white/10 bg-[#0a0a0a]/95 backdrop-blur-md shadow-xl shadow-black/40 overflow-hidden"
        @click.stop
      >
        <div class="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <p class="text-sm font-semibold text-white">Novidades</p>
          <button
            v-if="unread > 0"
            type="button"
            class="inline-flex items-center gap-1 text-[11px] text-orange-300 hover:text-orange-200"
            @click="markAllRead"
          >
            <CheckCheck class="w-3.5 h-3.5" /> Marcar como lidas
          </button>
        </div>

        <div class="max-h-[60vh] overflow-y-auto">
          <p v-if="!items.length" class="text-center text-xs text-neutral-500 py-8">
            Nenhum informativo por aqui.
          </p>
          <button
            v-for="a in visible"
            :key="a.id"
            type="button"
            class="w-full text-left flex gap-3 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors"
            @click="expand(a)"
          >
            <component :is="kindOf(a.kind).icon" class="w-4 h-4 mt-0.5 shrink-0" :class="kindOf(a.kind).color" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-white truncate">{{ a.title }}</p>
              <p class="text-xs text-neutral-400 mt-0.5 line-clamp-2 break-words">{{ stripHtml(a.body) }}</p>
              <p class="text-[10px] text-neutral-600 mt-1">{{ a.kind_label }} · {{ fmt(a.published_at) }}</p>
            </div>
            <img v-if="a.image_url" :src="a.image_url" alt="" class="w-11 h-11 rounded-md object-cover shrink-0">
          </button>

          <button
            v-if="!showAll && items.length > 3"
            type="button"
            class="w-full text-center text-[11px] font-medium text-orange-300 hover:text-orange-200 hover:bg-white/5 py-2.5 transition-colors"
            @click="showAll = true"
          >
            Carregar mais antigas ({{ items.length - 3 }})
          </button>
        </div>
      </div>
    </Transition>

    <!-- Modal expandido: leitura confortável -->
    <ClientOnly>
      <Teleport to="body">
        <Transition name="fade">
          <div
            v-if="selected"
            class="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            @click.self="selected = null"
          >
            <div class="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl border border-white/10 bg-[#0a0a0a] shadow-xl shadow-black/50">
              <div class="flex items-start gap-3 p-5 border-b border-white/5">
                <component :is="kindOf(selected.kind).icon" class="w-5 h-5 mt-0.5 shrink-0" :class="kindOf(selected.kind).color" />
                <div class="flex-1 min-w-0">
                  <h2 class="text-lg font-semibold text-white break-words">{{ selected.title }}</h2>
                  <p class="text-[11px] text-neutral-500 mt-0.5">{{ selected.kind_label }} · {{ fmt(selected.published_at) }}</p>
                </div>
                <button
                  type="button"
                  aria-label="Fechar"
                  class="p-1.5 rounded-full text-neutral-400 hover:text-white hover:bg-white/10 transition-colors shrink-0"
                  @click="selected = null"
                >
                  <X class="w-5 h-5" />
                </button>
              </div>
              <div class="p-5">
                <img
                  v-if="selected.image_url"
                  :src="selected.image_url"
                  alt=""
                  class="w-full rounded-lg mb-4 border border-white/10 cursor-zoom-in"
                  @click="zoomSrc = selected.image_url"
                >
                <!-- body é HTML rico do editor (imagens/vídeos inline). Conteúdo é criado só por staff. -->
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div class="ann-body prose prose-invert prose-sm max-w-none text-neutral-200 break-words" v-html="selected.body" @click="onBodyClick" />
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>
    </ClientOnly>

    <!-- Lightbox: imagem em tela cheia -->
    <ClientOnly>
      <Teleport to="body">
        <Transition name="fade">
          <div
            v-if="zoomSrc"
            class="fixed inset-0 z-[110] flex items-center justify-center bg-black/90 p-4 cursor-zoom-out"
            @click="zoomSrc = null"
          >
            <img :src="zoomSrc" alt="" class="max-w-full max-h-full rounded-lg object-contain">
          </div>
        </Transition>
      </Teleport>
    </ClientOnly>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
/* mídia inline do informativo cabe no modal */
.ann-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
  cursor: zoom-in;
}
.ann-body :deep([data-youtube-video]),
.ann-body :deep(iframe) {
  max-width: 100%;
}
.ann-body :deep([data-youtube-video]) iframe {
  width: 100%;
  aspect-ratio: 16 / 9;
  height: auto;
  border-radius: 0.5rem;
}
</style>
