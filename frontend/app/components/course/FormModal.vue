<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import type { CourseForm } from '~/composables/useCourse'

const props = defineProps<{ open: boolean; form: CourseForm; submitting?: boolean }>()
const emit = defineEmits<{ close: []; later: []; submit: [answers: Record<string, unknown>] }>()

const answers = reactive<Record<string, unknown>>({})
const error = ref('')

// Reinicia as respostas quando o form muda (rating começa null; resto string vazia).
watch(
  () => props.form,
  (f) => {
    for (const k of Object.keys(answers)) delete answers[k]
    f?.fields.forEach((field) => {
      answers[field.key] = field.type === 'rating' ? null : ''
    })
    error.value = ''
  },
  { immediate: true }
)

const submit = () => {
  const missing = props.form.fields.filter(
    (f) => f.required && !String(answers[f.key] ?? '').trim()
  )
  if (missing.length) {
    error.value = `Preencha: ${missing.map((m) => m.label).join(', ')}`
    return
  }
  error.value = ''
  emit('submit', { ...answers })
}

const inputClass =
  'w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none'
</script>

<template>
  <AdminModal :open="open" :title="form.title || 'Formulário'" @close="emit('close')">
    <div class="space-y-5">
      <p v-if="form.description" class="text-sm text-neutral-400">{{ form.description }}</p>

      <div v-for="field in form.fields" :key="field.key" class="space-y-1.5">
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400">
          {{ field.label }}
          <span v-if="field.required" class="text-orange-400">*</span>
        </label>

        <input
          v-if="field.type === 'text'"
          v-model="answers[field.key]"
          type="text"
          :class="inputClass"
        >

        <textarea
          v-else-if="field.type === 'textarea'"
          v-model="answers[field.key]"
          rows="3"
          :class="inputClass"
        />

        <div v-else-if="field.type === 'rating'" class="flex gap-2">
          <button
            v-for="n in 5"
            :key="n"
            type="button"
            :class="[
              'w-10 h-10 rounded-lg text-sm font-bold transition-colors',
              answers[field.key] === n
                ? 'bg-orange-500 text-white'
                : 'bg-white/5 text-neutral-300 hover:bg-white/10',
            ]"
            @click="answers[field.key] = n"
          >
            {{ n }}
          </button>
        </div>

        <div v-else-if="field.type === 'choice'" class="space-y-1.5">
          <label
            v-for="opt in field.options"
            :key="opt"
            class="flex items-center gap-2 text-sm text-neutral-300 cursor-pointer"
          >
            <input
              v-model="answers[field.key]"
              type="radio"
              :value="opt"
              class="accent-orange-500"
            >
            {{ opt }}
          </label>
        </div>
      </div>

      <p v-if="error" class="text-xs text-red-400">{{ error }}</p>

      <div class="flex items-center gap-3">
        <button
          type="button"
          :disabled="submitting"
          class="flex-1 px-4 py-2.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-bold uppercase tracking-wider rounded-lg disabled:opacity-50"
          @click="submit"
        >
          <Loader2 v-if="submitting" class="w-4 h-4 animate-spin inline" />
          <span v-else>Enviar</span>
        </button>
        <button
          type="button"
          :disabled="submitting"
          class="px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-neutral-400 hover:text-white disabled:opacity-50"
          @click="emit('later')"
        >
          Depois
        </button>
      </div>
    </div>
  </AdminModal>
</template>
