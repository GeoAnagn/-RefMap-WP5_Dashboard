<template>
  <div class="dashboard-bg">
    <div class="noise-assessment-container">
      <!-- Section 1: Header -->
      <div class="noise-assessment-section noise-assessment-section-header">
        <v-btn icon class="back-arrow-btn" @click="$emit('close')">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <v-btn icon class="doc-btn" @click="openDocumentation">
          <v-icon>mdi-book-open-variant</v-icon>
        </v-btn>
      </div>

      <!-- Section 2: Title -->
      <div class="noise-assessment-section noise-assessment-section-title">
        <span class="ltr-letters-wrapper ltr-letters-animate">
          <span class="ltr-letters">Noise Assessment</span>
        </span>
      </div>

      <!-- Section 3: Filters -->
      <div class="noise-assessment-section noise-assessment-section-filters">
        <div class="filters-row">
          <v-select
            v-model="filters.city"
            :items="cityOptions"
            label="City"
            variant="outlined"
            class="filter-select"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.time"
            :items="timeOptions"
            label="Time"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.city"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.flightZone"
            :items="flightZoneOptions"
            label="Flight Zones"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.time"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.flightsPerHour"
            :items="flightsPerHourOptions"
            label="Flights Per Hour"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.flightZone"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.metric"
            :items="metricOptions"
            label="Metric"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.flightsPerHour"
            item-title="title"
            item-value="value"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
        </div>
      </div>

      <!-- Section 4: Cards -->
      <div class="noise-assessment-section noise-assessment-section-cards">
        <div class="noise-assessment-cards-grid">
          <v-card elevation="6" class="refmap-card refmap-card-inline map-card-shell">
            <div class="map-card-body">
              <template v-if="showMap">
                <LMap
                  ref="mapRefEl"
                  :zoom="5"
                  :center="mapCenter"
                  :bounds="heatmapBounds"
                  :minZoom="minZoom"
                  :maxZoom="maxZoom"
                  :maxBounds="europeBounds"
                  :use-global-leaflet="false"
                  class="map-leaflet"
                >
                  <LTileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                    attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
                  />
                  <LImageOverlay
                    v-if="overlayUrl && heatmapBounds"
                    :url="overlayUrl"
                    :bounds="heatmapBounds"
                    :opacity="1"
                  />
                </LMap>
              </template>
              <!-- Color bar overlay -->
              <div v-if="overlayUrl" class="color-bar-container horizontal">
                <div class="color-bar-label color-bar-label-left">{{ colorBarMin }}</div>
                <div class="color-bar-overlay" :style="colorBarStyle"></div>
                <div class="color-bar-label color-bar-label-right">{{ colorBarMax }}</div>
              </div>
            </div>
          </v-card>
        </div>
      </div>
    </div>
  </div>
  <DocumentationOverlay :show="showDocOverlay" toolId="s1" @close="closeDocumentation" />
</template>

<script setup>
const emit = defineEmits(['close'])
import { ref, onMounted, watch, computed, onBeforeUnmount, nextTick } from 'vue'
import 'leaflet/dist/leaflet.css';
import { LMap, LTileLayer, LImageOverlay } from '@vue-leaflet/vue-leaflet';
import DocumentationOverlay from './DocumentationOverlay.vue';

// --- Filter options ---
const cityOptions = ref([])
const timeOptions = ref([])
const flightZoneOptions = ref([])
const flightsPerHourOptions = ref([])
const metricOptions = ref([])

const filters = ref({
  city: null,
  time: null,
  flightZone: null,
  flightsPerHour: null,
  metric: null,
})

const availableCombos = ref({})

// --- Map logic ---

const mapCenter = ref([52.0, 4.37]) // Default center (Netherlands)
const mapZoom = ref(5) // Start with 5, will update on bounds
const minZoom = ref(4)
const maxZoom = ref(18)
const showMap = ref(false)
const mapRefEl = ref(null)
// overlayUrl and heatmapBounds already declared above
const overlayUrl = ref("")
const heatmapBounds = ref(null)
// Add europeBounds as in WindAssessment.vue
const europeBounds = ref([[34.5, -10.5], [71.5, 31.5]])

// --- Color bar properties ---
const colorBarMin = ref('0 dB')
const colorBarMax = ref('100 dB')

// Use the provided scale image with a fallback gradient
const colorBarStyle = computed(() => {
  const fallbackGradient = 'linear-gradient(to right, ' +
    '#000080 0%, ' +
    '#0040a0 8.33%, ' +
    '#0080ff 16.66%, ' +
    '#00c8ff 25%, ' +
    '#00ffbf 33.33%, ' +
    '#00ff40 41.66%, ' +
    '#80ff00 50%, ' +
    '#c8ff00 58.33%, ' +
    '#ffff00 66.66%, ' +
    '#ffbf00 75%, ' +
    '#ff8000 83.33%, ' +
    '#ff0000 91.66%, ' +
    '#ff00ff 100%)';
  return {
    background: `url('/api/noise_assessment/scale-argb.png') no-repeat center/100% 100%, ${fallbackGradient}`
  };
})

// --- Fetch available filter options from backend step by step ---
onMounted(async () => {
  // Load available cities on mount
  try {
    const resp = await fetch('/api/noise_assessment/api/noise_cities')
    cityOptions.value = await resp.json()
    showMap.value = true
  } catch (e) {
    cityOptions.value = []
    showMap.value = false
  }
})

// Fetch times when city changes
watch(() => filters.value.city, async (newCity) => {
  filters.value.time = null
  filters.value.flightZone = null
  filters.value.flightsPerHour = null
  filters.value.metric = null
  timeOptions.value = []
  flightZoneOptions.value = []
  flightsPerHourOptions.value = []
  metricOptions.value = []
  if (!newCity) return
  try {
    const resp = await fetch(`/api/noise_assessment/api/noise_times?city=${encodeURIComponent(newCity)}`)
    timeOptions.value = await resp.json()
  } catch (e) {
    timeOptions.value = []
  }
})

// Fetch Flight Zones when City or Time changes
watch(() => filters.value.time, async (newTime) => {
  filters.value.flightZone = null
  filters.value.flightsPerHour = null
  filters.value.metric = null
  flightZoneOptions.value = []
  flightsPerHourOptions.value = []
  metricOptions.value = []
  if (!filters.value.city || !newTime) return
  try {
    const resp = await fetch(`/api/noise_assessment/api/noise_flight_zones?city=${encodeURIComponent(filters.value.city)}&time=${encodeURIComponent(newTime)}`)
    flightZoneOptions.value = await resp.json()
  } catch (e) {
    flightZoneOptions.value = []
  }
})

// Fetch Flights Per Hour when Flight Zone changes (with city/time)
watch(() => filters.value.flightZone, async (newZone) => {
  filters.value.flightsPerHour = null
  filters.value.metric = null
  flightsPerHourOptions.value = []
  metricOptions.value = []
  if (!filters.value.city || !filters.value.time || !newZone) return
  try {
    const resp = await fetch(`/api/noise_assessment/api/noise_flights_per_hour?city=${encodeURIComponent(filters.value.city)}&time=${encodeURIComponent(filters.value.time)}&flight_zone=${encodeURIComponent(newZone)}`)
    const data = await resp.json()
    flightsPerHourOptions.value = data.sort((a, b) => {
      const numA = parseInt(a, 10)
      const numB = parseInt(b, 10)
      return numA - numB
    })
  } catch (e) {
    flightsPerHourOptions.value = []
  }
})

// Fetch Metrics when Flights Per Hour changes
watch(() => filters.value.flightsPerHour, async (newFph) => {
  filters.value.metric = null
  metricOptions.value = []
  if (!filters.value.city || !filters.value.time || !filters.value.flightZone || !newFph) return
  try {
    const resp = await fetch(`/api/noise_assessment/api/noise_metrics?city=${encodeURIComponent(filters.value.city)}&time=${encodeURIComponent(filters.value.time)}&flight_zone=${encodeURIComponent(filters.value.flightZone)}&flights_per_hour=${encodeURIComponent(newFph)}`)
    const metrics = await resp.json()
    const labelMap = {
      'Ambient': 'Ambient Noise',
      'AnnoyanceShift(ambi)': 'Mean change in annoyance',
      'HighAnnoyPerc(ambi)': 'Percentage of highly annoyed',
      'L(AE)eq': 'Noise of drones Leq'
    }
    metricOptions.value = (metrics || []).map(m => ({ title: labelMap[m] ?? m, value: m }))
  } catch (e) {
    metricOptions.value = []
  }
})

// Fetch overlay info and boundaries when all filters are selected
watch(() => filters.value.metric, async (metric) => {
  overlayUrl.value = ''
  heatmapBounds.value = null
  const { city, time, flightZone, flightsPerHour } = filters.value
  if (!city || !time || !flightZone || !flightsPerHour || !metric) return
  try {
    const params = new URLSearchParams({
      city,
      time,
      flight_zone: flightZone,
      flights_per_hour: flightsPerHour,
      metric
    })
    const resp = await fetch(`/api/noise_assessment/api/noise_image_info?${params.toString()}`)
    const data = await resp.json()
    if (data.error) throw new Error(data.error)
    if (data.image_data) {
      overlayUrl.value = `data:image/png;base64,${data.image_data}`
    } else {
      overlayUrl.value = ''
    }
    if (data.bounds) {
      heatmapBounds.value = [
        [data.bounds['lat-min'], data.bounds['lon-min']],
        [data.bounds['lat-max'], data.bounds['lon-max']]
      ]
    } else {
      heatmapBounds.value = null
    }
    // Update colorbar labels based on metric
    // Ambient -> 0–100 dB, L(AE)eq -> 0–100 dB, AnnoyanceShift(ambi) -> 0–10, HighAnnoyPerc(ambi) -> 0–100%
    const m = metric
    if (m === 'Ambient' || m === 'L(AE)eq') {
      colorBarMin.value = '0 dB'
      colorBarMax.value = '100 dB'
    } else if (m === 'AnnoyanceShift(ambi)') {
      colorBarMin.value = '0'
      colorBarMax.value = '10'
    } else if (m === 'HighAnnoyPerc(ambi)') {
      colorBarMin.value = '0%'
      colorBarMax.value = '100%'
    } else {
      // default fallback
      colorBarMin.value = '0'
      colorBarMax.value = '100'
    }
  } catch (e) {
    overlayUrl.value = ''
  }
})

onBeforeUnmount(() => {
  // Clean up if needed
})

// When heatmap bounds update, refocus the map to fit them
watch(heatmapBounds, async (newBounds) => {
  if (!newBounds) return
  await nextTick()
  const map = mapRefEl.value && mapRefEl.value.leafletObject
  if (map) {
    try {
      map.fitBounds(newBounds, { padding: [20, 20], animate: true })
    } catch (e) {
      // ignore
    }
  }
})

// --- Documentation overlay logic ---
const showDocOverlay = ref(false)
function openDocumentation() {
  showDocOverlay.value = true
}
function closeDocumentation() {
  showDocOverlay.value = false
}
</script>

<style scoped>
/* Noise Assessment Container */
.noise-assessment-container {
  width: 100vw;
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 4rem);
  padding-bottom: 5rem;
  margin-left: calc(-50vw + 50%);
}

/* Common section styling */
.noise-assessment-section {
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 clamp(1rem, 3vw, 2rem);
}

/* Section 1: Header */
.noise-assessment-section-header {
  flex: 0 0 auto;
  justify-content: space-between;
}

.back-arrow-btn, .doc-btn {
  background: rgba(255,255,255,0.08);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.25);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

/* Section 2: Title */
.noise-assessment-section-title {
  flex: 0 0 auto;
}

.ltr-letters-wrapper {
  display: inline-block;
}

.ltr-letters {
  font-size: clamp(1.5rem, 4vw, 3rem);
  font-weight: 600;
  color: #fff;
  text-shadow: 0 2px 4px rgba(0,0,0,0.4);
}

/* --- FILTER SECTION STYLING --- */
.noise-assessment-section-filters {
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

/* Section 4: Cards */
.noise-assessment-section-cards {
  flex: 1 1 auto;
  align-items: flex-start;
  padding-bottom: clamp(1rem, 3vh, 2rem);
}

.noise-assessment-cards-grid {
  display: flex;
  width: 90%;
  max-width: 100%;
}

.map-card-shell { 
  padding: 0;
  width: 100%;
  border-radius: 1.5rem;
}

.map-card-body {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 70vh;
}

.map-leaflet {
  width: 100%;
  height: 100%;
  min-height: 70vh;
  border-radius: 1.5rem;
  overflow: hidden;
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

/* Horizontal color bar overlay */
.color-bar-container {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  min-width: 240px;
  max-width: 70%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  z-index: 2000;
  pointer-events: none; /* don't block map interactions */
}
.color-bar-container.horizontal { flex-direction: row; align-items: center; gap: 10px; }
.color-bar-overlay {
  width: 260px;
  height: 34px;
  border-radius: 999px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.6);
}
.color-bar-label {
  color: black;
  font-size: 1rem;
  background-color: white;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0,0,0,0.4);
  padding: 2px 8px;
  border-radius: 999px;
}
.color-bar-label-left, .color-bar-label-right { white-space: nowrap; }

/* Documentation overlay */
.doc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
  display: grid;
  place-items: center;
  z-index: 30;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.doc-card {
  width: min(920px, 94vw);
  height: 75vh;
  background: rgba(255,255,255,0.98);
  -webkit-backdrop-filter: blur(16px);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.8);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
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
  border-bottom: 1px solid rgba(20,93,160,0.15);
}

.doc-card-tabs { 
  display: flex; 
  gap: 0.5rem;
  flex-wrap: wrap;
}

.doc-tab {
  background: rgba(20,93,160,0.08);
  color: #0A2342;
  border: 1px solid rgba(20,93,160,0.25);
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.doc-tab:hover {
  background: rgba(20,93,160,0.15);
  border-color: rgba(20,93,160,0.4);
  transform: translateY(-1px);
}

.doc-tab.active { 
  background: linear-gradient(135deg, #145DA0, #21CE99); 
  color: #fff; 
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(20,93,160,0.3);
}

.doc-close-btn { 
  background: rgba(255,255,255,0.9);
  color: #0A2342;
  -webkit-backdrop-filter: blur(8px); 
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.doc-close-btn:hover {
  background: rgba(255,255,255,1);
  transform: rotate(90deg);
}

.doc-card-body { 
  flex: 1 1 auto;
  padding: 1.5rem 1.5rem 1.25rem;
  color: #0A2342;
  overflow-y: auto;
  line-height: 1.7;
}

.doc-card-body::-webkit-scrollbar {
  width: 8px;
}

.doc-card-body::-webkit-scrollbar-track {
  background: rgba(20,93,160,0.05);
  border-radius: 4px;
}

.doc-card-body::-webkit-scrollbar-thumb {
  background: rgba(20,93,160,0.3);
  border-radius: 4px;
}

.doc-card-body::-webkit-scrollbar-thumb:hover {
  background: rgba(20,93,160,0.5);
}

.doc-card-body h3 {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-size: 1.4rem;
  font-weight: 700;
  color: #145DA0;
}

.doc-card-body h3:first-child {
  margin-top: 0;
}

.doc-card-body h4 {
  margin-top: 1.25rem;
  margin-bottom: 0.6rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #0A2342;
}

.doc-card-body p {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.doc-card-body ul {
  margin-left: 1.5rem;
  margin-bottom: 1rem;
}

.doc-card-body li {
  margin-bottom: 0.6rem;
  color: #2c3e50;
}

.doc-card-body li b {
  color: #145DA0;
  font-weight: 600;
}

.doc-card-body code {
  background: rgba(20,93,160,0.1);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: #145DA0;
}

/* Footer is handled globally; ensure spacing */
.refmap-footer { margin-top: 1rem; }
</style>
