<script setup lang="ts">
import { Plus, Loader2, Search, Upload } from 'lucide-vue-next'
import type { AdminUser, EnrollmentItem } from '~/composables/useAdmin'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Alunos — Admin' })

const admin = useAdmin()

const search = ref('')
const courseFilter = ref<number | null>(null)
const statusFilter = ref<string>('')
const showCreate = ref(false)
const showBulk = ref(false)
const showEdit = ref(false)
const showAddEnrollment = ref(false)
const showEditEnrollment = ref(false)

const editingUser = ref<AdminUser | null>(null)
const targetUser = ref<AdminUser | null>(null)
const targetExcluded = ref<number[]>([])
const editingEnrollment = ref<EnrollmentItem | null>(null)

const { data: users, pending, refresh } = await useAsyncData(
  'admin-users',
  () => admin.listUsers(search.value || undefined),
  { watch: [search] }
)

const { data: courses } = await useAsyncData('admin-courses-light', () =>
  admin.listCourses()
)

const openEdit = (u: AdminUser) => {
  editingUser.value = u
  showEdit.value = true
}

const openAddEnrollment = (u: AdminUser, excluded: number[]) => {
  targetUser.value = u
  targetExcluded.value = excluded
  showAddEnrollment.value = true
}

const openEditEnrollment = (e: EnrollmentItem) => {
  editingEnrollment.value = e
  showEditEnrollment.value = true
}

const rowsRef = ref<Map<number, any>>(new Map())
const setRowRef = (id: number, el: any) => {
  if (el) rowsRef.value.set(id, el)
  else rowsRef.value.delete(id)
}

const reloadRow = (userId: number) => {
  const r = rowsRef.value.get(userId)
  if (r?.load) r.load()
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-3xl font-medium tracking-tight">Alunos</h1>
        <p class="text-sm text-neutral-500 mt-1">
          Clique no aluno para ver matrículas
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold uppercase tracking-wider rounded-lg"
          @click="showBulk = true"
        >
          <Upload class="w-3.5 h-3.5" />
          Importar em massa
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 px-4 py-2.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-bold uppercase tracking-wider rounded-lg"
          @click="showCreate = true"
        >
          <Plus class="w-3.5 h-3.5" />
          Novo aluno
        </button>
      </div>
    </header>

    <div class="flex flex-wrap items-center gap-2">
      <div class="relative flex-1 min-w-[16rem] max-w-sm">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
        <input
          v-model="search"
          type="search"
          :placeholder="courseFilter ? 'Buscar aluno na matrícula...' : 'Buscar por nome ou email...'"
          class="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <select
        v-model.number="courseFilter"
        class="py-2.5 px-3 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none [&>option]:bg-[#0a0a0a] [&>option]:text-white"
      >
        <option :value="null">Todos os cursos</option>
        <option v-for="c in courses || []" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>

      <select
        v-if="courseFilter"
        v-model="statusFilter"
        class="py-2.5 px-3 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none [&>option]:bg-[#0a0a0a] [&>option]:text-white"
      >
        <option value="">Todos os status</option>
        <option value="active">Ativas</option>
        <option value="expired">Expiradas</option>
        <option value="lifetime">Vitalícias</option>
        <option value="inactive">Inativas</option>
      </select>
    </div>

    <!-- Modo gestão em massa: filtrou por curso -->
    <AdminEnrollmentBulkPanel
      v-if="courseFilter"
      :course-id="courseFilter"
      :status="statusFilter"
      :search="search"
      :courses="courses || []"
    />

    <!-- Modo padrão: lista de alunos -->
    <template v-else>
      <div v-if="pending" class="flex justify-center py-16">
        <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
      </div>

      <div
        v-else-if="users?.length"
        class="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden"
      >
        <AdminUserRow
          v-for="u in users"
          :key="u.id"
          :ref="(el) => setRowRef(u.id, el)"
          :user="u"
          :courses="courses || []"
          @edit="openEdit"
          @add-enrollment="openAddEnrollment"
          @edit-enrollment="openEditEnrollment"
          @deleted="refresh()"
        />
      </div>

      <div v-else class="bg-white/[0.02] border border-white/5 rounded-xl py-16 text-center">
        <p class="text-sm text-neutral-500">Nenhum aluno encontrado.</p>
      </div>
    </template>

    <AdminUserCreateModal
      :open="showCreate"
      :courses="courses || []"
      @close="showCreate = false"
      @created="refresh()"
    />
    <AdminUserBulkImportModal
      :open="showBulk"
      :courses="courses || []"
      @close="showBulk = false"
      @done="refresh()"
    />
    <AdminUserEditModal
      :open="showEdit"
      :user="editingUser"
      @close="showEdit = false"
      @saved="refresh()"
    />
    <AdminEnrollmentAddModal
      :open="showAddEnrollment"
      :user="targetUser"
      :courses="courses || []"
      :exclude-course-ids="targetExcluded"
      @close="showAddEnrollment = false"
      @saved="targetUser && reloadRow(targetUser.id)"
    />
    <AdminEnrollmentEditModal
      :open="showEditEnrollment"
      :enrollment="editingEnrollment"
      @close="showEditEnrollment = false"
      @saved="editingEnrollment && reloadRow(editingEnrollment.user_id)"
    />
  </div>
</template>
