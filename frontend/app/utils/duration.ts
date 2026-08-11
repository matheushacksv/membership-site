// Duração TOTAL de um curso (soma de segundos) → "3h 20min" / "45min".
// Formato de curso, não de aula: o fmtDuration de LessonNavItem é m:ss/m min.
// < 60s (ou vazio/None) → '' pra esconder a linha no template.
export const formatCourseDuration = (s?: number | null): string => {
  if (!s || s < 60) return ''
  const h = Math.floor(s / 3600)
  const m = Math.round((s % 3600) / 60)
  if (h && m) return `${h}h ${m}min`
  return h ? `${h}h` : `${m}min`
}
