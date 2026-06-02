<script setup lang="ts">
import { Check, Loader2, CircleCheck } from 'lucide-vue-next'
import type { Lesson } from '~/composables/useCourse'

const props = defineProps<{
  lesson: Lesson
  saving: boolean
}>()

const emit = defineEmits<{ toggleComplete: [] }>()
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-start gap-4 flex-wrap">
      <h1 class="text-2xl md:text-3xl font-medium tracking-tight text-white flex-1">
        {{ lesson.name }}
      </h1>
      <button
        type="button"
        :disabled="saving"
        :class="[
          'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors disabled:opacity-50',
          lesson.completed
            ? 'bg-emerald-500/10 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/20'
            : 'bg-orange-500 hover:bg-orange-400 text-white',
        ]"
        @click="emit('toggleComplete')"
      >
        <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
        <CircleCheck v-else-if="lesson.completed" class="w-3.5 h-3.5" />
        <Check v-else class="w-3.5 h-3.5" />
        {{ lesson.completed ? 'Concluída' : 'Marcar como concluída' }}
      </button>
    </div>

    <p v-if="lesson.description" class="text-sm text-neutral-400 leading-relaxed">
      {{ lesson.description }}
    </p>
  </div>
</template>
