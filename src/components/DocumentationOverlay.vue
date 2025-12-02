<template>
  <transition name="fade">
    <div v-if="show" class="doc-overlay">
      <v-card class="doc-card" elevation="12">
        <div class="doc-card-header">
          <div class="doc-card-tabs">
            <button
              v-for="(tab, index) in docData?.tabs || []"
              :key="index"
              :class="['doc-tab', { active: activeTab === index }]"
              @click="activeTab = index"
            >
              {{ tab.name }}
            </button>
          </div>
          <v-btn icon class="doc-close-btn" @click="$emit('close')">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <div class="doc-card-body">
          <div v-for="(tab, index) in docData?.tabs || []" :key="index" v-show="activeTab === index">
            <template v-for="(section, sIdx) in tab.content.sections" :key="sIdx">
            <template v-for="(item, iIdx) in section.content || []" :key="iIdx">
              <h3 v-if="item.type === 'heading'" v-html="item.text"></h3>
              <h4 v-else-if="item.type === 'subheading'" v-html="item.text"></h4>
              <p v-else-if="item.type === 'paragraph'" v-html="item.text"></p>
              <ul v-else-if="item.type === 'list'">
                <li v-for="(listItem, lIdx) in item.items" :key="lIdx" v-html="listItem"></li>
              </ul>
              <div v-else-if="item.type === 'image'" class="doc-image-container">
                <img
                  :src="item.src"
                  :alt="item.alt || 'Documentation image'"
                  class="doc-image"
                  :style="item.size ? { width: item.size, maxWidth: '100%' } : {}"
                />
                <p v-if="item.caption" class="doc-image-caption">{{ item.caption }}</p>
              </div>
            </template>
            </template>
          </div>
        </div>
      </v-card>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from 'vue'
import documentationData from '../data/documentation.json'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  toolId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['close'])

const activeTab = ref(0)
const docData = ref(null)

watch(
  () => props.toolId,
  (newToolId) => {
    if (newToolId && documentationData[newToolId]) {
      docData.value = documentationData[newToolId]
      activeTab.value = 0
    } else {
      docData.value = null
    }
  },
  { immediate: true }
)

watch(
  () => props.show,
  (newShow) => {
    if (newShow) {
      activeTab.value = 0
    }
  }
)
</script>

<style scoped>
/* Documentation overlay */
.doc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
  display: grid;
  place-items: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.doc-card {
  width: min(920px, 94vw);
  height: 75vh;
  background: rgba(255, 255, 255, 0.98);
  -webkit-backdrop-filter: blur(16px);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
  display: flex;
  flex-direction: column;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.doc-card-header {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(20, 93, 160, 0.15);
}

.doc-card-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.doc-tab {
  background: rgba(20, 93, 160, 0.08);
  color: #0a2342;
  border: 1px solid rgba(20, 93, 160, 0.25);
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.doc-tab:hover {
  background: rgba(20, 93, 160, 0.15);
  border-color: rgba(20, 93, 160, 0.4);
  transform: translateY(-1px);
}

.doc-tab.active {
  background: linear-gradient(135deg, #145da0, #21ce99);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(20, 93, 160, 0.3);
}

.doc-close-btn {
  background: rgba(255, 255, 255, 0.9);
  color: #0a2342;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.doc-close-btn:hover {
  background: rgba(255, 255, 255, 1);
  transform: rotate(90deg);
}

.doc-card-body {
  flex: 1 1 auto;
  padding: 1.5rem 1.5rem 1.25rem;
  color: #0a2342;
  overflow-y: auto;
  line-height: 1.7;
}

.doc-card-body::-webkit-scrollbar {
  width: 8px;
}

.doc-card-body::-webkit-scrollbar-track {
  background: rgba(20, 93, 160, 0.05);
  border-radius: 4px;
}

.doc-card-body::-webkit-scrollbar-thumb {
  background: rgba(20, 93, 160, 0.3);
  border-radius: 4px;
}

.doc-card-body::-webkit-scrollbar-thumb:hover {
  background: rgba(20, 93, 160, 0.5);
}

.doc-card-body h3 {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-size: 1.4rem;
  font-weight: 700;
  color: #145da0;
}

.doc-card-body h3:first-child {
  margin-top: 0;
}

.doc-card-body h4 {
  margin-top: 1.25rem;
  margin-bottom: 0.6rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #0a2342;
}

.doc-card-body p {
  margin-bottom: 1rem;
  color: #2c3e50;
  text-align: justify;
}

.doc-card-body ul {
  margin-left: 1.5rem;
  margin-bottom: 1rem;
  text-align: justify;
}

.doc-card-body li {
  margin-bottom: 0.6rem;
  color: #2c3e50;
  text-align: justify;
}

.doc-card-body :deep(li b),
.doc-card-body :deep(p b) {
  color: #145da0;
  font-weight: 600;
}

.doc-card-body code {
  background: rgba(20, 93, 160, 0.1);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: #145da0;
}

.doc-image-container {
  margin: 1.5rem 0;
  text-align: center;
}

.doc-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(20, 93, 160, 0.15);
}

.doc-image-caption {
  margin-top: 0.75rem;
  font-size: 0.9rem;
  color: #5a6c7d;
  font-style: italic;
  text-align: center;
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
