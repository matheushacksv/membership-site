<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Award, Camera, Download, Loader2 } from 'lucide-vue-next'
import { saveBlob, useCertificates, type Certificate } from '~/composables/useCertificates'

definePageMeta({ layout: 'default' })
useHead({ title: 'Perfil | Grupo Enriquecedor' })

const { data: me, refresh } = useMe()
const { update, uploadAvatar } = useProfile()
const certApi = useCertificates()
const toast = useToast()

const ACCEPTED_MIME = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
const MAX_AVATAR_BYTES = 2 * 1024 * 1024

// avatar
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const avatarPreview = ref<string | null>(null)

const previewSrc = computed(() => avatarPreview.value || me.value?.avatar || null)
const initial = computed(() => {
  const s = me.value?.name || me.value?.email || ''
  return s.charAt(0).toUpperCase() || '?'
})

const triggerAvatar = () => avatarInput.value?.click()

const onAvatarChange = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  if (!ACCEPTED_MIME.includes(file.type)) {
    toast.error('Formato não suportado. Use JPG, PNG, GIF ou WEBP.')
    return
  }
  if (file.size > MAX_AVATAR_BYTES) {
    toast.error('Imagem maior que 2MB.')
    return
  }

  const localUrl = URL.createObjectURL(file)
  avatarPreview.value = localUrl
  avatarUploading.value = true
  try {
    await uploadAvatar(file)
    await refresh()
    toast.success('Avatar atualizado')
  } catch (err: any) {
    toast.error(err?.data?.detail || 'Falha ao enviar avatar')
    avatarPreview.value = null
  } finally {
    URL.revokeObjectURL(localUrl)
    avatarUploading.value = false
  }
}

// dados pessoais
const form = ref({ name: '', phone: '', cpf: '' })
const savingProfile = ref(false)

const syncForm = () => {
  form.value.name = me.value?.name || ''
  form.value.phone = me.value?.phone || ''
  form.value.cpf = me.value?.cpf || ''
}
watch(me, syncForm, { immediate: true })

const dirty = computed(() => {
  const n = (me.value?.name || '') !== form.value.name.trim()
  const p = (me.value?.phone || '') !== form.value.phone.trim()
  const c = (me.value?.cpf || '') !== form.value.cpf.trim()
  return n || p || c
})

const saveProfile = async () => {
  if (!dirty.value) return
  savingProfile.value = true
  try {
    await update({
      name: form.value.name.trim(),
      phone: form.value.phone.trim() || null,
      cpf: form.value.cpf.trim(),
    })
    await refresh()
    toast.success('Dados atualizados')
  } catch (err: any) {
    toast.error(err?.data?.detail || 'Falha ao salvar')
  } finally {
    savingProfile.value = false
  }
}

// meus certificados
const certificates = ref<Certificate[]>([])
const certDownloading = ref<string | null>(null)
const fmtDate = (iso: string) => new Date(iso).toLocaleDateString('pt-BR')

onMounted(async () => {
  try {
    certificates.value = await certApi.list()
  } catch { /* silencioso */ }
})

const downloadCert = async (cert: Certificate) => {
  certDownloading.value = cert.code
  try {
    const blob = await certApi.download(cert.code)
    saveBlob(blob, `certificado-${cert.code}.pdf`)
  } catch (err: any) {
    toast.error(err?.data?.detail || 'Falha ao baixar certificado')
  } finally {
    certDownloading.value = null
  }
}

// senha
const pwd = ref({ current: '', next: '', confirm: '' })
const pwdErrors = ref<{ current?: string; next?: string; confirm?: string }>({})
const savingPwd = ref(false)

const validatePwd = () => {
  const e: typeof pwdErrors.value = {}
  if (!pwd.value.current) e.current = 'Informe a senha atual'
  if (pwd.value.next.length < 8) e.next = 'Mínimo 8 caracteres'
  if (pwd.value.next !== pwd.value.confirm) e.confirm = 'As senhas não conferem'
  pwdErrors.value = e
  return Object.keys(e).length === 0
}

const changePassword = async () => {
  if (!validatePwd()) return
  savingPwd.value = true
  try {
    await update({
      current_password: pwd.value.current,
      new_password: pwd.value.next,
    })
    pwd.value = { current: '', next: '', confirm: '' }
    pwdErrors.value = {}
    toast.success('Senha alterada')
  } catch (err: any) {
    toast.error(err?.data?.detail || 'Falha ao alterar senha')
  } finally {
    savingPwd.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <header class="mb-2">
      <h1 class="text-3xl md:text-4xl font-medium tracking-tighter">Perfil</h1>
      <p class="text-sm text-neutral-500 mt-1">Gerencie suas informações de conta.</p>
    </header>

    <!-- Avatar -->
    <section class="bg-white/5 border border-white/10 rounded-xl p-6">
      <div class="flex flex-col sm:flex-row sm:items-center gap-5">
        <div class="relative">
          <img
            v-if="previewSrc"
            :src="previewSrc"
            alt="Avatar"
            class="w-24 h-24 rounded-full object-cover border border-white/10"
          >
          <div
            v-else
            class="w-24 h-24 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-3xl font-semibold text-white"
          >
            {{ initial }}
          </div>
          <div
            v-if="avatarUploading"
            class="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center"
          >
            <Loader2 class="w-5 h-5 text-white animate-spin" />
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <p class="text-base font-medium text-white truncate">{{ me?.name || 'Sem nome' }}</p>
          <p class="text-sm text-neutral-500 truncate">{{ me?.email }}</p>
          <input
            ref="avatarInput"
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            class="hidden"
            @change="onAvatarChange"
          >
          <button
            type="button"
            class="mt-3 inline-flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-200 disabled:opacity-50"
            :disabled="avatarUploading"
            @click="triggerAvatar"
          >
            <Camera class="w-3.5 h-3.5" />
            Trocar foto
          </button>
          <p class="text-[11px] text-neutral-600 mt-2">JPG, PNG, GIF ou WEBP. Máx 2MB.</p>
        </div>
      </div>
    </section>

    <!-- Dados pessoais -->
    <section class="bg-white/5 border border-white/10 rounded-xl p-6">
      <h2 class="text-lg font-medium tracking-tight mb-4">Dados pessoais</h2>
      <form class="space-y-4" @submit.prevent="saveProfile">
        <AppInput
          v-model="form.name"
          icon="user"
          label="Nome"
          placeholder="Seu nome"
          autocomplete="name"
        />
        <AppInput
          v-model="form.phone"
          label="Telefone"
          placeholder="(11) 99999-9999"
          autocomplete="tel"
        />
        <div>
          <AppInput
            v-model="form.cpf"
            label="CPF"
            placeholder="Somente números"
          />
          <p class="mt-1 text-[11px] text-neutral-600">Usado para emitir os certificados de conclusão.</p>
        </div>
        <label class="block">
          <span class="block text-xs font-medium tracking-wider uppercase text-neutral-400 mb-2">Email</span>
          <input
            :value="me?.email || ''"
            type="email"
            disabled
            class="w-full bg-white/[0.03] border border-white/5 rounded-lg py-3 px-4 text-sm text-neutral-500 cursor-not-allowed"
          >
          <p class="mt-1 text-[11px] text-neutral-600">O email não pode ser alterado.</p>
        </label>
        <div class="pt-2">
          <PrimaryButton
            type="submit"
            :loading="savingProfile"
            :disabled="!dirty"
            :show-arrow="false"
          >
            Salvar alterações
          </PrimaryButton>
        </div>
      </form>
    </section>

    <!-- Senha -->
    <section class="bg-white/5 border border-white/10 rounded-xl p-6">
      <h2 class="text-lg font-medium tracking-tight mb-4">Alterar senha</h2>
      <form class="space-y-4" @submit.prevent="changePassword">
        <AppInput
          v-model="pwd.current"
          type="password"
          icon="lock"
          label="Senha atual"
          autocomplete="current-password"
          :error="pwdErrors.current"
        />
        <AppInput
          v-model="pwd.next"
          type="password"
          icon="lock"
          label="Nova senha"
          autocomplete="new-password"
          :error="pwdErrors.next"
        />
        <AppInput
          v-model="pwd.confirm"
          type="password"
          icon="lock"
          label="Confirmar nova senha"
          autocomplete="new-password"
          :error="pwdErrors.confirm"
        />
        <div class="pt-2">
          <PrimaryButton
            type="submit"
            :loading="savingPwd"
            :show-arrow="false"
          >
            Alterar senha
          </PrimaryButton>
        </div>
      </form>
    </section>

    <!-- Meus certificados -->
    <section class="bg-white/5 border border-white/10 rounded-xl p-6">
      <h2 class="text-lg font-medium tracking-tight mb-4 flex items-center gap-2">
        <Award class="w-5 h-5 text-emerald-400" />
        Meus certificados
      </h2>
      <p v-if="!certificates.length" class="text-sm text-neutral-500">
        Conclua 100% de um curso com certificado para emitir o seu.
      </p>
      <ul v-else class="space-y-2">
        <li
          v-for="cert in certificates"
          :key="cert.code"
          class="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-white truncate">{{ cert.course_name }}</p>
            <p class="text-[11px] text-neutral-500 mt-0.5">
              Emitido em {{ fmtDate(cert.issued_at) }}<span v-if="cert.hours"> · {{ cert.hours }}h</span>
            </p>
          </div>
          <button
            type="button"
            :disabled="certDownloading === cert.code"
            class="shrink-0 inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-bold uppercase tracking-wider disabled:opacity-50"
            @click="downloadCert(cert)"
          >
            <Loader2 v-if="certDownloading === cert.code" class="w-3.5 h-3.5 animate-spin" />
            <Download v-else class="w-3.5 h-3.5" />
            Baixar
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>
