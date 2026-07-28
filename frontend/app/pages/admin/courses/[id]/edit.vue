<script setup lang="ts">
import draggable from 'vuedraggable'
import {
  ArrowLeft,
  Plus,
  Loader2,
  Check,
  Trash2,
  Copy,
  Webhook,
  ClipboardList,
  Gift,
} from 'lucide-vue-next'
import type { CourseInput, ModuleItem } from '~/composables/useAdmin'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const route = useRoute()
const router = useRouter()
const admin = useAdmin()
const toast = useToast()

const courseId = Number(route.params.id)

const { data: course, refresh: refreshCourse } = await useAsyncData(
  `admin-course-${courseId}`,
  async () => {
    const list = await admin.listCourses()
    return list.find((c) => c.id === courseId) || null
  }
)

if (!course.value) {
  await navigateTo('/admin/courses')
}

useHead({ title: () => `Editar ${course.value?.name || ''} — Admin` })

const form = reactive<CourseInput>({
  name: course.value?.name || '',
  category: course.value?.category || 'sales',
  sales_page: course.value?.sales_page || '',
  checkout_link: course.value?.checkout_link || '',
  is_active: course.value?.is_active ?? true,
  kiwify_product_id: course.value?.kiwify_product_id || '',
  access_days: course.value?.access_days ?? null,
  quiz_webhook_url: course.value?.quiz_webhook_url || '',
  is_free: course.value?.is_free ?? false,
  slug: course.value?.slug || '',
  lp_template: course.value?.lp_template || '',
})

const config = useRuntimeConfig()
const api = useApi()
const { data: kiwifyConfig } = await useAsyncData('kiwify-config', () =>
  api<{ token: string }>('/integrations/kiwify/config').catch(() => ({ token: '' }))
)
const webhookUrl = computed(() => {
  const base = (config.public.apiBase as string)?.replace(/\/$/, '') || ''
  const token = kiwifyConfig.value?.token
  const sig = token ? encodeURIComponent(token) : 'SEU_TOKEN'
  return `${base}/integrations/kiwify/webhook?signature=${sig}`
})
const hasToken = computed(() => !!kiwifyConfig.value?.token)
const copied = ref(false)
const copyWebhook = async () => {
  try {
    await navigator.clipboard.writeText(webhookUrl.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    toast.error('Falha ao copiar')
  }
}

// LP de curso gratuito: slug vira /lp/<slug> no MESMO domínio do front (cursos.*).
const slugify = (s: string) =>
  s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
const origin = ref('')
onMounted(() => (origin.value = window.location.origin))
const lpUrl = computed(() => (form.slug ? `${origin.value}/lp/${slugify(form.slug)}` : ''))
const copiedLp = ref(false)
const copyLp = async () => {
  try {
    await navigator.clipboard.writeText(lpUrl.value)
    copiedLp.value = true
    setTimeout(() => (copiedLp.value = false), 1500)
  } catch {
    toast.error('Falha ao copiar')
  }
}

const CATEGORIES = [
  { value: 'sales', label: 'Vendas' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'strategy', label: 'Estratégia' },
  { value: 'tool', label: 'Ferramentas' },
  { value: 'customer', label: 'Customer Success' },
  { value: 'lifestyle', label: 'Estilo de Vida' },
  { value: 'development', label: 'Desenvolvimento' },
]

const savedAt = ref<Date | null>(null)
const saving = ref(false)
let saveTimer: ReturnType<typeof setTimeout> | null = null

const persistCourse = async () => {
  saving.value = true
  try {
    await admin.updateCourse(courseId, {
      name: form.name,
      category: form.category,
      sales_page: form.sales_page || null,
      checkout_link: form.checkout_link || null,
      is_active: form.is_active,
      kiwify_product_id: form.kiwify_product_id || '',
      access_days: form.access_days ?? null,
      quiz_webhook_url: form.quiz_webhook_url || '',
      is_free: form.is_free,
      slug: form.slug ? slugify(form.slug) : null,
      lp_template: form.lp_template || '',
    })
    savedAt.value = new Date()
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}

watch(form, () => {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(persistCourse, 800)
})

// Modules state
const modules = ref<ModuleItem[]>([])
const loadingModules = ref(true)
const newModuleName = ref('')
const creatingModule = ref(false)
const showModuleInput = ref(false)
const modulePickerOpen = ref(false)

const loadModules = async () => {
  loadingModules.value = true
  try {
    modules.value = await admin.listModules(courseId)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar módulos')
  } finally {
    loadingModules.value = false
  }
}

await loadModules()

const createModule = async () => {
  const name = newModuleName.value.trim()
  if (!name) return
  creatingModule.value = true
  try {
    await admin.createModule({
      course_id: courseId,
      name,
      is_published: true,
    })
    newModuleName.value = ''
    showModuleInput.value = false
    await loadModules()
    toast.success('Módulo criado')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao criar módulo')
  } finally {
    creatingModule.value = false
  }
}

const removeModule = async (id: number) => {
  if (!confirm('Deletar este módulo? Todas as aulas serão removidas.')) return
  const prev = modules.value
  modules.value = modules.value.filter((m) => m.id !== id)
  try {
    await admin.deleteModule(id)
    toast.success('Módulo deletado')
  } catch (e: any) {
    modules.value = prev
    toast.error(e?.data?.detail || 'Falha ao deletar')
  }
}

const toggleModulePublish = async (m: ModuleItem) => {
  const next = !m.is_published
  m.is_published = next
  try {
    await admin.updateModule(m.id, { is_published: next })
  } catch {
    m.is_published = !next
    toast.error('Falha ao atualizar')
  }
}

const onModuleReorder = async () => {
  const order = modules.value.map((m) => m.id)
  try {
    await admin.reorderModules(courseId, order)
  } catch {
    toast.error('Falha ao reordenar')
    await loadModules()
  }
}

const onImportModule = async (moduleId: number) => {
  try {
    await admin.copyModule(moduleId, courseId)
    await loadModules()
    toast.success('Módulo importado (despublicado — revise e publique)')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao importar módulo')
  }
}

const deletingCourse = ref(false)
const removeCourse = async () => {
  if (!confirm(`Deletar curso "${form.name}"? Esta ação não pode ser desfeita.`)) return
  deletingCourse.value = true
  try {
    await admin.deleteCourse(courseId)
    toast.success('Curso deletado')
    await navigateTo('/admin/courses')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao deletar')
  } finally {
    deletingCourse.value = false
  }
}

// Lesson edit modal
const editingLessonId = ref<number | null>(null)
const lessonModalOpen = ref(false)
const openLesson = (id: number) => {
  editingLessonId.value = id
  lessonModalOpen.value = true
}

const savedLabel = computed(() => {
  if (saving.value) return 'Salvando...'
  if (!savedAt.value) return ''
  return 'Salvo'
})
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-center gap-3">
      <button
        type="button"
        class="p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5"
        @click="router.back()"
      >
        <ArrowLeft class="w-4 h-4" />
      </button>
      <div class="flex-1">
        <p class="text-xs text-neutral-500 uppercase tracking-widest">Editar curso</p>
        <h1 class="text-2xl font-medium tracking-tight">{{ form.name || 'Sem título' }}</h1>
      </div>
      <span v-if="savedLabel" class="text-xs text-neutral-500 inline-flex items-center gap-1">
        <Loader2 v-if="saving" class="w-3 h-3 animate-spin" />
        <Check v-else class="w-3 h-3 text-emerald-400" />
        {{ savedLabel }}
      </span>
      <NuxtLink
        :to="`/admin/courses/${courseId}/form`"
        class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
      >
        <ClipboardList class="w-3.5 h-3.5" />
        Formulário
      </NuxtLink>
      <button
        type="button"
        :disabled="deletingCourse"
        class="p-2 rounded-lg text-neutral-500 hover:text-red-300 hover:bg-red-500/10 transition-colors disabled:opacity-50"
        title="Deletar curso"
        @click="removeCourse"
      >
        <Trash2 class="w-4 h-4" />
      </button>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <!-- Left: course form -->
      <section class="lg:col-span-2 space-y-5 bg-white/[0.02] border border-white/5 rounded-xl p-6">
        <AdminCourseImageUploader
          :course-id="courseId"
          :current-url="course?.image"
          @uploaded="refreshCourse()"
        />

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Nome</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Categoria</label>
          <select
            v-model="form.category"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
            <option v-for="c in CATEGORIES" :key="c.value" :value="c.value" class="bg-black">
              {{ c.label }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Página de vendas</label>
          <input
            v-model="form.sales_page"
            type="url"
            placeholder="https://..."
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Checkout</label>
          <input
            v-model="form.checkout_link"
            type="url"
            placeholder="https://..."
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
          <input v-model="form.is_active" type="checkbox" class="accent-orange-500">
          Curso publicado
        </label>

        <div class="pt-4 mt-2 border-t border-white/5 space-y-4">
          <div class="flex items-center gap-2">
            <Gift class="w-3.5 h-3.5 text-emerald-400" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-neutral-300">Curso gratuito (LP)</h3>
          </div>

          <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
            <input v-model="form.is_free" type="checkbox" class="accent-orange-500">
            Liberar cadastro por LP pública
          </label>

          <template v-if="form.is_free">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Slug da URL</label>
              <input
                v-model="form.slug"
                type="text"
                placeholder="curso-gratis"
                class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none font-mono"
              >
              <p class="text-[11px] text-neutral-500 mt-1">Só letras, números e hífen — gera a URL pública abaixo.</p>
            </div>

            <div v-if="lpUrl">
              <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">URL da LP</label>
              <div class="flex items-stretch gap-2">
                <code class="flex-1 px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-[11px] text-neutral-300 font-mono truncate">
                  {{ lpUrl }}
                </code>
                <button
                  type="button"
                  class="px-2.5 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-neutral-300"
                  :aria-label="copiedLp ? 'Copiado' : 'Copiar'"
                  @click="copyLp"
                >
                  <Check v-if="copiedLp" class="w-3.5 h-3.5 text-emerald-400" />
                  <Copy v-else class="w-3.5 h-3.5" />
                </button>
              </div>
              <p class="text-[11px] text-neutral-500 mt-1">Compartilhe. Quem se cadastrar ganha acesso a este curso.</p>
            </div>
            <p v-else class="text-[11px] text-amber-400">Defina um slug pra gerar a URL da LP.</p>

            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Template da LP</label>
              <select
                v-model="form.lp_template"
                class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
              >
                <option value="" class="bg-black">Padrão (form simples)</option>
                <option value="closer" class="bg-black">Pré-qualificação SDR e Closer</option>
              </select>
              <p class="text-[11px] text-neutral-500 mt-1">Escolhe o layout da página pública.</p>
            </div>
          </template>
        </div>

        <div class="pt-4 mt-2 border-t border-white/5 space-y-4">
          <div class="flex items-center gap-2">
            <Webhook class="w-3.5 h-3.5 text-orange-400" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-neutral-300">Integração Kiwify</h3>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Kiwify Product ID</label>
            <input
              v-model="form.kiwify_product_id"
              type="text"
              placeholder="acfe6050-4387-..."
              class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none font-mono"
            >
            <p class="text-[11px] text-neutral-500 mt-1">Cole o ID do produto na Kiwify.</p>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Dias de acesso</label>
            <input
              v-model.number="form.access_days"
              type="number"
              min="1"
              placeholder="Vazio = vitalício"
              class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
            >
            <p class="text-[11px] text-neutral-500 mt-1">Quantos dias o aluno terá acesso após a compra.</p>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Webhook ao concluir exercício</label>
            <input
              v-model="form.quiz_webhook_url"
              type="url"
              placeholder="https://... (vazio = desligado)"
              class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none font-mono"
            >
            <p class="text-[11px] text-neutral-500 mt-1">POST com aluno + respostas sempre que um exercício deste curso for finalizado.</p>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">URL do webhook</label>
            <div class="flex items-stretch gap-2">
              <code class="flex-1 px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-[11px] text-neutral-300 font-mono truncate">
                {{ webhookUrl }}
              </code>
              <button
                type="button"
                class="px-2.5 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-neutral-300"
                :aria-label="copied ? 'Copiado' : 'Copiar'"
                @click="copyWebhook"
              >
                <Check v-if="copied" class="w-3.5 h-3.5 text-emerald-400" />
                <Copy v-else class="w-3.5 h-3.5" />
              </button>
            </div>
            <p v-if="hasToken" class="text-[11px] text-neutral-500 mt-1">
              Cole essa URL no painel Kiwify (Webhooks).
            </p>
            <p v-else class="text-[11px] text-amber-400 mt-1">
              Defina <code class="text-orange-300">KIWIFY_WEBHOOK_TOKEN</code> no .env do servidor.
            </p>
          </div>
        </div>
      </section>

      <!-- Right: modules tree -->
      <section class="lg:col-span-3 space-y-3">
        <div class="flex items-end justify-between">
          <div>
            <h2 class="text-lg font-medium tracking-tight">Estrutura</h2>
            <p class="text-xs text-neutral-500 mt-0.5">Arraste pra reordenar</p>
          </div>
        </div>

        <div v-if="loadingModules" class="flex justify-center py-10">
          <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
        </div>

        <template v-else>
          <ClientOnly>
            <draggable
              v-model="modules"
              handle=".module-handle"
              item-key="id"
              ghost-class="opacity-30"
              class="space-y-2"
              @end="onModuleReorder"
            >
              <template #item="{ element }">
                <AdminModuleItem
                  :module="element"
                  @remove="removeModule(element.id)"
                  @toggle-publish="toggleModulePublish(element)"
                  @edit-lesson="openLesson"
                />
              </template>
            </draggable>
            <template #fallback>
              <div class="space-y-2">
                <div
                  v-for="m in modules"
                  :key="m.id"
                  class="px-3 py-3 border border-white/10 rounded-lg bg-white/[0.02] text-sm text-white"
                >
                  {{ m.name }}
                </div>
              </div>
            </template>
          </ClientOnly>

          <div v-if="showModuleInput" class="flex items-center gap-2">
            <input
              v-model="newModuleName"
              type="text"
              placeholder="Nome do módulo..."
              class="flex-1 px-4 py-2.5 bg-white/5 border border-orange-500/40 rounded-lg text-sm text-white focus:outline-none"
              autofocus
              @keydown.enter.prevent="createModule"
              @keydown.escape="(showModuleInput = false), (newModuleName = '')"
            >
            <button
              type="button"
              :disabled="creatingModule"
              class="px-4 py-2.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-bold uppercase rounded-lg disabled:opacity-50"
              @click="createModule"
            >
              <Loader2 v-if="creatingModule" class="w-3.5 h-3.5 animate-spin inline" />
              <span v-else>Adicionar</span>
            </button>
          </div>

          <div v-else class="flex items-center gap-2">
            <button
              type="button"
              class="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-dashed border-white/10 text-sm text-neutral-500 hover:text-orange-300 hover:border-orange-500/40 transition-colors"
              @click="showModuleInput = true"
            >
              <Plus class="w-4 h-4" />
              Novo módulo
            </button>
            <button
              type="button"
              class="flex items-center gap-2 px-4 py-3 rounded-lg border border-dashed border-white/10 text-sm text-neutral-500 hover:text-orange-300 hover:border-orange-500/40 transition-colors"
              @click="modulePickerOpen = true"
            >
              <Copy class="w-4 h-4" />
              Importar módulo
            </button>
          </div>
        </template>
      </section>
    </div>

    <AdminModulePickerModal
      :open="modulePickerOpen"
      :exclude-course-id="courseId"
      @close="modulePickerOpen = false"
      @pick="onImportModule"
    />

    <AdminLessonEditModal
      :open="lessonModalOpen"
      :lesson-id="editingLessonId"
      @close="lessonModalOpen = false"
      @saved="() => {}"
    />
  </div>
</template>
