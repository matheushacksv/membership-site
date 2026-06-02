<script setup lang="ts">
import { ListVideo, AlertCircle, RefreshCw } from 'lucide-vue-next'
import type { CourseDetail, Lesson } from '~/composables/useCourse'

definePageMeta({ layout: 'course' })

const route = useRoute()
const courseId = computed(() => Number(route.params.id))
const lessonId = computed(() => Number(route.params.lessonId))

const courseApi = useCourse()
const toast = useToast()

const { data: course, error, refresh } = await useAsyncData<CourseDetail>(
  `course-${courseId.value}`,
  () => courseApi.detail(courseId.value),
  { watch: [courseId] }
)

const allLessons = computed<Lesson[]>(() =>
  course.value?.modules.flatMap((m) => m.lessons) || []
)

const currentLesson = computed<Lesson | null>(() => {
  return allLessons.value.find((l) => l.id === lessonId.value) || null
})

const prevLesson = computed<Lesson | null>(() => {
  const idx = allLessons.value.findIndex((l) => l.id === lessonId.value)
  return idx > 0 ? allLessons.value[idx - 1]! : null
})

const nextLesson = computed<Lesson | null>(() => {
  const idx = allLessons.value.findIndex((l) => l.id === lessonId.value)
  return idx >= 0 && idx < allLessons.value.length - 1
    ? allLessons.value[idx + 1]!
    : null
})

// Preconnect ao host de vídeo da próxima aula → iframe abre mais rápido ao avançar.
const preconnectLinks = computed(() => {
  const next = nextLesson.value
  if (!next?.video_provider) return []
  const origins: string[] = []
  if (next.video_provider === 'youtube') {
    origins.push('https://www.youtube.com', 'https://i.ytimg.com')
  } else if (next.video_provider === 'vimeo') {
    origins.push('https://player.vimeo.com')
  } else if (next.video_provider === 'panda' && next.video_id) {
    try {
      origins.push(new URL(next.video_id.trim()).origin)
    } catch { /* video_id não é URL completa */ }
  }
  return origins.map((href) => ({ rel: 'preconnect' as const, href, crossorigin: '' as const }))
})

useHead(() => ({
  title: currentLesson.value
    ? `${currentLesson.value.name} — ${course.value?.name || 'Curso'}`
    : 'Curso',
  link: preconnectLinks.value,
}))

const saving = ref(false)
const lastSentSeconds = ref(0)
const autoCompleted = ref(false)
const sidebarOpen = ref(false)

watch(lessonId, () => {
  lastSentSeconds.value = 0
  autoCompleted.value = false
  sidebarOpen.value = false
})

const patchLocalCompleted = (id: number, value = true) => {
  if (!course.value) return
  // Reatribui o objeto inteiro (imutável) → garante reatividade nos computeds
  // que derivam progresso (CourseSidebar, ModuleAccordion), não só na aula atual.
  course.value = {
    ...course.value,
    modules: course.value.modules.map((m) => ({
      ...m,
      lessons: m.lessons.map((l) =>
        l.id === id ? { ...l, completed: value } : l
      ),
    })),
  }
}

const onProgress = async (seconds: number, duration: number) => {
  if (!currentLesson.value) return

  // throttle: only fire each ~15s of new watch
  if (seconds - lastSentSeconds.value >= 15) {
    lastSentSeconds.value = seconds
    try {
      await courseApi.markProgress(currentLesson.value.id, Math.floor(seconds), false)
    } catch { /* silent */ }
  }

  // auto-complete near end
  if (
    !autoCompleted.value &&
    !currentLesson.value.completed &&
    duration > 0 &&
    seconds / duration > 0.95
  ) {
    autoCompleted.value = true
    try {
      await courseApi.markProgress(currentLesson.value.id, Math.floor(seconds), true)
      patchLocalCompleted(currentLesson.value.id)
      refreshNuxtData('home-mine')
    } catch { /* silent */ }
  }
}

const onEnded = async () => {
  if (!currentLesson.value || currentLesson.value.completed) return
  try {
    await courseApi.markProgress(
      currentLesson.value.id,
      currentLesson.value.duration_seconds || 0,
      true
    )
    patchLocalCompleted(currentLesson.value.id)
    refreshNuxtData('home-mine')
  } catch { /* silent */ }
}

const toggleComplete = async () => {
  if (!currentLesson.value) return
  const target = !currentLesson.value.completed
  saving.value = true
  try {
    await courseApi.markProgress(
      currentLesson.value.id,
      currentLesson.value.duration_seconds || 0,
      target
    )
    patchLocalCompleted(currentLesson.value.id, target)
    refreshNuxtData('home-mine')
    toast.success(target ? 'Aula concluída' : 'Marcada como não concluída')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao atualizar conclusão')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="course && currentLesson" class="flex">
    <CourseSidebar
      :course="course"
      :active-lesson-id="currentLesson.id"
      :open="sidebarOpen"
      @close="sidebarOpen = false"
    />

    <div class="flex-1 min-w-0 px-4 sm:px-6 md:px-10 py-4 md:py-8 max-w-5xl mx-auto space-y-5 md:space-y-6 w-full">
      <button
        type="button"
        class="lg:hidden inline-flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-300 self-start"
        @click="sidebarOpen = true"
      >
        <ListVideo class="w-3.5 h-3.5" />
        Aulas
      </button>

      <CourseVideoPlayer
        :provider="currentLesson.video_provider"
        :video-id="currentLesson.video_id"
        @progress="onProgress"
        @ended="onEnded"
      />

      <CourseLessonHeader
        :lesson="currentLesson"
        :saving="saving"
        @toggle-complete="toggleComplete"
      />

      <CourseLessonContent :content="currentLesson.content" />

      <CourseLessonAttachments :attachments="currentLesson.attachments" />

      <CourseLessonNav
        :course-id="course.id"
        :prev="prevLesson"
        :next="nextLesson"
      />

      <CourseCommentsSection :lesson-id="currentLesson.id" />
    </div>
  </div>

  <!-- Erro -->
  <div v-else-if="error" class="flex items-center justify-center min-h-[60vh] px-4">
    <div class="bg-white/5 border border-red-500/20 rounded-xl p-8 text-center max-w-sm">
      <AlertCircle class="w-6 h-6 text-red-400 mx-auto mb-3" />
      <p class="text-sm text-white/70">Não foi possível carregar o curso.</p>
      <button
        type="button"
        class="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-300 transition-colors"
        @click="refresh()"
      >
        <RefreshCw class="w-3.5 h-3.5" />
        Tentar novamente
      </button>
    </div>
  </div>

  <!-- Loading skeleton -->
  <div v-else class="px-4 sm:px-6 md:px-10 py-4 md:py-8 max-w-5xl mx-auto space-y-5 md:space-y-6 w-full">
    <div class="w-full aspect-video rounded-xl bg-white/5 animate-pulse" />
    <div class="h-7 w-2/3 rounded bg-white/5 animate-pulse" />
    <div class="h-4 w-full rounded bg-white/5 animate-pulse" />
    <div class="h-4 w-4/5 rounded bg-white/5 animate-pulse" />
  </div>
</template>
