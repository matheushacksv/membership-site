export interface Certificate {
  code: string
  course_id: number
  course_name: string
  hours: number | null
  issued_at: string
}

// Dispara o download de um Blob no browser (mesmo padrão do LessonAttachments).
export const saveBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const useCertificates = () => {
  const api = useApi()
  return {
    list: () => api<Certificate[]>('/enrollments/me/certificates'),
    // emite (ou devolve) o certificado; 409 = sem CPF, 403 = incompleto/sem acesso
    issue: (courseId: number) =>
      api<Certificate>(`/enrollments/me/courses/${courseId}/certificate`),
    download: (code: string) =>
      api<Blob>(`/enrollments/me/certificates/${code}/download`, { responseType: 'blob' }),
  }
}
