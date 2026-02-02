<template>
	<div class="dashboard-bg">
		<div class="emissions-container">
			<!-- Section 1: Header -->
			<div class="emissions-section emissions-section-header">
				<v-btn icon class="back-arrow-btn" @click="$emit('close')">
					<v-icon>mdi-arrow-left</v-icon>
				</v-btn>
				<v-btn icon class="doc-btn" @click="openDocumentation">
					<v-icon>mdi-book-open-variant</v-icon>
				</v-btn>
			</div>

			<!-- Section 2: Title -->
			<div class="emissions-section emissions-section-title">
				<span class="ltr-letters-wrapper ltr-letters-animate">
					<span class="ltr-letters">Emissions</span>
				</span>
			</div>

			<!-- Section 3: Filters -->
			<div class="emissions-section emissions-section-filters">
        <v-card class="filters-card refmap-card-inline" elevation="0">
          <v-row class="filter-row" dense justify="center" align="center">
            <v-col cols="12" sm="4" md="4">
              <v-select
                v-model="selectedReduction"
                :items="reductionDisplayOptions"
                label="NOx Reduction"
                class="filter-select"
                variant="outlined"
                density="comfortable"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="12" sm="4" md="4">
              <v-select
                v-model="selectedMetric"
                :items="metricOptions"
                label="Metric"
                class="filter-select"
                :disabled="!selectedReduction"
                variant="outlined"
                density="comfortable"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="12" sm="4" md="4" class="toggle-col">
              <v-btn-toggle
                v-model="showDifference"
                class="diff-toggle"
                :disabled="!selectedMetric || !selectedReduction"
                color="primary"
                density="comfortable"
                mandatory
                rounded
              >
                <v-btn :value="false" variant="outlined">Case</v-btn>
                <v-btn :value="true" variant="outlined">Difference</v-btn>
              </v-btn-toggle>
            </v-col>
          </v-row>
        </v-card>
			</div>

      <!-- Section 4: Cards -->
      <div class="emissions-section emissions-section-cards">
        <div class="emissions-cards-grid two-column">
          <v-card elevation="6" class="refmap-card refmap-card-inline map-card-shell">
            <div class="map-card-body">
              <div class="map-card-title">Base</div>
              <template v-if="showMap">
                <LMap
                  ref="mapBaseRef"
                  :zoom="5"
                  :center="mapCenter"
                  :bounds="europeBounds"
                  :minZoom="minZoom"
                  :maxZoom="maxZoom"
                  :maxBounds="europeBounds"
                  :use-global-leaflet="false"
                  @moveend="syncFromBase"
                  @zoomend="syncFromBase"
                  class="map-leaflet"
                >
                  <LTileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                      attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
                      :z-index="200"
                  />
                    <LImageOverlay
                      v-if="overlayBase.url?.value && overlayBase.bounds?.value"
                      :url="overlayBase.url?.value || ''"
                      :bounds="europeBounds"
                      :z-index="500"
                      :opacity="1"
                    />
                </LMap>
              </template>
                <div v-if="colorbarBase.visible && colorbarBase.units" class="color-bar-units">{{ colorbarBase.units }}</div>
                <div v-if="colorbarBase.visible" class="color-bar-container horizontal">
                  <div v-if="colorbarBase.labelLeft" class="color-bar-label color-bar-label-left">{{ colorbarBase.labelLeft }}</div>
                  <div class="color-bar-overlay" :style="colorbarBase.style"></div>
                  <div v-if="colorbarBase.labelRight" class="color-bar-label color-bar-label-right">{{ colorbarBase.labelRight }}</div>
                </div>
            </div>
          </v-card>

          <v-card elevation="6" class="refmap-card refmap-card-inline map-card-shell">
            <div class="map-card-body">
              <div class="map-card-title">{{ rightTitle }}</div>
              <template v-if="showMap">
                <LMap
                  ref="mapCaseRef"
                  :zoom="5"
                  :center="mapCenter"
                  :bounds="europeBounds"
                  :minZoom="minZoom"
                  :maxZoom="maxZoom"
                  :maxBounds="europeBounds"
                  :use-global-leaflet="false"
                  @moveend="syncFromCase"
                  @zoomend="syncFromCase"
                  class="map-leaflet"
                >
                  <LTileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                      attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
                      :z-index="200"
                  />
                    <LImageOverlay
                      v-if="overlayCase.url?.value && overlayCase.bounds?.value"
                      :url="overlayCase.url?.value || ''"
                      :bounds="europeBounds"
                      :z-index="500"
                      :opacity="1"
                    />
                </LMap>
              </template>
                <div v-if="!overlayCase.url?.value && selectedMetric && selectedReduction" class="map-empty-text">No data available for this view.</div>
                <div v-if="colorbarCase.visible && colorbarCase.units" class="color-bar-units">{{ colorbarCase.units }}</div>
                <div v-if="colorbarCase.visible" class="color-bar-container horizontal">
                  <div v-if="colorbarCase.labelLeft" class="color-bar-label color-bar-label-left">{{ colorbarCase.labelLeft }}</div>
                  <div class="color-bar-overlay" :style="colorbarCase.style"></div>
                  <div v-if="colorbarCase.labelRight" class="color-bar-label color-bar-label-right">{{ colorbarCase.labelRight }}</div>
                </div>
            </div>
          </v-card>
        </div>
      </div>
		</div>
	</div>
	<DocumentationOverlay :show="showDocOverlay" toolId="l2" @close="closeDocumentation" />
</template>

<script setup>
const emit = defineEmits(['close'])
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import 'leaflet/dist/leaflet.css'
import { LMap, LTileLayer, LImageOverlay } from '@vue-leaflet/vue-leaflet'
import DocumentationOverlay from './DocumentationOverlay.vue'

// Filters
const reductionOptions = ref([])
const metricOptions = ref([])
const selectedReduction = ref('')
const selectedMetric = ref('')
const showDifference = ref(false)
const reductionDisplayOptions = computed(() => reductionOptions.value.map((r) => ({ title: `${r}%`, value: r })))

// Map state
const mapCenter = ref([52.0, 4.37])
const minZoom = ref(5)
const maxZoom = ref(18)
const europeBounds = ref([[[28.0, -15.5], [70.5, 50.0]]]) // (lat_min, lon_min) to (lat_max, lon_max) from backend extent
const overlayLatOffsetDeg = 0
const overlayLonOffsetDeg = 0
const isSyncing = ref(false)

function offsetBounds(bounds, latOffsetDeg = 0, lonOffsetDeg = 0) {
  if (!Array.isArray(bounds) || bounds.length !== 2) return bounds
  const [[south, west], [north, east]] = bounds
  return [
    [south + latOffsetDeg, west + lonOffsetDeg],
    [north + latOffsetDeg, east + lonOffsetDeg],
  ]
}

function deriveBoundsFromApi(boundsObj) {
  if (!boundsObj || typeof boundsObj !== 'object') {
    return offsetBounds(europeBounds.value, overlayLatOffsetDeg, overlayLonOffsetDeg)
  }
  const south = Number(boundsObj['lat-min'])
  const west = Number(boundsObj['lon-min'])
  const north = Number(boundsObj['lat-max'])
  const east = Number(boundsObj['lon-max'])
  const numbers = [south, west, north, east]
  if (numbers.some((v) => Number.isNaN(v))) {
    return offsetBounds(europeBounds.value, overlayLatOffsetDeg, overlayLonOffsetDeg)
  }
  return offsetBounds([[south, west], [north, east]], overlayLatOffsetDeg, overlayLonOffsetDeg)
}

function createOverlayState() {
  return {
    url: ref(''),
    bounds: ref(offsetBounds(europeBounds.value, overlayLatOffsetDeg, overlayLonOffsetDeg)),
    colorbarMin: ref(null),
    colorbarMax: ref(null),
    colorbarUnits: ref(''),
    colorbarType: ref('diverging'),
  }
}

const overlayBase = createOverlayState()
const overlayCase = createOverlayState()

const showMap = ref(true)
const mapBaseRef = ref(null)
const mapCaseRef = ref(null)

function colorbarComputed(state) {
  const visible = computed(() => Boolean(state.url.value) && Boolean(state.colorbarType.value))
  const labelLeft = computed(() => (typeof state.colorbarMin.value === 'number' ? `${state.colorbarMin.value}` : ''))
  const labelRight = computed(() => (typeof state.colorbarMax.value === 'number' ? `${state.colorbarMax.value}` : ''))
  const units = computed(() => state.colorbarUnits.value || '')
  const style = computed(() => {
    if (state.colorbarType.value === 'sequential') {
      return {
        background: 'linear-gradient(to right, #1b4dd8 0%, #5fa3ff 25%, #ffffff 50%, #ff9b9b 75%, #c50000 100%)'
      }
    }
    return {
      background: 'linear-gradient(to right, #1b4dd8 0%, #5fa3ff 25%, #ffffff 50%, #ff9b9b 75%, #c50000 100%)',
      backgroundSize: '100% 100%'
    }
  })

  // Expose plain getters so templates don't need `.value` and the style binding stays reactive
  return {
    get visible() { return visible.value },
    get labelLeft() { return labelLeft.value },
    get labelRight() { return labelRight.value },
    get units() { return units.value },
    get style() { return style.value },
  }
}

const colorbarBase = colorbarComputed(overlayBase)
const colorbarCase = colorbarComputed(overlayCase)

const currentRightCase = computed(() => (showDifference.value ? 'difference' : 'increase'))
const rightTitle = computed(() => (showDifference.value ? 'Difference' : 'Case'))

function resetOverlay(state) {
  state.url.value = ''
  state.bounds.value = offsetBounds(europeBounds.value, overlayLatOffsetDeg, overlayLonOffsetDeg)
  state.colorbarMin.value = null
  state.colorbarMax.value = null
  state.colorbarUnits.value = ''
  state.colorbarType.value = 'diverging'
}

function syncMaps(srcRef, dstRef) {
  if (isSyncing.value) return
  const src = srcRef?.value && srcRef.value.leafletObject
  const dst = dstRef?.value && dstRef.value.leafletObject
  if (!src || !dst) return
  const center = src.getCenter()
  const zoom = src.getZoom()
  isSyncing.value = true
  dst.setView(center, zoom, { animate: false })
  isSyncing.value = false
}

function syncFromBase() {
  syncMaps(mapBaseRef, mapCaseRef)
}

function syncFromCase() {
  syncMaps(mapCaseRef, mapBaseRef)
}

// no-op helper removed (case selection handled via toggle)

async function loadOverlay(metric, kase, state, mapRef, reduction) {
  resetOverlay(state)
  if (!metric || !kase || !reduction) return
  try {
    const params = new URLSearchParams({ metric, case: kase, reduction, b64: '1' })
    const resp = await fetch(`/api/emissions/api/emissions_image?${params.toString()}`)
    if (!resp.ok) throw new Error('Failed to fetch overlay metadata')
    const data = await resp.json()

    const urlFromApi = data.image_url ? new URL(data.image_url, window.location.origin).toString() : ''
    const urlFromBase64 = data.image_data ? `data:image/png;base64,${data.image_data}` : ''
    // Prefer base64 when present to avoid any proxy/path issues; otherwise use URL
    state.url.value = urlFromBase64 || urlFromApi

    if (!state.url.value) {
      console.warn('No overlay URL/data received', { metric, kase, reduction, resp: data })
    }

    state.bounds.value = deriveBoundsFromApi(data.bounds)
    if (data.colorbar) {
      if (typeof data.colorbar.min === 'number') state.colorbarMin.value = data.colorbar.min
      if (typeof data.colorbar.max === 'number') state.colorbarMax.value = data.colorbar.max
      if (typeof data.colorbar.units === 'string') state.colorbarUnits.value = data.colorbar.units
      if (typeof data.colorbar.type === 'string') state.colorbarType.value = data.colorbar.type
    }
    // Always force diverging with fixed range when backend omits fields
    if (!state.colorbarType.value) state.colorbarType.value = 'diverging'
    if (state.colorbarMin.value === null) state.colorbarMin.value = -0.5
    if (state.colorbarMax.value === null) state.colorbarMax.value = 0.5
    if (!state.colorbarUnits.value && metric && metric.toLowerCase().includes('no')) {
      // Backend sometimes omits units for NO* metrics; default to ppbv so the label is visible
      state.colorbarUnits.value = 'ppbv'
    }
    
    // Zoom to overlay bounds after loading
    await zoomToOverlayBounds(mapRef, state.bounds.value)
  } catch (err) {
    resetOverlay(state)
  }
}

async function zoomToOverlayBounds(mapRef, bounds) {
  if (!bounds || !Array.isArray(bounds) || bounds.length !== 2) return
  
  await nextTick()
  
  const map = mapRef?.value?.leafletObject
  if (!map) return
  
  try {
    // Import Leaflet dynamically if needed
    const L = await import('leaflet')
    
    // Create Leaflet bounds object
    const leafletBounds = L.default.latLngBounds(bounds)
    
    // Calculate appropriate zoom level
    const mapContainer = map.getContainer()
    const mapSize = { x: mapContainer.offsetWidth, y: mapContainer.offsetHeight }
    const boundsSize = map.project(leafletBounds.getNorthEast(), 18)
      .subtract(map.project(leafletBounds.getSouthWest(), 18))
    
    const zoom = Math.min(
      maxZoom.value, // Maximum zoom
      Math.max(
        minZoom.value, // Minimum zoom
        Math.floor(Math.log2(Math.min(mapSize.x / boundsSize.x, mapSize.y / boundsSize.y)))
      )
    )
    
    // Fly to bounds with calculated zoom
    map.flyToBounds(leafletBounds, {
      padding: [40, 40],
      animate: true,
      duration: 1.2,
      easeLinearity: 0.25
    })
    
    // Force zoom adjustment after animation for better visibility
    setTimeout(() => {
      if (map) {
        const targetZoom = Math.min(zoom + 1, Math.min(10, maxZoom.value))
        map.setZoom(targetZoom)
      }
    }, 1300)
  } catch (error) {
    console.error('Error zooming to bounds:', error)
  }
}

// Load reductions on mount
onMounted(async () => {
  try {
    const resp = await fetch('/api/emissions/api/emissions_reductions')
    const reductions = await resp.json()
    reductionOptions.value = reductions
  } catch (e) {
    reductionOptions.value = []
  }
})

// When reduction changes, load metrics and reset selections
watch(selectedReduction, async (reduction) => {
  selectedMetric.value = ''
  resetOverlay(overlayBase)
  resetOverlay(overlayCase)
  metricOptions.value = []
  if (!reduction) return
  try {
    const resp = await fetch(`/api/emissions/api/emissions_metrics?reduction=${encodeURIComponent(reduction)}`)
    const metrics = await resp.json()
    metricOptions.value = metrics || []
  } catch (e) {
    metricOptions.value = []
  }
})

// When metric changes, load base and right overlays
watch([selectedReduction, selectedMetric], async ([reduction, metric]) => {
  resetOverlay(overlayBase)
  resetOverlay(overlayCase)
  if (!reduction || !metric) return
  await loadOverlay(metric, 'base', overlayBase, mapBaseRef, reduction)
  await loadOverlay(metric, currentRightCase.value, overlayCase, mapCaseRef, reduction)
  
  // Sync both maps after loading overlays
  await nextTick()
  syncFromBase()
})

// When toggle changes, refresh right overlay
watch(currentRightCase, async (kase) => {
  if (!selectedReduction.value || !selectedMetric.value) return
  resetOverlay(overlayCase)
  await loadOverlay(selectedMetric.value, kase, overlayCase, mapCaseRef, selectedReduction.value)
})

// Docs overlay
const showDocOverlay = ref(false)
function openDocumentation() {
	showDocOverlay.value = true
}
function closeDocumentation() {
	showDocOverlay.value = false
}
</script>

<style scoped>
/* Emissions Container */
.emissions-container {
  width: 100vw;
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 4rem);
  padding-bottom: 5rem;
  margin-left: calc(-50vw + 50%);
}

/* Common section styling */
.emissions-section {
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 clamp(1rem, 3vw, 2rem);
}

/* Section 1: Header */
.emissions-section-header {
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
.emissions-section-title {
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

/* Section 3: Filters */
.emissions-section-filters {
  flex: 0 0 auto;
  padding: 1.5rem 0;
}

.filters-card {
  width: 100%;
  max-width: 1200px;
  padding: 1rem;
  background: transparent;
}

.filter-row {
  margin-top: 1%;
  width: 100%;
  max-width: 1200px;
  /* row-gap: 12px; */
  column-gap: 1.5rem;
  justify-content: center;
}

/* Polished field styling aligned with OptimizedTrajectories */
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

.filter-select :deep(.v-field:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.15);
  border-color: #145DA0;
}

.filter-select :deep(.v-label.v-field-label) {
  color: #145DA0 !important;
  font-weight: 700 !important;
  opacity: 1 !important;
  font-size: 1.1rem !important;
  max-width: none !important;
  width: auto !important;
  overflow: visible !important;
  white-space: nowrap !important;
  text-overflow: clip !important;
}

.filter-select :deep(.v-label.v-field-label--floating) {
  color: #ffffff !important;
  font-weight: 700 !important;
  opacity: 1 !important;
  font-size: 1.1rem !important;
  transform: translateY(-30px) scale(1) !important;
  padding: 0 8px;
  margin-left: -8px;
  z-index: 100;
}

.filter-select :deep(.v-field__input) {
  color: #145DA0 !important;
  font-weight: 600;
  font-size: 1.05rem !important;
}

.filter-select :deep(.v-field__append-inner .v-icon) {
  color: #145DA0 !important;
  opacity: 1;
  font-size: 1.6rem;
}

.filter-select :deep(.v-field--disabled) {
  background-color: #e0e0e0 !important;
  border: 1px solid #999;
}

.toggle-col {
  display: flex;
  align-items: center;
  justify-content: center;
}

.diff-toggle :deep(.v-btn) {
  text-transform: none;
  font-weight: 600;
}

.diff-toggle {
  width: 100%;
  display: flex;
  justify-content: center;
  margin-top: 3%;
  margin-left: 10%;
  column-gap: 6%;
  border-radius: 14px;
  border: 1px solid rgba(20, 93, 160, 0.18);
}

.diff-toggle :deep(.v-btn) {
  min-width: 120px;
  font-size: 1.4rem;
  border-radius: 10px;
  color: #145DA0 !important;
  background-color: white;
}

.diff-toggle :deep(.v-btn.v-btn--active) {
  background: linear-gradient(135deg, #145DA0, #21CE99);
  color: #fff !important;
  border-color: transparent;
  box-shadow: 0 6px 16px rgba(20, 93, 160, 0.25);
}

.diff-toggle :deep(.v-btn.v-btn--disabled) {
  opacity: 0.6;
}

/* Section 4: Cards */
.emissions-section-cards {
  flex: 1 1 auto;
  align-items: flex-start;
  padding-bottom: clamp(1rem, 3vh, 2rem);
}

.emissions-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 1.5rem;
  width: 100%;
  padding: 0 1rem;
}

.map-card-shell { 
  padding: 0;
  border-radius: 1.5rem;
}

.emissions-cards-grid.two-column .map-card-shell {
  min-width: 320px;
}

.map-card-body { 
  position: relative; 
  width: 100%; 
  height: 100%; 
  min-height: 70vh; 
}

.map-card-title {
  position: absolute;
  z-index: 2100;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 16px;
  background: rgba(255,255,255,0.92);
  color: #0A2342;
  border-radius: 999px;
  font-weight: 700;
  font-size: 1.5rem;
  box-shadow: 0 6px 16px rgba(0,0,0,0.14);
  backdrop-filter: blur(6px);
}

.map-empty-text {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #0A2342;
  font-weight: 600;
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(4px);
}

.map-leaflet { 
  width: 100%; 
  height: 100%; 
  min-height: 70vh; 
  border-radius: 1.5rem; 
  overflow: hidden; 
}

.color-bar-units {
	position: absolute;
	left: 50%;
	bottom: 52px; /* place above the bar */
	transform: translateX(-50%);
	color: black;
	font-size: 0.95rem;
	background-color: white;
	font-weight: 700;
	text-shadow: 0 1px 2px rgba(0,0,0,0.2);
	padding: 2px 8px;
	border-radius: 999px;
	z-index: 2000;
	pointer-events: none;
  font-size: 1.4rem;
}
.color-bar-container { position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%); min-width: 240px; max-width: 70%; display: flex; flex-direction: row; align-items: center; gap: 10px; z-index: 2000; pointer-events: none; }
.color-bar-overlay { 
  width: 260px; 
  height: 34px; 
  border-radius: 999px; 
  box-shadow: 0 6px 18px rgba(0,0,0,0.28);
  border: 1px solid rgba(0,0,0,0.2);
  background-color: #ffffff;
  opacity: 1;
  mix-blend-mode: normal;
}
.color-bar-label { 
  color: black; 
  font-size: 1rem; 
  background-color: white; 
  font-weight: 700; 
  text-shadow: 0 1px 2px rgba(0,0,0,0.4); 
  padding: 2px 8px; 
  border-radius: 999px; 
  font-size: 1.25rem;
}

.color-bar-label-left, .color-bar-label-right { 
  white-space: nowrap; 
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .emissions-section-header {
    padding-top: clamp(0.5rem, 1.5vh, 1rem);
    padding-bottom: clamp(0.25rem, 1vh, 0.5rem);
  }
  
  .emissions-section-title {
    padding: clamp(0.25rem, 1vh, 0.5rem) 0;
  }
  
  .ltr-letters {
    font-size: clamp(1.25rem, 5vw, 2rem);
  }
  
  .emissions-section-filters {
    padding: clamp(0.5rem, 1.5vh, 1rem) 0;
  }
  
  .filters-card {
    max-width: 90%;
    padding: 0.75rem;
  }
}

@media (max-width: 480px) {
  .emissions-section-cards {
    padding-top: 0.5rem;
  }
  
  .emissions-cards-grid {
    width: 100%;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .emissions-cards-grid.two-column {
    gap: 1rem;
  }
}

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
</style>
