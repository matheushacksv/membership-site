<script setup lang="ts">
import { BadgeCheck, ShieldX } from 'lucide-vue-next'

definePageMeta({ layout: false })

interface VerifyOut {
  code: string
  student_name: string
  student_cpf: string
  course_name: string
  hours: number | null
  issued_at: string
}

const route = useRoute()
const api = useApi()
const code = String(route.params.code || '')

useHead({ title: 'Verificação de certificado | Grupo Enriquecedor' })

const { data: cert, error } = await useAsyncData(`verify-${code}`, () =>
  api<VerifyOut>(`/enrollments/verify/${encodeURIComponent(code)}`),
)

const fmtDate = (iso: string) => new Date(iso).toLocaleDateString('pt-BR')
</script>

<template>
  <div class="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="flex justify-center mb-6">
        <AppLogo />
      </div>

      <!-- Válido -->
      <div
        v-if="cert"
        class="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.06] overflow-hidden"
      >
        <div class="flex items-center gap-3 px-6 py-5 border-b border-emerald-500/20">
          <BadgeCheck class="w-8 h-8 text-emerald-400 shrink-0" />
          <div>
            <p class="text-lg font-semibold text-white">Certificado válido</p>
            <p class="text-xs text-emerald-300/80">Autenticidade confirmada</p>
          </div>
        </div>
        <dl class="px-6 py-5 space-y-3 text-sm">
          <div>
            <dt class="text-[11px] uppercase tracking-wider text-neutral-500">Aluno</dt>
            <dd class="text-white font-medium">{{ cert.student_name }}</dd>
          </div>
          <div>
            <dt class="text-[11px] uppercase tracking-wider text-neutral-500">CPF</dt>
            <dd class="text-neutral-300">{{ cert.student_cpf }}</dd>
          </div>
          <div>
            <dt class="text-[11px] uppercase tracking-wider text-neutral-500">Curso</dt>
            <dd class="text-white">{{ cert.course_name }}</dd>
          </div>
          <div class="flex gap-8">
            <div v-if="cert.hours">
              <dt class="text-[11px] uppercase tracking-wider text-neutral-500">Carga horária</dt>
              <dd class="text-neutral-300">{{ cert.hours }} horas</dd>
            </div>
            <div>
              <dt class="text-[11px] uppercase tracking-wider text-neutral-500">Emissão</dt>
              <dd class="text-neutral-300">{{ fmtDate(cert.issued_at) }}</dd>
            </div>
          </div>
          <div>
            <dt class="text-[11px] uppercase tracking-wider text-neutral-500">Código</dt>
            <dd class="text-neutral-400 font-mono text-xs">{{ cert.code }}</dd>
          </div>
        </dl>
      </div>

      <!-- Inválido / não encontrado -->
      <div
        v-else
        class="rounded-2xl border border-red-500/30 bg-red-500/[0.06] px-6 py-8 text-center"
      >
        <ShieldX class="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p class="text-lg font-semibold text-white">Certificado não encontrado</p>
        <p class="text-sm text-neutral-400 mt-1">
          O código <span class="font-mono text-neutral-300">{{ code }}</span> não corresponde a
          nenhum certificado emitido.
        </p>
      </div>

      <p class="text-center text-[11px] text-neutral-600 mt-6">
        Grupo Enriquecedor · Verificação pública de certificados
      </p>
    </div>
  </div>
</template>
