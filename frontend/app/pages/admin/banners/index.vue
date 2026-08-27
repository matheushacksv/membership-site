<script setup lang="ts">
import { Plus, Loader2, Trash2, Eye, EyeOff, ImagePlus, ExternalLink } from 'lucide-vue-next'
import type { BannerItem } from '~/composables/useCatalog'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Banners | Admin' })

// Dimensão recomendada do banner (proporção 4:1). Exibida no modal pra quem faz upload.
const REC_W = 1600
const REC_H = 400

const admin = useAdmin()
const toast = useToast()

const { data: banners, pending, refresh } = await useAsyncData(
  'admin-banners',
  () => admin.listBanners()
)

const showCreate = ref(false)
const creating = ref(false)
const busyId = ref<number | null>(null)

const form = reactive({ title: '', url: '', is_active: true })
const file = ref<File | null>(null)
const preview = ref<string | null>(null)

const resetForm = () => {
  form.title = ''
  form.url = ''
  form.is_active = true
  file.value = null
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = null
}

const onPick = (e: Event) => {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  if (!f.type.match(/^image\/(jpeg|png|webp)$/)) {
    toast.error('Use JPEG, PNG ou WebP')
    return
  }
  if (f.size > 5 * 1024 * 1024) {
    toast.error('Máximo 5MB')
    return
  }
  file.value = f
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = URL.createObjectURL(f)
}

const submit = async () => {
  if (!file.value) {
    toast.error('Escolha uma imagem')
    return
  }
  if (!form.url.startsWith('http://') && !form.url.startsWith('https://')) {
    toast.error('URL deve começar com http:// ou https://')
    return
  }
  creating.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('title', form.title || file.value.name)
    fd.append('url', form.url)
    fd.append('is_active', String(form.is_active))
    await admin.createBanner(fd)
    toast.success('Banner criado')
    showCreate.value = false
    resetForm()
    await refresh()
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao criar banner')
  } finally {
    creating.value = false
  }
}

const toggleActive = async (b: BannerItem) => {
  busyId.value = b.id
  try {
    await admin.updateBanner(b.id, { is_active: !b.is_active })
    await refresh()
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao atualizar')
  } finally {
    busyId.value = null
  }
}

const remove = async (b: BannerItem) => {
  if (!confirm(`Excluir o banner "${b.title}"?`)) return
  busyId.value = b.id
  try {
    await admin.deleteBanner(b.id)
    await refresh()
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao excluir')
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div class="space-y-8">
    <header class="flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-medium tracking-tight">Banners</h1>
        <p class="text-sm text-neutral-500 mt-1">
          Aparecem no topo da área de membros e abrem o link em nova aba
        </p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2.5 bg-orange-500 hover:bg-orange-400 text-white font-bold uppercase tracking-wider text-xs rounded-lg transition-colors"
        @click="showCreate = true"
      >
        <Plus class="w-4 h-4" />
        Novo banner
      </button>
    </header>

    <div v-if="pending" class="flex justify-center py-16">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>

    <div v-else-if="banners?.length" class="space-y-4">
      <div
        v-for="b in banners"
        :key="b.id"
        class="flex items-center gap-4 bg-white/[0.03] border border-white/10 rounded-xl p-3"
      >
        <div class="relative w-48 shrink-0 aspect-[4/1] rounded-lg overflow-hidden bg-neutral-900">
          <img v-if="b.image" :src="b.image" :alt="b.title" class="absolute inset-0 w-full h-full object-cover">
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-white truncate">{{ b.title }}</p>
          <a
            :href="b.url"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1 text-xs text-neutral-500 hover:text-orange-300 truncate max-w-full"
          >
            <ExternalLink class="w-3 h-3 shrink-0" />
            <span class="truncate">{{ b.url }}</span>
          </a>
        </div>
        <button
          type="button"
          :disabled="busyId === b.id"
          :class="[
            'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest border transition-colors disabled:opacity-50',
            b.is_active
              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25'
              : 'bg-black/40 text-neutral-400 border-white/10 hover:bg-white/5',
          ]"
          @click="toggleActive(b)"
        >
          <component :is="b.is_active ? Eye : EyeOff" class="w-3 h-3" />
          {{ b.is_active ? 'Ativo' : 'Inativo' }}
        </button>
        <button
          type="button"
          :disabled="busyId === b.id"
          aria-label="Excluir"
          class="p-2 rounded-lg text-neutral-500 hover:text-red-300 hover:bg-white/5 transition-colors disabled:opacity-50"
          @click="remove(b)"
        >
          <Loader2 v-if="busyId === b.id" class="w-4 h-4 animate-spin" />
          <Trash2 v-else class="w-4 h-4" />
        </button>
      </div>
    </div>

    <div v-else class="bg-white/[0.02] border border-white/5 rounded-xl py-16 text-center">
      <p class="text-sm text-neutral-500">
        Nenhum banner ainda. Clique em <strong>Novo banner</strong> pra começar.
      </p>
    </div>

    <!-- Modal: Novo banner -->
    <AdminModal :open="showCreate" title="Novo banner" @close="showCreate = false">
      <form class="space-y-4" @submit.prevent="submit">
        <!-- Imagem + dimensão recomendada bem destacada -->
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Imagem</label>
          <div
            class="relative aspect-[4/1] rounded-lg border-2 border-dashed border-white/10 hover:border-white/20 overflow-hidden cursor-pointer group bg-white/[0.02]"
            @click="($refs.fileInput as HTMLInputElement)?.click()"
          >
            <img v-if="preview" :src="preview" class="absolute inset-0 w-full h-full object-cover">
            <div
              :class="[
                'absolute inset-0 flex flex-col items-center justify-center gap-1.5 transition-opacity',
                preview ? 'bg-black/60 opacity-0 group-hover:opacity-100' : 'opacity-100',
              ]"
            >
              <ImagePlus class="w-6 h-6 text-neutral-400" />
              <p class="text-xs text-neutral-400">{{ preview ? 'Trocar imagem' : 'Clique pra escolher' }}</p>
            </div>
          </div>
          <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" class="hidden" @change="onPick">
          <p class="mt-2 text-xs text-orange-300/90 bg-orange-500/10 border border-orange-500/20 rounded-md px-3 py-2">
            <strong>Tamanho recomendado: {{ REC_W }}×{{ REC_H }}px</strong> (proporção 4:1, formato largo).
            JPEG, PNG ou WebP, máx 5MB. Imagens fora dessa proporção serão cortadas pra caber.
          </p>
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Título</label>
          <input
            v-model="form.title"
            type="text"
            placeholder="Ex: Promoção Black Friday"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none transition-colors"
          >
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">URL de destino</label>
          <input
            v-model="form.url"
            type="url"
            required
            placeholder="https://..."
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none transition-colors"
          >
        </div>

        <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
          <input v-model="form.is_active" type="checkbox" class="accent-orange-500">
          Ativar agora
        </label>

        <div class="flex justify-end gap-2 pt-4 border-t border-white/5">
          <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="showCreate = false">
            Cancelar
          </button>
          <button
            type="submit"
            :disabled="creating || !file || !form.url"
            class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          >
            <Loader2 v-if="creating" class="w-3.5 h-3.5 animate-spin" />
            Criar banner
          </button>
        </div>
      </form>
    </AdminModal>
  </div>
</template>
