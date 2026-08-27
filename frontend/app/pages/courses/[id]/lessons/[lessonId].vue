<script setup lang="ts">
import { ListVideo, AlertCircle, RefreshCw } from 'lucide-vue-next'
import type { CourseDetail, CourseForm, Lesson } from '~/composables/useCourse'

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
    ? `${currentLesson.value.name}, ${course.value?.name || 'Curso'}`
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
  // O `locked` do módulo (requires_previous) é calculado no servidor e depende de aulas
  // que o módulo travado nem manda no payload → não dá pra recomputar no cliente.
  // Refetch quando há módulo travado (concluir pode destravar) ou ao desmarcar (pode retravar).
  if (value === false || course.value.modules.some((m) => m.locked)) refresh()
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
      checkForm()
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
    checkForm()
  } catch { /* silent */ }
}

// Quiz: o submit já gravou LessonProgress no servidor (submit_lesson_quiz). Aqui só
// sincroniza a UI, igual ao onEnded do vídeo.
const onQuizCompleted = () => {
  if (!currentLesson.value) return
  patchLocalCompleted(currentLesson.value.id)
  refreshNuxtData('home-mine')
  checkForm()
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
    if (target) checkForm()
    toast.success(target ? 'Aula concluída' : 'Marcada como não concluída')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao atualizar conclusão')
  } finally {
    saving.value = false
  }
}

// Smart form: aparece quando devido (cadência + ≥1 aula concluída). Checa no load e
// logo após concluir uma aula (gatilho "após concluir aula/módulo").
const dueForm = ref<CourseForm | null>(null)
const formModalOpen = ref(false)
const submittingForm = ref(false)
const openedFormId = ref<number | null>(null) // evita reabrir o mesmo form a cada conclusão/troca de aula

const checkForm = async () => {
  try {
    const { form } = await courseApi.dueForm(courseId.value)
    dueForm.value = form
    // abre direto (sem clique), mas só uma vez por form na sessão
    if (form && form.id !== openedFormId.value) {
      formModalOpen.value = true
      openedFormId.value = form.id
    }
  } catch { /* silent */ }
}

const onFormSubmit = async (answers: Record<string, unknown>) => {
  if (!dueForm.value) return
  submittingForm.value = true
  try {
    await courseApi.submitForm(dueForm.value.id, { answers })
    formModalOpen.value = false
    dueForm.value = null
    toast.success('Obrigado pela resposta!')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao enviar')
  } finally {
    submittingForm.value = false
  }
}

// "Depois": registra skip (backend reabre só após 24h).
const laterForm = async () => {
  if (!dueForm.value) return
  const id = dueForm.value.id
  formModalOpen.value = false
  dueForm.value = null
  try { await courseApi.submitForm(id, { skipped: true }) } catch { /* silent */ }
}

// Fechar pelo X/esc/backdrop = mesmo que "Depois" (grava skip → backend reabre só após 24h).
// Sem isso, fechar sem gravar fazia o form reaparecer ao trocar de aula (page remonta).
const closeForm = () => laterForm()

onMounted(checkForm)
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

      <CourseQuizPanel
        v-if="currentLesson.kind === 'quiz'"
        :lesson-id="currentLesson.id"
        @completed="onQuizCompleted"
      />
      <CourseVideoPlayer
        v-else
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

      <CourseCommentsSection
        v-if="course.comments_enabled && currentLesson.kind !== 'quiz'"
        :lesson-id="currentLesson.id"
      />
    </div>

    <CourseFormModal
      v-if="dueForm"
      :open="formModalOpen"
      :form="dueForm"
      :submitting="submittingForm"
      @close="closeForm"
      @later="laterForm"
      @submit="onFormSubmit"
    />
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
