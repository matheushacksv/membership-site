<script setup lang="ts">
import {
  ChevronDown,
  Pencil,
  Mail,
  Loader2,
  Shield,
  Plus,
  Trash2,
  GraduationCap,
  Infinity as InfinityIcon,
} from 'lucide-vue-next'
import type { AdminCourse, AdminUser, EnrollmentItem } from '~/composables/useAdmin'

const props = defineProps<{
  user: AdminUser
  courses: AdminCourse[]
}>()

const emit = defineEmits<{
  edit: [user: AdminUser]
  resend: [user: AdminUser]
  addEnrollment: [user: AdminUser, excluded: number[]]
  editEnrollment: [enrollment: EnrollmentItem]
}>()

const admin = useAdmin()
const toast = useToast()

const expanded = ref(false)
const loading = ref(false)
const enrollments = ref<EnrollmentItem[]>([])
const revoking = ref<number | null>(null)
const resending = ref(false)

const load = async () => {
  loading.value = true
  try {
    enrollments.value = await admin.listEnrollments({ user_id: props.user.id })
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar matrículas')
  } finally {
    loading.value = false
  }
}

const toggle = async () => {
  expanded.value = !expanded.value
  if (expanded.value && enrollments.value.length === 0) await load()
}

const courseName = (id: number) =>
  props.courses.find((c) => c.id === id)?.name || `#${id}`

const revoke = async (id: number) => {
  if (!confirm('Revogar matrícula?')) return
  revoking.value = id
  try {
    await admin.deleteEnrollment(id)
    enrollments.value = enrollments.value.filter((e) => e.id !== id)
    toast.success('Matrícula revogada')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao revogar')
  } finally {
    revoking.value = null
  }
}

const resend = async () => {
  resending.value = true
  try {
    await admin.resendWelcome(props.user.id)
    toast.success('Email reenviado')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao reenviar')
  } finally {
    resending.value = false
  }
}

const initial = computed(() =>
  (props.user.name || props.user.email).charAt(0).toUpperCase()
)

const fmtDate = (s: string | null) => {
  if (!s) return null
  return new Date(s).toLocaleDateString('pt-BR')
}

const excludedCourseIds = computed(() => enrollments.value.map((e) => e.course_id))

defineExpose({ load })
</script>

<template>
  <div class="border-b border-white/5 last:border-b-0">
    <div
      class="flex items-center gap-3 px-5 py-3 hover:bg-white/[0.02] cursor-pointer"
      @click="toggle"
    >
      <ChevronDown
        class="w-4 h-4 text-neutral-500 transition-transform shrink-0"
        :class="{ 'rotate-180': expanded }"
      />

      <img
        v-if="user.avatar"
        :src="user.avatar"
        class="w-9 h-9 rounded-full object-cover border border-white/10"
      >
      <div
        v-else
        class="w-9 h-9 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-xs font-semibold text-black"
      >
        {{ initial }}
      </div>

      <div class="flex-1 min-w-0">
        <p class="text-sm text-white truncate">{{ user.name || '—' }}</p>
        <p class="text-xs text-neutral-500 truncate">{{ user.email }}</p>
      </div>

      <span
        v-if="user.is_staff"
        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/30 text-[10px] font-bold uppercase tracking-wider text-orange-300 shrink-0"
      >
        <Shield class="w-3 h-3" />
        Staff
      </span>

      <div class="flex items-center gap-1 shrink-0" @click.stop>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-neutral-400 hover:text-white hover:bg-white/5 rounded-md"
          @click="emit('edit', user)"
        >
          <Pencil class="w-3.5 h-3.5" />
          Editar
        </button>
        <button
          type="button"
          :disabled="resending"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-neutral-400 hover:text-orange-300 hover:bg-white/5 rounded-md disabled:opacity-50"
          @click="resend"
        >
          <Loader2 v-if="resending" class="w-3.5 h-3.5 animate-spin" />
          <Mail v-else class="w-3.5 h-3.5" />
          Reenviar
        </button>
      </div>
    </div>

    <div v-if="expanded" class="px-5 pb-4 pt-1 bg-white/[0.015]">
      <div class="flex items-center justify-between mb-2.5 ml-12">
        <h4 class="text-xs font-bold uppercase tracking-wider text-neutral-500 inline-flex items-center gap-1.5">
          <GraduationCap class="w-3.5 h-3.5" />
          Matrículas ({{ enrollments.length }})
        </h4>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-orange-300 hover:text-orange-200 hover:bg-orange-500/10 border border-orange-500/30 rounded-md"
          @click="emit('addEnrollment', user, excludedCourseIds)"
        >
          <Plus class="w-3 h-3" />
          Adicionar curso
        </button>
      </div>

      <div v-if="loading" class="flex justify-center py-4">
        <Loader2 class="w-4 h-4 text-orange-500 animate-spin" />
      </div>

      <div
        v-else-if="enrollments.length"
        class="ml-12 space-y-1.5"
      >
        <div
          v-for="e in enrollments"
          :key="e.id"
          class="flex items-center gap-2 px-3 py-2 rounded-md bg-white/[0.02] border border-white/5"
        >
          <span
            :class="[
              'inline-block w-1.5 h-1.5 rounded-full shrink-0',
              e.is_active ? 'bg-emerald-400' : 'bg-neutral-600',
            ]"
          />
          <span class="flex-1 text-sm text-white truncate">{{ courseName(e.course_id) }}</span>
          <span
            v-if="!e.expires_at"
            class="text-[10px] uppercase tracking-wider text-neutral-500 inline-flex items-center gap-1"
          >
            <InfinityIcon class="w-3 h-3" />
            Vitalícia
          </span>
          <span v-else class="text-[10px] uppercase tracking-wider text-neutral-500">
            Expira {{ fmtDate(e.expires_at) }}
          </span>
          <button
            type="button"
            class="p-1.5 rounded text-neutral-500 hover:text-white"
            @click="emit('editEnrollment', e)"
          >
            <Pencil class="w-3 h-3" />
          </button>
          <button
            type="button"
            :disabled="revoking === e.id"
            class="p-1.5 rounded text-neutral-500 hover:text-red-400 disabled:opacity-50"
            @click="revoke(e.id)"
          >
            <Loader2 v-if="revoking === e.id" class="w-3 h-3 animate-spin" />
            <Trash2 v-else class="w-3 h-3" />
          </button>
        </div>
      </div>

      <p v-else class="ml-12 text-xs text-neutral-600 italic py-2">
        Aluno sem matrículas.
      </p>
    </div>
  </div>
</template>
