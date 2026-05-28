<script setup lang="ts">
import { ArrowLeft, ArrowRight } from 'lucide-vue-next'
import type { Lesson } from '~/composables/useCourse'

defineProps<{
  courseId: number
  prev: Lesson | null
  next: Lesson | null
}>()
</script>

<template>
  <div class="flex items-center justify-between gap-3 pt-4 border-t border-white/5">
    <NuxtLink
      v-if="prev"
      :to="`/courses/${courseId}/lessons/${prev.id}`"
      class="flex-1 inline-flex items-center gap-2 px-4 py-3 bg-white/[0.02] hover:bg-white/5 border border-white/5 rounded-lg text-sm text-neutral-300"
    >
      <ArrowLeft class="w-4 h-4 shrink-0" />
      <div class="min-w-0 text-left">
        <p class="text-[10px] uppercase tracking-wider text-neutral-500">Anterior</p>
        <p class="truncate">{{ prev.name }}</p>
      </div>
    </NuxtLink>
    <div v-else class="flex-1" />

    <NuxtLink
      v-if="next"
      :to="`/courses/${courseId}/lessons/${next.id}`"
      class="flex-1 inline-flex items-center gap-2 px-4 py-3 bg-white/[0.02] hover:bg-white/5 border border-white/5 rounded-lg text-sm text-neutral-300 justify-end text-right"
    >
      <div class="min-w-0">
        <p class="text-[10px] uppercase tracking-wider text-neutral-500">Próxima</p>
        <p class="truncate">{{ next.name }}</p>
      </div>
      <ArrowRight class="w-4 h-4 shrink-0" />
    </NuxtLink>
    <div v-else class="flex-1" />
  </div>
</template>
