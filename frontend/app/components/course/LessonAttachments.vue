<script setup lang="ts">
import { Download, Loader2, Paperclip } from 'lucide-vue-next'
import type { LessonAttachment } from '~/composables/useCourse'

defineProps<{ attachments: LessonAttachment[] }>()

const toast = useToast()
const courseApi = useCourse()
const { data: me } = useMe()
const downloading = ref<number | null>(null)

// Carimbo forense visível (deterrente). Feito no browser: o backend só redireciona pro MinIO
// (rápido) e não relê o arquivo. IP não fica aqui (cliente não sabe o próprio IP público) mas o
// DownloadLog do backend já grava IP/email/hora. Marca é contornável pela URL pública, igual antes.
const signatureText = () => {
  const u = me.value
  const who = u?.name || u?.email || ''
  const when = new Date().toLocaleDateString('pt-BR')
  return `Baixado por ${who} · ${u?.email || ''} · ${when}`
}

// Carimba 1ª/meio/última página (custo baixo, marca no começo/meio/fim). Lança se o PDF for
// inválido → o caller degrada pro arquivo cru.
const stampPdf = async (buf: ArrayBuffer): Promise<Uint8Array> => {
  const { PDFDocument, StandardFonts, rgb } = await import('pdf-lib') // lazy: só carrega no 1º download
  const doc = await PDFDocument.load(buf)
  const font = await doc.embedFont(StandardFonts.Helvetica)
  const pages = doc.getPages()
  const n = pages.length
  const idx = [...new Set([0, Math.floor(n / 2), n - 1])]
  const text = signatureText()
  for (const i of idx) {
    pages[i].drawText(text, { x: 18, y: 10, size: 7, font, color: rgb(0.45, 0.45, 0.45) })
  }
  return doc.save()
}

const fmtSize = (b: number) => {
  if (!b) return ''
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

const handleDownload = async (a: LessonAttachment) => {
  downloading.value = a.id
  try {
    // Backend registra o DownloadLog (IP/email/hora) e redireciona pro MinIO; aqui pegamos os bytes.
    const blob = await courseApi.downloadAttachment(a.id)
    let out: Blob = blob
    const isPdf = blob.type === 'application/pdf' || a.title.toLowerCase().endsWith('.pdf')
    if (isPdf) {
      try {
        out = new Blob([await stampPdf(await blob.arrayBuffer())], { type: 'application/pdf' })
      }
      catch { /* PDF que a lib não abre: baixa o cru */ }
    }
    const blobUrl = URL.createObjectURL(out)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = a.title
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
