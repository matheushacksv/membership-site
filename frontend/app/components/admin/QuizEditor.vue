<script setup lang="ts">
import { Plus, Trash2, X } from 'lucide-vue-next'
import type { AdminQuizQuestion } from '~/composables/useAdmin'

// v-model: LessonEditModal é dono do array; mutação in-place reflete no pai (mesma ref).
const questions = defineModel<AdminQuizQuestion[]>({ required: true })

const inputClass =
  'w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-600 focus:border-orange-500/50 focus:outline-none'

// Começa com 2 opções vazias: o backend exige no mínimo 2 (QuizQuestionIn).
const addQuestion = () =>
  questions.value.push({ prompt: '', type: 'choice', options: ['', ''], correct: 0, explanation: '' })

const removeQuestion = (i: number) => questions.value.splice(i, 1)

// Dissertativa não tem opções; ao voltar p/ escolha garante o mínimo de 2 exigido no backend.
const setType = (q: AdminQuizQuestion, t: 'choice' | 'text') => {
  q.type = t
  if (t === 'choice' && q.options.length < 2) q.options = ['', '']
}

const addOption = (q: AdminQuizQuestion) => q.options.push('')

const removeOption = (q: AdminQuizQuestion, oi: number) => {
  q.options.splice(oi, 1)
  // Mantém `correct` apontando pra opção certa após remover uma linha acima dela.
  if (q.correct === oi) q.correct = 0
  else if (q.correct > oi) q.correct -= 1
}
</script>

<template>
  <div class="space-y-3">
    <div
      v-for="(q, qi) in questions"
      :key="qi"
      class="bg-white/[0.02] border border-white/5 rounded-xl p-4 space-y-3"
    >
      <div class="flex items-start gap-2">
        <span class="mt-2 text-xs font-bold text-neutral-500 shrink-0">{{ qi + 1 }}.</span>
        <input v-model="q.prompt" type="text" placeholder="Enunciado da pergunta" :class="inputClass">
        <button
          type="button"
          class="mt-1 p-1.5 rounded-md text-neutral-500 hover:text-red-300 hover:bg-red-500/10 shrink-0"
          @click="removeQuestion(qi)"
        >
          <Trash2 class="w-4 h-4" />
        </button>
      </div>

      <div class="pl-6 flex gap-1">
        <button
          v-for="t in (['choice', 'text'] as const)"
          :key="t"
          type="button"
          class="px-3 py-1 text-[11px] font-bold uppercase tracking-wider rounded-md border"
          :class="q.type === t
            ? 'border-orange-500/50 bg-orange-500/10 text-orange-200'
            : 'border-white/10 text-neutral-500 hover:text-neutral-300'"
          @click="setType(q, t)"
        >
          {{ t === 'choice' ? 'Múltipla escolha' : 'Dissertativa' }}
        </button>
      </div>

      <div v-if="q.type === 'choice'" class="pl-6 space-y-2">
        <p class="text-[11px] font-bold uppercase tracking-wider text-neutral-500">
          Opções <span class="text-neutral-600">(marque a correta)</span>
        </p>
        <div v-for="(_opt, oi) in q.options" :key="oi" class="flex items-center gap-2">
          <input
            type="radio"
            class="accent-orange-500 shrink-0"
            :name="`correct-${qi}`"
            :checked="q.correct === oi"
            @change="q.correct = oi"
          >
          <input
            v-model="q.options[oi]"
            type="text"
            :placeholder="`Opção ${oi + 1}`"
            :class="inputClass"
          >
          <button
            type="button"
            :disabled="q.options.length <= 2"
            class="p-1.5 rounded-md text-neutral-500 hover:text-red-300 hover:bg-red-500/10 disabled:opacity-30 disabled:hover:bg-transparent shrink-0"
            @click="removeOption(q, oi)"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1 text-xs text-neutral-500 hover:text-orange-300"
          @click="addOption(q)"
        >
          <Plus class="w-3 h-3" />
          Adicionar opção
        </button>
      </div>

      <div class="pl-6">
        <input
          v-model="q.explanation"
          type="text"
          placeholder="Explicação (opcional, aparece após responder)"
          :class="inputClass"
        >
      </div>
    </div>

    <button
      type="button"
      class="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-dashed border-white/10 text-sm text-neutral-500 hover:text-orange-300 hover:border-orange-500/40 transition-colors"
      @click="addQuestion"
    >
      <Plus class="w-4 h-4" />
      Adicionar pergunta
    </button>
  </div>
</template>
