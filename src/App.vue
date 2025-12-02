<template>
  <div class="dashboard-bg">
    <!-- Tool views -->
    <template v-if="showClimateImpact">
      <div class="dashboard-center tool-view">
        <ClimateImpact @close="closeClimateImpact" />
      </div>
    </template>
    <template v-else-if="showAtmosphericPollution">
      <div class="dashboard-center tool-view">
        <AtmosphericPollution @close="closeAtmosphericPollution" />
      </div>
    </template>
    <template v-else-if="showEmissions">
      <div class="dashboard-center tool-view">
        <Emissions @close="closeEmissions" />
      </div>
    </template>
    <template v-else-if="showWindAssessment">
      <div class="dashboard-center tool-view">
        <WindAssessment @close="closeWindAssessment" />
      </div>
    </template>
    <template v-else-if="showNoiseAssessment">
      <div class="dashboard-center tool-view">
        <NoiseAssessment @close="closeNoiseAssessment" />
      </div>
    </template>
    <template v-else-if="showOptimizedTrajectories">
      <div class="dashboard-center tool-view">
        <OptimizedTrajectories @close="closeOptimizedTrajectories" />
      </div>
    </template>

    <!-- Dashboard home -->
    <template v-else>
      <div class="dashboard-home-container">
        <!-- Section 1: Logo -->
        <transition name="fade">
          <div v-if="showLogo" class="dashboard-section dashboard-section-logo">
            <img src="./assets/refmap-logo.avif" alt="RefMap Logo" class="refmap-logo" />
          </div>
        </transition>

        <!-- Section 2: Logo Text / Title -->
        <div class="dashboard-section dashboard-section-title">
          <span class="ltr-letters-wrapper" :class="{ 'ltr-letters-animate': animateUp }">
            <span class="ltr-letters">
              <span
                v-for="(char, i) in letters"
                :key="i"
                class="ltr-letter"
                :style="{ animationDelay: (i * 0.04) + 's' }"
              >
                {{ char === ' ' ? '\u00A0' : char }}
              </span>
            </span>
          </span>
        </div>

        <!-- Section 3: Filters -->
        <transition name="fade">
          <div v-if="showButtons" class="dashboard-section dashboard-section-filters">
            <v-btn
              class="dashboard-btn-simple"
              :class="{ active: selected === 'large' }"
              color="secondary"
              variant="elevated"
              rounded="xl"
              size="default"
              @click="toggleSelected('large', $event)"
            >
              Large scale tools
            </v-btn>
            <v-btn
              class="dashboard-btn-simple"
              :class="{ active: selected === 'small' }"
              color="secondary"
              variant="elevated"
              rounded="xl"
              size="default"
              @click="toggleSelected('small', $event)"
            >
              Small scale tools
            </v-btn>
          </div>
        </transition>

        <!-- Section 4: Cards -->
        <transition name="fade">
          <div v-if="showButtons" class="dashboard-section dashboard-section-cards">
            <transition-group name="card-fade" tag="div" class="dashboard-cards-grid" v-if="filteredTools.length">
              <div v-for="tool in filteredTools" :key="tool.id" class="dashboard-card-wrapper">
                <v-card class="refmap-card refmap-card-inline">
                  <div class="refmap-card-header">
                    <v-card-title class="refmap-card-title">{{ tool.title }}</v-card-title>
                    <div class="refmap-card-separator"></div>
                  </div>
                  <div class="refmap-card-body">
                    <v-card-subtitle class="refmap-card-subtitle">{{ tool.group === 'large' ? 'Large Scale' : 'Small Scale' }}</v-card-subtitle>
                    <v-card-text class="refmap-card-desc">{{ tool.desc }}</v-card-text>
                  </div>
                  <div class="refmap-card-footer">
                    <v-card-actions class="refmap-card-actions">
                      <v-btn v-if="tool.id === 'l1'" color="primary" variant="flat" class="refmap-card-btn launch" size="small" @click="openClimateImpact">Launch</v-btn>
                      <v-btn v-else-if="tool.id === 'l3'" color="primary" variant="flat" class="refmap-card-btn launch" size="small" @click="openAtmosphericPollution">Launch</v-btn>
                      <v-btn v-else-if="tool.id === 'l2'" color="primary" variant="flat" class="refmap-card-btn launch" size="small" @click="openEmissions">Launch</v-btn>
                      <v-btn v-else-if="tool.id === 's2'" color="primary" variant="flat" class="refmap-card-btn launch" size="small" @click="openWindAssessment">Launch</v-btn>
                      <v-btn v-else-if="tool.id === 's1'" color="primary" variant="flat" class="refmap-card-btn launch" size="small" @click="openNoiseAssessment">Launch</v-btn>
                      <v-btn v-else-if="tool.id === 'l4'" color="primary" variant="flat" class="refmap-card-btn launch" size="small" @click="openOptimizedTrajectories">Launch</v-btn>
                      <v-btn v-else color="primary" variant="flat" class="refmap-card-btn launch" size="small">Launch</v-btn>
                      <v-btn color="primary" variant="outlined" class="refmap-card-btn documentation" size="small" @click="openDocumentation(tool.id)">Documentation</v-btn>
                    </v-card-actions>
                  </div>
                </v-card>
              </div>
            </transition-group>
            <div v-else class="dashboard-cards-empty">
              <v-alert type="info" color="primary">No tools found.</v-alert>
            </div>
          </div>
        </transition>
      </div>
    </template>

    <!-- Unified footer -->
    <transition name="fade">
      <footer v-if="showFooter" class="refmap-footer">
        <span class="footer-text">&copy; 2025 RefMap Project. All rights reserved.</span>
      </footer>
    </transition>

    <!-- Documentation Overlay -->
    <DocumentationOverlay :show="showDocOverlay" :toolId="currentDocTool" @close="closeDocumentation" />

  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import ClimateImpact from './components/ClimateImpact.vue'
import AtmosphericPollution from './components/AtmosphericPollution.vue'
import WindAssessment from './components/WindAssessment.vue'
import NoiseAssessment from './components/NoiseAssessment.vue'
import OptimizedTrajectories from './components/OptimizedTrajectories.vue'
import Emissions from './components/Emissions.vue'
import DocumentationOverlay from './components/DocumentationOverlay.vue'

const text = 'RefMap Dashboard'
const letters = computed(() => text.split(''))
const animateUp = ref(true)
const showButtons = ref(true)
const showLogo = ref(true)
const showFooter = ref(true)
const selected = ref(null)
const showClimateImpact = ref(false)
const showAtmosphericPollution = ref(false)
const showEmissions = ref(false)
const showWindAssessment = ref(false)
const showNoiseAssessment = ref(false)
const showOptimizedTrajectories = ref(false)
const showDocOverlay = ref(false)
const currentDocTool = ref(null)
// animations removed for a cleaner, static experience

function toggleSelected(group, event) {
  selected.value = selected.value === group ? null : group
  event.currentTarget.blur()
}

function openClimateImpact() {
  showClimateImpact.value = true
}
function closeClimateImpact() {
  showClimateImpact.value = false
  // Do not reset animation state
}
function openEmissions() {
  showEmissions.value = true
}
function closeEmissions() {
  showEmissions.value = false
}
function openAtmosphericPollution() {
  showAtmosphericPollution.value = true
}
function closeAtmosphericPollution() {
  showAtmosphericPollution.value = false
}
function openWindAssessment() {
  showWindAssessment.value = true
}
function closeWindAssessment() {
  showWindAssessment.value = false
}
function openNoiseAssessment() {
  showNoiseAssessment.value = true
}
function closeNoiseAssessment() {
  showNoiseAssessment.value = false
}
function openOptimizedTrajectories() {
  showOptimizedTrajectories.value = true
}
function closeOptimizedTrajectories() {
  showOptimizedTrajectories.value = false
}

function openDocumentation(toolId) {
  currentDocTool.value = toolId
  showDocOverlay.value = true
}

function closeDocumentation() {
  showDocOverlay.value = false
  currentDocTool.value = null
}

const tools = [
  { id: 'l1', group: 'large', title: 'Climate Impact', desc: 'Analyze and visualize the environmental impact of projects or activities.' },
  { id: 'l2', group: 'large', title: 'Emissions', desc: 'Visualize emissions overlays for PM2.5, NO2, and O3 across scenarios.' },
  { id: 'l3', group: 'large', title: 'Atmospheric Pollution', desc: 'Assess air quality and model the dispersion of atmospheric pollutants over wide areas.' },
  { id: 'l4', group: 'small', title: 'Airflow Trajectory Optimization', desc: 'Optimize transportation or logistics routes for efficiency based on turbulence effects' },
  { id: 's1', group: 'small', title: 'Noise Assessment', desc: 'Evaluate and map noise levels for small sites, buildings, or local environments.' },
  { id: 's2', group: 'small', title: 'Wind Risk Assessment', desc: 'Analyze wind patterns and potential for small-scale wind energy or site planning.' },
]

const filteredTools = computed(() => {
  if (selected.value === 'large') return tools.filter(t => t.group === 'large')
  if (selected.value === 'small') return tools.filter(t => t.group === 'small')
  return tools
})

// No animated mounting logic or watchers required
</script>

<style scoped>
/* Base dashboard layout */
.dashboard-bg {
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  /* padding: clamp(1rem, 3vw, 2rem); */
  position: relative;
  /* overflow-x: hidden; */
}

/* Tool view container */
.tool-view {
  width: 100%;
  max-width: 100%;
  padding: 0;
}

/* Dashboard home container */
.dashboard-home-container {
  width: 100%;
  max-width: 1400px;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 4rem);
  padding-bottom: 5rem;
}

/* Common section styling */
.dashboard-section {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 clamp(0.5rem, 2vw, 1rem);
}

/* Section 1: Logo */
.dashboard-section-logo {
  flex: 0 0 auto;
  padding-top: clamp(1rem, 3vh, 2rem);
  padding-bottom: clamp(0.5rem, 2vh, 1rem);
}

.refmap-logo {
  width: clamp(80px, 12vw, 140px);
  height: auto;
  filter: drop-shadow(0 8px 16px rgba(0,0,0,0.25));
}

/* Section 2: Title */
.dashboard-section-title {
  flex: 0 0 auto;
  padding: clamp(0.5rem, 2vh, 1rem) 0;
}

.ltr-letters-wrapper {
  display: inline-block;
}

.ltr-letters {
  font-size: clamp(1.5rem, 4vw, 3rem);
  font-weight: 800;
  letter-spacing: 0.03em;
  color: #ffffff;
  line-height: 1.2;
  word-wrap: break-word;
}

.ltr-letter {
  display: inline-block;
}

/* Section 3: Filters */
.dashboard-section-filters {
  flex: 0 0 auto;
  padding: clamp(0.75rem, 2vh, 1.5rem) 0;
  gap: clamp(0.75rem, 2vw, 1.5rem);
  flex-wrap: wrap;
}

.dashboard-btn-simple {
  flex: 0 1 auto;
  min-width: clamp(140px, 20vw, 180px);
  font-size: clamp(0.85rem, 1.5vw, 1rem) !important;
  padding: clamp(0.5rem, 1.5vw, 0.75rem) clamp(1rem, 2vw, 1.5rem) !important;
}

/* Section 4: Cards */
.dashboard-section-cards {
  flex: 1 1 auto;
  align-items: flex-start;
  padding-top: clamp(0.75rem, 2vh, 1.5rem);
  padding-bottom: clamp(1rem, 3vh, 2rem);
  overflow-y: auto;
}

/* Cards grid */
.dashboard-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
  gap: clamp(1rem, 2vw, 1.5rem);
  width: 100%;
  position: relative;
}

.dashboard-card-wrapper {
  display: flex;
  min-height: 100%;
  transition: all 0.4s ease;
}

.refmap-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.refmap-card-header {
  padding: clamp(0.75rem, 2vw, 1rem) clamp(0.75rem, 2vw, 1.25rem) 0;
}

.refmap-card-title {
  font-size: clamp(1.1rem, 2vw, 1.35rem) !important;
  font-weight: 800 !important;
  word-wrap: break-word;
  line-height: 1.3 !important;
  white-space: normal !important;
  overflow-wrap: break-word;
}

.refmap-card-body {
  padding: clamp(0.5rem, 1.5vw, 0.75rem) clamp(0.75rem, 2vw, 1.25rem);
  flex-grow: 1;
}

.refmap-card-subtitle {
  font-size: clamp(0.8rem, 1.5vw, 0.95rem) !important;
  margin-bottom: clamp(0.25rem, 1vw, 0.5rem);
}

.refmap-card-desc {
  font-size: clamp(0.85rem, 1.5vw, 1rem) !important;
  line-height: 1.5;
}

.refmap-card-footer {
  padding: 0 clamp(0.5rem, 1.5vw, 1rem) clamp(0.75rem, 2vw, 1rem);
  margin-top: auto;
}

.refmap-card-actions {
  display: flex;
  gap: clamp(0.5rem, 1vw, 0.75rem);
  flex-wrap: wrap;
  justify-content: center;
  width: 100%;
}

.refmap-card-btn {
  flex: 1 1 auto;
  min-width: clamp(80px, 15vw, 100px);
  font-size: clamp(0.75rem, 1.5vw, 0.9rem) !important;
  font-weight: 700 !important;
}

.dashboard-cards-empty {
  display: flex;
  justify-content: center;
  padding: 2rem 1rem;
}

/* Footer */
.refmap-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  text-align: center;
  padding: clamp(0.5rem, 1.5vw, 0.8rem);
  font-size: clamp(0.75rem, 1.5vw, 0.95rem);
  z-index: 100;
}

.footer-text {
  display: inline-block;
  white-space: nowrap;
}

/* Tablet breakpoint (768px and below) */
@media (max-width: 768px) {
  .dashboard-home-container {
    padding-bottom: 4rem;
  }

  .dashboard-section-logo {
    padding-top: clamp(0.75rem, 2vh, 1.5rem);
    padding-bottom: clamp(0.5rem, 1.5vh, 0.75rem);
  }

  .refmap-logo {
    width: clamp(70px, 15vw, 110px);
  }

  .dashboard-section-title {
    padding: clamp(0.5rem, 1.5vh, 0.75rem) 0;
  }

  .ltr-letters {
    font-size: clamp(1.5rem, 5vw, 2.5rem);
  }

  .dashboard-section-filters {
    padding: clamp(0.5rem, 1.5vh, 1rem) 0;
    gap: 1rem;
  }

  .dashboard-btn-simple {
    min-width: 150px;
    font-size: 0.9rem !important;
  }

  .dashboard-section-cards {
    padding-top: clamp(0.5rem, 1.5vh, 1rem);
  }

  .dashboard-cards-grid {
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 250px), 1fr));
    gap: 1rem;
  }

  .refmap-card-actions {
    flex-direction: column;
    gap: 0.5rem;
  }

  .refmap-card-btn {
    width: 100%;
    min-width: 100%;
  }
}

/* Mobile breakpoint (480px and below) */
@media (max-width: 480px) {
  .dashboard-bg {
    padding: 0.75rem 0.5rem;
  }

  .dashboard-home-container {
    padding-bottom: 3.5rem;
  }

  .dashboard-section-logo {
    padding-top: 0.75rem;
    padding-bottom: 0.5rem;
  }

  .refmap-logo {
    width: clamp(60px, 20vw, 90px);
  }

  .dashboard-section-title {
    padding: 0.5rem 0;
  }

  .ltr-letters {
    font-size: clamp(1.25rem, 6vw, 1.8rem);
  }

  .dashboard-section-filters {
    flex-direction: column;
    padding: 0.75rem 0;
    gap: 0.75rem;
  }

  .dashboard-btn-simple {
    width: 100%;
    min-width: 100%;
    font-size: 0.95rem !important;
    padding: 0.75rem 1rem !important;
  }

  .dashboard-section-cards {
    padding-top: 0.75rem;
  }

  .dashboard-cards-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .refmap-card-header {
    padding: 0.75rem 1rem 0;
  }

  .refmap-card-title {
    font-size: 1.15rem !important;
  }

  .refmap-card-body {
    padding: 0.5rem 1rem;
  }

  .refmap-card-footer {
    padding: 0 0.75rem 0.75rem;
  }

  .refmap-card-actions {
    gap: 0.5rem;
  }

  .refmap-footer {
    padding: 0.6rem 0.5rem;
    font-size: 0.7rem;
  }

  .footer-text {
    white-space: normal;
    word-wrap: break-word;
  }
}

/* Large desktop breakpoint (1400px and above) */
@media (min-width: 1400px) {
  .dashboard-cards-below {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 2rem;
  }

  .refmap-card-title {
    font-size: 1.5rem !important;
  }

  .refmap-card-desc {
    font-size: 1.05rem !important;
  }
}

/* Landscape mobile devices */
@media (max-height: 600px) and (orientation: landscape) {
  .dashboard-home-container {
    padding-bottom: 3rem;
  }

  .dashboard-section-logo {
    padding-top: 0.5rem;
    padding-bottom: 0.25rem;
  }

  .refmap-logo {
    width: clamp(50px, 8vh, 70px);
  }

  .dashboard-section-title {
    padding: 0.25rem 0;
  }

  .ltr-letters {
    font-size: clamp(1.2rem, 3.5vh, 1.5rem);
  }

  .dashboard-section-filters {
    padding: 0.5rem 0;
  }

  .dashboard-section-cards {
    padding-top: 0.5rem;
  }

  .refmap-footer {
    padding: 0.4rem;
    font-size: 0.75rem;
  }
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

/* Card fade transition */
.card-fade-enter-active {
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.card-fade-leave-active {
  transition: all 0.3s ease;
  position: absolute;
}

.card-fade-enter-from {
  opacity: 0;
  transform: translateY(30px) scale(0.9);
}

.card-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
}

.card-fade-move {
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
</style>

