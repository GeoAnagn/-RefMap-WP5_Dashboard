<template>
  <div class="dashboard-bg">
    <div class="optimized-trajectories-container">
      <div class="optimized-trajectories-section optimized-trajectories-section-header">
        <v-btn icon class="back-arrow-btn" @click="$emit('close')">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <v-btn icon class="doc-btn" @click="openDocumentation">
          <v-icon>mdi-book-open-variant</v-icon>
        </v-btn>
      </div>

      <div class="optimized-trajectories-section optimized-trajectories-section-title">
        <span class="ltr-letters-wrapper ltr-letters-animate">
          <span class="ltr-letters">Optimized Trajectories</span>
        </span>
      </div>

      <div class="optimized-trajectories-section optimized-trajectories-section-filters">
        <div class="filters-row">
          <v-select
            v-model="filters.area"
            :items="availableAreas"
            label="Area"
            variant="outlined"
            class="filter-select"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.turbulence"
            :items="availableTurbulence"
            label="Turbulence Level"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.area"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.takeoff"
            :items="availableTakeoff"
            label="Takeoff Vertiport"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.turbulence"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.landing"
            :items="availableLanding"
            label="Landing Vertiport"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.takeoff"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
        </div>
      </div>

      <div class="optimized-trajectories-section optimized-trajectories-section-cards">
        <div class="optimized-trajectories-cards-grid">
          <v-card elevation="0" class="refmap-card refmap-card-inline map-card-shell">
            <div class="map-card-body">
              <template v-if="selectedCasePath">
                <div class="gif-controls">
                  <v-btn icon size="small" class="replay-btn" @click="replayGif" :title="'Replay'">
                    <v-icon size="20">mdi-replay</v-icon>
                  </v-btn>
                </div>
                <img :src="displayUrl" style="max-width:100%; max-height: 59vh; border-radius:1.5rem;" />
              </template>
              <template v-else>
                <div class="map-placeholder" style="color:#fff;">
                  Please select all filter parameters to view the trajectory animation.
                </div>
              </template>
            </div>
          </v-card>
        </div>
      </div>
    </div>
  </div>
  <DocumentationOverlay :show="showDocOverlay" toolId="l4" @close="closeDocumentation" />
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import DocumentationOverlay from './DocumentationOverlay.vue'

const apiBase = '/api/optimized_trajectories'

// State
const allCases = ref([])
const filters = ref({
  area: null,
  turbulence: null,
  takeoff: null,
  landing: null
})
const gifBust = ref(Date.now())
const isPlaying = ref(true)

// --- Cascading Logic ---

const availableAreas = computed(() => {
  return [...new Set(allCases.value.map(c => c.area))].sort()
})

const availableTurbulence = computed(() => {
  if (!filters.value.area) return []
  const subset = allCases.value.filter(c => c.area === filters.value.area)
  return [...new Set(subset.map(c => c.turbulence))].sort()
})

const availableTakeoff = computed(() => {
  if (!filters.value.turbulence) return []
  const subset = allCases.value.filter(c => 
    c.area === filters.value.area && 
    c.turbulence === filters.value.turbulence
  )
  return [...new Set(subset.map(c => c.takeoff))].sort()
})

const availableLanding = computed(() => {
  if (!filters.value.takeoff) return []
  const subset = allCases.value.filter(c => 
    c.area === filters.value.area && 
    c.turbulence === filters.value.turbulence &&
    c.takeoff === filters.value.takeoff
  )
  return [...new Set(subset.map(c => c.landing))].sort()
})

// Determine the actual path of the GIF to load
const selectedCasePath = computed(() => {
  const match = allCases.value.find(c => 
    c.area === filters.value.area &&
    c.turbulence === filters.value.turbulence &&
    c.takeoff === filters.value.takeoff &&
    c.landing === filters.value.landing
  )
  return match ? match.id : null
})

const displayUrl = computed(() => {
  if (!selectedCasePath.value) return ''
  return `${apiBase}/gif/${encodeURIComponent(selectedCasePath.value)}?t=${gifBust.value}`
})

// --- Watchers to reset children when parents change ---

watch(() => filters.value.area, () => {
  filters.value.turbulence = null; filters.value.takeoff = null; filters.value.landing = null
})
watch(() => filters.value.turbulence, () => {
  filters.value.takeoff = null; filters.value.landing = null
})
watch(() => filters.value.takeoff, () => {
  filters.value.landing = null
})

// --- Methods ---

function replayGif() {
  gifBust.value = Date.now()
}

onMounted(async () => {
  try {
    const res = await fetch(`${apiBase}/cases`)
    const data = await res.json()
    allCases.value = data.cases || []
    
    // Auto-select first available option
    if (allCases.value.length > 0) {
      const first = allCases.value[0]
      filters.value.area = first.area
      filters.value.turbulence = first.turbulence
      filters.value.takeoff = first.takeoff
      filters.value.landing = first.landing
    }
  } catch (e) {
    console.error('Failed to load cases', e)
  }
})

// Doc overlay logic
const showDocOverlay = ref(false)
const openDocumentation = () => { showDocOverlay.value = true }
const closeDocumentation = () => { showDocOverlay.value = false }
</script>

<style scoped>
.optimized-trajectories-container {
  width: 100vw;
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 4rem);
  padding-bottom: 5rem;
  margin-left: calc(-50vw + 50%);
}

.optimized-trajectories-section {
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 clamp(1rem, 3vw, 2rem);
}

.optimized-trajectories-section-header {
  flex: 0 0 auto;
  justify-content: space-between;
}

.back-arrow-btn, .doc-btn {
  background: rgba(255,255,255,0.08);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.25);
  backdrop-filter: blur(10px);
}

.ltr-letters {
  font-size: clamp(1.5rem, 4vw, 3rem);
  font-weight: 600;
  color: #fff;
  text-shadow: 0 2px 4px rgba(0,0,0,0.4);
}

/* --- FILTER SECTION STYLING --- */
.optimized-trajectories-section-filters {
  padding: 1.5rem 0;
}

.filters-row {
  margin-top: 1%;
  display: flex;
  gap: 1.5rem;
  width: 90%;
  max-width: 1200px;
  justify-content: center;
}

.filter-select {
  flex: 1;
  min-width: 150px;
}

/* 1. CONTAINER STYLE */
.filter-select :deep(.v-field) {
  background-color: #ffffff !important;
  border-radius: 12px;
  border: 1px solid rgba(20, 93, 160, 0.2); 
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  min-height: 64px !important;
  display: flex;
  align-items: center;
}

/* 2. HOVER EFFECT */
.filter-select :deep(.v-field:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.15);
  border-color: #145DA0;
}

/* 3. FIXING THE LABELS (Truncation & Visibility) */

/* General label style */
.filter-select :deep(.v-label.v-field-label) {
  color: #145DA0 !important;
  font-weight: 700 !important;
  opacity: 1 !important;
  font-size: 1.3rem !important;
  
  /* CRITICAL: Allow label to expand fully */
  max-width: none !important;
  width: auto !important;
  overflow: visible !important;
  white-space: nowrap !important;
  text-overflow: clip !important; /* Stop the "..." */
}

/* THE FLOATING TITLE (Selected State) */
.filter-select :deep(.v-label.v-field-label--floating) {
  color: white !important; 
  font-weight: 700 !important;
  opacity: 1 !important;
  font-size: 1.3rem !important;

  /* Position adjustments */
  transform: translateY(-34px) scale(1) !important;
  padding: 0 8px; /* More padding to cover border */
  margin-left: -8px;
  z-index: 100; /* Ensure it sits on top of everything */
}

/* The Selected Input Value */
.filter-select :deep(.v-field__input) {
  color: #145DA0 !important;
  font-weight: 600;
  font-size: 1.25rem !important; 
}

/* The dropdown arrow */
.filter-select :deep(.v-field__append-inner .v-icon) {
  color: #145DA0 !important;
  opacity: 1;
  font-size: 2rem; 
}

/* Disabled State */
.filter-select :deep(.v-field--disabled) {
  background-color: #e0e0e0 !important;
  border: 1px solid #999;
}

/* --- END FILTER STYLING --- */

/* Map/GIF Display Area */
.map-card-shell { 
  margin-top: 3%;
  width: 100%;
  background: transparent !important;
  border-color: transparent;
}

.map-card-body {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gif-controls {
  position: absolute;
  top: 15px;
  right: 15px;
  z-index: 5;
}

.replay-btn {
  background: #fff !important;
  color: #145DA0 !important;
}

@media (max-width: 960px) {
  .filters-row {
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }
  .filter-select {
    width: 100%;
    max-width: 400px;
  }
}
</style>

<style>
.filter-menu-content .v-list-item-title {
  font-size: 1.1rem !important; 
  font-weight: 500 !important;
  padding: 8px 0 !important;
}
</style>