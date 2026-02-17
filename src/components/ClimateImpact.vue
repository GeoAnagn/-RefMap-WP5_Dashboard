<template>
  <div class="dashboard-bg">
    <div class="climate-impact-container">

      <div class="climate-section climate-section-header">
        <v-btn icon class="back-arrow-btn" @click="$emit('close')">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <v-btn icon class="doc-btn" @click="openDocumentation">
          <v-icon>mdi-book-open-variant</v-icon>
        </v-btn>
      </div>


      <div class="climate-section-title">
        <span class="ltr-letters-wrapper ltr-letters-animate">
          <span class="ltr-letters">Climate Impact</span>
        </span>
      </div>


      <div class="climate-section climate-section-filters">
        <div class="filters-row">
          <v-select v-model="selectedDateDisplay" :items="dateOptionsDisplay" label="Date" class="filter-select"
            variant="outlined" density="comfortable" hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }" />
          <v-select v-model="selectedDataTypeDisplay" :items="dataTypeOptionsDisplay" label="Data Type"
            class="filter-select" :disabled="!selectedDate" variant="outlined" density="comfortable" hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }" />
          <v-select v-model="selectedScaleOrdered" :items="scaleOptionsOrdered" label="Scale" class="filter-select"
            :disabled="!selectedDataType" variant="outlined" density="comfortable" hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }" />
          <v-select v-model="selectedCostDisplay" :items="costOptionsDisplay" label="Cost" class="filter-select"
            :disabled="!selectedScale" variant="outlined" density="comfortable" hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }" />
          <v-select v-model="selectedFlightLevel" :items="flightLevelOptions" label="Flight Level" class="filter-select"
            :disabled="!selectedCost" variant="outlined" density="comfortable" hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }" />
          <v-select v-model="selectedTimeDisplay" :items="timeOptionsDisplay" label="Time" class="filter-select"
            :disabled="!selectedFlightLevel" variant="outlined" density="comfortable" hide-details
            :menu-props="{ contentClass: 'filter-menu-content' }" />
        </div>
      </div>


      <div class="climate-section climate-section-cards">
        <div class="climate-cards-grid">
          <div class="climate-card-wrapper pie-card">
            <v-card elevation="6" class="refmap-card refmap-card-inline scrollable-pie-card">
              <div v-for="(bar, idx) in barCharts" :key="idx" class="pie-chart-wrapper">
                <VuePlotly :data="bar.data" :layout="bar.layout" :config="{ displayModeBar: false, responsive: true }"
                  :useResizeHandler="true" style="width:100%;height:240px;" />
                <hr v-if="idx < barCharts.length - 1"
                  style="border:0;border-top:2px solid #eee;margin:1.2rem auto;opacity:0.7;" />
              </div>
            </v-card>
          </div>
          <div class="climate-card-wrapper map-card">
            <v-card elevation="6" class="refmap-card refmap-card-inline map-card-shell">
              <div class="map-card-body">
                <template v-if="showMap">
                  <LMap :zoom="5" :center="mapCenter" :minZoom="minZoom" :maxZoom="maxZoom" :maxBounds="europeBounds"
                    :use-global-leaflet="false" class="map-leaflet">
                    <LTileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                      attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>" />
                    <LImageOverlay v-if="heatmapImageUrl && heatmapBounds" :url="heatmapImageUrl"
                      :bounds="heatmapBounds" :opacity="0.7" />
                  </LMap>
                </template>
                <div
                  v-if="selectedDate && selectedDataType && selectedScale && selectedCost && selectedFlightLevel && selectedTime"
                  class="color-bar-container horizontal">
                  <div class="color-bar-label color-bar-label-left">{{ colorBarMinLabel }}</div>
                  <div class="color-bar-overlay" :style="{ background: colorBarGradient }"></div>
                  <div class="color-bar-label color-bar-label-right">{{ colorBarMaxLabel }}</div>
                </div>
              </div>
            </v-card>
          </div>
        </div>
      </div>
    </div>
  </div>
  <DocumentationOverlay :show="showDocOverlay" toolId="l1" @close="closeDocumentation" />
</template>

<script setup>
const emit = defineEmits(['close'])
import { ref, onMounted, watch, computed } from 'vue'
import { VuePlotly } from 'vue3-plotly'
import 'leaflet/dist/leaflet.css';
import { LMap, LTileLayer, LImageOverlay } from '@vue-leaflet/vue-leaflet';
import DocumentationOverlay from './DocumentationOverlay.vue';


const dateOptionsRaw = ref([])
const dateOptions = ref([])
const dataTypeOptions = ref([])
const scaleOptions = ref([])
const costOptions = ref([])

const selectedDate = ref('')
const selectedDataType = ref('')
const selectedScale = ref('')
const selectedCost = ref('')

const heatmapImageUrl = ref('')
const heatmapBounds = ref(null)

const europeBounds = [
  [34.5, -11.25],
  [71.0, 31.5]
];
const mapCenter = [52, 10];
const minZoom = 4;
const maxZoom = 7;

const showMap = ref(false)
onMounted(() => {
  showMap.value = true
})

onMounted(async () => {
  try {
    const res = await fetch('/api/climate_impact/api/get-dates')
    const data = await res.json()
    dateOptionsRaw.value = data.dates || []
    dateOptions.value = dateOptionsRaw.value.slice()
    selectedDate.value = ''
  } catch (e) {
    console.error('Failed to fetch dates', e)
  }
})


watch(selectedDate, async (newDate) => {
  if (!newDate) {
    dataTypeOptions.value = []
    scaleOptions.value = []
    costOptions.value = []
    selectedDataType.value = ''
    selectedScale.value = ''
    selectedCost.value = ''
    return
  }
  try {
    const res = await fetch(`/api/climate_impact/api/get-data-types?date=${encodeURIComponent(newDate)}`)
    const data = await res.json()
    dataTypeOptions.value = data.dataTypes || []
    scaleOptions.value = []
    costOptions.value = []
    selectedDataType.value = ''
    selectedScale.value = ''
    selectedCost.value = ''
  } catch (e) {
    console.error('Failed to fetch data types', e)
    dataTypeOptions.value = []
  }
})


watch(selectedDataType, async (newType) => {
  if (!selectedDate.value || !newType) {
    scaleOptions.value = []
    costOptions.value = []
    selectedScale.value = ''
    selectedCost.value = ''
    return
  }
  try {
    const res = await fetch(`/api/climate_impact/api/get-scales?date=${encodeURIComponent(selectedDate.value)}&dataType=${encodeURIComponent(newType)}`)
    const data = await res.json()
    scaleOptions.value = data.scales || []
    costOptions.value = []
    selectedScale.value = ''
    selectedCost.value = ''
  } catch (e) {
    console.error('Failed to fetch scales', e)
    scaleOptions.value = []
  }
})


const atrPercentageData = ref([])
watch(selectedScale, async (newScale) => {
  if (!selectedDate.value || !selectedDataType.value || !newScale) {
    costOptions.value = []
    selectedCost.value = ''
    atrPercentageData.value = []
    return
  }

  try {
    const res = await fetch(`/api/climate_impact/api/get-costs?date=${encodeURIComponent(selectedDate.value)}&dataType=${encodeURIComponent(selectedDataType.value)}&scale=${encodeURIComponent(newScale)}`)
    const data = await res.json()
    costOptions.value = data.costs || []
    selectedCost.value = ''
  } catch (e) {
    console.error('Failed to fetch costs', e)
    costOptions.value = []
  }

  try {
    const res = await fetch(`/api/climate_impact/api/get-atr-percentage-increase?date=${encodeURIComponent(selectedDate.value)}&scale=${encodeURIComponent(newScale)}`)
    const data = await res.json()
    atrPercentageData.value = data.data || []
  } catch (e) {
    console.error('Failed to fetch ATR percentage increase', e)
    atrPercentageData.value = []
  }
})


const categories = ['Energy', 'Transport', 'Agriculture', 'Industry']
const years = [2022, 2023, 2024, 2025]

const flightLevelOptions = ref([])
const timeOptions = ref([])
const selectedFlightLevel = ref('')
const selectedTime = ref('')


function formatTimeLabel(timeVal) {

  const sec = Number(timeVal)
  if (isNaN(sec)) return String(timeVal)
  const hour = 12 + Math.floor(sec / 3600)
  const min = Math.floor((sec % 3600) / 60)

  const hourStr = hour.toString().padStart(2, '0')
  const minStr = min.toString().padStart(2, '0')
  return `${hourStr}:${minStr}`
}

const timeOptionsDisplay = computed(() => timeOptions.value.map(formatTimeLabel))

const selectedTimeDisplay = computed({
  get() {
    const idx = timeOptions.value.findIndex(opt => opt === selectedTime.value)
    return timeOptionsDisplay.value[idx] || ''
  },
  set(val) {

    const idx = timeOptionsDisplay.value.findIndex(opt => opt === val)
    selectedTime.value = timeOptions.value[idx] || ''
  }
})


watch(selectedCost, async (newCost) => {

  if (!selectedDate.value || !selectedDataType.value || !selectedScale.value || !newCost) {
    flightLevelOptions.value = []
    timeOptions.value = []
    selectedFlightLevel.value = ''
    selectedTime.value = ''
    heatmapImageUrl.value = ''
    heatmapBounds.value = null
    colorBarMinRaw.value = COLOR_BAR_MIN_VALUE
    colorBarMaxRaw.value = COLOR_BAR_MAX_VALUE
    return
  }
  try {

    const params = new URLSearchParams({
      date: selectedDate.value,
      dataType: selectedDataType.value,
      scale: selectedScale.value,
      cost: newCost
    })
    const metaRes = await fetch(`/api/climate_impact/api/get-netcdf-metadata?${params.toString()}`)
    const metaData = await metaRes.json()
    flightLevelOptions.value = Array.isArray(metaData.altitudes) ? metaData.altitudes.map(a => a.toString()) : []
    timeOptions.value = Array.isArray(metaData.times) ? metaData.times : []
    selectedFlightLevel.value = ''
    selectedTime.value = ''

    if (
      typeof metaData.lat_min === 'number' &&
      typeof metaData.lat_max === 'number' &&
      typeof metaData.lon_min === 'number' &&
      typeof metaData.lon_max === 'number'
    ) {
      heatmapBounds.value = [
        [metaData.lat_min, metaData.lon_min],
        [metaData.lat_max, metaData.lon_max]
      ]
    } else {
      heatmapBounds.value = null
    }

    colorBarMinRaw.value = COLOR_BAR_MIN_VALUE
    colorBarMaxRaw.value = COLOR_BAR_MAX_VALUE
  } catch (e) {
    flightLevelOptions.value = []
    timeOptions.value = []
    selectedFlightLevel.value = ''
    selectedTime.value = ''
    heatmapBounds.value = null
    colorBarMinRaw.value = COLOR_BAR_MIN_VALUE
    colorBarMaxRaw.value = COLOR_BAR_MAX_VALUE
  }
})

watch([
  selectedDate,
  selectedDataType,
  selectedScale,
  selectedCost,
  selectedFlightLevel,
  selectedTime
], async ([date, dataType, scale, cost, flightLevel, time]) => {

  if (!date || !dataType || !scale || !cost || !flightLevel || !time) {
    heatmapImageUrl.value = ''
    return
  }
  try {

    const params = new URLSearchParams({
      date,
      dataType,
      scale,
      cost
    })
    const metaRes = await fetch(`/api/climate_impact/api/get-netcdf-metadata?${params.toString()}`)
    const metaData = await metaRes.json()
    if (metaData.error || !metaData.file_base) {
      heatmapImageUrl.value = ''
      return
    }

    const altIdx = flightLevelOptions.value.findIndex(a => a === flightLevel)
    const timeIdx = timeOptions.value.findIndex(t => t === time)
    if (altIdx === -1 || timeIdx === -1) {
      heatmapImageUrl.value = ''
      return
    }

    const url = `/api/climate_impact/api/get-heatmap-overlay?file=${encodeURIComponent(metaData.file_base)}&date=${encodeURIComponent(date)}&altitude=${altIdx}&time=${timeIdx}`
    heatmapImageUrl.value = url
  } catch (e) {
    heatmapImageUrl.value = ''
  }
})


const colorBarGradient = computed(() => {
  const dt = selectedDataType.value ? selectedDataType.value.replace(/_/g, '').toLowerCase() : '';
  if (dt === 'contrails' || dt === 'netatr') {
    return 'linear-gradient(to right, #0052cc 0%, #fff 50%, #ff2d55 100%)';
  }

  return 'linear-gradient(to right, #fff 0%, #ff2d55 100%)';
})


const selectedDataTypeLabel = computed(() => {
  if (!selectedDataType.value) return '';
  if (selectedDataType.value.replace(/_/g, '').toLowerCase() === 'netatr') return 'Net ATR';

  return selectedDataType.value.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
})


const COLOR_BAR_MIN_VALUE = -2e-9
const COLOR_BAR_MAX_VALUE = 2e9

const colorBarMinRaw = ref(COLOR_BAR_MIN_VALUE)
const colorBarMaxRaw = ref(COLOR_BAR_MAX_VALUE)

function formatSci(val) {
  if (val === '-' || val === '' || val == null) return '-';
  const num = Number(val);
  if (isNaN(num)) return String(val);

  return num.toExponential(2).replace(/e\+?(-?\d+)/, 'e$1');
}

const colorBarMin = computed(() => formatSci(colorBarMinRaw.value));
const colorBarMax = computed(() => formatSci(colorBarMaxRaw.value));

const colorBarMinLabel = computed(() => `${colorBarMin.value} K`);
const colorBarMaxLabel = computed(() => `${colorBarMax.value} K`);


function makeBarLayout(title, tickvals = [], xData = []) {
  const nums = Array.isArray(xData) ? xData.filter(v => typeof v === 'number' && !isNaN(v)) : [];
  let min = Math.min(0, ...nums);
  let max = Math.max(0, ...nums);
  if (min === max) {
    const pad = Math.abs(min || 1) * 0.1;
    min -= pad;
    max += pad;
  } else {
    const span = max - min;
    const pad = span * 0.1;
    min -= pad;
    max += pad;
  }
  return {
    autosize: true,
    title: { text: title, font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
    yaxis: {
      title: 'Increase in Cost (%)',
      tickvals,
      color: '#fff',
      tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
      titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
      showgrid: false,
      gridcolor: 'rgba(0,0,0,0)',
      zeroline: false,
      zerolinecolor: 'rgba(0,0,0,0)',
      showline: false,
      linecolor: 'rgba(0,0,0,0)'
    },
    xaxis: {
      title: 'Change vs BAU (%)',
      range: [min, max],
      color: '#fff',
      tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
      titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
      showgrid: false,
      gridcolor: 'rgba(0,0,0,0)',
      zeroline: false,
      zerolinecolor: 'rgba(0,0,0,0)',
      showline: false,
      linecolor: 'rgba(0,0,0,0)'
    },
    margin: { t: 50, b: 40, l: 60, r: 20 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    showlegend: false
  };
}



function getCategoryColors(n) {

  const refmapGreen = '#21CE99';
  return Array(n).fill(refmapGreen);
}

const categoryColors = getCategoryColors(categories.length);

const barCharts = ref([
  {
    title: 'Net ATR',
    data: [{
      type: 'bar',
      y: [],
      x: [],
      orientation: 'h',
      marker: { color: categoryColors },
      name: 'Net ATR',
      text: [],
      textposition: 'auto',
      textfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
      hovertemplate: '<div style="background:#fff;padding:10px 14px 10px 14px;border-radius:1rem;box-shadow:0 2px 8px #0002;min-width:120px;max-width:220px;">'
        + '<span style="font-size:1.1em;font-weight:bold;color:#145DA0;">%{fullData.name}</span><br>'
        + '<span style="color:#888;font-size:0.98em;">Cost: <b>%{y}</b></span><br>'
        + '<span style="color:#21CE99;font-size:1.05em;">Change vs BAU:</span> <b style="color:#ff2d55;">%{x:.2f}%</b>'
        + '</div><extra></extra>',
    }],
    layout: {
      autosize: true,
      title: { text: 'Net ATR', font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
      yaxis: {
        title: 'Increase in Cost (%)',
        tickvals: [],
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      xaxis: {
        title: 'Change vs BAU (%)',
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      margin: { t: 50, b: 40, l: 60, r: 20 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      showlegend: false
    }
  },
  {
    title: 'NOx',
    data: [{
      type: 'bar',
      y: [],
      x: [],
      orientation: 'h',
      marker: { color: categoryColors },
      name: 'NOx',
      text: [],
      textposition: 'auto',
      textfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
      hovertemplate: '<div style="background:#fff;padding:10px 14px 10px 14px;border-radius:1rem;box-shadow:0 2px 8px #0002;min-width:120px;max-width:220px;">'
        + '<span style="font-size:1.1em;font-weight:bold;color:#145DA0;">%{fullData.name}</span><br>'
        + '<span style="color:#888;font-size:0.98em;">Cost: <b>%{y}</b></span><br>'
        + '<span style="color:#21CE99;font-size:1.05em;">Change vs BAU:</span> <b style="color:#ff2d55;">%{x:.2f}%</b>'
        + '</div><extra></extra>',
    }],
    layout: {
      autosize: true,
      title: { text: 'NOx', font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
      yaxis: {
        title: 'Increase in Cost (%)',
        tickvals: [],
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      xaxis: {
        title: 'Change vs BAU (%)',
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      margin: { t: 50, b: 40, l: 60, r: 20 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      showlegend: false
    }
  },
  {
    title: 'H₂O',
    data: [{
      type: 'bar',
      y: [],
      x: [],
      orientation: 'h',
      marker: { color: categoryColors },
      name: 'H₂O',
      text: [],
      textposition: 'auto',
      textfont: { color: '#fff', size: 14 },
    }],
    layout: {
      autosize: true,
      title: { text: 'H₂O', font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
      yaxis: {
        title: 'Increase in Cost (%)',
        tickvals: [],
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      xaxis: {
        title: 'Change vs BAU (%)',
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      margin: { t: 50, b: 40, l: 60, r: 20 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      showlegend: false
    }
  },
  {
    title: 'CO₂',
    data: [{
      type: 'bar',
      y: [],
      x: [],
      orientation: 'h',
      marker: { color: categoryColors },
      name: 'CO₂',
      text: [],
      textposition: 'auto',
      textfont: { color: '#fff', size: 14 },
    }],
    layout: {
      autosize: true,
      title: { text: 'CO₂', font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
      yaxis: {
        title: 'Increase in Cost (%)',
        tickvals: [],
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      xaxis: {
        title: 'Change vs BAU (%)',
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      margin: { t: 50, b: 40, l: 60, r: 20 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      showlegend: false
    }
  },
  {
    title: 'AIC',
    data: [{
      type: 'bar',
      y: [],
      x: [],
      orientation: 'h',
      marker: { color: categoryColors },
      name: 'AIC',
      text: [],
      textposition: 'auto',
      textfont: { color: '#fff', size: 14 },
    }],
    layout: {
      autosize: true,
      title: { text: 'AIC', font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
      yaxis: {
        title: 'Increase in Cost (%)',
        tickvals: [],
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      xaxis: {
        title: 'Change vs BAU (%)',
        color: '#fff',
        tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
        showgrid: false,
        gridcolor: 'rgba(0,0,0,0)',
        zeroline: false,
        zerolinecolor: 'rgba(0,0,0,0)',
        showline: false,
        linecolor: 'rgba(0,0,0,0)'
      },
      margin: { t: 50, b: 40, l: 60, r: 20 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      showlegend: false
    }
  }
])


function formatDataTypeLabel(type) {
  if (!type) return ''
  if (type.replace(/_/g, '').toLowerCase() === 'netatr') return 'Net ATR'

  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}


function formatCostLabel(cost) {
  if (cost === null || cost === undefined || cost === '') return ''
  if (cost === 'noCost') return 'noCost'
  if (typeof cost === 'string' && cost.trim().endsWith('%')) return cost
  return `${cost}%`
}


function formatDateLabel(dateStr) {
  if (!dateStr || typeof dateStr !== 'string' || dateStr.length !== 8) return dateStr;
  const day = dateStr.slice(0, 2);
  const month = dateStr.slice(2, 4);
  const year = dateStr.slice(4, 8);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthIdx = parseInt(month, 10) - 1;
  if (monthIdx < 0 || monthIdx > 11) return dateStr;
  return `${day} ${months[monthIdx]} ${year}`;
}

const dateOptionsDisplay = computed(() => dateOptions.value.map(formatDateLabel))

const selectedDateDisplay = computed({
  get() {
    const idx = dateOptions.value.findIndex(opt => opt === selectedDate.value)
    return dateOptionsDisplay.value[idx] || ''
  },
  set(val) {

    const idx = dateOptionsDisplay.value.findIndex(opt => opt === val)
    selectedDate.value = dateOptions.value[idx] || ''
  }
})

const dataTypeOptionsDisplay = computed(() => dataTypeOptions.value.map(formatDataTypeLabel))

const selectedDataTypeDisplay = computed({
  get() {
    const idx = dataTypeOptions.value.findIndex(opt => opt === selectedDataType.value)
    return dataTypeOptionsDisplay.value[idx] || ''
  },
  set(val) {
    const idx = dataTypeOptionsDisplay.value.findIndex(opt => opt === val)
    selectedDataType.value = dataTypeOptions.value[idx] || ''
  }
})

const costOptionsDisplay = computed(() => costOptions.value.map(formatCostLabel))

const selectedCostDisplay = computed({
  get() {
    const idx = costOptions.value.findIndex(opt => opt === selectedCost.value)
    return costOptionsDisplay.value[idx] || ''
  },
  set(val) {

    const raw = typeof val === 'string' ? val.replace(/%$/, '') : val
    const idx = costOptions.value.findIndex(opt => String(opt) === raw)
    selectedCost.value = costOptions.value[idx] || ''
  }
})


function orderScaleOptions(scales) {
  if (!Array.isArray(scales)) return []
  const order = ['BAU', 'Micro', 'Macro']
  const lower = s => (s || '').toLowerCase()

  const ordered = order
    .map(key => scales.find(s => lower(s) === key.toLowerCase()))
    .filter(Boolean)
  const rest = scales.filter(s => !order.some(key => lower(s) === key.toLowerCase()))
  return [...ordered, ...rest]
}

const scaleOptionsOrdered = computed(() => orderScaleOptions(scaleOptions.value))

const selectedScaleOrdered = computed({
  get() {

    return scaleOptionsOrdered.value.find(opt => opt === selectedScale.value) || ''
  },
  set(val) {

    if (scaleOptions.value.includes(val)) {
      selectedScale.value = val
    } else {

      const match = scaleOptions.value.find(opt => (opt || '').toLowerCase() === (val || '').toLowerCase())
      selectedScale.value = match || ''
    }
  }
})



watch(atrPercentageData, (data) => {
  const metrics = [
    { key: 'Net_ATR', label: 'Net ATR' },
    { key: 'NOx', label: 'NOx' },
    { key: 'H2O', label: 'H₂O' },
    { key: 'CO2', label: 'CO₂' },
    { key: 'AIC', label: 'AIC' }
  ];
  const hovertemplate = '<span style="font-size:1.1em;font-weight:bold;">%{fullData.name}</span><br>'
    + '<span style="font-size:1.1em;font-weight:bold;">Cost: <b>%{y}</b></span><br>'
    + '<span style="font-size:1.1em;font-weight:bold;">Change vs BAU:</span> <b style="color:#black">%{x:.2f}%</b>'
    + '<extra></extra>';
  if (!data || !Array.isArray(data) || data.length === 0) {
    barCharts.value = metrics.map(metric => ({
      title: metric.label,
      data: [{
        type: 'bar',
        y: ['0%'],
        x: [0],
        orientation: 'h',
        marker: { color: categoryColors },
        name: metric.label,
        text: ['0%'],
        textposition: 'auto',
        textfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        hovertemplate: hovertemplate,
      }],
      layout: {
        autosize: true,
        title: { text: metric.label, font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
        yaxis: {
          title: 'Increase in Cost (%)',
          tickvals: ['0%'],
          color: '#fff',
          tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
          titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
          showgrid: false,
          gridcolor: 'rgba(0,0,0,0)',
          zeroline: false,
          zerolinecolor: 'rgba(0,0,0,0)',
          showline: false,
          linecolor: 'rgba(0,0,0,0)'
        },
        xaxis: {
          title: 'Change vs BAU (%)',
          color: '#fff',
          tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
          titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
          showgrid: false,
          gridcolor: 'rgba(0,0,0,0)',
          zeroline: false,
          zerolinecolor: 'rgba(0,0,0,0)',
          showline: false,
          linecolor: 'rgba(0,0,0,0)'
        },
        margin: { t: 50, b: 40, l: 60, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        showlegend: false
      }
    }))
    return
  }
  barCharts.value = metrics.map(metric => {
    const y = data.map(entry => entry.cost_increase + '%')
    const x = data.map(entry => entry[metric.key] != null ? entry[metric.key] : 0)
    return {
      title: metric.label,
      data: [{
        type: 'bar',
        y: y,
        x: x,
        orientation: 'h',
        marker: { color: categoryColors },
        name: metric.label,
        text: x.map(v => (v != null ? v.toFixed(2) : '0') + '%'),
        textposition: 'auto',
        textfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
        hovertemplate: hovertemplate,
      }],
      layout: {
        autosize: true,
        title: { text: metric.label, font: { color: '#fff', size: 18, family: 'inherit', weight: 'bold' }, x: 0.5, y: 0.98 },
        yaxis: {
          title: 'Increase in Cost (%)',
          tickvals: y,
          color: '#fff',
          tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
          titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
          showgrid: false,
          gridcolor: 'rgba(0,0,0,0)',
          zeroline: false,
          zerolinecolor: 'rgba(0,0,0,0)',
          showline: false,
          linecolor: 'rgba(0,0,0,0)'
        },
        xaxis: {
          title: 'Change vs BAU (%)',
          color: '#fff',
          tickfont: { color: '#fff', size: 14, family: 'inherit', weight: 'bold' },
          titlefont: { color: '#fff', size: 16, family: 'inherit', weight: 'bold' },
          showgrid: false,
          gridcolor: 'rgba(0,0,0,0)',
          zeroline: false,
          zerolinecolor: 'rgba(0,0,0,0)',
          showline: false,
          linecolor: 'rgba(0,0,0,0)'
        },
        margin: { t: 50, b: 40, l: 60, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        showlegend: false
      }
    }
  })
})

const showDocOverlay = ref(false)

function openDocumentation() {
  showDocOverlay.value = true
}

function closeDocumentation() {
  showDocOverlay.value = false
}
</script>

<style scoped>
/* Climate Impact Container */
.climate-impact-container {
  width: 100vw;
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 4rem);
  padding-bottom: 5rem;
  margin-left: calc(-50vw + 50%);
}

/* Common section styling */
.climate-section {
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 clamp(1rem, 3vw, 2rem);
}

/* Section 1: Header */
.climate-section-header {
  flex: 0 0 auto;
  justify-content: space-between;
}

.back-arrow-btn,
.doc-btn {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.25);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}

/* Section 2: Title */
.climate-section-title {
  flex: 0 0 auto;
}

.ltr-letters-wrapper {
  display: inline-block;
}

.ltr-letters {
  font-size: clamp(1.5rem, 4vw, 3rem);
  font-weight: 600;
  color: #fff;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
}

/* Section 3: Filters */
.climate-section-filters {
  flex: 0 0 auto;
  padding: clamp(0.75rem, 2vh, 1.5rem) 0;
}

.filters-row {
  margin-top: 1%;
  display: flex;
  gap: 1.5rem;
  width: 90%;
  max-width: 1200px;
  justify-content: center;
  flex-wrap: nowrap;
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
  text-overflow: clip !important;
  /* Stop the "..." */
}

/* THE FLOATING TITLE (Selected State) */
.filter-select :deep(.v-label.v-field-label--floating) {
  color: white !important;
  font-weight: 700 !important;
  opacity: 1 !important;
  font-size: 1.3rem !important;

  /* Position adjustments */
  transform: translateY(-34px) scale(1) !important;
  padding: 0 8px;
  /* More padding to cover border */
  margin-left: -8px;
  z-index: 100;
  /* Ensure it sits on top of everything */
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

.filters-card {
  width: 100%;
  max-width: 80%;
  padding: 1rem;
  background: transparent;
}

.filter-row {
  row-gap: 8px;
}

.filter-select :deep(.v-field) {
  background: rgba(255, 255, 255, 0.85);
  border-radius: 14px;
}

.filter-select :deep(.v-label) {
  color: #0A2342;
  opacity: 0.9;
}

.filter-select :deep(.v-field__input) {
  color: #0A2342;
}

/* Section 4: Cards */
.climate-section-cards {
  flex: 1 1 auto;
  align-items: flex-start;
  padding-bottom: clamp(1rem, 3vh, 2rem);
}

.climate-cards-grid {
  display: grid;
  grid-template-columns: minmax(320px, 25%) 1fr;
  width: 90%;
  max-width: 100%;
  align-items: start;
}

.climate-card-wrapper {
  display: flex;
  width: 100%;
}

.pie-card {
  grid-column: 1;
}

.scrollable-pie-card {
  height: 70vh;
  width: 100%;
  border-radius: 1.5rem 0 0 1.5rem !important;
  overflow-y: auto;
  background-color: transparent;
}

.pie-chart-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem 1rem;
}

.map-card {
  grid-column: 2;
}

.map-card-shell {
  padding: 0;
  border-radius: 0 1.5rem 1.5rem 0 !important;
  border-color: transparent !important;
}

.map-card-body {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0vh;
}

.map-leaflet {
  width: 100%;
  height: 100%;
  min-height: 70vh;
  min-width: 70vw;
  overflow: hidden;
}

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
  pointer-events: none;
}

.color-bar-container.horizontal {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.color-bar-overlay {
  width: 260px;
  height: 34px;
  border-radius: 999px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.color-bar-label {
  color: black;
  font-size: 1rem;
  background-color: white;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
  border-radius: 1.5rem;
  padding: 0.2rem 0.6rem;
}

.color-bar-label-left,
.color-bar-label-right {
  white-space: nowrap;
}

/* Responsive adjustments */
@media (max-width: 1200px) {
  .climate-cards-grid {
    grid-template-columns: 1fr;
  }

  .pie-card,
  .map-card {
    grid-column: 1;
  }

  .scrollable-pie-card {
    height: auto;
    max-height: 50vh;
  }
}

@media (max-width: 768px) {
  .climate-section-header {
    padding-top: clamp(0.5rem, 1.5vh, 1rem);
    padding-bottom: clamp(0.25rem, 1vh, 0.5rem);
  }

  .climate-section-title {
    padding: clamp(0.25rem, 1vh, 0.5rem) 0;
  }

  .ltr-letters {
    font-size: clamp(1.25rem, 5vw, 2rem);
  }

  .climate-section-filters {
    padding: clamp(0.5rem, 1.5vh, 1rem) 0;
  }

  .filters-card {
    padding: 0.75rem;
  }
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

@media (max-width: 480px) {
  .climate-section-cards {
    padding-top: 0.5rem;
  }

  .climate-cards-grid {
    gap: 0.75rem;
  }
}

/* Documentation overlay */
.doc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
  display: grid;
  place-items: center;
  z-index: 30;
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
  color: #0A2342;
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
  background: linear-gradient(135deg, #145DA0, #21CE99);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(20, 93, 160, 0.3);
}

.doc-close-btn {
  background: rgba(255, 255, 255, 0.9);
  color: #0A2342;
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
  color: #0A2342;
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
  background: rgba(20, 93, 160, 0.1);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: #145DA0;
}
</style>

<style>
.filter-menu-content .v-list-item-title {
  font-size: 1.1rem !important;
  font-weight: 500 !important;
  padding: 8px 0 !important;
}
</style>