import { onMounted, onUnmounted } from 'vue'
import type { useArticlesStore } from '@/stores/articles'

export function useReaderKeyboard(
  articlesStore: ReturnType<typeof useArticlesStore>,
  onClose?: () => void,
) {
  function handler(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement).tagName.toLowerCase()
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return

    const ids = articlesStore.articles.map(a => a.id)
    const current = articlesStore.selectedArticleId
    const idx = current ? ids.indexOf(current) : -1

    switch (e.key) {
      case 'j': {
        const next = ids[idx + 1]
        if (next) articlesStore.selectedArticleId = next
        break
      }
      case 'k': {
        const prev = ids[idx - 1]
        if (prev !== undefined) articlesStore.selectedArticleId = prev
        break
      }
      case 's': {
        if (current) articlesStore.toggleStar(current)
        break
      }
      case 'u': {
        if (current) articlesStore.toggleRead(current)
        break
      }
      case 'o': {
        const article = articlesStore.selectedArticle
        if (article?.url) window.open(article.url, '_blank', 'noopener,noreferrer')
        break
      }
      case 'Escape': {
        articlesStore.selectedArticleId = null
        onClose?.()
        break
      }
    }
  }

  onMounted(() => window.addEventListener('keydown', handler))
  onUnmounted(() => window.removeEventListener('keydown', handler))
}
