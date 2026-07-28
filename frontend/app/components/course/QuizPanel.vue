<script setup lang="ts">
import { Loader2, CheckCircle2, XCircle, RotateCcw, AlertCircle, Timer, Play } from 'lucide-vue-next'
import type { QuizQuestion, QuizResult } from '~/composables/useCourse'

const props = defineProps<{ lessonId: number }>()
const emit = defineEmits<{ completed: [] }>()

const courseApi = useCourse()
const toast = useToast()

const loading = ref(true)
const submitting = ref(false)
const questions = ref<QuizQuestion[]>([])
const selected = ref<Record<string, number | string>>({})
const result = ref<QuizResult | null>(null)
const allowRetake = ref(true)

// Timer (exercício cronometrado). time_limit=0 → sem tempo, comporta como antes.
const timeLimit = ref(0)
const remaining = ref<number | null>(null) // segundos restantes; null = não iniciado
const attempts = ref(0)
const lastTimedOut = ref(false)
let ticker: ReturnType<typeof setInterval> | null = null
let serverOffset = 0 // (server_now - Date.now()) → contagem imune a relógio torto do cliente
let expiresAt = 0
let finishing = false // evita submit duplo (tick + clique)

const timed = computed(() => timeLimit.value > 0)
// Formulário aparece: sem tempo → sempre; com tempo → só depois de iniciar.
const showForm = computed(() => !result.value && (!timed.value || remaining.value !== null))
const showGate = computed(() => !result.value && timed.value && remaining.value === null)

const mmss = computed(() => {
  const s = Math.max(0, remaining.value ?? 0)
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})

const stopTicker = () => {
  if (ticker) { clearInterval(ticker); ticker = null }
}

const runCountdown = (server_now: string, expires_at: string) => {
  serverOffset = new Date(server_now).getTime() - Date.now()
  expiresAt = new Date(expires_at).getTime()
  stopTicker()
  const tick = () => {
    remaining.value = Math.max(0, Math.ceil((expiresAt - (Date.now() + serverOffset)) / 1000))
    if (remaining.value <= 0) onExpire()
  }
  tick()
  ticker = setInterval(tick, 1000)
}

const load = async () => {
  loading.value = true
  stopTicker()
  finishing = false
  selected.value = {}
  result.value = null
  remaining.value = null
  try {
    const state = await courseApi.getQuiz(props.lessonId)
    questions.value = state.questions
    allowRetake.value = state.allow_retake
    timeLimit.value = state.time_limit_seconds || 0
    attempts.value = state.attempts || 0
    lastTimedOut.value = state.timed_out || false
    result.value = state.attempt // já finalizou antes → mostra o resultado direto
    // Reload no meio de uma tentativa cronometrada → retoma o tempo restante (não zera).
    if (!result.value && state.timer) {
      runCountdown(state.timer.server_now, state.timer.expires_at)
    }
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar exercício')
    questions.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.lessonId, load, { immediate: true })
onBeforeUnmount(stopTicker)

// Inicia (ou recomeça) a tentativa cronometrada: servidor grava o início e devolve o timer.
const begin = async () => {
  lastTimedOut.value = false
  try {
    const timer = await courseApi.startQuiz(props.lessonId)
    runCountdown(timer.server_now, timer.expires_at)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao iniciar exercício')
  }
}

// Escolha: respondida quando tem índice; dissertativa: quando o texto não está vazio.
const isAnswered = (q: QuizQuestion) => {
  const v = selected.value[q.key]
  return q.type === 'text' ? typeof v === 'string' && v.trim() !== '' : typeof v === 'number'
}
const allAnswered = computed(() => questions.value.length > 0 && questions.value.every(isAnswered))

const resultByKey = computed(() =>
  Object.fromEntries((result.value?.results || []).map((r) => [r.key, r]))
)

const submit = async () => {
  if (!allAnswered.value || submitting.value || finishing) return
  finishing = true
  submitting.value = true
  stopTicker()
  try {
    result.value = await courseApi.submitQuiz(props.lessonId, selected.value)
    emit('completed')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao enviar respostas')
  } finally {
    submitting.value = false
    finishing = false
  }
}

// Tempo esgotou: finaliza como falha no servidor e VOLTA AO INÍCIO (campos limpos).
const onExpire = async () => {
  if (finishing) return
  finishing = true
  stopTicker()
  remaining.value = null
  try {
    await courseApi.submitQuiz(props.lessonId, selected.value, true)
    emit('completed') // timeout ainda conclui a aula
  } catch { /* silent — servidor já registra a falha via task */ }
  selected.value = {}
  attempts.value += 1
  lastTimedOut.value = true
  finishing = false
}

const retake = () => {
  selected.value = {}
  result.value = null
  remaining.value = null // exercício cronometrado volta pro gate "Iniciar"
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

    <!-- Gate: exercício cronometrado antes de iniciar -->
    <div v-else-if="showGate" class="space-y-4 py-4 text-center">
      <div
        v-if="lastTimedOut"
        class="flex items-center justify-center gap-2 text-sm text-red-300"
      >
        <XCircle class="w-4 h-4" />
        Tempo esgotado — tentativa falha {{ attempts }}.
      </div>
      <div class="flex items-center justify-center gap-2 text-neutral-300">
        <Timer class="w-5 h-5 text-orange-400" />
        <span class="text-sm">
          Você terá <strong class="text-white">{{ Math.round(timeLimit / 60) || 1 }} min</strong>.
          Ao esgotar, o teste finaliza sozinho como tentativa falha.
        </span>
      </div>
      <button
        v-if="allowRetake || attempts === 0"
        type="button"
        class="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-400 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
        @click="begin"
      >
        <Play class="w-3.5 h-3.5" />
        {{ attempts > 0 ? 'Tentar de novo' : 'Iniciar exercício' }}
      </button>
      <p v-else class="text-xs text-neutral-500">Sem novas tentativas disponíveis.</p>
    </div>

    <!-- Resultado -->
    <div v-else-if="result" class="space-y-5">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-neutral-400">Seu resultado</p>
          <p v-if="result.total > 0" class="text-2xl font-bold text-white">
            {{ result.score }}<span class="text-neutral-500">/{{ result.total }}</span>
          </p>
          <p v-else class="text-lg font-bold text-green-300">Respostas enviadas ✓</p>
        </div>
        <button
          v-if="allowRetake"
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

        <!-- Dissertativa: mostra o que o aluno escreveu (sem certo/errado) -->
        <div v-if="q.type === 'text'" class="rounded-md border border-white/5 bg-white/[0.02] px-3 py-2">
          <p class="text-[11px] font-bold uppercase tracking-wider text-neutral-500 mb-1">Sua resposta</p>
          <p class="text-sm text-neutral-200 whitespace-pre-wrap">{{ resultByKey[q.key]?.answer_text || '—' }}</p>
        </div>

        <!-- Múltipla escolha: pinta escolhida vs correta -->
        <div v-else class="space-y-1.5">
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
            <XCircle v-else-if="oi === resultByKey[q.key]?.chosen" class="w-4 h-4 shrink-0" />
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
    <form v-else-if="showForm" class="space-y-5" @submit.prevent="submit">
      <!-- Contagem regressiva -->
      <div
        v-if="timed"
        class="flex items-center justify-between gap-2 px-3 py-2 rounded-lg border"
        :class="(remaining ?? 0) <= 10 ? 'border-red-500/40 bg-red-500/10' : 'border-white/10 bg-white/[0.02]'"
      >
        <span class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-neutral-400">
          <Timer class="w-3.5 h-3.5" />
          Tempo restante
        </span>
        <span
          class="text-lg font-bold tabular-nums"
          :class="(remaining ?? 0) <= 10 ? 'text-red-300' : 'text-white'"
        >{{ mmss }}</span>
      </div>

      <div
        v-for="(q, qi) in questions"
        :key="q.key"
        class="rounded-lg border border-white/5 bg-white/[0.02] p-4 space-y-2.5"
      >
        <p class="text-sm font-medium text-white">
          <span class="text-neutral-500">{{ qi + 1 }}.</span> {{ q.prompt }}
        </p>

        <!-- Dissertativa -->
        <textarea
          v-if="q.type === 'text'"
          :value="(selected[q.key] as string) || ''"
          rows="4"
          placeholder="Escreva sua resposta..."
          class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md text-sm text-white placeholder:text-neutral-600 focus:border-orange-500/50 focus:outline-none resize-y"
          @input="selected = { ...selected, [q.key]: ($event.target as HTMLTextAreaElement).value }"
        />

        <!-- Múltipla escolha -->
        <label
          v-for="(opt, oi) in q.options"
          v-else
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
