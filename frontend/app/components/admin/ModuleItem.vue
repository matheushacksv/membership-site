<script setup lang="ts">
import draggable from 'vuedraggable'
import {
  GripVertical,
  ChevronDown,
  Trash2,
  Eye,
  EyeOff,
  Plus,
  Pencil,
  Check,
  X,
  Loader2,
  Lock,
  LockOpen,
} from 'lucide-vue-next'
import type { LessonItem as Lesson, ModuleItem as Module } from '~/composables/useAdmin'
import LessonItemRow from './LessonItem.vue'

const props = defineProps<{ module: Module }>()
const emit = defineEmits<{
  remove: []
  togglePublish: []
  editLesson: [id: number]
}>()

const admin = useAdmin()
const toast = useToast()

const expanded = ref(false)
const lessons = ref<Lesson[]>([])
const loadingLessons = ref(false)
const newLessonName = ref('')
const creatingLesson = ref(false)
const showInlineInput = ref(false)

const editingName = ref(false)
const nameInput = ref('')
const savingName = ref(false)

const startEditName = () => {
  nameInput.value = props.module.name
  editingName.value = true
}

const cancelEditName = () => {
  editingName.value = false
  nameInput.value = ''
}

const saveName = async () => {
  const name = nameInput.value.trim()
  if (!name || name === props.module.name) {
    cancelEditName()
    return
  }
  savingName.value = true
  try {
    await admin.updateModule(props.module.id, { name })
    props.module.name = name
    editingName.value = false
    toast.success('Módulo renomeado')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao renomear')
  } finally {
    savingName.value = false
  }
}

// Trava o módulo até as aulas dos módulos anteriores estarem concluídas. Otimista.
const toggleRequiresPrevious = async () => {
  const next = !props.module.requires_previous
  props.module.requires_previous = next
  try {
    await admin.updateModule(props.module.id, { requires_previous: next })
  } catch {
    props.module.requires_previous = !next
    toast.error('Falha ao atualizar')
  }
}

const loadLessons = async () => {
  loadingLessons.value = true
  try {
    lessons.value = await admin.listLessons(props.module.id)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar aulas')
  } finally {
    loadingLessons.value = false
  }
}

const toggle = async () => {
  expanded.value = !expanded.value
  if (expanded.value && lessons.value.length === 0) await loadLessons()
}

const createLesson = async () => {
  const name = newLessonName.value.trim()
  if (!name) return
  creatingLesson.value = true
  try {
    await admin.createLesson({
      module_id: props.module.id,
      name,
      is_published: false,
    })
    await loadLessons()
    newLessonName.value = ''
    showInlineInput.value = false
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao criar aula')
  } finally {
    creatingLesson.value = false
  }
}

const removeLesson = async (id: number) => {
  if (!confirm('Deletar esta aula?')) return
  const prev = lessons.value
  lessons.value = lessons.value.filter((l) => l.id !== id)
  try {
    await admin.deleteLesson(id)
    toast.success('Aula deletada')
  } catch (e: any) {
    lessons.value = prev
    toast.error(e?.data?.detail || 'Falha ao deletar')
  }
}

const toggleLessonPublish = async (lesson: Lesson) => {
  const next = !lesson.is_published
  lesson.is_published = next
  try {
    await admin.updateLesson(lesson.id, { is_published: next })
  } catch {
    lesson.is_published = !next
    toast.error('Falha ao atualizar')
  }
}

const onReorder = async () => {
  const order = lessons.value.map((l) => l.id)
  try {
    await admin.reorderLessons(props.module.id, order)
  } catch (e: any) {
    toast.error('Falha ao reordenar')
    await loadLessons()
  }
}

defineExpose({ loadLessons })
</script>

<template>
  <div class="border border-white/10 rounded-lg bg-white/[0.02] overflow-hidden">
    <div class="flex items-center gap-2 px-3 py-3">
      <GripVertical class="module-handle w-4 h-4 text-neutral-600 cursor-grab shrink-0" />
      <template v-if="editingName">
        <input
          v-model="nameInput"
          type="text"
          placeholder="Nome do módulo..."
          class="flex-1 px-3 py-1.5 bg-white/5 border border-orange-500/40 rounded-md text-sm text-white focus:outline-none"
          autofocus
          @keydown.enter.prevent="saveName"
          @keydown.escape="cancelEditName"
        >
        <button
          type="button"
          :disabled="savingName"
          title="Salvar"
          class="p-1.5 rounded text-neutral-500 hover:text-green-400 disabled:opacity-50"
          @click="saveName"
        >
          <Loader2 v-if="savingName" class="w-4 h-4 animate-spin" />
          <Check v-else class="w-4 h-4" />
        </button>
        <button
          type="button"
          title="Cancelar"
          class="p-1.5 rounded text-neutral-500 hover:text-red-400"
          @click="cancelEditName"
        >
          <X class="w-4 h-4" />
        </button>
      </template>
      <template v-else>
        <button
          type="button"
          class="flex-1 flex items-center gap-2 text-left text-sm font-medium text-white"
          @click="toggle"
        >
          <ChevronDown
            class="w-4 h-4 text-neutral-500 transition-transform"
            :class="{ 'rotate-180': expanded }"
          />
          {{ module.name }}
          <span v-if="lessons.length" class="text-xs text-neutral-500 ml-2">
            {{ lessons.length }} aula{{ lessons.length === 1 ? '' : 's' }}
          </span>
        </button>
        <button
          type="button"
          title="Renomear módulo"
          class="p-1.5 rounded text-neutral-500 hover:text-orange-300"
          @click="startEditName"
        >
          <Pencil class="w-4 h-4" />
        </button>
        <button
          type="button"
          :title="module.requires_previous ? 'Travado até concluir os módulos anteriores' : 'Liberar só após os módulos anteriores'"
          class="p-1.5 rounded"
          :class="module.requires_previous ? 'text-orange-400 hover:text-orange-300' : 'text-neutral-500 hover:text-orange-300'"
          @click="toggleRequiresPrevious"
        >
          <component :is="module.requires_previous ? Lock : LockOpen" class="w-4 h-4" />
        </button>
        <button
          type="button"
          :title="module.is_published ? 'Despublicar' : 'Publicar'"
          class="p-1.5 rounded text-neutral-500 hover:text-orange-300"
          @click="emit('togglePublish')"
        >
          <component :is="module.is_published ? Eye : EyeOff" class="w-4 h-4" />
        </button>
        <button
          type="button"
          title="Deletar módulo"
          class="p-1.5 rounded text-neutral-500 hover:text-red-400"
          @click="emit('remove')"
        >
          <Trash2 class="w-4 h-4" />
        </button>
      </template>
    </div>

    <div v-if="expanded" class="px-3 pb-3 pt-1 space-y-1.5 border-t border-white/5">
      <div v-if="loadingLessons" class="flex justify-center py-4">
        <Loader2 class="w-4 h-4 text-orange-500 animate-spin" />
      </div>
      <template v-else>
        <ClientOnly>
          <draggable
            v-model="lessons"
            handle=".lesson-handle"
            item-key="id"
            ghost-class="opacity-30"
            @end="onReorder"
          >
            <template #item="{ element }">
              <LessonItemRow
                :lesson="element"
                @edit="emit('editLesson', element.id)"
                @remove="removeLesson(element.id)"
                @toggle-publish="toggleLessonPublish(element)"
              />
            </template>
          </draggable>
        </ClientOnly>

        <div v-if="showInlineInput" class="flex items-center gap-2 mt-1.5">
          <input
            v-model="newLessonName"
            type="text"
            placeholder="Nome da aula..."
            class="flex-1 px-3 py-1.5 bg-white/5 border border-orange-500/40 rounded-md text-sm text-white focus:outline-none"
            autofocus
            @keydown.enter.prevent="createLesson"
            @keydown.escape="(showInlineInput = false), (newLessonName = '')"
          >
          <button
            type="button"
            :disabled="creatingLesson"
            class="px-3 py-1.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-bold uppercase rounded-md disabled:opacity-50"
            @click="createLesson"
          >
            <Loader2 v-if="creatingLesson" class="w-3 h-3 animate-spin inline" />
            <span v-else>OK</span>
          </button>
        </div>

        <button
          v-else
          type="button"
          class="w-full mt-1 flex items-center gap-2 px-3 py-2 rounded-md border border-dashed border-white/10 text-xs text-neutral-500 hover:text-orange-300 hover:border-orange-500/40 transition-colors"
          @click="showInlineInput = true"
        >
          <Plus class="w-3.5 h-3.5" />
          Nova aula
        </button>
      </template>
    </div>
  </div>
</template>
