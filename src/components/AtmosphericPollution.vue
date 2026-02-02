<template>
  <div class="dashboard-bg">
    <div class="atmospheric-pollution-container">
      <!-- Section 1: Header -->
      <div class="atmospheric-pollution-section atmospheric-pollution-section-header">
        <v-btn icon class="back-arrow-btn" @click="$emit('close')">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <v-btn icon class="doc-btn" @click="openDocumentation">
          <v-icon>mdi-book-open-variant</v-icon>
        </v-btn>
      </div>

      <!-- Section 2: Title -->
      <div class="atmospheric-pollution-section atmospheric-pollution-section-title">
        <span class="ltr-letters-wrapper ltr-letters-animate">
          <span class="ltr-letters">Atmospheric Pollution</span>
        </span>
      </div>

      <!-- Section 3: Filters -->
      <div class="atmospheric-pollution-section atmospheric-pollution-section-filters">
        <div class="filter-controls">
          <!-- Area Selector -->
          <v-select
            v-model="selectedArea"
            :items="areaOptions"
            label="Area"
            variant="outlined"
            density="compact"
            class="filter-select"
            hide-details
          ></v-select>

          <!-- Species Selector -->
          <v-select
            v-model="selectedSpecies"
            :items="speciesOptions"
            item-title="name"
            item-value="id"
            label="Pollutant Species"
            variant="outlined"
            density="compact"
            class="filter-select"
            hide-details
          ></v-select>

          <!-- Date Range -->
          <v-text-field
            v-model="startDate"
            label="Start Date"
            type="date"
            variant="outlined"
            density="compact"
            class="filter-select"
            hide-details
            :min="minDate"
            :max="maxDate"
          ></v-text-field>

          <v-text-field
            v-model="endDate"
            label="End Date"
            type="date"
            variant="outlined"
            density="compact"
            class="filter-select"
            hide-details
            :min="minDate"
            :max="maxDate"
          ></v-text-field>

          <!-- Interval Selector -->
          <v-select
            v-model="interval"
            :items="intervalOptions"
            label="Interval"
            variant="outlined"
            density="compact"
            class="filter-select"
            hide-details
          ></v-select>

          <!-- Fetch Data Button -->
          <v-btn
            @click="fetchTimeSeries"
            color="primary"
            :loading="loading"
            :disabled="!selectedArea"
            class="fetch-btn"
          >
            <v-icon left>mdi-chart-line</v-icon>
            Analyze
          </v-btn>
        </div>
      </div>

      <!-- Section 4: Cards -->
      <div class="atmospheric-pollution-section atmospheric-pollution-section-cards">
        <div class="atmospheric-pollution-cards-grid two-column">
          <!-- Map Card -->
          <v-card elevation="6" class="refmap-card refmap-card-inline map-card-shell">
            <div class="map-card-body">
              <div class="map-card-title">Map View</div>
              <template v-if="showMap">
                <LMap
                  ref="mapRef"
                  :zoom="mapZoom"
                  :center="mapCenter"
                  :maxBounds="mapMaxBounds"
                  :use-global-leaflet="false"
                  class="map-leaflet"
                >
                  <LTileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                    attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
                    :maxZoom="18"
                  />
                  <LImageOverlay
                    v-if="heatmapOverlay.visible && heatmapOverlay.url && heatmapOverlay.bounds"
                    :url="heatmapOverlay.url"
                    :bounds="heatmapOverlay.bounds"
                    :opacity="0.6"
                  />
                </LMap>
                
                <!-- Map Legend -->
                <div v-if="legendData.visible" class="map-legend">
                  <div class="legend-title">{{ legendData.species }}</div>
                  <div class="legend-gradient" :style="legendGradientStyle"></div>
                  <div class="legend-labels">
                    <span class="legend-min">{{ formatValue(legendData.min) }}</span>
                    <span class="legend-max">{{ formatValue(legendData.max) }}</span>
                  </div>
                  <div class="legend-unit">{{ legendData.unit }}</div>
                </div>
              </template>
            </div>
          </v-card>

          <!-- Chart Card -->
          <v-card elevation="6" class="refmap-card refmap-card-inline map-card-shell">
            <div class="map-card-body">
              <div class="map-card-title">Time Series Analysis</div>
              <div class="chart-content">
                <div v-if="!chartData" class="no-data-message">
                  <v-icon size="64" color="grey">mdi-chart-line-variant</v-icon>
                  <p>Select an area and click "Analyze" to view pollution trends</p>
                </div>
                <div v-else class="chart-with-stats">
                  <canvas id="pollution-chart"></canvas>
                  <div class="statistics-panel">
                    <div class="stat-item">
                      <span class="stat-label">Average:</span>
                      <span class="stat-value">{{ formatValue(statistics.average) }} {{ currentUnit }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">Minimum:</span>
                      <span class="stat-value">{{ formatValue(statistics.min) }} {{ currentUnit }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">Maximum:</span>
                      <span class="stat-value">{{ formatValue(statistics.max) }} {{ currentUnit }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">Data Points:</span>
                      <span class="stat-value">{{ statistics.count }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </v-card>
        </div>
      </div>
    </div>
  </div>
  <DocumentationOverlay :show="showDocOverlay" toolId="l3" @close="closeDocumentation" />
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw'
import 'leaflet-draw/dist/leaflet.draw.css'
import { Chart, registerables } from 'chart.js'
import DocumentationOverlay from './DocumentationOverlay.vue'
import { LMap, LTileLayer, LImageOverlay } from '@vue-leaflet/vue-leaflet'

Chart.register(...registerables)

// Define emits
const emit = defineEmits(['close'])

// Map state
const map = ref(null)
const mapRef = ref(null)
const areaLayer = ref(null)
const mapCenter = ref([52.3676, 4.9041])
const mapZoom = ref(8)
const mapMaxBounds = ref(null)
const heatmapOverlay = ref({
  url: '',
  bounds: null,
  visible: false
})
const legendData = ref({
  visible: false,
  min: 0,
  max: 0,
  unit: '',
  species: '',
  colormap: 'YlOrRd'
})
const showMap = ref(false)

// Data state
const metadata = ref(null)
const areaOptions = ref(['Amsterdam Airport'])
const selectedArea = ref(null)
const speciesOptions = ref([])
const selectedSpecies = ref(null)
const startDate = ref('')
const endDate = ref('')
const interval = ref(null)
const loading = ref(false)
const chartData = ref(null)
const statistics = ref({ average: 0, min: 0, max: 0, count: 0 })
const chartInstance = ref(null)
const areaGeometry = ref(null)

// Interval options
const intervalOptions = [
  { title: 'Daily', value: '1D' },
  { title: 'Weekly', value: '7D' },
  { title: 'Bi-weekly', value: '14D' },
  { title: 'Monthly', value: '1M' }
]

// Documentation
const showDocOverlay = ref(false)

// Computed
const currentUnit = computed(() => {
  if (!metadata.value) return ''
  const species = metadata.value.species.find(s => s.id === selectedSpecies.value)
  return species ? species.unit : ''
})

const legendGradientStyle = computed(() => {
  // YlOrRd colormap gradient (from matplotlib)
  return {
    background: 'linear-gradient(to right, #ffffcc, #ffeda0, #fed976, #feb24c, #fd8d3c, #fc4e2a, #e31a1c, #bd0026, #800026)'
  }
})

const minDate = computed(() => {
  if (!metadata.value?.timeRange?.min) return ''
  return new Date(metadata.value.timeRange.min).toISOString().split('T')[0]
})

const maxDate = computed(() => {
  if (!metadata.value?.timeRange?.max) return ''
  return new Date(metadata.value.timeRange.max).toISOString().split('T')[0]
})

// Initialize map
onMounted(async () => {
  await loadMetadata()
  showMap.value = true
  await initializeMap()
})

// Cleanup
onUnmounted(() => {
  if (chartInstance.value) {
    chartInstance.value.destroy()
  }
  if (map.value) {
    map.value.remove()
  }
})

async function loadMetadata() {
  try {
    const response = await fetch('/api/atmospheric_pollution/api/metadata')
    if (!response.ok) throw new Error('Failed to load metadata')
    
    metadata.value = await response.json()
    speciesOptions.value = metadata.value.species
  } catch (error) {
    console.error('Error loading metadata:', error)
    alert('Failed to load atmospheric pollution data. Please check the backend service.')
  }
}

async function initializeMap() {
  // Wait for map to be ready
  await new Promise(resolve => setTimeout(resolve, 300))
  
  // Load Amsterdam Airport area geometry
  await loadAreaGeometry()
}

async function loadAreaGeometry() {
  try {
    const response = await fetch('/api/atmospheric_pollution/data/Amsterdam_airport.geojson')
    if (!response.ok) throw new Error('Failed to load area geometry')
    
    const geojson = await response.json()
    areaGeometry.value = geojson.features[0].geometry
    
    // Only add to map if leaflet instance is available
    if (map.value && map.value.leafletObject) {
      // Display area on map
      if (areaLayer.value) {
        map.value.leafletObject.removeLayer(areaLayer.value)
      }
      
      areaLayer.value = L.geoJSON(geojson, {
        style: {
          color: '#3498db',
          weight: 3,
          fillOpacity: 0.2
        }
      }).addTo(map.value.leafletObject)
      
      // Fit map to area bounds
      map.value.leafletObject.fitBounds(areaLayer.value.getBounds())
    }
  } catch (error) {
    console.error('Error loading area geometry:', error)
    alert('Failed to load area geometry')
  }
}

async function loadHeatmap() {
  if (!areaGeometry.value || !endDate.value) return
  
  try {
    const response = await fetch('/api/atmospheric_pollution/api/heatmap', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        geometry: areaGeometry.value,
        species: selectedSpecies.value,
        timestamp: endDate.value
      })
    })
    
    if (!response.ok) throw new Error('Failed to load heatmap')
    
    const data = await response.json()
    
    // Set heatmap overlay
    const bounds = [
      [data.bounds.latMin, data.bounds.lonMin],
      [data.bounds.latMax, data.bounds.lonMax]
    ]
    
    heatmapOverlay.value = {
      url: `data:image/png;base64,${data.image_data}`,
      bounds: bounds,
      visible: true
    }
    
    // Set legend data
    if (data.legend) {
      legendData.value = {
        visible: true,
        min: data.legend.min,
        max: data.legend.max,
        unit: data.legend.unit,
        species: data.legend.species,
        colormap: data.legend.colormap
      }
    }
    
    // Zoom to heatmap bounds and restrict panning
    if (map.value && map.value.leafletObject) {
      // Wait for next tick to ensure overlay is rendered
      await nextTick()
      
      // Create Leaflet bounds object
      const leafletBounds = L.latLngBounds(bounds)
      
      // Add padding to bounds for max bounds (prevent panning outside)
      const paddedBounds = leafletBounds.pad(0.1) // 10% padding
      mapMaxBounds.value = [[paddedBounds.getSouth(), paddedBounds.getWest()], [paddedBounds.getNorth(), paddedBounds.getEast()]]
      
      // Set max bounds on the map
      map.value.leafletObject.setMaxBounds(paddedBounds)
      
      // Fit to bounds with animation
      map.value.leafletObject.flyToBounds(leafletBounds, {
        padding: [50, 50],
        animate: true,
        duration: 1.5,
        maxZoom: 13
      })
    }
  } catch (error) {
    console.error('Error loading heatmap:', error)
    heatmapOverlay.value.visible = false
    legendData.value.visible = false
  }
}

function setDefaultDates() {
  if (!metadata.value) return
  
  const end = new Date(metadata.value.timeRange.max)
  const start = new Date(end)
  start.setMonth(start.getMonth() - 3) // Default to 3 months
  
  endDate.value = end.toISOString().split('T')[0]
  startDate.value = start.toISOString().split('T')[0]
}

async function fetchTimeSeries() {
  if (!areaGeometry.value) {
    alert('Area not loaded')
    return
  }

  loading.value = true

  try {
    const response = await fetch('/api/atmospheric_pollution/api/timeseries', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        geometry: areaGeometry.value,
        species: selectedSpecies.value,
        startDate: startDate.value,
        endDate: endDate.value,
        interval: interval.value
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to fetch time series')
    }

    const result = await response.json()
    chartData.value = result.data
    statistics.value = result.statistics

    // Update chart after DOM updates
    await nextTick()
    updateChart()
    
    // Load heatmap overlay
    await loadHeatmap()

  } catch (error) {
    console.error('Error fetching time series:', error)
    alert(`Failed to fetch time series: ${error.message}`)
  } finally {
    loading.value = false
  }
}

function updateChart() {
  if (!chartData.value || chartData.value.length === 0) return

  const ctx = document.getElementById('pollution-chart')
  if (!ctx) return

  // Destroy existing chart
  if (chartInstance.value) {
    chartInstance.value.destroy()
  }

  // Prepare data
  const labels = chartData.value.map(d => new Date(d.timestamp).toLocaleDateString())
  const values = chartData.value.map(d => d.value)

  // Get species name
  const speciesName = speciesOptions.value.find(s => s.id === selectedSpecies.value)?.name || selectedSpecies.value

  // Create new chart
  chartInstance.value = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: `${speciesName} (${currentUnit.value})`,
        data: values,
        borderColor: '#3498db',
        backgroundColor: 'rgba(52, 152, 219, 0.1)',
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${formatValue(context.parsed.y)}`
            }
          }
        }
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: 'Date'
          }
        },
        y: {
          display: true,
          title: {
            display: true,
            text: currentUnit.value
          },
          beginAtZero: false
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  })
}

function formatValue(value) {
  if (value === null || value === undefined) return 'N/A'
  return value.toExponential(3)
}

function openDocumentation() {
  showDocOverlay.value = true
}

function closeDocumentation() {
  showDocOverlay.value = false
}

// Watch for species changes to update chart if data exists
watch(selectedSpecies, () => {
  if (chartData.value && areaGeometry.value) {
    fetchTimeSeries()
  }
})

// Watch for area changes to reload geometry
watch(selectedArea, async () => {
  await loadAreaGeometry()
  chartData.value = null
  statistics.value = { average: 0, min: 0, max: 0, count: 0 }
  heatmapOverlay.value.visible = false
  legendData.value.visible = false
  if (chartInstance.value) {
    chartInstance.value.destroy()
    chartInstance.value = null
  }
})

// Watch mapRef to get leaflet instance
watch(mapRef, (newVal) => {
  if (newVal && newVal.leafletObject) {
    map.value = newVal
  }
})
</script>

<style scoped>
/* Atmospheric Pollution Container */
.atmospheric-pollution-container {
  width: 100vw;
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 4rem);
  padding-bottom: 5rem;
  margin-left: calc(-50vw + 50%);
}

/* Common section styling */
.atmospheric-pollution-section {
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 clamp(1rem, 3vw, 2rem);
}

/* Section 1: Header */
.atmospheric-pollution-section-header {
  flex: 0 0 auto;
  justify-content: space-between;
  padding-top: 1rem;
  padding-bottom: 0.5rem;
}

.back-arrow-btn, .doc-btn {
  background: rgba(255,255,255,0.08);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.25);
  backdrop-filter: blur(10px);
}

.back-arrow-btn:hover, .doc-btn:hover {
  background: rgba(255,255,255,0.15);
}

/* Section 2: Title */
.atmospheric-pollution-section-title {
  flex: 0 0 auto;
  padding: 0.5rem 0;
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
.atmospheric-pollution-section-filters {
  flex: 0 0 auto;
  padding: 1rem 0;
}

.filter-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  width: 90%;
  max-width: 1400px;
  align-items: center;
}

.filter-select {
  min-width: 150px;
  flex: 1 1 auto;
}

/* Polished field styling aligned with Emissions */
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

.fetch-btn {
  min-width: 120px;
}

/* Section 4: Cards */
.atmospheric-pollution-section-cards {
  flex: 1 1 auto;
  align-items: flex-start;
  padding-bottom: clamp(1rem, 3vh, 2rem);
}

.atmospheric-pollution-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 1.5rem;
  width: 100%;
  padding: 0 1rem;
}

.atmospheric-pollution-cards-grid.two-column .map-card-shell {
  min-width: 320px;
}

.map-card-shell {
  padding: 0;
  border-radius: 1.5rem;
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

.map-leaflet {
  width: 100%;
  height: 100%;
  min-height: 70vh;
  border-radius: 1.5rem;
  overflow: hidden;
}

.chart-content {
  width: 100%;
  height: 100%;
  min-height: 70vh;
  border-radius: 1.5rem;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.98);
}

.chart-with-stats {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 3rem 1rem 1rem;
}

.map-legend {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(20, 93, 160, 0.2);
  z-index: 2000;
  min-width: 200px;
}

.legend-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #145DA0;
  margin-bottom: 8px;
  text-align: center;
}

.legend-gradient {
  height: 20px;
  border-radius: 4px;
  margin-bottom: 6px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.legend-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #666;
  margin-bottom: 4px;
}

.legend-min,
.legend-max {
  font-weight: 500;
}

.legend-unit {
  font-size: 0.75rem;
  color: #145DA0;
  text-align: center;
  font-weight: 600;
}

.no-data-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 70vh;
  text-align: center;
  color: #666;
  padding: 2rem;
}

.no-data-message p {
  margin-top: 1rem;
  font-size: 1.1rem;
}

#pollution-chart {
  flex: 1;
  width: 100%;
  min-height: 400px;
  padding: 1rem;
}

.statistics-panel {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  padding: 1.5rem;
  background: rgba(20, 93, 160, 0.05);
  border-radius: 0.5rem;
  margin: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
}

.stat-value {
  font-size: 1.1rem;
  color: #145DA0;
  font-weight: 600;
}

/* Responsive */
@media (max-width: 768px) {
  .atmospheric-pollution-section-header {
    padding-top: clamp(0.5rem, 1.5vh, 1rem);
    padding-bottom: clamp(0.25rem, 1vh, 0.5rem);
  }
  
  .atmospheric-pollution-section-title {
    padding: clamp(0.25rem, 1vh, 0.5rem) 0;
  }
  
  .ltr-letters {
    font-size: clamp(1.25rem, 5vw, 2rem);
  }
  
  .atmospheric-pollution-section-filters {
    padding: clamp(0.5rem, 1.5vh, 1rem) 0;
  }
  
  .filter-controls {
    width: 95%;
  }
  
  .filter-select {
    min-width: 100%;
  }
  
  .statistics-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .atmospheric-pollution-section-cards {
    padding-top: 0.5rem;
  }
  
  .atmospheric-pollution-cards-grid {
    width: 100%;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .atmospheric-pollution-cards-grid.two-column {
    gap: 1rem;
  }
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
</style>
