<template>
  <div class="markdown-renderer" v-if="renderedContent" v-html="renderedContent"></div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import 'highlight.js/styles/github.css'
import hljs from 'highlight.js'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

console.log('MarkdownRenderer props:', props)

// 添加watch监听content变化
watch(() => props.content, (newVal) => {
  console.log('MarkdownRenderer content changed:', newVal)
})

const md = ref<MarkdownIt | null>(null)

onMounted(() => {
  console.log('MarkdownRenderer mounted')
  // 初始化markdown-it
  md.value = new MarkdownIt({
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    },
    breaks: true,
    html: true
  })
})

const renderedContent = computed(() => {
  console.log('MarkdownRenderer content:', props.content)
  if (!md.value) {
    console.log('md not initialized')
    return ''
  }
  try {
    const result = md.value.render(props.content)
    console.log('Rendered HTML:', result)
    return result
  } catch (err) {
    console.error('Markdown rendering error:', err)
    return props.content
  }
})
</script>

<style lang="scss">
.markdown-renderer {
  padding: 0;
  margin: 0;

  h1 {
    font-size: 24px;
    font-weight: 600;
    margin: 0px 0 10px;
    color: #303133;
  }

  h2 {
    font-size: 20px;
    font-weight: 600;
    margin: 18px 0 8px;
    color: #303133;
  }

  h3 {
    font-size: 16px;
    font-weight: 600;
    margin: 16px 0 6px;
    color: #303133;
  }

  p {
    margin: 10px 0;
    line-height: 1.6;
    color: #606266;
  }

  ul, ol {
    margin: 10px 0;
    padding-left: 20px;

    li {
      margin: 5px 0;
      color: #606266;
    }
  }

  strong {
    font-weight: 600;
    color: #303133;
  }

  em {
    font-style: italic;
    color: #606266;
  }

  a {
    color: $primary-color;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  code {
    font-family: 'Courier New', Courier, monospace;
    background-color: #f5f7fa;
    padding: 2px 4px;
    border-radius: 3px;
    font-size: 0.9em;
  }

  pre {
    background-color: #f5f7fa;
    padding: $spacing-md;
    border-radius: $border-radius;
    overflow-x: auto;
    margin: $spacing-md 0;

    code {
      background-color: transparent;
      padding: 0;
    }
  }

  blockquote {
    border-left: 4px solid $primary-color;
    padding-left: $spacing-md;
    margin: $spacing-md 0;
    color: #606266;
    font-style: italic;
  }
}

@media (max-width: 768px) {
  .markdown-renderer {
    padding: $spacing-md;
  }
}
</style>