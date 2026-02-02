<template>
  <div class="dashboard-bg">
    <div class="wind-assessment-container">
      <!-- Section 1: Header -->
      <div class="wind-assessment-section wind-assessment-section-header">
        <v-btn icon class="back-arrow-btn" @click="$emit('close')">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <v-btn icon class="doc-btn" @click="openDocumentation">
          <v-icon>mdi-book-open-variant</v-icon>
        </v-btn>
      </div>

      <!-- Section 2: Title -->
      <div class="wind-assessment-section wind-assessment-section-title">
        <span class="ltr-letters-wrapper ltr-letters-animate">
          <span class="ltr-letters">Wind Risk Assessment</span>
        </span>
      </div>

      <!-- Section 3: Filters -->
      <div class="wind-assessment-section wind-assessment-section-filters">
        <div class="filters-row">
          <v-select
            v-model="filters.lod"
            :items="lodDisplayOptions"
            label="Level of Detail"
            variant="outlined"
            class="filter-select"
            item-title="label"
            item-value="value"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.city"
            :items="cityOptions"
            label="City"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.lod"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.parameter"
            :items="parameterOptions"
            label="Parameter"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.city"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
          <v-select
            v-model="filters.altitude"
            :items="altitudeDisplayOptions"
            label="Altitude"
            variant="outlined"
            class="filter-select"
            :disabled="!filters.parameter"
            item-title="label"
            item-value="value"
            hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }"
          />
        </div>
      </div>

      <!-- Section 4: Cards -->
      <div class="wind-assessment-section wind-assessment-section-cards">
        <div class="wind-assessment-cards-grid">
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
                    v-if="heatmapImageUrl && heatmapBounds"
                    :url="heatmapImageUrl"
                    :bounds="heatmapBounds"
                    :opacity="0.7"
                  />
                </LMap>
              </template>
              <!-- Wind knob overlay in map area -->
              <div v-if="filters.altitude" class="wind-knob-wrapper wind-knob-overlay">
                <div class="wind-knob-value" style="margin-bottom: 0.3rem; font-weight: bold;">Wind Source</div>
                <svg
                  :width="knobSize"
                  :height="knobSize"
                  viewBox="0 0 120 120"
                  @mousedown="startKnobDrag"
                  @touchstart.prevent="startKnobDrag"
                  style="cursor:pointer; user-select:none;"
                >
                  <circle cx="60" cy="60" r="50" fill="#fff" fill-opacity="0.85" stroke="#000" stroke-width="2.5" />
                  <g>
                    <template v-for="d in 8">
                      <line
                        v-if="d === 1 || d === 3 || d === 5 || d === 7"
                        :x1="60"
                        :y1="18"
                        :x2="60"
                        :y2="30"
                        :transform="`rotate(${d*45},60,60)`"
                        stroke="#21CE99" stroke-width="2.5"
                      />
                    </template>
                  </g>
                  <g>
                    <text v-for="(dir, i) in compassLabels" :key="dir.label" :x="60 + 38 * Math.sin(dir.angle * Math.PI/180)" :y="60 - 38 * Math.cos(dir.angle * Math.PI/180) + 7" text-anchor="middle" font-size="17" fill="#333" font-weight="bold">{{ dir.label }}</text>
                  </g>
                  <g>
                    <!-- Triangle handle only -->
                    <polygon
                      :points="arrowPoints(60, 60, selectedWindDirection)"
                      fill="#21CE99"
                      stroke="#fff"
                      stroke-width="2.5"
                    />
                  </g>
                </svg>
                <div class="wind-knob-value">
                  <span style="font-weight:bold;">{{ selectedWindDirection === 0 ? 1 : selectedWindDirection }}°</span>
                  <span style="margin-left:0.5em;">{{ windDirectionLabel }}</span>
                </div>
              </div>
              <div v-if="filters.altitude && (filters.parameter === 'Turbulence Level' || filters.parameter === 'Wind Speed')" class="color-bar-container">
                <div class="color-bar-label color-bar-label-left">{{ colorBarMin !== '-' ? colorBarMin : (filters.parameter === 'Turbulence Level' || filters.parameter === 'Wind Speed' ? '0m/s' : '-') }}</div>
                <div class="color-bar-overlay" :style="{ background: colorBarGradient }"></div>
                <div class="color-bar-label color-bar-label-right">{{ colorBarMax !== '-' ? colorBarMax : (filters.parameter === 'Turbulence Level' ? '8%' : filters.parameter === 'Wind Speed' ? '5m/s' : '-') }}</div>  
              </div>
            </div>
          </v-card>
        </div>
      </div>
    </div>
  </div>
  <DocumentationOverlay :show="showDocOverlay" toolId="s2" @close="closeDocumentation" />
</template>

<script setup>
import { ref, onMounted, watch, computed, nextTick, onBeforeUnmount } from 'vue'
import 'leaflet/dist/leaflet.css';
import { LMap, LTileLayer, LImageOverlay } from '@vue-leaflet/vue-leaflet';
import DocumentationOverlay from './DocumentationOverlay.vue';

// --- Wind Assessment Tool Filters (from backend) ---
const lodOptions = ref([])
const cityOptions = ref([])
const parameterOptions = ref([])
const altitudeOptions = ref([])
const altitudeDisplayOptions = computed(() => {
  // Map altitudeOptions to objects with label/value for v-select
  return altitudeOptions.value.map(val => ({
    label: val + ' m',
    value: val
  }))
})
// Display options for LoD (map 1.1 -> Low, 2.2 -> High iff those are the only two)
const lodDisplayOptions = computed(() => {
  const opts = lodOptions.value
  const showLowHigh = opts.length === 2 && opts.includes('1.1') && opts.includes('2.2')
  if (showLowHigh) {
    return opts.map(v => ({ label: v === '1.1' ? 'Low' : 'High', value: v }))
  }
  // default: show raw values
  return opts.map(v => ({ label: v, value: v }))
})
const windOptions = ref([])

const filters = ref({
  lod: null,
  city: null,
  parameter: null,
  altitude: null,
})
const selectedWindDirection = ref(0); // This will be the wind index

const knobSize = 120
const compassLabels = [
  { label: 'N', angle: 0 },
  { label: 'E', angle: 90 },
  { label: 'S', angle: 180 },
  { label: 'W', angle: 270 }
]

// --- Fetch available combinations from backend ---
const availableCombos = ref({})

// Draw triangle arrow centered at (cx, cy), pointing in deg direction
function arrowPoints(cx, cy, deg) {
  // Arrow size
  const length = 28; // length of arrow
  const width = 16; // width of arrow base
  // Reverse direction by adding 180 degrees
  const angle = (deg - 90 + 180) * Math.PI / 180;
  // Tip of arrow
  const tipX = cx + length * Math.cos(angle);
  const tipY = cy + length * Math.sin(angle);
  // Base points
  const baseX = cx - length * 0.5 * Math.cos(angle);
  const baseY = cy - length * 0.5 * Math.sin(angle);
  // Perpendicular for width
  const perpAngle = angle + Math.PI / 2;
  const leftX = baseX + (width / 2) * Math.cos(perpAngle);
  const leftY = baseY + (width / 2) * Math.sin(perpAngle);
  const rightX = baseX - (width / 2) * Math.cos(perpAngle);
  const rightY = baseY - (width / 2) * Math.sin(perpAngle);
  // Return as SVG points string
  return `${tipX},${tipY} ${leftX},${leftY} ${rightX},${rightY}`;
}

onMounted(async () => {
  try {
    const res = await fetch('/api/wind_assessment/api/available_combinations')
    if (!res.ok) {
       console.warn('API returned status:', res.status);
       // Ensure arrays are empty so filters show nothing (or you can show a user alert)
       availableCombos.value = {};
       lodOptions.value = [];
       return;
    }
    const data = await res.json()
    // Optional: check if data is empty object
    if (!data || Object.keys(data).length === 0) {
       availableCombos.value = {};
       lodOptions.value = [];
       return;
    }
    availableCombos.value = data
    lodOptions.value = Object.keys(data)
  } catch (e) {
    console.error('Failed to fetch available combinations', e)
    // Clear options on error
    availableCombos.value = {};
    lodOptions.value = [];
  }
})

// Update city options when LoD changes
watch(() => filters.value.lod, (newLoD) => {
  filters.value.city = null
  filters.value.parameter = null
  filters.value.altitude = null
  selectedWindDirection.value = 0
  cityOptions.value = []
  parameterOptions.value = []
  altitudeOptions.value = []
  windOptions.value = []
  if (!newLoD || !availableCombos.value[newLoD]) return
  cityOptions.value = Object.keys(availableCombos.value[newLoD])
})

// Update parameter options when City changes
watch(() => filters.value.city, (newCity) => {
  filters.value.parameter = null
  filters.value.altitude = null
  selectedWindDirection.value = 0
  parameterOptions.value = []
  altitudeOptions.value = []
  windOptions.value = []
  if (!filters.value.lod || !newCity || !availableCombos.value[filters.value.lod]?.[newCity]) return
  // Gather all unique params for this city
  const combos = availableCombos.value[filters.value.lod][newCity].combinations || []
  parameterOptions.value = [...new Set(combos.map(c => c.param))]
})

// Update altitude options when Parameter changes
watch(() => filters.value.parameter, (newParam) => {
  filters.value.altitude = null
  selectedWindDirection.value = 0
  altitudeOptions.value = []
  windOptions.value = []
  if (!filters.value.lod || !filters.value.city || !newParam || !availableCombos.value[filters.value.lod]?.[filters.value.city]) return
  const combos = availableCombos.value[filters.value.lod][filters.value.city].combinations || []
  altitudeOptions.value = [...new Set(combos.filter(c => c.param === newParam).map(c => c.zloc))]
})

// Update wind options when Altitude changes
watch(() => filters.value.altitude, (newAlt) => {
  selectedWindDirection.value = 0
  windOptions.value = []
  if (!filters.value.lod || !filters.value.city || !filters.value.parameter || !newAlt || !availableCombos.value[filters.value.lod]?.[filters.value.city]) return
  const combos = availableCombos.value[filters.value.lod][filters.value.city].combinations || []
  const combo = combos.find(c => c.param === filters.value.parameter && c.zloc === newAlt)
  windOptions.value = combo ? combo.winds : []
})

// --- Wind knob logic (use windOptions for valid indices) ---
function getKnobHandlePos(deg) {
  const r = 42
  // 0° is North, 90° is East, 180° is South, 270° is West
  // SVG 0° is vertical down, so subtract 90° to rotate to North
  const adjustedDeg = deg - 90
  const rad = adjustedDeg * Math.PI/180
  return {
    x: 60 + r * Math.cos(rad),
    y: 60 + r * Math.sin(rad)
  }
}
const knobHandle = computed(() => {
  // If windOptions is set, snap to those degrees, else use selectedWindDirection
  let deg = selectedWindDirection.value
  return getKnobHandlePos(deg)
})

let dragging = false
function startKnobDrag(e) {
  dragging = true
  document.addEventListener('mousemove', onKnobDrag)
  document.addEventListener('mouseup', stopKnobDrag)
  document.addEventListener('touchmove', onKnobDrag, { passive: false })
  document.addEventListener('touchend', stopKnobDrag)
  onKnobDrag(e)
}
function stopKnobDrag() {
  dragging = false
  document.removeEventListener('mousemove', onKnobDrag)
  document.removeEventListener('mouseup', stopKnobDrag)
  document.removeEventListener('touchmove', onKnobDrag)
  document.removeEventListener('touchend', stopKnobDrag)
}
function onKnobDrag(e) {
  if (!dragging) return
  let clientX, clientY
  if (e.touches && e.touches.length) {
    clientX = e.touches[0].clientX
    clientY = e.touches[0].clientY
  } else {
    clientX = e.clientX
    clientY = e.clientY
  }
  const rect = e.target.closest('svg').getBoundingClientRect()
  const x = clientX - rect.left - 60
  const y = clientY - rect.top - 60
  // SVG 0° is vertical down, so subtract 90° to rotate to North
  let deg = Math.atan2(y, x) * 180/Math.PI + 90
  if (deg < 0) deg += 360
  if (deg >= 360) deg -= 360
  // Snap to nearest wind index
  if (windOptions.value.length > 0) {
    // Find closest wind direction
    let closest = windOptions.value.reduce((prev, curr) => {
      return Math.abs(curr - deg) < Math.abs(prev - deg) ? curr : prev
    }, windOptions.value[0])
    selectedWindDirection.value = closest
  } else {
    selectedWindDirection.value = Math.round(deg)
  }
}

const windDirectionLabel = computed(() => {
  // Map degrees to compass label
  const degrees = selectedWindDirection.value
  if (degrees === '' || degrees === null || degrees === undefined) return ''
  // 0° is North, 90° is East, 180° is South, 270° is West
  const normalizedDegrees = ((degrees % 360) + 360) % 360
  const compassDirections = [
    { min: 0, max: 22.5, label: 'N' },
    { min: 22.5, max: 67.5, label: 'NE' },
    { min: 67.5, max: 112.5, label: 'E' },
    { min: 112.5, max: 157.5, label: 'SE' },
    { min: 157.5, max: 202.5, label: 'S' },
    { min: 202.5, max: 247.5, label: 'SW' },
    { min: 247.5, max: 292.5, label: 'W' },
    { min: 292.5, max: 337.5, label: 'NW' },
    { min: 337.5, max: 360, label: 'N' }
  ]
  for (const direction of compassDirections) {
    if (normalizedDegrees >= direction.min && normalizedDegrees < direction.max) {
      return direction.label
    }
  }
  return 'N' // fallback to North
})

// --- Map and overlay logic ---
const mapCenter = ref([52, 10])
const minZoom = 4
const maxZoom = 18
const europeBounds = [
  [34.5, -11.25],
  [71.0, 31.5]
]
const showMap = ref(false)
const mapRefEl = ref(null)
let mapRef = null
onMounted(() => {
  showMap.value = true
  // Watch for mapRefEl changes to get the map instance
  watch(mapRefEl, (val) => {
    if (val && val.leafletObject) {
      mapRef = val.leafletObject
    }
  }, { immediate: true })
})
onBeforeUnmount(() => {
  mapRef = null
})

const heatmapImageUrl = ref('')
const heatmapBounds = ref(null)
const colorBarMin = ref('-')
const colorBarMax = ref('-')

// Fetch overlay info when all filters are selected
watch([
  () => filters.value.lod,
  () => filters.value.city,
  () => filters.value.parameter,
  () => filters.value.altitude,
  selectedWindDirection
], async ([lod, city, param, zloc, wind]) => {
  if (!lod || !city || !param || !zloc || wind === '' || wind === null || wind === undefined) {
    heatmapImageUrl.value = ''
    heatmapBounds.value = null
    colorBarMin.value = '-'
    colorBarMax.value = '-'
    return
  }
  try {
    const res = await fetch(`/api/wind_assessment/api/image_info?lod=${encodeURIComponent(lod)}&city=${encodeURIComponent(city)}&param=${encodeURIComponent(param)}&zloc=${encodeURIComponent(zloc)}&wind=${encodeURIComponent(wind)}`)
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    // Use base64 image_data if present
    if (data.image_data) {
      heatmapImageUrl.value = `data:image/png;base64,${data.image_data}`
    } else {
      heatmapImageUrl.value = ''
    }
    heatmapBounds.value = data.bounds
    // Remove dynamic min/max for Turbulence Level and Wind Speed
    if (!(filters.value.parameter === 'Turbulence Level' || filters.value.parameter === 'Wind Speed')) {
      colorBarMin.value = data.minVal
      colorBarMax.value = data.maxVal
    }
    // --- Auto-zoom to bounds ---
    await nextTick()
    if (mapRef && data.bounds) {
      if (typeof mapRef.fitBounds === 'function') {
        mapRef.fitBounds(data.bounds, { maxZoom: 16, animate: true })
      }
    }
  } catch (e) {
    heatmapImageUrl.value = ''
    heatmapBounds.value = null
    colorBarMin.value = '-'
    colorBarMax.value = '-'
    console.error('Failed to fetch image info', e)
  }
})

// Also refocus whenever bounds change (defensive against async UI timing)
watch(heatmapBounds, async (newBounds) => {
  if (!newBounds) return
  await nextTick()
  const map = mapRef || (mapRefEl.value && mapRefEl.value.leafletObject)
  if (map && typeof map.fitBounds === 'function') {
    try {
      map.fitBounds(newBounds, { padding: [20, 20], maxZoom: 16, animate: true })
    } catch (_) { /* ignore */ }
  }
})

// --- Dynamic colorbar gradient ---
const colorBarGradient = computed(() => {
  // Matplotlib RdBu_r approximation: Blue (low) -> White -> Red (high)
  const gradient = 'linear-gradient(to right, #2166ac 0%, #f7f7f7 50%, #b2182b 100%)';
  
  if (filters.value.parameter === 'Turbulence Level') {
    return gradient;
  }
  if (filters.value.parameter === 'Wind Speed') {
    return gradient;
  }
  // Default fallback
  return gradient;
})

// --- Color bar min/max for Turbulence Level and Wind Speed ---
watch(() => filters.value.parameter, (param) => {
  if (param === 'Turbulence Level') {
    colorBarMin.value = '0%'
    colorBarMax.value = '8%' 
  } else if (param === 'Wind Speed') {
    colorBarMin.value = '0 m/s'
    colorBarMax.value = '7 m/s'
  }
})
 
// --- Add documentation button handler ---
const showDocOverlay = ref(false)

function openDocumentation() {
  showDocOverlay.value = true
}

function closeDocumentation() {
  showDocOverlay.value = false
}

// Old function kept for reference
function openDocumentation_old() {
  showDocOverlay.value = true
  docCardIndex.value = 0
}
</script>

<style scoped>
/* Wind Assessment Container */
.wind-assessment-container {
  width: 100vw;
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 4rem);
  padding-bottom: 5rem;
  margin-left: calc(-50vw + 50%);
}

/* Common section styling */
.wind-assessment-section {
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 clamp(1rem, 3vw, 2rem);
}

/* Section 1: Header */
.wind-assessment-section-header {
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
.wind-assessment-section-title {
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
.wind-assessment-section-filters {
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
.wind-assessment-section-cards {
  flex: 1 1 auto;
  align-items: flex-start;
  padding-bottom: clamp(1rem, 3vh, 2rem);
}

.wind-assessment-cards-grid {
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

/* Wind knob stays as overlay within map */
.wind-knob-wrapper {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  padding: 1rem;
  border-radius: 1rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.wind-knob-overlay {
  pointer-events: auto;
}

.wind-knob-value {
  font-size: 0.95rem;
  color: #0A2342;
  text-align: center;
}

.color-bar-container {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  min-width: 240px;
  max-width: 70%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  z-index: 2000;
  pointer-events: none;
}

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
  padding: 0.3rem 0.6rem;
  border-radius: 8px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0,0,0,0.4);
  white-space: nowrap;
}

.color-bar-label-left, .color-bar-label-right { 
  white-space: nowrap; 
}

.heatmap-preview {
  max-width: 100%;
  max-height: 400px;
  border-radius: 1.5rem;
  margin-top: 1rem;
}

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

/* Fade transition */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>