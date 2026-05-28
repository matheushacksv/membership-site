<script setup lang="ts">
import { Check, Circle, PlayCircle } from 'lucide-vue-next'
import type { Lesson } from '~/composables/useCourse'

const props = defineProps<{
  lesson: Lesson
  courseId: number
  active: boolean
}>()

const fmtDuration = (s: number) => {
  if (!s) return ''
  const m = Math.floor(s / 60)
  const sec = s % 60
  return sec ? `${m}:${sec.toString().padStart(2, '0')}` : `${m} min`
}
</script>

<template>
  <NuxtLink
    :to="`/courses/${courseId}/lessons/${lesson.id}`"
    :class="[
      'flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors border-l-2',
      active
        ? 'bg-orange-500/10 text-orange-200 border-orange-500'
        : 'text-neutral-400 hover:bg-white/5 hover:text-white border-transparent',
    ]"
  >
    <Check v-if="lesson.completed" class="w-3.5 h-3.5 text-emerald-400 shrink-0" />
    <PlayCircle v-else-if="active" class="w-3.5 h-3.5 text-orange-300 shrink-0" />
    <Circle v-else class="w-3.5 h-3.5 text-neutral-600 shrink-0" />
    <span class="flex-1 truncate">{{ lesson.name }}</span>
    <span
      v-if="lesson.duration_seconds"
      class="text-[10px] text-neutral-600 shrink-0"
    >
      {{ fmtDuration(lesson.duration_seconds) }}
    </span>
  </NuxtLink>
</template>
