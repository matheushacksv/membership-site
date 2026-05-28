import type { CourseListItem } from '~/composables/useCatalog'

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

export interface AttachmentItem {
  id: number
  title: string
  file_url: string
  size_bytes: number
}

export interface EnrollmentItem {
  id: number
  user_id: number
  course_id: number
  is_active: boolean
  expires_at: string | null
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
    bulkImport: (body: BulkImportBody) =>
      api<BulkImportResult>('/auth/admin/users/bulk-import', {
        method: 'POST',
        body,
      }),

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
  }
}
