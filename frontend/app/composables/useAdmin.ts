import type { BannerItem, CourseListItem } from '~/composables/useCatalog'

export interface AdminCourse extends CourseListItem {
  created_at?: string
  updated_at?: string
}

export interface CourseInput {
  name: string
  category: string
  sales_page?: string | null
  checkout_link?: string | null
  is_active?: boolean
  image?: string | null
  kiwify_product_id?: string
  access_days?: number | null
}

export interface ModuleItem {
  id: number
  course_id: number
  name: string
  order: number
  is_published: boolean
}

export interface ModuleInput {
  course_id: number
  name: string
  order?: number
  is_published?: boolean
}

export interface LessonItem {
  id: number
  module_id: number
  name: string
  kind?: 'video' | 'quiz'
  description?: string | null
  video_provider?: string | null
  video_id?: string | null
  content?: string | null
  order: number
  is_published: boolean
}

export interface LessonInput {
  module_id: number
  name: string
  kind?: 'video' | 'quiz'
  description?: string | null
  video_provider?: string | null
  video_id?: string | null
  content?: string | null
  order?: number
  is_published?: boolean
}

export interface AdminUser {
  id: number
  name: string | null
  email: string
  avatar: string | null
  is_staff: boolean
}

export interface StaffCreateUserBody {
  email: string
  name?: string | null
  course_ids?: number[]
}

export interface BulkImportBody {
  users: { email: string; name?: string | null }[]
  course_ids?: number[]
  send_welcome?: boolean
}

export interface BulkImportResult {
  created: number
  existing: number
  enrolled: number
  errors: string[]
}

export interface BulkImportQueued {
  task_id: string
  total: number
  chunks: number
}

export interface BulkImportStatus {
  status: 'pending' | 'done' | 'failed'
  result: BulkImportResult | null
}

export interface AttachmentItem {
  id: number
  title: string
  file_url: string
  size_bytes: number
}

export interface AttachmentLibraryItem extends AttachmentItem {
  lesson_name: string
  course_name: string
}

// Pergunta completa (com gabarito) — só trafega em rota staff.
export interface AdminQuizQuestion {
  key?: string
  prompt: string
  options: string[]
  correct: number
  explanation: string
}

export interface QuizResponseRow {
  user_name: string | null
  user_email: string
  score: number
  total: number
  answers: Record<string, number>
  updated_at: string
}

export interface EnrollmentItem {
  id: number
  user_id: number
  course_id: number
  is_active: boolean
  expires_at: string | null
  created_at: string
}

export type EnrollmentStatus = 'active' | 'inactive' | 'expired' | 'lifetime'

export interface EnrollmentAdminItem {
  id: number
  user_id: number
  user_name: string | null
  user_email: string
  course_id: number
  course_name: string
  expires_at: string | null
  is_active: boolean
  enrolled_at: string
}

export interface EnrollmentAdminPage {
  total: number
  items: EnrollmentAdminItem[]
}

export interface EnrollmentAdminFilters {
  course_id?: number
  status?: EnrollmentStatus
  search?: string
  limit?: number
  offset?: number
}

export type BulkEnrollmentAction =
  | 'set_expiry'
  | 'apply_course_days'
  | 'delete'
  | 'set_active'

export interface BulkEnrollmentBody {
  enrollment_ids: number[]
  action: BulkEnrollmentAction
  expires_at?: string | null
  is_active?: boolean
}

export interface AdminFormField {
  key?: string
  label: string
  type: 'text' | 'textarea' | 'rating' | 'choice'
  required: boolean
  options: string[]
}

export interface AdminCourseForm {
  id?: number
  title: string
  description: string
  fields: AdminFormField[]
  every_days: number
  required: boolean
  is_active: boolean
}

export interface FormResponseRow {
  id: number
  user_name: string | null
  user_email: string
  answers: Record<string, unknown>
  created_at: string
}

export const useAdmin = () => {
  const api = useApi()

  return {
    // Courses
    listCourses: () => api<AdminCourse[]>('/admin/courses'),
    createCourse: (body: CourseInput) =>
      api<AdminCourse>('/admin/courses', { method: 'POST', body }),
    updateCourse: (id: number, body: Partial<CourseInput>) =>
      api<AdminCourse>(`/admin/courses/${id}`, { method: 'PUT', body }),
    deleteCourse: (id: number) =>
      api(`/admin/courses/${id}`, { method: 'DELETE' }),
    uploadCourseImage: (id: number, file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return api<AdminCourse>(`/admin/courses/${id}/image`, {
        method: 'POST',
        body: fd,
      })
    },

    // Modules
    listModules: (course_id: number) =>
      api<ModuleItem[]>('/admin/modules', { query: { course_id } }),
    createModule: (body: ModuleInput) =>
      api<ModuleItem>('/admin/modules', { method: 'POST', body }),
    updateModule: (id: number, body: Partial<ModuleInput>) =>
      api<ModuleItem>(`/admin/modules/${id}`, { method: 'PUT', body }),
    deleteModule: (id: number) =>
      api(`/admin/modules/${id}`, { method: 'DELETE' }),
    reorderModules: (course_id: number, order: number[]) =>
      api(`/admin/courses/${course_id}/modules/reorder`, {
        method: 'PATCH',
        body: order,
      }),

    // Lessons
    listLessons: (module_id: number) =>
      api<LessonItem[]>('/admin/lessons', { query: { module_id } }),
    getLesson: (id: number) => api<LessonItem>(`/admin/lessons/${id}`),
    createLesson: (body: LessonInput) =>
      api<LessonItem>('/admin/lessons', { method: 'POST', body }),
    updateLesson: (id: number, body: Partial<LessonInput>) =>
      api<LessonItem>(`/admin/lessons/${id}`, { method: 'PUT', body }),
    deleteLesson: (id: number) =>
      api(`/admin/lessons/${id}`, { method: 'DELETE' }),
    reorderLessons: (module_id: number, order: number[]) =>
      api(`/admin/modules/${module_id}/lessons/reorder`, {
        method: 'PATCH',
        body: order,
      }),

    // Quiz (aula de exercício)
    getLessonQuiz: (lesson_id: number) =>
      api<AdminQuizQuestion[]>(`/admin/lessons/${lesson_id}/quiz`),
    saveLessonQuiz: (lesson_id: number, questions: AdminQuizQuestion[]) =>
      api<AdminQuizQuestion[]>(`/admin/lessons/${lesson_id}/quiz`, {
        method: 'PUT',
        body: { questions },
      }),
    listQuizResponses: (lesson_id: number) =>
      api<QuizResponseRow[]>(`/admin/lessons/${lesson_id}/quiz/responses`),

    // Attachments
    listAttachments: (lesson_id: number) =>
      api<AttachmentItem[]>(`/admin/lessons/${lesson_id}/attachments`),
    uploadAttachment: (lesson_id: number, file: File, title?: string) => {
      const fd = new FormData()
      fd.append('file', file)
      if (title) fd.append('title', title)
      return api<AttachmentItem>(
        `/admin/lessons/${lesson_id}/attachments/upload`,
        { method: 'POST', body: fd }
      )
    },
    deleteAttachment: (id: number) =>
      api(`/admin/attachments/${id}`, { method: 'DELETE' }),
    listAttachmentLibrary: (q = '') =>
      api<AttachmentLibraryItem[]>('/admin/attachments', { query: { q } }),
    linkAttachment: (lesson_id: number, attachment_id: number) =>
      api<AttachmentItem>(`/admin/lessons/${lesson_id}/attachments/link`, {
        method: 'POST',
        body: { attachment_id },
      }),

    // Users
    listUsers: (search?: string) =>
      api<AdminUser[]>('/auth/admin/users', {
        query: search ? { search } : {},
      }),
    createUser: (body: StaffCreateUserBody) =>
      api<AdminUser>('/auth/admin/users', { method: 'POST', body }),
    updateUser: (id: number, body: { name?: string; email?: string }) =>
      api<AdminUser>(`/auth/admin/users/${id}`, { method: 'PUT', body }),
    resendWelcome: (id: number) =>
      api<{ detail: string }>(`/auth/admin/users/${id}/resend-welcome`, {
        method: 'POST',
      }),
    // Importação roda no worker (sem timeout HTTP): POST enfileira e responde na
    // hora; aqui fazemos poll do status até terminar. Escala pra qualquer tamanho.
    bulkImport: async (body: BulkImportBody): Promise<BulkImportResult> => {
      const queued = await api<BulkImportQueued>('/auth/admin/users/bulk-import', {
        method: 'POST',
        body,
      })
      const started = Date.now()
      const TIMEOUT_MS = 10 * 60 * 1000
      while (true) {
        await new Promise((r) => setTimeout(r, 2000))
        const s = await api<BulkImportStatus>(
          `/auth/admin/users/bulk-import/${queued.task_id}`,
          { query: { chunks: queued.chunks } },
        )
        if (s.status === 'done' && s.result) return s.result
        if (s.status === 'failed') throw new Error('Falha no processamento da importação')
        if (Date.now() - started > TIMEOUT_MS) {
          throw new Error('Importação ainda processando; confira a lista em instantes')
        }
      }
    },

    // Enrollments
    listEnrollments: (filters?: { course_id?: number; user_id?: number }) =>
      api<EnrollmentItem[]>('/enrollments/enrollments', {
        query: filters || {},
      }),
    createEnrollment: (body: {
      user_id: number
      course_id: number
      expires_at?: string | null
      is_active?: boolean
    }) =>
      api<EnrollmentItem>('/enrollments/enrollments', { method: 'POST', body }),
    updateEnrollment: (
      id: number,
      body: { expires_at?: string | null; is_active?: boolean }
    ) =>
      api<EnrollmentItem>(`/enrollments/enrollments/${id}`, {
        method: 'PUT',
        body,
      }),
    deleteEnrollment: (id: number) =>
      api(`/enrollments/enrollments/${id}`, { method: 'DELETE' }),

    // Gestão em massa (centrada em curso): lista paginada + ids do filtro + ação bulk
    listEnrollmentsAdmin: (filters: EnrollmentAdminFilters) =>
      api<EnrollmentAdminPage>('/enrollments/admin', { query: filters }),
    enrollmentIds: (filters: Omit<EnrollmentAdminFilters, 'limit' | 'offset'>) =>
      api<number[]>('/enrollments/admin/ids', { query: filters }),
    bulkEnrollments: (body: BulkEnrollmentBody) =>
      api<{ affected: number }>('/enrollments/bulk', { method: 'POST', body }),

    // Course form (smart form recorrente)
    getCourseForm: (course_id: number) =>
      api<{ form: AdminCourseForm | null }>(`/admin/courses/${course_id}/form`),
    saveCourseForm: (course_id: number, body: AdminCourseForm) =>
      api<AdminCourseForm>(`/admin/courses/${course_id}/form`, { method: 'PUT', body }),
    listFormResponses: (course_id: number) =>
      api<FormResponseRow[]>(`/admin/courses/${course_id}/form/responses`),

    // Banners
    listBanners: () => api<BannerItem[]>('/admin/banners'),
    createBanner: (fd: FormData) =>
      api<BannerItem>('/admin/banners', { method: 'POST', body: fd }),
    updateBanner: (
      id: number,
      body: Partial<Pick<BannerItem, 'title' | 'url' | 'is_active'>>
    ) => api<BannerItem>(`/admin/banners/${id}`, { method: 'PUT', body }),
    deleteBanner: (id: number) =>
      api(`/admin/banners/${id}`, { method: 'DELETE' }),
  }
}
