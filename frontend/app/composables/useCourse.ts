export interface LessonAttachment {
  id: number
  title: string
  file_url: string
  size_bytes: number
}

export interface Lesson {
  id: number
  name: string
  description: string | null
  video_provider: string | null
  video_id: string | null
  duration_seconds: number
  content: string | null
  order: number
  attachments: LessonAttachment[]
  completed: boolean
}

export interface Module {
  id: number
  name: string
  order: number
  is_published: boolean
  lessons: Lesson[]
}

export interface CourseDetail {
  id: number
  name: string
  image: string | null
  category: string
  is_active: boolean
  sales_page: string | null
  checkout_link: string | null
  modules: Module[]
}

export interface CourseProgress {
  total_lessons: number
  completed_count: number
  percent: number
}

export const useCourse = () => {
  const api = useApi()
  return {
    detail: (id: number) => api<CourseDetail>(`/catalog/courses/${id}`),
    progress: (id: number) => api<CourseProgress>(`/enrollments/me/courses/${id}/progress`),
    markProgress: (lessonId: number, watch_seconds: number, completed: boolean) =>
      api(`/enrollments/me/lessons/${lessonId}/progress`, {
        method: 'POST',
        body: { watch_seconds, completed },
      }),
  }
}
