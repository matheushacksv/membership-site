<script setup lang="ts">
import { computed, resolveComponent } from 'vue'
import { ArrowRight, ExternalLink, PlayCircle } from 'lucide-vue-next'
import type { CourseListItem } from '~/composables/useCatalog'

const props = defineProps<{
  course: CourseListItem
  variant: 'enrolled' | 'available'
}>()

const NuxtLink = resolveComponent('NuxtLink')

const categoryLabel: Record<string, string> = {
  sales: 'Vendas',
  marketing: 'Marketing',
  strategy: 'Estratégia',
  tool: 'Ferramentas',
  customer: 'Customer Success',
  lifestyle: 'Estilo de Vida',
  development: 'Desenvolvimento',
}

const externalUrl = computed(() => props.course.sales_page || props.course.checkout_link || '#')
const isAvailable = computed(() => props.variant === 'available')

const total = computed(() => props.course.total_lessons ?? 0)
const completed = computed(() => props.course.completed_lessons ?? 0)
const percent = computed(() =>
  total.value ? Math.round((completed.value / total.value) * 100) : 0
)

const internalUrl = computed(() =>
  props.course.resume_lesson_id
    ? `/courses/${props.course.id}/lessons/${props.course.resume_lesson_id}`
    : `/courses/${props.course.id}`
)

const ctaLabel = computed(() => {
  if (isAvailable.value) return 'Saiba mais'
  return percent.value > 0 ? 'Retomar' : 'Começar'
})
</script>

<template>
  <component
    :is="isAvailable ? 'a' : NuxtLink"
    v-bind="
      isAvailable
        ? { href: externalUrl, target: '_blank', rel: 'noopener noreferrer' }
        : { to: internalUrl }
    "
    class="group relative block bg-white/5 border border-white/10 backdrop-blur-md rounded-xl overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:border-orange-500/30 hover:shadow-[0_0_40px_-10px_rgba(46,204,113,0.5)]"
    :style="{
      '--border-gradient': 'linear-gradient(180deg, rgba(255,255,255,0.1), rgba(255,255,255,0))',
      '--border-radius-before': '12px',
    }"
  >
    <!-- Image / Placeholder -->
    <div class="relative aspect-video overflow-hidden bg-gradient-to-br from-orange-500/20 via-neutral-900 to-neutral-950">
      <img
        v-if="course.image"
        :src="course.image"
        :alt="course.name"
        class="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
      >
      <div v-else class="absolute inset-0 flex items-center justify-center">
        <PlayCircle class="w-12 h-12 text-orange-500/40" />
      </div>

      <!-- Top gradient overlay -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/0 to-black/30 pointer-events-none" />

      <!-- Category badge -->
      <span
        class="absolute top-3 left-3 text-[10px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full bg-black/60 backdrop-blur-sm border border-white/10 text-orange-400"
      >
        {{ categoryLabel[course.category] || course.category }}
      </span>

      <!-- Variant badge -->
      <span
        v-if="isAvailable"
        class="absolute top-3 right-3 inline-flex items-center gap-1 text-[10px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full bg-orange-500/90 text-white"
      >
        Disponível
      </span>
    </div>

    <!-- Body -->
    <div class="p-5 flex flex-col gap-3">
      <h3 class="text-lg font-semibold tracking-tight text-white leading-snug line-clamp-2">
        {{ course.name }}
      </h3>

      <!-- Progress (só matriculados com aulas) -->
      <div v-if="!isAvailable && total > 0" class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-[11px] text-neutral-400">
          <span>{{ completed }}/{{ total }} aulas</span>
          <span class="font-semibold text-neutral-300">{{ percent }}%</span>
        </div>
        <div class="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
          <div
            class="h-full rounded-full bg-orange-500 transition-all duration-500"
            :style="{ width: `${percent}%` }"
          />
        </div>
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-white/5">
        <span class="text-xs font-medium tracking-wider uppercase text-neutral-500">
          {{ ctaLabel }}
        </span>
        <span
          class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 text-neutral-400 group-hover:bg-orange-500/20 group-hover:border-orange-500/40 group-hover:text-orange-300 transition-all"
        >
          <ExternalLink v-if="isAvailable" class="w-3.5 h-3.5" />
          <ArrowRight v-else class="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </div>
  </component>
</template>
