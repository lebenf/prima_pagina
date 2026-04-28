<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <section v-if="related.length > 0" class="related-articles">
    <h4 class="related-title">{{ t('article.relatedTitle') }}</h4>
    <div class="related-list">
      <article
        v-for="article in related"
        :key="article.id"
        class="related-item"
        @click="$emit('article-click', article)"
      >
        <div class="related-source">{{ article.feed_title }}</div>
        <h5 class="related-article-title">{{ article.title }}</h5>
        <div class="related-meta">
          <RelativeTime :date="article.published_at ?? ''" />
          <span v-for="tag in article.tags.slice(0, 2)" :key="tag" class="tag">
            {{ tag }}
          </span>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { articlesApi, type Article } from '@/api/articles'
import RelativeTime from '@/components/common/RelativeTime.vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ articleId: string | null }>()
const emit = defineEmits<{ 'article-click': [article: Article] }>()
const { t } = useI18n()

const related = ref<Article[]>([])

watch(
  () => props.articleId,
  async (id) => {
    if (!id) {
      related.value = []
      return
    }
    try {
      const res = await articlesApi.related(id)
      related.value = res.data
    } catch {
      related.value = []
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.related-articles {
  border-top: 2px solid var(--color-border, #e5e7eb);
  margin-top: 2rem;
  padding-top: 1.5rem;
}
.related-title {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-muted, #6b7280);
  margin-bottom: 1rem;
}
.related-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.related-item {
  padding: 0.75rem;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}
.related-item:hover {
  background: var(--color-surface-hover, #f9fafb);
}
.related-source {
  font-size: 0.7rem;
  color: var(--color-primary, #2563eb);
  font-weight: 600;
  margin-bottom: 0.25rem;
}
.related-article-title {
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.3;
  margin: 0 0 0.5rem;
}
.related-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.75rem;
  color: var(--color-text-muted, #6b7280);
}
.tag {
  background: var(--color-surface, #f3f4f6);
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-size: 0.65rem;
}
</style>
