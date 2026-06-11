<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
import type { Module } from '~/composables/useCourse'

const props = defineProps<{
  module: Module
  courseId: number
  activeLessonId: number
}>()

const containsActive = computed(() =>
  props.module.lessons.some((l) => l.id === props.activeLessonId)
)
const expanded = ref(containsActive.value)

watch(containsActive, (v) => { if (v) expanded.value = true })

const completedCount = computed(() =>
  props.module.lessons.filter((l) => l.completed).length
)
</script>

<template>
  <div class="border-b border-white/5 last:border-b-0">
    <button
      type="button"
      class="w-full flex items-start gap-2 px-3 py-2.5 text-left hover:bg-white/[0.03]"
      @click="expanded = !expanded"
    >
      <ChevronDown
        class="w-4 h-4 mt-0.5 text-neutral-500 shrink-0 transition-transform"
        :class="{ '-rotate-90': !expanded }"
      />
      <span class="flex-1 text-sm font-medium text-white break-words" :title="module.name">
        {{ module.name }}
      </span>
      <span class="text-[10px] text-neutral-500 shrink-0 mt-0.5">
        {{ completedCount }}/{{ module.lessons.length }}
      </span>
    </button>

    <div v-if="expanded" class="pb-2 pl-2 pr-2 space-y-0.5">
      <CourseLessonNavItem
        v-for="lesson in module.lessons"
        :key="lesson.id"
        :lesson="lesson"
        :course-id="courseId"
        :active="lesson.id === activeLessonId"
      />
    </div>
  </div>
</template>
