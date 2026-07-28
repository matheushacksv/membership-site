<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  MessageSquare,
  Reply,
  Trash2,
} from 'lucide-vue-next'
import type { AdminCommentThread, CommentTreeCourse } from '~/composables/useAdmin'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Comentários · Admin' })

const admin = useAdmin()
const toast = useToast()

const tree = ref<CommentTreeCourse[]>([])
const loading = ref(true)

// Colapso por curso/módulo (default expandido; guarda só os fechados).
const collapsed = reactive({ c: new Set<number>(), m: new Set<number>() })
const toggleCourse = (id: number) =>
  collapsed.c.has(id) ? collapsed.c.delete(id) : collapsed.c.add(id)
const toggleModule = (id: number) =>
  collapsed.m.has(id) ? collapsed.m.delete(id) : collapsed.m.add(id)

const loadTree = async () => {
  loading.value = true
  try {
    tree.value = await admin.listCommentsTree()
  } catch {
    toast.error('Falha ao carregar comentários')
  } finally {
    loading.value = false
  }
}

onMounted(loadTree)

// --- Thread de uma aula (modal) ---
const active = ref<{ id: number; name: string } | null>(null)
const thread = ref<AdminCommentThread[]>([])
const threadLoading = ref(false)
const replyTargetId = ref<number | null>(null)
const replyBody = ref('')
const submitting = ref(false)

const loadThread = async (lessonId: number) => {
  threadLoading.value = true
  try {
    thread.value = await admin.listLessonComments(lessonId)
  } catch {
    toast.error('Falha ao carregar a thread')
  } finally {
    threadLoading.value = false
  }
}

const openLesson = async (lessonId: number, name: string) => {
  active.value = { id: lessonId, name }
  replyTargetId.value = null
  replyBody.value = ''
  threadLoading.value = true
  try {
    thread.value = await admin.openLessonComments(lessonId) // abrir = moderar
    await loadTree() // some da fila
  } catch {
    toast.error('Falha ao carregar a thread')
  } finally {
    threadLoading.value = false
  }
}

const closeModal = () => {
  active.value = null
  loadTree() // contagens podem ter mudado
}

const startReply = (rootId: number) => {
  replyTargetId.value = rootId
  replyBody.value = ''
}

const submitReply = async () => {
  const target = replyTargetId.value
  const body = replyBody.value.trim()
  if (!target || !body) return
  submitting.value = true
  try {
    await admin.replyComment(target, body)
    replyTargetId.value = null
    replyBody.value = ''
    await Promise.all([loadThread(active.value!.id), loadTree()])
    toast.success('Resposta enviada — thread moderada')
  } catch {
    toast.error('Falha ao responder')
  } finally {
    submitting.value = false
  }
}

const removeComment = async (id: number) => {
  if (!confirm('Excluir este comentário? Respostas também são removidas.')) return
  try {
    await admin.deleteComment(id)
    await Promise.all([loadThread(active.value!.id), loadTree()])
    toast.success('Comentário excluído')
  } catch {
    toast.error('Falha ao excluir')
  }
}

const fmt = (iso: string) => new Date(iso).toLocaleString('pt-BR')
const displayName = (a: AdminCommentThread['author']) => a.name || a.email
const initial = (a: AdminCommentThread['author']) => displayName(a).charAt(0).toUpperCase()
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <header class="mb-6">
      <h1 class="text-2xl font-semibold tracking-tight flex items-center gap-2">
        <MessageSquare class="w-6 h-6 text-orange-400" />
        Comentários
      </h1>
      <p class="text-sm text-neutral-500 mt-1">
        Modere por aula. Ponto laranja = comentários novos desde sua última visita.
      </p>
    </header>

    <div v-if="loading" class="flex justify-center py-20">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>

    <p v-else-if="!tree.length" class="text-center text-neutral-500 py-20">
      Nenhum comentário ainda.
    </p>

    <div v-else class="space-y-3">
      <div
        v-for="course in tree"
        :key="course.course_id"
        class="rounded-lg border border-white/10 bg-white/5 overflow-hidden"
      >
        <!-- Curso -->
        <button
          type="button"
          class="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/5"
          @click="toggleCourse(course.course_id)"
        >
          <component
            :is="collapsed.c.has(course.course_id) ? ChevronRight : ChevronDown"
            class="w-4 h-4 text-neutral-500 shrink-0"
          />
          <span class="font-medium text-white">{{ course.course_name }}</span>
        </button>

        <!-- Módulos -->
        <div v-if="!collapsed.c.has(course.course_id)" class="border-t border-white/5">
          <div v-for="mod in course.modules" :key="mod.module_id">
            <button
              type="button"
              class="w-full flex items-center gap-2 px-4 py-2 pl-8 text-left hover:bg-white/5"
              @click="toggleModule(mod.module_id)"
            >
              <component
                :is="collapsed.m.has(mod.module_id) ? ChevronRight : ChevronDown"
                class="w-3.5 h-3.5 text-neutral-600 shrink-0"
              />
              <span class="text-sm text-neutral-300">{{ mod.module_name }}</span>
            </button>

            <!-- Aulas -->
            <div v-if="!collapsed.m.has(mod.module_id)">
              <button
                v-for="lesson in mod.lessons"
                :key="lesson.lesson_id"
                type="button"
                class="w-full flex items-center gap-3 px-4 py-2 pl-14 text-left text-sm hover:bg-orange-500/5"
                @click="openLesson(lesson.lesson_id, lesson.lesson_name)"
              >
                <span class="flex-1 min-w-0 truncate text-neutral-200">{{ lesson.lesson_name }}</span>
                <span
                  class="min-w-5 h-5 px-1.5 inline-flex items-center justify-center rounded-full bg-orange-500 text-white text-[10px] font-bold shrink-0"
                  :title="`${lesson.pending_count} pendente(s)`"
                >{{ lesson.pending_count }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: thread da aula -->
    <AdminModal
      :open="!!active"
      :title="active?.name || 'Comentários'"
      size="lg"
      @close="closeModal"
    >
      <div v-if="threadLoading" class="flex justify-center py-10">
        <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
      </div>

      <p v-else-if="!thread.length" class="text-center text-neutral-500 py-10">
        Sem comentários nesta aula.
      </p>

      <div v-else class="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
        <div v-for="root in thread" :key="root.id" class="space-y-2">
          <!-- Comentário raiz -->
          <div class="rounded-lg border border-white/10 bg-white/5 p-3">
            <div class="flex items-start gap-3">
              <img
                v-if="root.author.avatar"
                :src="root.author.avatar"
                alt=""
                class="w-8 h-8 rounded-full object-cover border border-white/10 shrink-0"
              >
              <div
                v-else
                class="w-8 h-8 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-xs font-semibold text-white shrink-0"
              >
                {{ initial(root.author) }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-medium text-white">{{ displayName(root.author) }}</span>
                  <span
                    v-if="root.author.is_staff"
                    class="text-[10px] uppercase tracking-wider font-bold text-orange-300 bg-orange-500/10 px-1.5 py-0.5 rounded"
                  >Staff</span>
                  <span class="text-[11px] text-neutral-500">{{ fmt(root.created_at) }}</span>
                </div>
                <p class="text-sm text-neutral-200 mt-1 whitespace-pre-wrap break-words">{{ root.body }}</p>
                <div class="flex items-center gap-3 mt-2">
                  <button
                    type="button"
                    class="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-orange-300"
                    @click="startReply(root.id)"
                  >
                    <Reply class="w-3.5 h-3.5" /> Responder
                  </button>
                  <button
                    type="button"
                    class="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-red-300"
                    @click="removeComment(root.id)"
                  >
                    <Trash2 class="w-3.5 h-3.5" /> Excluir
                  </button>
                </div>

                <!-- Caixa de resposta -->
                <div v-if="replyTargetId === root.id" class="mt-3 space-y-2">
                  <textarea
                    v-model="replyBody"
                    rows="2"
                    placeholder="Escreva sua resposta..."
                    class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-500 focus:border-orange-500/50 focus:outline-none resize-y"
                  />
                  <div class="flex justify-end gap-2">
                    <button
                      type="button"
                      class="px-3 py-1.5 text-xs text-neutral-400 hover:text-white"
                      @click="replyTargetId = null"
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      :disabled="submitting || !replyBody.trim()"
                      class="inline-flex items-center gap-1.5 px-4 py-1.5 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-[11px] rounded-lg"
                      @click="submitReply"
                    >
                      <Loader2 v-if="submitting" class="w-3.5 h-3.5 animate-spin" />
                      Responder
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Respostas -->
          <div
            v-for="rep in root.replies"
            :key="rep.id"
            class="ml-8 rounded-lg border border-white/5 bg-white/[0.02] p-3"
          >
            <div class="flex items-start gap-3">
              <img
                v-if="rep.author.avatar"
                :src="rep.author.avatar"
                alt=""
                class="w-7 h-7 rounded-full object-cover border border-white/10 shrink-0"
              >
              <div
                v-else
                class="w-7 h-7 rounded-full bg-gradient-to-tr from-neutral-600 to-neutral-500 flex items-center justify-center text-[11px] font-semibold text-white shrink-0"
              >
                {{ initial(rep.author) }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-medium text-white">{{ displayName(rep.author) }}</span>
                  <span
                    v-if="rep.author.is_staff"
                    class="text-[10px] uppercase tracking-wider font-bold text-orange-300 bg-orange-500/10 px-1.5 py-0.5 rounded"
                  >Staff</span>
                  <span class="text-[11px] text-neutral-500">{{ fmt(rep.created_at) }}</span>
                </div>
                <p class="text-sm text-neutral-200 mt-1 whitespace-pre-wrap break-words">{{ rep.body }}</p>
                <button
                  type="button"
                  class="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-red-300 mt-2"
                  @click="removeComment(rep.id)"
                >
                  <Trash2 class="w-3.5 h-3.5" /> Excluir
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminModal>
  </div>
</template>
