<script setup lang="ts">
import { Award, Loader2, X } from 'lucide-vue-next'
import type { CourseDetail } from '~/composables/useCourse'
import { saveBlob, useCertificates } from '~/composables/useCertificates'

const props = defineProps<{
  course: CourseDetail
  activeLessonId: number
  open?: boolean
}>()

const emit = defineEmits<{ close: [] }>()

const totals = computed(() => {
  const all = props.course.modules.flatMap((m) => m.lessons)
  const completed = all.filter((l) => l.completed).length
  return {
    total: all.length,
    completed,
    percent: all.length ? Math.round((completed / all.length) * 100) : 0,
  }
})

// Certificado: só quando o curso emite e o aluno está 100%.
const certApi = useCertificates()
const toast = useToast()
const certLoading = ref(false)
const showCertificate = computed(
  () => props.course.certificate_enabled && totals.value.total > 0 && totals.value.percent === 100,
)

const getCertificate = async () => {
  certLoading.value = true
  try {
    const cert = await certApi.issue(props.course.id)
    const blob = await certApi.download(cert.code)
    saveBlob(blob, `certificado-${cert.code}.pdf`)
  } catch (e: any) {
    const detail = e?.data?.detail || 'Falha ao emitir certificado'
    // 409 = nome/CPF faltando → toast com atalho pro perfil
    if (e?.response?.status === 409 || e?.status === 409) {
      toast.error(detail, { label: 'Ir ao perfil', to: '/profile' })
    } else {
      toast.error(detail)
    }
  } finally {
    certLoading.value = false
  }
}

const navRef = ref<HTMLElement | null>(null)

// O <nav> tem scroll próprio; ao trocar de aula a instância é reusada e o scroll
// fica preso onde estava. Traz o item ativo para a view (sem mexer na janela).
const scrollActiveIntoView = () => {
  const el = navRef.value?.querySelector<HTMLElement>(
    `[data-lesson-id="${props.activeLessonId}"]`
  )
  el?.scrollIntoView({ block: 'nearest' })
}

// nextTick: o ModuleAccordion da aula só expande após o re-render, então o item
// alvo precisa existir/estar visível no DOM antes do scroll.
onMounted(() => nextTick(scrollActiveIntoView))
watch(() => props.activeLessonId, () => nextTick(scrollActiveIntoView))
</script>

<template>
  <div
    v-if="open"
    class="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
    @click="emit('close')"
  />

  <aside
    :class="[
      'border-r border-white/5 bg-[#0a0a0a]/95 lg:bg-[#0a0a0a]/60 flex flex-col',
      // Desktop: sticky sidebar
      'lg:w-80 lg:shrink-0 lg:h-[calc(100vh-57px)] lg:sticky lg:top-[57px] lg:translate-x-0',
      // Mobile: off-canvas drawer
      'fixed lg:relative inset-y-0 left-0 z-50 w-[85vw] max-w-sm h-screen transition-transform duration-200 ease-out',
      open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    ]"
  >
    <div class="px-5 py-4 border-b border-white/5 flex items-start gap-2">
      <div class="flex-1 min-w-0">
        <h2 class="text-sm font-bold text-white truncate">{{ course.name }}</h2>
        <div class="mt-3">
          <div class="flex items-center justify-between text-[10px] text-neutral-500 mb-1">
            <span>Progresso</span>
            <span>{{ totals.completed }}/{{ totals.total }} · {{ totals.percent }}%</span>
          </div>
          <div class="h-1 bg-white/5 rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-orange-500 to-amber-400 transition-all"
              :style="{ width: `${totals.percent}%` }"
            />
          </div>
          <button
            v-if="showCertificate"
            type="button"
            :disabled="certLoading"
            class="mt-3 w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-bold uppercase tracking-wider disabled:opacity-50"
            @click="getCertificate"
          >
            <Loader2 v-if="certLoading" class="w-3.5 h-3.5 animate-spin" />
            <Award v-else class="w-3.5 h-3.5" />
            Baixar certificado
          </button>
        </div>
      </div>
      <button
        type="button"
        class="lg:hidden p-1.5 -mr-1 text-neutral-500 hover:text-white"
        aria-label="Fechar"
        @click="emit('close')"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <nav ref="navRef" class="flex-1 overflow-y-auto py-2">
      <CourseModuleAccordion
        v-for="module in course.modules"
        :key="module.id"
        :module="module"
        :course-id="course.id"
        :active-lesson-id="activeLessonId"
      />

      <p v-if="!course.modules.length" class="px-5 py-6 text-xs text-neutral-600 text-center">
        Sem módulos publicados.
      </p>
    </nav>
  </aside>
</template>
