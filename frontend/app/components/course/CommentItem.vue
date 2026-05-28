<script setup lang="ts">
import { Pencil, Reply, Shield, Trash2 } from 'lucide-vue-next'
import type { CommentItem as CommentT } from '~/composables/useComments'

const props = defineProps<{
  comment: CommentT
  isReply?: boolean
  meId: number | null
  meIsStaff: boolean
}>()

const emit = defineEmits<{
  reply: [parentId: number, body: string]
  edit: [id: number, body: string]
  remove: [id: number]
}>()

const editing = ref(false)
const replying = ref(false)

const canEdit = computed(() => props.meId === props.comment.author.id)
const canDelete = computed(
  () => props.meId === props.comment.author.id || props.meIsStaff
)
const wasEdited = computed(() => {
  if (!props.comment.updated_at) return false
  const c = new Date(props.comment.created_at).getTime()
  const u = new Date(props.comment.updated_at).getTime()
  return u - c > 2000
})

const initial = computed(() =>
  (props.comment.author.name || '?').charAt(0).toUpperCase()
)

const relTime = (iso: string) => {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'agora'
  if (diff < 3600) return `há ${Math.floor(diff / 60)} min`
  if (diff < 86400) return `há ${Math.floor(diff / 3600)} h`
  if (diff < 604800) return `há ${Math.floor(diff / 86400)} d`
  return new Date(iso).toLocaleDateString('pt-BR')
}

const onEdit = (body: string) => {
  emit('edit', props.comment.id, body)
  editing.value = false
}

const onReply = (body: string) => {
  emit('reply', props.comment.id, body)
  replying.value = false
}

const onRemove = () => {
  if (confirm('Excluir comentário?')) emit('remove', props.comment.id)
}
</script>

<template>
  <div :class="['flex gap-3 group', isReply ? 'ml-10' : '']">
    <img
      v-if="comment.author.avatar"
      :src="comment.author.avatar"
      class="w-8 h-8 rounded-full object-cover border border-white/10 shrink-0"
    >
    <div
      v-else
      class="w-8 h-8 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-[10px] font-semibold text-black shrink-0"
    >
      {{ initial }}
    </div>

    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 flex-wrap text-xs">
        <span class="font-medium text-white truncate">
          {{ comment.author.name || 'Usuário' }}
        </span>
        <span
          v-if="comment.author.is_staff"
          class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/30 text-[9px] font-bold uppercase tracking-wider text-orange-300"
        >
          <Shield class="w-2.5 h-2.5" /> Staff
        </span>
        <span class="text-neutral-600">·</span>
        <span class="text-neutral-500">{{ relTime(comment.created_at) }}</span>
        <span v-if="wasEdited" class="text-neutral-600">(editado)</span>
      </div>

      <CourseCommentForm
        v-if="editing"
        :initial-body="comment.body"
        submit-label="Salvar"
        :show-cancel="true"
        autofocus
        class="mt-2"
        @submit="onEdit"
        @cancel="editing = false"
      />
      <p v-else class="text-sm text-neutral-300 mt-1 whitespace-pre-wrap break-words">
        {{ comment.body }}
      </p>

      <div v-if="!editing" class="flex items-center gap-3 mt-1.5 text-[11px] text-neutral-500 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          v-if="!isReply"
          type="button"
          class="inline-flex items-center gap-1 hover:text-orange-300"
          @click="replying = !replying"
        >
          <Reply class="w-3 h-3" /> Responder
        </button>
        <button
          v-if="canEdit"
          type="button"
          class="inline-flex items-center gap-1 hover:text-white"
          @click="editing = true"
        >
          <Pencil class="w-3 h-3" /> Editar
        </button>
        <button
          v-if="canDelete"
          type="button"
          class="inline-flex items-center gap-1 hover:text-red-400"
          @click="onRemove"
        >
          <Trash2 class="w-3 h-3" /> Excluir
        </button>
      </div>

      <CourseCommentForm
        v-if="replying"
        submit-label="Responder"
        :show-cancel="true"
        placeholder="Escreva uma resposta..."
        autofocus
        class="mt-3"
        @submit="onReply"
        @cancel="replying = false"
      />

      <div v-if="comment.replies?.length" class="mt-3 space-y-3">
        <CourseCommentItem
          v-for="reply in comment.replies"
          :key="reply.id"
          :comment="reply"
          :is-reply="true"
          :me-id="meId"
          :me-is-staff="meIsStaff"
          @edit="(id, body) => emit('edit', id, body)"
          @remove="(id) => emit('remove', id)"
        />
      </div>
    </div>
  </div>
</template>
