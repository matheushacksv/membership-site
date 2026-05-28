<script setup lang="ts">
import { Upload, Loader2, ImagePlus } from 'lucide-vue-next'

const props = defineProps<{
  courseId: number
  currentUrl?: string | null
}>()

const emit = defineEmits<{ uploaded: [url: string] }>()

const admin = useAdmin()
const toast = useToast()
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const dragOver = ref(false)

const handleFile = async (file: File) => {
  if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
    toast.error('Use JPEG, PNG ou WebP')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    toast.error('Máximo 5MB')
    return
  }

  uploading.value = true
  try {
    const c = await admin.uploadCourseImage(props.courseId, file)
    emit('uploaded', c.image || '')
    toast.success('Imagem enviada')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha no upload')
  } finally {
    uploading.value = false
  }
}

const onDrop = (e: DragEvent) => {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

const onPick = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) handleFile(file)
}
</script>

<template>
  <div
    :class="[
      'relative aspect-video rounded-lg border-2 border-dashed overflow-hidden transition-colors cursor-pointer group',
      dragOver
        ? 'border-orange-500/60 bg-orange-500/5'
        : 'border-white/10 hover:border-white/20 bg-white/[0.02]',
    ]"
    @click="fileInput?.click()"
    @dragover.prevent="dragOver = true"
    @dragleave.prevent="dragOver = false"
    @drop.prevent="onDrop"
  >
    <img
      v-if="currentUrl"
      :src="currentUrl"
      class="absolute inset-0 w-full h-full object-cover"
    >
    <div
      :class="[
        'absolute inset-0 flex flex-col items-center justify-center gap-2 transition-opacity',
        currentUrl ? 'bg-black/60 opacity-0 group-hover:opacity-100' : 'opacity-100',
      ]"
    >
      <Loader2 v-if="uploading" class="w-6 h-6 text-orange-400 animate-spin" />
      <template v-else>
        <component :is="currentUrl ? Upload : ImagePlus" class="w-6 h-6 text-neutral-400" />
        <p class="text-xs text-neutral-400 text-center px-4">
          {{ currentUrl ? 'Trocar imagem' : 'Arraste ou clique pra enviar' }}
        </p>
        <p class="text-[10px] text-neutral-600">JPEG/PNG/WebP — máx 5MB</p>
      </template>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="hidden"
      @change="onPick"
    >
  </div>
</template>
