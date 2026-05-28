<script setup lang="ts">
import { Loader2, MessageSquare } from 'lucide-vue-next'
import type { CommentItem as CommentT } from '~/composables/useComments'

const props = defineProps<{ lessonId: number }>()

const comments = useComments()
const toast = useToast()
const { data: me } = useMe()

const items = ref<CommentT[]>([])
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    items.value = await comments.list(props.lessonId)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar comentários')
  } finally {
    loading.value = false
  }
}

watch(() => props.lessonId, load, { immediate: true })

const submitRoot = async (body: string) => {
  try {
    const created = await comments.create(props.lessonId, body, null)
    items.value.push(created)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao comentar')
  }
}

const submitReply = async (parentId: number, body: string) => {
  try {
    const created = await comments.create(props.lessonId, body, parentId)
    const root = items.value.find((c) => c.id === parentId)
    if (root) {
      root.replies = [...(root.replies || []), created]
    }
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao responder')
  }
}

const editComment = async (id: number, body: string) => {
  try {
    const updated = await comments.update(id, body)
    for (const c of items.value) {
      if (c.id === id) Object.assign(c, updated)
      else if (c.replies?.length) {
        const r = c.replies.find((x) => x.id === id)
        if (r) Object.assign(r, updated)
      }
    }
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao editar')
  }
}

const removeComment = async (id: number) => {
  const prev = JSON.parse(JSON.stringify(items.value))
  items.value = items.value
    .filter((c) => c.id !== id)
    .map((c) => ({ ...c, replies: c.replies?.filter((r) => r.id !== id) || [] }))
  try {
    await comments.remove(id)
  } catch (e: any) {
    items.value = prev
    toast.error(e?.data?.detail || 'Falha ao excluir')
  }
}
</script>

<template>
  <section class="space-y-5 pt-6 border-t border-white/5">
    <h3 class="text-sm font-bold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
      <MessageSquare class="w-4 h-4" />
      Comentários ({{ items.length }})
    </h3>

    <CourseCommentForm placeholder="Compartilhe sua dúvida ou observação..." @submit="submitRoot" />

    <div v-if="loading" class="flex justify-center py-6">
      <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
    </div>

    <div v-else-if="items.length" class="space-y-5">
      <CourseCommentItem
        v-for="c in items"
        :key="c.id"
        :comment="c"
        :me-id="me?.id ?? null"
        :me-is-staff="!!me?.is_staff"
        @reply="submitReply"
        @edit="editComment"
        @remove="removeComment"
      />
    </div>

    <p v-else class="text-xs text-neutral-600 italic">
      Seja o primeiro a comentar.
    </p>
  </section>
</template>
