<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Paperclip, X } from 'lucide-vue-next'

// Abre o anexo num modal (sem <a href>: não expõe a URL do S3 como link clicável).
// ponytail: a URL ainda vai no src do img/iframe (visível no devtools). Esconder de vez =
// endpoint proxy no backend servindo o arquivo (liga com bucket privado, ver memory
// download-watermark-bypass). Só necessário se sigilo do anexo virar requisito.
const props = defineProps<{ url: string }>()
const open = ref(false)
const isPdf = computed(() => props.url.split('?')[0].toLowerCase().endsWith('.pdf'))

const onKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1 text-xs text-orange-300 hover:text-orange-200 mt-2"
    @click="open = true"
  >
    <Paperclip class="w-3.5 h-3.5" /> Ver anexo
  </button>

  <ClientOnly>
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="open"
          class="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          @click.self="open = false"
        >
          <button
            type="button"
            aria-label="Fechar"
            class="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            @click="open = false"
          >
            <X class="w-5 h-5" />
          </button>
          <iframe
            v-if="isPdf"
            :src="url"
            title="Anexo"
            class="w-full max-w-4xl h-[85vh] rounded-lg bg-white"
          />
          <img
            v-else
            :src="url"
            alt="Anexo"
            class="max-h-[85vh] max-w-full rounded-lg object-contain"
          >
        </div>
      </Transition>
    </Teleport>
  </ClientOnly>
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
</style>
