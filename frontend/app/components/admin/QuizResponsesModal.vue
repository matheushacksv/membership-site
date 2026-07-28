<script setup lang="ts">
import { Loader2, Download } from 'lucide-vue-next'
import type { AdminQuizQuestion, QuizResponseRow } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean; lessonId: number | null }>()
const emit = defineEmits<{ close: [] }>()

const admin = useAdmin()
const toast = useToast()

const rows = ref<QuizResponseRow[]>([])
const questions = ref<AdminQuizQuestion[]>([])
const loading = ref(false)

// Só as dissertativas — são as que têm texto pra mostrar/exportar.
const textQuestions = computed(() => questions.value.filter((q) => q.type === 'text'))

const load = async () => {
  if (!props.lessonId) return
  loading.value = true
  try {
    const [r, q] = await Promise.all([
      admin.listQuizResponses(props.lessonId),
      admin.getLessonQuiz(props.lessonId),
    ])
    rows.value = r
    questions.value = q
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar respostas')
    rows.value = []
    questions.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) load()
    else {
      rows.value = []
      questions.value = []
    }
  }
)

// Mesmo gerador de CSV do form.vue: BOM p/ Excel ler acento.
const csvCell = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`

const exportCsv = () => {
  const header = ['Aluno', 'Email', 'Nota', 'Total', 'Tentativas', 'Timeout', 'Data', ...textQuestions.value.map((q) => q.prompt)]
  const lines = rows.value.map((r) => [
    r.user_name || '',
    r.user_email,
    r.score,
    r.total,
    r.attempts,
    r.timed_out ? 'sim' : 'não',
    new Date(r.updated_at).toLocaleString('pt-BR'),
    ...textQuestions.value.map((q) => r.answers[q.key ?? ''] ?? ''),
  ])
  const csv = [header, ...lines].map((l) => l.map(csvCell).join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `respostas-quiz-${props.lessonId}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <AdminModal :open="open" title="Respostas do exercício" size="md" @close="emit('close')">
    <div class="space-y-4">
      <div v-if="loading" class="flex justify-center py-10">
        <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
      </div>

      <template v-else>
        <div class="flex items-center justify-between">
          <p class="text-sm text-neutral-400">{{ rows.length }} resposta(s)</p>
          <button
            type="button"
            :disabled="!rows.length"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-neutral-300 hover:text-white hover:bg-white/5 border border-white/15 rounded-md disabled:opacity-40"
            @click="exportCsv"
          >
            <Download class="w-3.5 h-3.5" />
            Exportar CSV
          </button>
        </div>

        <div
          v-if="rows.length"
          class="max-h-96 overflow-y-auto rounded-lg border border-white/10 bg-white/5 divide-y divide-white/5"
        >
          <div v-for="(r, i) in rows" :key="i" class="px-4 py-2.5 text-sm space-y-2">
            <div class="flex items-center gap-3">
              <span class="flex-1 min-w-0">
                <span class="block text-white truncate">{{ r.user_name || r.user_email }}</span>
                <span v-if="r.user_name" class="block text-[11px] text-neutral-500 truncate">{{ r.user_email }}</span>
              </span>
              <span
                v-if="r.timed_out"
                class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider text-red-300 bg-red-500/10 border border-red-500/30"
                title="Tentativa finalizada por tempo esgotado"
              >Timeout</span>
              <span v-if="r.attempts > 1" class="shrink-0 text-[10px] text-neutral-500" :title="`${r.attempts} tentativas`">
                ×{{ r.attempts }}
              </span>
              <span class="text-white font-medium shrink-0">
                {{ r.score }}<span class="text-neutral-500">/{{ r.total }}</span>
              </span>
            </div>

            <!-- Respostas dissertativas deste aluno -->
            <div
              v-for="q in textQuestions"
              :key="q.key"
              class="rounded-md border border-white/5 bg-white/[0.02] px-3 py-2"
            >
              <p class="text-[11px] text-neutral-500">{{ q.prompt }}</p>
              <p class="text-neutral-200 whitespace-pre-wrap">{{ r.answers[q.key ?? ''] || '—' }}</p>
            </div>
          </div>
        </div>

        <p v-else class="text-xs text-neutral-500 text-center py-10">
          Ninguém respondeu este exercício ainda.
        </p>
      </template>
    </div>
  </AdminModal>
</template>
