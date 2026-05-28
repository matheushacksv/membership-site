<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

definePageMeta({ layout: 'course' })

const route = useRoute()
const courseId = Number(route.params.id)
const { detail } = useCourse()

const error = ref<string | null>(null)

try {
  const course = await detail(courseId)
  const firstUnfinished = course.modules
    .flatMap((m) => m.lessons)
    .find((l) => !l.completed)
  const firstLesson = course.modules[0]?.lessons[0]
  const target = firstUnfinished || firstLesson

  if (target) {
    await navigateTo(`/courses/${courseId}/lessons/${target.id}`, { replace: true })
  } else {
    error.value = 'Curso sem aulas disponíveis.'
  }
} catch {
  error.value = 'Falha ao carregar curso.'
}
</script>

<template>
  <div class="flex items-center justify-center min-h-[60vh]">
    <p v-if="error" class="text-sm text-red-400">{{ error }}</p>
    <Loader2 v-else class="w-6 h-6 text-orange-500 animate-spin" />
  </div>
</template>
