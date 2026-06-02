<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  initialBody?: string
  submitLabel?: string
  showCancel?: boolean
  placeholder?: string
  autofocus?: boolean
}>()

const emit = defineEmits<{
  submit: [body: string]
  cancel: []
}>()

const body = ref(props.initialBody || '')
const submitting = ref(false)

const submit = async () => {
  const trimmed = body.value.trim()
  if (!trimmed) return
  submitting.value = true
  try {
    await emit('submit', trimmed)
    body.value = ''
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="space-y-2" @submit.prevent="submit">
    <textarea
      v-model="body"
      :placeholder="placeholder || 'Escreva um comentário...'"
      :autofocus="autofocus"
      rows="3"
      maxlength="2000"
      class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-neutral-600 focus:border-orange-500/50 focus:outline-none resize-y"
    />
    <div class="flex justify-end gap-2">
      <button
        v-if="showCancel"
        type="button"
        class="px-4 py-1.5 text-xs text-neutral-400 hover:text-white"
        @click="emit('cancel')"
      >
        Cancelar
      </button>
      <button
        type="submit"
        :disabled="submitting || !body.trim()"
        class="inline-flex items-center gap-2 px-4 py-1.5 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-md"
      >
        <Loader2 v-if="submitting" class="w-3.5 h-3.5 animate-spin" />
        {{ submitLabel || 'Comentar' }}
      </button>
    </div>
  </form>
</template>
