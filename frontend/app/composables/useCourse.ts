export interface LessonAttachment {
  id: number
  title: string
  file_url: string
  size_bytes: number
}

export interface Lesson {
  id: number
  name: string
  kind: string
  description: string | null
  video_provider: string | null
  video_id: string | null
  duration_seconds: number
  content: string | null
  allow_retake?: boolean
  order: number
  attachments: LessonAttachment[]
  completed: boolean
}

export interface Module {
  id: number
  name: string
  order: number
  is_published: boolean
  locked?: boolean
  lesson_count?: number
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
  comments_enabled: boolean
  certificate_enabled: boolean
  duration_seconds?: number | null
  modules: Module[]
}

export interface CourseProgress {
  total_lessons: number
  completed_count: number
  percent: number
}

export interface FormField {
  key: string
  label: string
  type: 'text' | 'textarea' | 'rating' | 'choice'
  required: boolean
  options: string[]
}

export interface CourseForm {
  id: number
  title: string
  description: string
  fields: FormField[]
  every_days: number
  required: boolean
  is_active: boolean
}

// Quiz (aula de exercício). O aluno recebe as perguntas SEM gabarito antes de responder;
// `correct`/`explanation` só chegam dentro do resultado, corrigido no servidor.
export interface QuizQuestion {
  key: string
  prompt: string
  type: string // 'choice' | 'text' (dissertativa)
  options: string[]
}

export interface QuizResultItem {
  key: string
  type: string
  correct: number
  chosen: number | null
  answer_text: string | null
  explanation: string
}

export interface QuizResult {
  score: number
  total: number
  results: QuizResultItem[]
}

export interface QuizTimer {
  started_at: string
  expires_at: string
  server_now: string
}

export interface QuizState {
  questions: QuizQuestion[]
  attempt: QuizResult | null
  allow_retake: boolean
  time_limit_seconds: number
  timer: QuizTimer | null
  attempts: number
  timed_out: boolean
}

export const useCourse = () => {
  const api = useApi()
  return {
    detail: (id: number) => api<CourseDetail>(`/catalog/courses/${id}`),
    getQuiz: (lessonId: number) =>
      api<QuizState>(`/catalog/lessons/${lessonId}/quiz`),
    startQuiz: (lessonId: number) =>
      api<QuizTimer>(`/catalog/lessons/${lessonId}/quiz/start`, { method: 'POST' }),
    submitQuiz: (
      lessonId: number,
      answers: Record<string, number | string>,
      timed_out = false
    ) =>
      api<QuizResult>(`/catalog/lessons/${lessonId}/quiz`, {
        method: 'POST',
        body: { answers, timed_out },
      }),
    progress: (id: number) => api<CourseProgress>(`/enrollments/me/courses/${id}/progress`),
    markProgress: (lessonId: number, watch_seconds: number, completed: boolean) =>
      api(`/enrollments/me/lessons/${lessonId}/progress`, {
        method: 'POST',
        body: { watch_seconds, completed },
      }),
    dueForm: (id: number) =>
      api<{ form: CourseForm | null }>(`/catalog/courses/${id}/form`),
    submitForm: (
      formId: number,
      body: { answers?: Record<string, unknown>; skipped?: boolean }
    ) => api(`/catalog/forms/${formId}/responses`, { method: 'POST', body }),
    downloadAttachment: (id: number) =>
      api<Blob>(`/catalog/attachments/${id}/download`, { responseType: 'blob' }),
  }
}
