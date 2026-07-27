<script setup lang="ts">
import { Loader2, CheckCircle2, XCircle, RotateCcw, AlertCircle } from 'lucide-vue-next'
import type { QuizQuestion, QuizResult } from '~/composables/useCourse'

const props = defineProps<{ lessonId: number }>()
const emit = defineEmits<{ completed: [] }>()

const courseApi = useCourse()
const toast = useToast()

const loading = ref(true)
const submitting = ref(false)
const questions = ref<QuizQuestion[]>([])
const selected = ref<Record<string, number>>({})
const result = ref<QuizResult | null>(null)

const load = async () => {
  loading.value = true
  selected.value = {}
  result.value = null
  try {
    const state = await courseApi.getQuiz(props.lessonId)
    questions.value = state.questions
    result.value = state.attempt // já respondeu antes → mostra o resultado direto
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar exercício')
    questions.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.lessonId, load, { immediate: true })

const allAnswered = computed(() =>
  questions.value.length > 0 && questions.value.every((q) => q.key in selected.value)
)

// Índice correto/escolhido por pergunta, pra pintar as opções na tela de resultado.
const resultByKey = computed(() =>
  Object.fromEntries((result.value?.results || []).map((r) => [r.key, r]))
)

const submit = async () => {
  if (!allAnswered.value) return
  submitting.value = true
  try {
    result.value = await courseApi.submitQuiz(props.lessonId, selected.value)
    emit('completed')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao enviar respostas')
  } finally {
    submitting.value = false
  }
}

const retake = () => {
  selected.value = {}
  result.value = null
}
</script>

<template>
  <div class="rounded-xl border border-white/10 bg-white/[0.03] p-5 md:p-6">
    <div v-if="loading" class="flex justify-center py-10">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>

    <div v-else-if="!questions.length" class="flex items-center gap-2 text-sm text-neutral-400 py-6">
      <AlertCircle class="w-4 h-4 text-neutral-500" />
      Este exercício ainda não tem perguntas.
    </div>

    <!-- Resultado -->
    <div v-else-if="result" class="space-y-5">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-neutral-400">Seu resultado</p>
          <p class="text-2xl font-bold text-white">
            {{ result.score }}<span class="text-neutral-500">/{{ result.total }}</span>
          </p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-bold uppercase tracking-wider text-neutral-300 hover:text-white hover:bg-white/5 border border-white/15 rounded-md"
          @click="retake"
        >
          <RotateCcw class="w-3.5 h-3.5" />
          Refazer
        </button>
      </div>

      <div
        v-for="(q, qi) in questions"
        :key="q.key"
        class="rounded-lg border border-white/5 bg-white/[0.02] p-4 space-y-2.5"
      >
        <p class="text-sm font-medium text-white">
          <span class="text-neutral-500">{{ qi + 1 }}.</span> {{ q.prompt }}
        </p>
        <div class="space-y-1.5">
          <div
            v-for="(opt, oi) in q.options"
            :key="oi"
            class="flex items-center gap-2 px-3 py-2 rounded-md text-sm border"
            :class="[
              oi === resultByKey[q.key]?.correct
                ? 'border-green-500/40 bg-green-500/10 text-green-200'
                : oi === resultByKey[q.key]?.chosen
                  ? 'border-red-500/40 bg-red-500/10 text-red-200'
                  : 'border-white/5 text-neutral-400',
            ]"
          >
            <CheckCircle2 v-if="oi === resultByKey[q.key]?.correct" class="w-4 h-4 shrink-0" />
            <XCircle
              v-else-if="oi === resultByKey[q.key]?.chosen"
              class="w-4 h-4 shrink-0"
            />
            <span v-else class="w-4 h-4 shrink-0" />
            {{ opt }}
          </div>
        </div>
        <p
          v-if="resultByKey[q.key]?.explanation"
          class="text-xs text-neutral-400 border-l-2 border-orange-500/40 pl-3"
        >
          {{ resultByKey[q.key].explanation }}
        </p>
      </div>
    </div>

    <!-- Responder -->
    <form v-else class="space-y-5" @submit.prevent="submit">
      <div
        v-for="(q, qi) in questions"
        :key="q.key"
        class="rounded-lg border border-white/5 bg-white/[0.02] p-4 space-y-2.5"
      >
        <p class="text-sm font-medium text-white">
          <span class="text-neutral-500">{{ qi + 1 }}.</span> {{ q.prompt }}
        </p>
        <label
          v-for="(opt, oi) in q.options"
          :key="oi"
          class="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-neutral-300 cursor-pointer hover:bg-white/5 border border-transparent"
          :class="selected[q.key] === oi ? 'border-orange-500/40 bg-orange-500/5 text-white' : ''"
        >
          <input
            type="radio"
            class="accent-orange-500"
            :name="q.key"
            :value="oi"
            :checked="selected[q.key] === oi"
            @change="selected = { ...selected, [q.key]: oi }"
          >
          {{ opt }}
        </label>
      </div>

      <button
        type="submit"
        :disabled="!allAnswered || submitting"
        class="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-400 disabled:opacity-40 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
      >
        <Loader2 v-if="submitting" class="w-3.5 h-3.5 animate-spin" />
        Enviar respostas
      </button>
    </form>
  </div>
</template>
