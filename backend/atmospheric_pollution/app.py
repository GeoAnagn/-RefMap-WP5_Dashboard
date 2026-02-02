import os
import dask
import base64
import traceback
import matplotlib
import numpy as np
import xarray as xr
import rioxarray
import pandas as pd
from io import BytesIO
from flask_cors import CORS
from typing import Optional
from threading import Lock
import matplotlib.pyplot as plt
from shapely.geometry import shape
from flask import Flask, jsonify, request, send_file

dask.config.set(scheduler='synchronous')
dask.config.set(pool=dict(max_workers=8))

app = Flask(__name__)
CORS(app)

_plot_lock = Lock()
matplotlib.use('Agg')

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')

def find_zarr_store(search_path):
    print(f"Searching for ZARR store in: {search_path}")
    for root, dirs, files in os.walk(search_path):
        for d in dirs:
            if d.endswith('.zarr'):
                found_path = os.path.join(root, d)
                print(f"Found ZARR store at: {found_path}")
                return found_path
    return None

zarr_path = find_zarr_store(DATA_DIR)

ZARR_STORE = os.environ.get(
    'ZARR_STORE',
    zarr_path
)

_ds_cache: Optional[xr.Dataset] = None

SPECIES = [
    'no2_density',
    'co_density', 
    'so2_density',
    'ch4_density',
    'o3_density',
    'pm1_density',
    'pm2p5_density',
    'pm10_density'
]

SPECIES_DISPLAY_NAMES = {
    'no2_density': 'NO₂',
    'co_density': 'CO',
    'so2_density': 'SO₂',
    'ch4_density': 'CH₄',
    'o3_density': 'O₃',
    'pm1_density': 'PM1',
    'pm2p5_density': 'PM2.5',
    'pm10_density': 'PM10'
}

SPECIES_UNITS = {
    'no2_density': 'mol/m²',
    'co_density': 'mol/m²',
    'so2_density': 'mol/m²',
    'ch4_density': 'mol/m²',
    'o3_density': 'mol/m²',
    'pm1_density': 'kg/m²',
    'pm2p5_density': 'kg/m²',
    'pm10_density': 'kg/m²'
}


def get_dataset() -> xr.Dataset:
    """Load and cache the ZARR dataset."""
    global _ds_cache
    
    if _ds_cache is None:
        if ZARR_STORE is None or not os.path.exists(ZARR_STORE):
            raise FileNotFoundError(f"ZARR store not found at {ZARR_STORE}")
        
        print(f"Loading ZARR store from {ZARR_STORE}...")
        _ds_cache = xr.open_zarr(ZARR_STORE, consolidated=True)
        
        if not hasattr(_ds_cache, 'rio') or _ds_cache.rio.crs is None:
            _ds_cache = _ds_cache.rio.write_crs("EPSG:4326")
        
        print(f"Dataset loaded. Available variables: {list(_ds_cache.data_vars)}")
        print(f"Time range: {_ds_cache.time.min().values} to {_ds_cache.time.max().values}")
    
    return _ds_cache


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'atmospheric_pollution'})


@app.route('/data/<path:filename>', methods=['GET'])
def serve_data_file(filename):
    """Serve data files (e.g., geojson)."""
    try:
        file_path = os.path.join(DATA_DIR, filename)
        
        # Check if file exists directly
        if os.path.exists(file_path):
            return send_file(file_path)

        # Search for file in subdirectories
        print(f"Searching for {filename} in {DATA_DIR}...")
        for root, dirs, files in os.walk(DATA_DIR):
            if filename in files:
                found_path = os.path.join(root, filename)
                print(f"Found file at: {found_path}")
                return send_file(found_path)
                
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get dataset metadata including available species, time range, and bounds."""
    try:
        ds = get_dataset()
        
        time_min = pd.Timestamp(ds.time.min().values).isoformat()
        time_max = pd.Timestamp(ds.time.max().values).isoformat()
        
        lat_min = float(ds.latitude.min().values)
        lat_max = float(ds.latitude.max().values)
        lon_min = float(ds.longitude.min().values)
        lon_max = float(ds.longitude.max().values)
        
        available_species = [s for s in SPECIES if s in ds.data_vars]
        
        return jsonify({
            'species': [
                {
                    'id': s,
                    'name': SPECIES_DISPLAY_NAMES.get(s, s),
                    'unit': SPECIES_UNITS.get(s, '')
                }
                for s in available_species
            ],
            'timeRange': {
                'min': time_min,
                'max': time_max
            },
            'bounds': {
                'latMin': lat_min,
                'latMax': lat_max,
                'lonMin': lon_min,
                'lonMax': lon_max
            }
        })
    except Exception as e:
        print(f"Error in get_metadata: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeseries', methods=['POST'])
def get_timeseries():
    """
    Get time series data for a polygon area.
    
    Request body:
    {
        "geometry": GeoJSON geometry (Polygon or MultiPolygon),
        "species": species ID (e.g., "no2_density"),
        "startDate": ISO datetime string,
        "endDate": ISO datetime string,
        "interval": resampling interval (e.g., "1D", "7D", "1W")
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'geometry' not in data:
            return jsonify({'error': 'Missing geometry'}), 400
        
        geometry_json = data['geometry']
        species = data.get('species', 'no2_density')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        interval = data.get('interval', '7D')
        
        if start_date:
            start_date = pd.Timestamp(start_date)
        if end_date:
            end_date = pd.Timestamp(end_date)
        
        ds = get_dataset()
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found in dataset'}), 400
        
        geometry = shape(geometry_json)
        min_x, min_y, max_x, max_y = geometry.bounds
        ds_subset = ds.sel(
            longitude=slice(min_x, max_x),
            latitude=slice(min_y, max_y)
        )
        
        if start_date or end_date:
            ds_subset = ds_subset.sel(time=slice(start_date, end_date))
        
        print(f"Clipping to geometry and computing mean for {species}...")
        aoi_data = ds_subset.rio.clip([geometry], crs="EPSG:4326").mean(
            dim=["longitude", "latitude"], skipna=True
        )
        
        if aoi_data.time.size == 0:
            print("Warning: No data found for the selected time range and geometry.")
            return jsonify({
                'data': [],
                'stats': {
                    'average': 0.0,
                    'min': 0.0,
                    'max': 0.0
                },
                'species': species,
                'unit': SPECIES_UNITS.get(species, '')
            })

        print(f"Resampling to {interval}...")
        values = (
            aoi_data[species]
            .resample(time=interval, skipna=True)
            .mean()
            .compute()
        )
        
        timestamps = aoi_data["time"].resample(time=interval).last()
        timestamps = pd.DatetimeIndex(timestamps).tz_localize("UTC").tolist()
        
        clean_data = [
            {
                'timestamp': ts.isoformat(),
                'value': float(val)
            }
            for val, ts in zip(values.values, timestamps)
            if not np.isnan(val)
        ]
        
        valid_values = [d['value'] for d in clean_data]
        average = float(np.mean(valid_values)) if valid_values else 0.0
        minimum = float(np.min(valid_values)) if valid_values else 0.0
        maximum = float(np.max(valid_values)) if valid_values else 0.0
        
        return jsonify({
            'data': clean_data,
            'statistics': {
                'average': average,
                'min': minimum,
                'max': maximum,
                'count': len(clean_data)
            },
            'metadata': {
                'species': species,
                'unit': SPECIES_UNITS.get(species, ''),
                'interval': interval
            }
        })
        
    except Exception as e:
        print(f"Error in get_timeseries: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/snapshot', methods=['POST'])
def get_snapshot():
    """
    Get spatial snapshot for a specific time.
    
    Request body:
    {
        "species": species ID,
        "timestamp": ISO datetime string,
        "bounds": {latMin, latMax, lonMin, lonMax} (optional)
    }
    """
    try:
        data = request.get_json()
        
        species = data.get('species', 'no2_density')
        timestamp = data.get('timestamp')
        bounds = data.get('bounds')
        
        if not timestamp:
            return jsonify({'error': 'Missing timestamp'}), 400
        
        ts = pd.Timestamp(timestamp)
        ds = get_dataset()
        
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found'}), 400
        
        ds_time = ds.sel(time=ts, method='nearest')
        if bounds:
            ds_time = ds_time.sel(
                latitude=slice(bounds.get('latMin'), bounds.get('latMax')),
                longitude=slice(bounds.get('lonMin'), bounds.get('lonMax'))
            )
        
        data_array = ds_time[species].compute()
        lats = data_array.latitude.values.tolist()
        lons = data_array.longitude.values.tolist()
        values = data_array.values.tolist()
        actual_time = pd.Timestamp(ds_time.time.values).isoformat()
        
        return jsonify({
            'latitude': lats,
            'longitude': lons,
            'values': values,
            'timestamp': actual_time,
            'species': species,
            'unit': SPECIES_UNITS.get(species, '')
        })
        
    except Exception as e:
        print(f"Error in get_snapshot: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/heatmap', methods=['POST'])
def get_heatmap():
    """
    Generate heatmap overlay for a specific area and time.
    
    Request body:
    {
        "geometry": GeoJSON geometry (Polygon or MultiPolygon),
        "species": species ID,
        "timestamp": ISO datetime string,
    }
    """
    fig = None
    try:
        data = request.get_json()
        
        if not data or 'geometry' not in data:
            return jsonify({'error': 'Missing geometry'}), 400
        
        geometry_json = data['geometry']
        species = data.get('species', 'no2_density')
        timestamp = data.get('timestamp')
        
        if not timestamp:
            return jsonify({'error': 'Missing timestamp'}), 400
        
        ts = pd.Timestamp(timestamp)
        ds = get_dataset()
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found'}), 400
        
        geometry = shape(geometry_json)
        
        min_x, min_y, max_x, max_y = geometry.bounds
        
        ds_time = ds.sel(time=ts, method='nearest')
        
        ds_subset = ds_time.sel(
            longitude=slice(min_x, max_x),
            latitude=slice(min_y, max_y)
        )
        
        data_array = ds_subset[species].compute()
        
        if data_array.size == 0:
            return jsonify({'error': 'No data in selected region'}), 400
        
        actual_time = pd.Timestamp(ds_time.time.values).isoformat()
        
        lon = data_array.longitude.values
        lat = data_array.latitude.values
        values = data_array.values
        
        if len(lon) == 0 or len(lat) == 0:
            return jsonify({'error': 'Invalid data dimensions'}), 400
        
        vmin = float(np.nanmin(values))
        vmax = float(np.nanmax(values))
        
        if np.isnan(vmin) or np.isnan(vmax) or vmin == vmax:
            return jsonify({
                'image_data': '',
                'bounds': {
                    'latMin': float(min_y),
                    'latMax': float(max_y),
                    'lonMin': float(min_x),
                    'lonMax': float(max_x)
                },
                'timestamp': actual_time,
                'species': species,
                'unit': SPECIES_UNITS.get(species, ''),
                'colorbar': {'min': 0, 'max': 0},
                'legend': {
                    'min': 0,
                    'max': 0,
                    'unit': SPECIES_UNITS.get(species, ''),
                    'species': SPECIES_DISPLAY_NAMES.get(species, species),
                    'colormap': 'YlOrRd'
                }
            })
        
        with _plot_lock:
            fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
            fig.patch.set_alpha(0)
            ax.set_aspect('equal')
            
            try:
                im = ax.pcolormesh(lon, lat, values, cmap='YlOrRd', alpha=0.6, 
                                   shading='auto', vmin=vmin, vmax=vmax)
                
                ax.set_xlim(min_x, max_x)
                ax.set_ylim(min_y, max_y)
                ax.axis('off')
                
                buf = BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', 
                           pad_inches=0, transparent=True)
                buf.seek(0)
                
                image_base64 = base64.b64encode(buf.read()).decode('utf-8')
                buf.close()
                
            finally:
                plt.close(fig)
        
        return jsonify({
            'image_data': image_base64,
            'bounds': {
                'latMin': float(min_y),
                'latMax': float(max_y),
                'lonMin': float(min_x),
                'lonMax': float(max_x)
            },
            'timestamp': actual_time,
            'species': species,
            'unit': SPECIES_UNITS.get(species, ''),
            'colorbar': {
                'min': vmin,
                'max': vmax
            },
            'legend': {
                'min': vmin,
                'max': vmax,
                'unit': SPECIES_UNITS.get(species, ''),
                'species': SPECIES_DISPLAY_NAMES.get(species, species),
                'colormap': 'YlOrRd'
            }
        })
        
    except Exception as e:
        if fig is not None:
            with _plot_lock:
                plt.close(fig)
        
        print(f"Error in get_heatmap: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/point', methods=['POST'])
def get_point_data():
    """
    Get time series for a specific point location.
    
    Request body:
    {
        "latitude": float,
        "longitude": float,
        "species": species ID,
        "startDate": ISO datetime string (optional),
        "endDate": ISO datetime string (optional)
    }
    """
    try:
        data = request.get_json()
        
        lat = data.get('latitude')
        lon = data.get('longitude')
        species = data.get('species', 'no2_density')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        
        if lat is None or lon is None:
            return jsonify({'error': 'Missing latitude or longitude'}), 400
        
        ds = get_dataset()
        
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found'}), 400
        
        ds_point = ds.sel(latitude=lat, longitude=lon, method='nearest')
        
        if start_date or end_date:
            ds_point = ds_point.sel(time=slice(start_date, end_date))
        
        timeseries = ds_point[species].compute()
        
        timestamps = pd.DatetimeIndex(timeseries.time.values).tz_localize("UTC")
        values = timeseries.values
        
        clean_data = [
            {
                'timestamp': ts.isoformat(),
                'value': float(val)
            }
            for ts, val in zip(timestamps, values)
            if not np.isnan(val)
        ]
        
        return jsonify({
            'data': clean_data,
            'location': {
                'latitude': float(ds_point.latitude.values),
                'longitude': float(ds_point.longitude.values)
            },
            'species': species,
            'unit': SPECIES_UNITS.get(species, '')
        })
        
    except Exception as e:
        print(f"Error in get_point_data: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if ZARR_STORE is None or not os.path.exists(ZARR_STORE):
        print(f"WARNING: ZARR store not found at {ZARR_STORE}")
        print("API endpoints requiring ZARR data will return errors until ZARR_STORE is configured.")
    
    print(f"Starting Atmospheric Pollution API server...")
    print(f"Using ZARR store: {ZARR_STORE}")
    
    try:
        get_dataset()
        print("Dataset loaded successfully!")
    except Exception as e:
        print(f"WARNING: Could not load initial dataset: {e}")
        print("Server will start, but data endpoints may fail.")
    
    port = int(os.environ.get('PORT', 4006))
    app.run(host='0.0.0.0', port=port)
