<script setup lang="ts">
import { ref } from 'vue'
import { Award, Eraser, Loader2, Pencil, Trash2, Upload } from 'lucide-vue-next'
import type { CertificateConfig } from '~/composables/useAdmin'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Certificado — Admin' })

const admin = useAdmin()
const toast = useToast()

const form = reactive({ signer_name: '', signer_role: '' })
const hasSignature = ref(false)
const previewUrl = ref<string | null>(null)
const saving = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const loadPreview = async () => {
  if (!hasSignature.value) {
    previewUrl.value = null
    return
  }
  try {
    const blob = await admin.certificateSignatureBlob()
    previewUrl.value = URL.createObjectURL(blob)
  } catch {
    previewUrl.value = null
  }
}

const { pending } = await useAsyncData('admin-certificate-config', async () => {
  const cfg = await admin.getCertificateConfig()
  form.signer_name = cfg.signer_name
  form.signer_role = cfg.signer_role
  hasSignature.value = cfg.has_signature
  await loadPreview()
  return cfg
})

const apply = (cfg: CertificateConfig) => {
  form.signer_name = cfg.signer_name
  form.signer_role = cfg.signer_role
  hasSignature.value = cfg.has_signature
}

const save = async () => {
  saving.value = true
  try {
    apply(await admin.saveCertificateConfig({ ...form }))
    toast.success('Configuração salva')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}

const onPickSignature = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (fileInput.value) fileInput.value.value = ''
  if (!file) return
  if (file.type !== 'image/png') {
    toast.error('Envie um PNG com fundo transparente')
    return
  }
  uploading.value = true
  try {
    apply(await admin.uploadCertificateSignature(file))
    await loadPreview()
    toast.success('Assinatura enviada')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao enviar assinatura')
  } finally {
    uploading.value = false
  }
}

const removeSignature = async () => {
  if (!confirm('Remover a assinatura do certificado?')) return
  try {
    apply(await admin.deleteCertificateSignature())
    previewUrl.value = null
    toast.success('Assinatura removida')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao remover')
  }
}

// Desenhar assinatura (canvas) → PNG transparente → mesmo upload
const mode = ref<'draw' | 'upload'>('draw')
const pad = ref<{ clear: () => void; isEmpty: () => boolean; toBlob: () => Promise<Blob | null> } | null>(null)

const saveDrawing = async () => {
  const blob = await pad.value?.toBlob()
  if (!blob) {
    toast.error('Desenhe a assinatura antes de salvar')
    return
  }
  const file = new File([blob], 'assinatura.png', { type: 'image/png' })
  uploading.value = true
  try {
    apply(await admin.uploadCertificateSignature(file))
    await loadPreview()
    pad.value?.clear()
    toast.success('Assinatura salva')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar assinatura')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <div class="flex items-center gap-3 mb-1">
      <Award class="w-5 h-5 text-orange-400" />
      <h1 class="text-2xl font-medium tracking-tight text-white">Certificado</h1>
    </div>
    <p class="text-sm text-neutral-500 mb-8">
      Responsável e assinatura impressos nos certificados de conclusão.
    </p>

    <div v-if="pending" class="flex justify-center py-12">
      <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
    </div>

    <section v-else class="bg-white/[0.02] border border-white/10 rounded-xl p-6 md:p-8 space-y-6">
      <form class="space-y-5" @submit.prevent="save">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Nome do responsável</label>
          <input
            v-model="form.signer_name"
            type="text"
            placeholder="Vazio = nome da marca (Grupo Enriquecedor)"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Cargo</label>
          <input
            v-model="form.signer_role"
            type="text"
            placeholder="Ex.: Coordenação, Diretor"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>
        <div class="flex justify-end">
          <button
            type="submit"
            :disabled="saving"
            class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          >
            <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
            Salvar
          </button>
        </div>
      </form>

      <div class="pt-6 border-t border-white/5">
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Assinatura</label>
        <p class="text-[11px] text-neutral-500 mb-3">
          Desenhe abaixo ou envie um PNG (fundo transparente, traço escuro, ~600×200px, máx 1MB).
          Aparece acima da linha do responsável.
        </p>

        <!-- assinatura atual -->
        <div v-if="previewUrl" class="inline-flex flex-col items-start gap-2 mb-5">
          <div class="p-3 rounded-lg bg-white border border-white/10">
            <img :src="previewUrl" alt="Assinatura" class="max-h-24 max-w-[280px] object-contain">
          </div>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-red-300 hover:text-red-200"
            @click="removeSignature"
          >
            <Trash2 class="w-3.5 h-3.5" />
            Remover
          </button>
        </div>

        <!-- definir / trocar -->
        <p class="text-xs font-bold uppercase tracking-wider text-neutral-500 mb-2">
          {{ previewUrl ? 'Trocar assinatura' : 'Definir assinatura' }}
        </p>
        <div class="inline-flex rounded-lg border border-white/10 overflow-hidden mb-3">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold uppercase tracking-wider"
            :class="mode === 'draw' ? 'bg-orange-500 text-white' : 'text-neutral-400 hover:text-white'"
            @click="mode = 'draw'"
          >
            <Pencil class="w-3.5 h-3.5" />
            Desenhar
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold uppercase tracking-wider"
            :class="mode === 'upload' ? 'bg-orange-500 text-white' : 'text-neutral-400 hover:text-white'"
            @click="mode = 'upload'"
          >
            <Upload class="w-3.5 h-3.5" />
            Enviar PNG
          </button>
        </div>

        <div v-if="mode === 'draw'" class="space-y-2">
          <AdminSignaturePad ref="pad" />
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-bold uppercase tracking-wider text-neutral-300 hover:text-white border border-white/15 rounded-lg"
              @click="pad?.clear()"
            >
              <Eraser class="w-3.5 h-3.5" />
              Limpar
            </button>
            <button
              type="button"
              :disabled="uploading"
              class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
              @click="saveDrawing"
            >
              <Loader2 v-if="uploading" class="w-3.5 h-3.5 animate-spin" />
              Salvar assinatura
            </button>
          </div>
        </div>

        <button
          v-else
          type="button"
          :disabled="uploading"
          class="inline-flex items-center gap-2 px-4 py-3 border border-dashed border-white/15 rounded-lg text-sm text-neutral-300 hover:text-white hover:border-white/25 disabled:opacity-50"
          @click="fileInput?.click()"
        >
          <Loader2 v-if="uploading" class="w-4 h-4 animate-spin" />
          <Upload v-else class="w-4 h-4" />
          Enviar assinatura (PNG)
        </button>

        <input
          ref="fileInput"
          type="file"
          accept="image/png"
          class="hidden"
          @change="onPickSignature"
        >
      </div>
    </section>
  </div>
</template>
