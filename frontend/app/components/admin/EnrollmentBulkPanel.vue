<script setup lang="ts">
import {
  Loader2,
  Infinity as InfinityIcon,
  Trash2,
  CalendarClock,
  Power,
  PowerOff,
  ChevronLeft,
  ChevronRight,
} from 'lucide-vue-next'
import type { AdminCourse, EnrollmentStatus } from '~/composables/useAdmin'

const props = defineProps<{
  courseId: number
  status: string
  search: string
  courses: AdminCourse[]
}>()

const admin = useAdmin()
const toast = useToast()

const PAGE = 50
const offset = ref(0)
const selected = ref<Set<number>>(new Set())

const filters = computed(() => ({
  course_id: props.courseId,
  status: (props.status || undefined) as EnrollmentStatus | undefined,
  search: props.search || undefined,
}))

// Filtro mudou: volta pra 1ª página e limpa seleção (no mesmo tick que o refetch).
watch(
  () => [props.courseId, props.status, props.search],
  () => {
    offset.value = 0
    selected.value = new Set()
  }
)

const { data, pending, refresh } = await useAsyncData(
  'admin-enrollments',
  () => admin.listEnrollmentsAdmin({ ...filters.value, limit: PAGE, offset: offset.value }),
  { watch: [() => props.courseId, () => props.status, () => props.search, offset] }
)

const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE)))
const page = computed(() => Math.floor(offset.value / PAGE) + 1)
const course = computed(() => props.courses.find((c) => c.id === props.courseId))

const prev = () => {
  if (offset.value > 0) offset.value = Math.max(0, offset.value - PAGE)
}
const next = () => {
  if (page.value < pageCount.value) offset.value += PAGE
}

// Seleção
const toggle = (id: number) => {
  const n = new Set(selected.value)
  n.has(id) ? n.delete(id) : n.add(id)
  selected.value = n
}
const pageAllSelected = computed(
  () => items.value.length > 0 && items.value.every((e) => selected.value.has(e.id))
)
const togglePage = () => {
  const n = new Set(selected.value)
  if (pageAllSelected.value) items.value.forEach((e) => n.delete(e.id))
  else items.value.forEach((e) => n.add(e.id))
  selected.value = n
}

const selectingAll = ref(false)
const selectAllMatching = async () => {
  selectingAll.value = true
  try {
    const ids = await admin.enrollmentIds(filters.value)
    selected.value = new Set(ids)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao selecionar todos')
  } finally {
    selectingAll.value = false
  }
}
const clearSelection = () => {
  selected.value = new Set()
}

// Ações em massa
const working = ref(false)
const showExpiry = ref(false)
const expiryForm = reactive({ lifetime: false, expires_at: '' })

const runBulk = async (body: { action: any; expires_at?: string | null; is_active?: boolean }) => {
  if (!selected.value.size) return
  working.value = true
  try {
    const { affected } = await admin.bulkEnrollments({
      enrollment_ids: [...selected.value],
      ...body,
    })
    toast.success(`${affected} matrícula(s) atualizada(s)`)
    selected.value = new Set()
    await refresh()
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha na ação em massa')
  } finally {
    working.value = false
  }
}

const applyCourseDays = () => runBulk({ action: 'apply_course_days' })
const setActive = (v: boolean) => runBulk({ action: 'set_active', is_active: v })

const openExpiry = () => {
  expiryForm.lifetime = false
  expiryForm.expires_at = ''
  showExpiry.value = true
}
const submitExpiry = () => {
  const expires_at = expiryForm.lifetime
    ? null
    : expiryForm.expires_at
      ? new Date(expiryForm.expires_at).toISOString()
      : null
  showExpiry.value = false
  runBulk({ action: 'set_expiry', expires_at })
}

const removeSel = () => {
  if (!confirm(`Excluir ${selected.value.size} matrícula(s)? Isso revoga o acesso.`)) return
  runBulk({ action: 'delete' })
}

const fmtDate = (s: string | null) => (s ? new Date(s).toLocaleDateString('pt-BR') : null)
const isExpired = (s: string | null) => !!s && new Date(s) <= new Date()
</script>

<template>
  <div class="space-y-3">
    <!-- Barra de ações em massa -->
    <div
      v-if="selected.size"
      class="flex flex-wrap items-center gap-2 px-4 py-3 bg-orange-500/10 border border-orange-500/30 rounded-xl sticky top-2 z-10 backdrop-blur"
    >
      <span class="text-sm font-medium text-orange-200 mr-1">
        {{ selected.size }} selecionada(s)
      </span>
      <button type="button" class="text-xs text-neutral-400 hover:text-white underline" @click="clearSelection">
        limpar
      </button>

      <div class="flex-1" />

      <button
        type="button"
        :disabled="working"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold uppercase tracking-wider rounded-lg disabled:opacity-50"
        :title="course?.access_days ? `${course.access_days} dias a partir da matrícula` : 'Curso vitalício (access_days vazio)'"
        @click="applyCourseDays"
      >
        <Loader2 v-if="working" class="w-3.5 h-3.5 animate-spin" />
        Aplicar access_days
      </button>
      <button
        type="button"
        :disabled="working"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold uppercase tracking-wider rounded-lg disabled:opacity-50"
        @click="openExpiry"
      >
        <CalendarClock class="w-3.5 h-3.5" />
        Definir expiração
      </button>
      <button
        type="button"
        :disabled="working"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold uppercase tracking-wider rounded-lg disabled:opacity-50"
        @click="setActive(true)"
      >
        <Power class="w-3.5 h-3.5" />
        Ativar
      </button>
      <button
        type="button"
        :disabled="working"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold uppercase tracking-wider rounded-lg disabled:opacity-50"
        @click="setActive(false)"
      >
        <PowerOff class="w-3.5 h-3.5" />
        Desativar
      </button>
      <button
        type="button"
        :disabled="working"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-300 text-xs font-bold uppercase tracking-wider rounded-lg disabled:opacity-50"
        @click="removeSel"
      >
        <Trash2 class="w-3.5 h-3.5" />
        Excluir
      </button>
    </div>

    <div v-if="pending" class="flex justify-center py-16">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>

    <div v-else-if="total" class="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
      <!-- Cabeçalho da tabela -->
      <div class="flex items-center gap-3 px-5 py-3 border-b border-white/10 text-xs font-bold uppercase tracking-wider text-neutral-500">
        <input
          type="checkbox"
          class="accent-orange-500 shrink-0"
          :checked="pageAllSelected"
          @change="togglePage"
        >
        <span class="flex-1">Aluno ({{ total }})</span>
        <span class="w-40 text-right">Expiração</span>
      </div>

      <!-- "Selecionar todos os N" -->
      <div
        v-if="pageAllSelected && selected.size < total"
        class="px-5 py-2 bg-white/[0.02] border-b border-white/5 text-center text-xs text-neutral-400"
      >
        {{ selected.size }} desta página selecionada(s).
        <button
          type="button"
          :disabled="selectingAll"
          class="font-bold text-orange-300 hover:text-orange-200 disabled:opacity-50"
          @click="selectAllMatching"
        >
          <Loader2 v-if="selectingAll" class="inline w-3 h-3 animate-spin" />
          Selecionar todas as {{ total }} matrículas
        </button>
      </div>

      <div
        v-for="e in items"
        :key="e.id"
        class="flex items-center gap-3 px-5 py-3 border-b border-white/5 last:border-b-0 hover:bg-white/[0.02]"
        :class="{ 'bg-orange-500/[0.06]': selected.has(e.id) }"
      >
        <input
          type="checkbox"
          class="accent-orange-500 shrink-0"
          :checked="selected.has(e.id)"
          @change="toggle(e.id)"
        >
        <span
          :class="[
            'inline-block w-1.5 h-1.5 rounded-full shrink-0',
            e.is_active ? 'bg-emerald-400' : 'bg-neutral-600',
          ]"
          :title="e.is_active ? 'Ativa' : 'Inativa'"
        />
        <div class="flex-1 min-w-0">
          <p class="text-sm text-white truncate">{{ e.user_name || '-' }}</p>
          <p class="text-xs text-neutral-500 truncate">{{ e.user_email }}</p>
        </div>
        <span
          v-if="!e.expires_at"
          class="w-40 text-right text-[10px] uppercase tracking-wider text-neutral-500 inline-flex items-center justify-end gap-1"
        >
          <InfinityIcon class="w-3 h-3" />
          Vitalícia
        </span>
        <span
          v-else
          class="w-40 text-right text-[10px] uppercase tracking-wider"
          :class="isExpired(e.expires_at) ? 'text-red-400' : 'text-neutral-500'"
        >
          {{ isExpired(e.expires_at) ? 'Expirou' : 'Expira' }} {{ fmtDate(e.expires_at) }}
        </span>
      </div>

      <!-- Paginação -->
      <div
        v-if="pageCount > 1"
        class="flex items-center justify-between px-5 py-3 border-t border-white/10 text-xs text-neutral-500"
      >
        <span>Página {{ page }} de {{ pageCount }}</span>
        <div class="flex items-center gap-1">
          <button
            type="button"
            :disabled="page <= 1"
            class="p-1.5 rounded-md hover:bg-white/5 hover:text-white disabled:opacity-30"
            @click="prev"
          >
            <ChevronLeft class="w-4 h-4" />
          </button>
          <button
            type="button"
            :disabled="page >= pageCount"
            class="p-1.5 rounded-md hover:bg-white/5 hover:text-white disabled:opacity-30"
            @click="next"
          >
            <ChevronRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <div v-else class="bg-white/[0.02] border border-white/5 rounded-xl py-16 text-center">
      <p class="text-sm text-neutral-500">Nenhuma matrícula neste filtro.</p>
    </div>

    <!-- Modal: definir expiração -->
    <AdminModal :open="showExpiry" title="Definir expiração" size="sm" @close="showExpiry = false">
      <form class="space-y-4" @submit.prevent="submitExpiry">
        <p class="text-sm text-neutral-400">
          Aplicar a <span class="text-orange-300 font-medium">{{ selected.size }}</span> matrícula(s) selecionada(s).
        </p>

        <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
          <input v-model="expiryForm.lifetime" type="checkbox" class="accent-orange-500">
          Tornar vitalícia (sem expiração)
        </label>

        <template v-if="!expiryForm.lifetime">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">
              Expira em
            </label>
            <input
              v-model="expiryForm.expires_at"
              type="datetime-local"
              required
              class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
            >
          </div>
        </template>

        <div class="flex justify-end gap-2 pt-2 border-t border-white/5">
          <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="showExpiry = false">
            Cancelar
          </button>
          <button
            type="submit"
            class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          >
            Aplicar
          </button>
        </div>
      </form>
    </AdminModal>
  </div>
</template>
