"""
Flask backend for Atmospheric Pollution data visualization.
Loads ZARR store and provides API endpoints for time series and spatial data.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import xarray as xr
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, Point, Polygon, mapping
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import traceback
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from threading import Lock
import dask

# Configure Dask for multi-threaded Flask app
dask.config.set(scheduler='synchronous')  # Use synchronous scheduler to avoid thread pool issues
dask.config.set(pool=dict(max_workers=8))  # Limit concurrent workers

app = Flask(__name__)
CORS(app)

# Thread lock for matplotlib operations (matplotlib is not thread-safe)
_plot_lock = Lock()

# Configuration
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')

# ZARR store path - can be overridden via environment variable
ZARR_STORE = os.environ.get(
    'ZARR_STORE',
    '/home/refmap-imafusa/Documents/external_volume/zarr_store_f32_251_59_47.zarr'
)

# Global dataset cache
_ds_cache: Optional[xr.Dataset] = None

# Available species in the dataset
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
        if not os.path.exists(ZARR_STORE):
            raise FileNotFoundError(f"ZARR store not found at {ZARR_STORE}")
        
        print(f"Loading ZARR store from {ZARR_STORE}...")
        _ds_cache = xr.open_zarr(ZARR_STORE, consolidated=True)
        
        # Add CRS if not present
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
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        return send_file(file_path)
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get dataset metadata including available species, time range, and bounds."""
    try:
        ds = get_dataset()
        
        # Get time range
        time_min = pd.Timestamp(ds.time.min().values).isoformat()
        time_max = pd.Timestamp(ds.time.max().values).isoformat()
        
        # Get spatial bounds
        lat_min = float(ds.latitude.min().values)
        lat_max = float(ds.latitude.max().values)
        lon_min = float(ds.longitude.min().values)
        lon_max = float(ds.longitude.max().values)
        
        # Filter species that actually exist in the dataset
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
        
        # Validate required fields
        if not data or 'geometry' not in data:
            return jsonify({'error': 'Missing geometry'}), 400
        
        geometry_json = data['geometry']
        species = data.get('species', 'no2_density')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        interval = data.get('interval', '7D')
        
        # Parse dates
        if start_date:
            start_date = pd.Timestamp(start_date)
        if end_date:
            end_date = pd.Timestamp(end_date)
        
        # Load dataset
        ds = get_dataset()
        
        # Validate species
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found in dataset'}), 400
        
        # Convert geometry to shapely
        geometry = shape(geometry_json)
        
        # Get bounding box
        min_x, min_y, max_x, max_y = geometry.bounds
        
        # Select data subset
        ds_subset = ds.sel(
            longitude=slice(min_x, max_x),
            latitude=slice(min_y, max_y)
        )
        
        # Apply time filter if specified
        if start_date or end_date:
            ds_subset = ds_subset.sel(time=slice(start_date, end_date))
        
        # Clip to geometry and compute mean
        print(f"Clipping to geometry and computing mean for {species}...")
        aoi_data = ds_subset.rio.clip([geometry], crs="EPSG:4326").mean(
            dim=["longitude", "latitude"], skipna=True
        )
        
        # Resample to specified interval
        print(f"Resampling to {interval}...")
        values = (
            aoi_data[species]
            .resample(time=interval, skipna=True)
            .mean()
            .compute()  # Trigger computation
        )
        
        timestamps = aoi_data["time"].resample(time=interval).last()
        timestamps = pd.DatetimeIndex(timestamps).tz_localize("UTC").tolist()
        
        # Convert to lists, filtering out NaN values
        clean_data = [
            {
                'timestamp': ts.isoformat(),
                'value': float(val)
            }
            for val, ts in zip(values.values, timestamps)
            if not np.isnan(val)
        ]
        
        # Compute statistics
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
        
        # Parse timestamp
        ts = pd.Timestamp(timestamp)
        
        # Load dataset
        ds = get_dataset()
        
        # Validate species
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found'}), 400
        
        # Select time slice (nearest time)
        ds_time = ds.sel(time=ts, method='nearest')
        
        # Apply spatial bounds if provided
        if bounds:
            ds_time = ds_time.sel(
                latitude=slice(bounds.get('latMin'), bounds.get('latMax')),
                longitude=slice(bounds.get('lonMin'), bounds.get('lonMax'))
            )
        
        # Get the data array
        data_array = ds_time[species].compute()
        
        # Convert to simple format for transfer
        lats = data_array.latitude.values.tolist()
        lons = data_array.longitude.values.tolist()
        values = data_array.values.tolist()
        
        # Get actual timestamp used
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
        
        # Parse timestamp
        ts = pd.Timestamp(timestamp)
        
        # Load dataset
        ds = get_dataset()
        
        # Validate species
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found'}), 400
        
        # Convert geometry to shapely
        geometry = shape(geometry_json)
        
        # Get bounding box with padding
        min_x, min_y, max_x, max_y = geometry.bounds
        
        # Select time slice (nearest time)
        ds_time = ds.sel(time=ts, method='nearest')
        
        # Select spatial region
        ds_subset = ds_time.sel(
            longitude=slice(min_x, max_x),
            latitude=slice(min_y, max_y)
        )
        
        # Get the data array and compute
        data_array = ds_subset[species].compute()
        
        # Validate we have data
        if data_array.size == 0:
            return jsonify({'error': 'No data in selected region'}), 400
        
        # Get actual timestamp used
        actual_time = pd.Timestamp(ds_time.time.values).isoformat()
        
        # Extract data
        lon = data_array.longitude.values
        lat = data_array.latitude.values
        values = data_array.values
        
        # Validate data dimensions
        if len(lon) == 0 or len(lat) == 0:
            return jsonify({'error': 'Invalid data dimensions'}), 400
        
        # Get colorbar range (before plotting)
        vmin = float(np.nanmin(values))
        vmax = float(np.nanmax(values))
        
        # Check if we have valid data
        if np.isnan(vmin) or np.isnan(vmax) or vmin == vmax:
            # Return empty/placeholder response for no valid data
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
        
        # Use lock for thread-safe matplotlib operations
        with _plot_lock:
            # Create heatmap image
            fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
            fig.patch.set_alpha(0)
            ax.set_aspect('equal')
            
            try:
                # Plot heatmap with explicit bounds checking
                im = ax.pcolormesh(lon, lat, values, cmap='YlOrRd', alpha=0.6, 
                                   shading='auto', vmin=vmin, vmax=vmax)
                
                # Remove axes
                ax.set_xlim(min_x, max_x)
                ax.set_ylim(min_y, max_y)
                ax.axis('off')
                
                # Save to bytes with proper buffer handling
                buf = BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', 
                           pad_inches=0, transparent=True)
                buf.seek(0)
                
                # Encode to base64
                image_base64 = base64.b64encode(buf.read()).decode('utf-8')
                buf.close()
                
            finally:
                # Always close the figure
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
        # Ensure figure is closed on error
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
        
        # Load dataset
        ds = get_dataset()
        
        # Validate species
        if species not in ds.data_vars:
            return jsonify({'error': f'Species {species} not found'}), 400
        
        # Select nearest point
        ds_point = ds.sel(latitude=lat, longitude=lon, method='nearest')
        
        # Apply time filter if specified
        if start_date or end_date:
            ds_point = ds_point.sel(time=slice(start_date, end_date))
        
        # Get time series
        timeseries = ds_point[species].compute()
        
        # Convert to list format
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
    # Verify ZARR store exists before starting
    if not os.path.exists(ZARR_STORE):
        print(f"ERROR: ZARR store not found at {ZARR_STORE}")
        print("Please set the ZARR_STORE environment variable to the correct path")
        exit(1)
    
    print(f"Starting Atmospheric Pollution API server...")
    print(f"Using ZARR store: {ZARR_STORE}")
    
    # Pre-load the dataset
    try:
        get_dataset()
        print("Dataset loaded successfully!")
    except Exception as e:
        print(f"ERROR loading dataset: {e}")
        exit(1)
    
    port = int(os.environ.get('PORT', 4006))
    app.run(host='0.0.0.0', port=port, debug=True)
