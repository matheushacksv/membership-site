export interface CourseListItem {
  id: number
  name: string
  image: string | null
  category: string
  is_active: boolean
  sales_page?: string | null
  checkout_link?: string | null
  kiwify_product_id?: string
  access_days?: number | null
  total_lessons?: number | null
  completed_lessons?: number | null
  resume_lesson_id?: number | null
}

export interface BannerItem {
  id: number
  title: string
  image: string | null
  url: string
  is_active: boolean
}

export const useCatalog = () => {
  const api = useApi()

  const myCourses = () => api<CourseListItem[]>('/catalog/courses')

  const availableCourses = (category?: string) =>
    api<CourseListItem[]>('/catalog/courses/available', {
      query: category ? { category } : {},
    })

  const banners = () => api<BannerItem[]>('/catalog/banners')

  return { myCourses, availableCourses, banners }
}
