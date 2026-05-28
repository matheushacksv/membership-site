<script setup lang="ts">
import { Download, Loader2, Paperclip } from 'lucide-vue-next'
import type { LessonAttachment } from '~/composables/useCourse'

defineProps<{ attachments: LessonAttachment[] }>()

const toast = useToast()
const downloading = ref<number | null>(null)

const fmtSize = (b: number) => {
  if (!b) return ''
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

const filenameFromUrl = (url: string, fallback: string) => {
  try {
    const path = new URL(url).pathname
    const last = path.split('/').pop() || ''
    return last || fallback
  } catch {
    return fallback
  }
}

const handleDownload = async (a: LessonAttachment) => {
  downloading.value = a.id
  try {
    const res = await fetch(a.file_url)
    if (!res.ok) throw new Error('fetch failed')
    const blob = await res.blob()
    const blobUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filenameFromUrl(a.file_url, a.title)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)
  } catch {
    toast.error('Falha ao baixar arquivo')
  } finally {
    downloading.value = null
  }
}
</script>

<template>
  <section v-if="attachments.length" class="space-y-2">
    <h3 class="text-xs font-bold uppercase tracking-wider text-neutral-500 flex items-center gap-1.5">
      <Paperclip class="w-3.5 h-3.5" />
      Materiais ({{ attachments.length }})
    </h3>
    <div class="grid sm:grid-cols-2 gap-2">
      <button
        v-for="a in attachments"
        :key="a.id"
        type="button"
        :disabled="downloading === a.id"
        class="flex items-center gap-3 px-4 py-3 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 rounded-lg group text-left disabled:opacity-60 disabled:cursor-progress"
        @click="handleDownload(a)"
      >
        <Loader2 v-if="downloading === a.id" class="w-4 h-4 text-orange-300 animate-spin shrink-0" />
        <Download v-else class="w-4 h-4 text-neutral-500 group-hover:text-orange-300 shrink-0" />
        <div class="flex-1 min-w-0">
          <p class="text-sm text-white truncate">{{ a.title }}</p>
          <p v-if="a.size_bytes" class="text-[10px] text-neutral-500">{{ fmtSize(a.size_bytes) }}</p>
        </div>
      </button>
    </div>
  </section>
</template>
