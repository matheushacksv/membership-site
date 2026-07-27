<script setup lang="ts">
import {
  GripVertical,
  Pencil,
  Trash2,
  Video,
  FileText,
  ListChecks,
  Eye,
  EyeOff,
} from 'lucide-vue-next'
import type { LessonItem as Lesson } from '~/composables/useAdmin'

defineProps<{ lesson: Lesson }>()
const emit = defineEmits<{ edit: []; remove: []; togglePublish: [] }>()
</script>

<template>
  <div
    class="group flex items-center gap-2 px-3 py-2 rounded-md bg-white/[0.02] border border-white/5 hover:border-white/10 hover:bg-white/5 transition-colors"
  >
    <GripVertical
      class="lesson-handle w-4 h-4 text-neutral-700 group-hover:text-neutral-400 cursor-grab shrink-0"
    />
    <component
      :is="lesson.kind === 'quiz' ? ListChecks : lesson.video_id ? Video : FileText"
      class="w-3.5 h-3.5 text-neutral-500 shrink-0"
    />
    <span class="flex-1 text-sm text-white truncate">{{ lesson.name }}</span>
    <button
      type="button"
      :title="lesson.is_published ? 'Despublicar' : 'Publicar'"
      class="opacity-0 group-hover:opacity-100 p-1 rounded text-neutral-500 hover:text-orange-300 transition-all"
      @click="emit('togglePublish')"
    >
      <component :is="lesson.is_published ? Eye : EyeOff" class="w-3.5 h-3.5" />
    </button>
    <button
      type="button"
      class="opacity-0 group-hover:opacity-100 p-1 rounded text-neutral-500 hover:text-white transition-all"
      @click="emit('edit')"
    >
      <Pencil class="w-3.5 h-3.5" />
    </button>
    <button
      type="button"
      class="opacity-0 group-hover:opacity-100 p-1 rounded text-neutral-500 hover:text-red-400 transition-all"
      @click="emit('remove')"
    >
      <Trash2 class="w-3.5 h-3.5" />
    </button>
  </div>
</template>
