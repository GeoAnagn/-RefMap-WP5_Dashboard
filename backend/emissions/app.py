import os
import json
import base64
import time
import xarray as xr
import numpy as np
from urllib.parse import quote_plus
from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_BASE_DIR = os.path.join(APP_ROOT, 'data', 'contour_maps')

app = Flask(__name__)
CORS(app)

# Default geographic bounds for Europe region used in plots
DEFAULT_BOUNDS = {
	'lat-min': 30.0,
	'lat-max': 80.0,
	'lon-min': -15.0,
	'lon-max': 50.0,
}

# Case normalization to present consistent options (base, increase, difference)
CASE_SYNONYMS = {
	'base': ['base'],
	'increase': ['increase', 'sens', 'sensitivity', 'scenario', 'reduction', '10perc_reduction'],
	'difference': ['diff', 'difference'],
}

UNITS_BY_METRIC = {
	'pm25': 'ug/m3',
	'no2': 'ppbv',
	'o3': 'ppbv',
}

# Map canonical case to metadata key used in colorbar.json
COLORBAR_CASE_KEY = {
	'base': 'base',
	'increase': 'sens',
	'difference': 'diff',
}


def _canonical_case(case: str):
	"""Normalize a requested case string to canonical label: base | increase | difference."""
	if not case:
		return None
	lower = case.lower()
	for canonical, aliases in CASE_SYNONYMS.items():
		if lower == canonical or lower in aliases:
			return canonical
	return None

# Cache computed bounds so we don't reopen the NetCDF on every request
_BOUNDS_CACHE = None


def _compute_bounds_from_nc():
	"""Read lat/lon from NetCDF and derive Leaflet-friendly bounds."""
	global _BOUNDS_CACHE
	if _BOUNDS_CACHE:
		return _BOUNDS_CACHE

	# Prefer base file; fall back to sensitivity if needed
	base_nc = os.path.join(APP_ROOT, 'data', 'latlon_regrid_base.nc4')
	sens_nc = os.path.join(APP_ROOT, 'data', 'latlon_regrid_sens.nc4')
	nc_path = base_nc if os.path.isfile(base_nc) else sens_nc
	if not os.path.isfile(nc_path):
		return DEFAULT_BOUNDS

	try:
		ds = xr.open_dataset(nc_path)
		lat = ds['lat']
		lon = ds['lon']
		lat_min = float(lat.min().item())
		lat_max = float(lat.max().item())
		lon_min = float(lon.min().item())
		lon_max = float(lon.max().item())

		# Pad by half a grid step to cover cell edges (if regular grid)
		dlat = np.nan
		dlon = np.nan
		try:
			if lat.size > 1:
				dlat = float(np.nanmedian(np.abs(np.diff(lat.values.ravel()))))
			if lon.size > 1:
				dlon = float(np.nanmedian(np.abs(np.diff(lon.values.ravel()))))
		except Exception:
			pass

		if np.isfinite(dlat) and dlat > 0:
			lat_min -= dlat / 2
			lat_max += dlat / 2
		if np.isfinite(dlon) and dlon > 0:
			lon_min -= dlon / 2
			lon_max += dlon / 2

		_BOUNDS_CACHE = {
			'lat-min': lat_min,
			'lat-max': lat_max,
			'lon-min': lon_min,
			'lon-max': lon_max,
		}
		ds.close()
		return _BOUNDS_CACHE
	except Exception as e:
		print(f"[WARNING] Failed to compute bounds from {nc_path}: {e}")
		return DEFAULT_BOUNDS


def _canonical_case_from_name(name: str):
	"""Map a filename stem to canonical case: base | increase | difference."""
	lower = name.lower()
	for canonical, keys in CASE_SYNONYMS.items():
		for key in keys:
			if key in lower:
				return canonical
	return None


def _scan_case_files(metric_path: str):
	"""Return mapping canonical_case -> filename for available PNGs."""
	result = {}
	if not os.path.isdir(metric_path):
		return result
	for fname in os.listdir(metric_path):
		base, ext = os.path.splitext(fname)
		if ext.lower() != '.png':
			continue
		canonical = _canonical_case_from_name(base)
		if canonical and canonical not in result:
			result[canonical] = fname
	return result


def _find_case_insensitive_dir(parent: str, name: str):
	"""Return a directory path under parent that matches name (case-insensitive)."""
	if not os.path.isdir(parent):
		return None
	lower_name = name.lower()
	for entry in os.listdir(parent):
		if os.path.isdir(os.path.join(parent, entry)) and entry.lower() == lower_name:
			return os.path.join(parent, entry)
	return None


def _resolve_case_png_path(reduction: str, metric: str, case: str):
	"""Resolve the on-disk PNG path for a reduction/metric/case selection (case-insensitive)."""
	reduction_dir = _find_case_insensitive_dir(DATA_BASE_DIR, reduction)
	if not reduction_dir:
		return None
	metric_dir = _find_case_insensitive_dir(reduction_dir, metric)
	if not metric_dir:
		return None

	selected_file = None
	case_files = _scan_case_files(metric_dir)
	selected_file = case_files.get(case)

	# Fallback: attempt exact stem match when canonical mapping is absent
	if not selected_file:
		for fname in os.listdir(metric_dir):
			base, ext = os.path.splitext(fname)
			if ext.lower() != '.png':
				continue
			if base.lower() == case.lower():
				selected_file = fname
				break

	if not selected_file:
		return None

	return os.path.join(metric_dir, selected_file)


def _read_colorbar_metadata(reduction: str, metric: str, canonical_case: str):
	"""Load vmin/vmax from colorbar.json for the selected case, if present."""
	case_key = COLORBAR_CASE_KEY.get(canonical_case)
	if not case_key:
		return None, None

	metric_dir = _find_case_insensitive_dir(DATA_BASE_DIR, reduction)
	if not metric_dir:
		return None, None
	metric_dir = _find_case_insensitive_dir(metric_dir, metric)
	if not metric_dir:
		return None, None

	meta_path = os.path.join(metric_dir, 'colorbar.json')
	if not os.path.isfile(meta_path):
		return None, None

	try:
		with open(meta_path, 'r', encoding='utf-8') as f:
			data = json.load(f)
		case_entry = data.get(case_key)
		if not case_entry:
			return None, None
		return case_entry.get('vmin'), case_entry.get('vmax')
	except Exception as e:
		print(f"[WARNING] Failed to read colorbar metadata at {meta_path}: {e}")
		return None, None


def _round_color_value(val):
	"""Round colorbar endpoints: tiny magnitudes to 2 decimals in scientific notation, others to 2 decimals."""
	if not isinstance(val, (int, float)) or not np.isfinite(val):
		return val
	abs_val = abs(val)
	if abs_val < 1e-3:
		return float(f"{val:.2e}")
	return round(val, 2)

def _list_reductions():
	"""Return available NOx reduction folders (top-level directories)."""
	if not os.path.isdir(DATA_BASE_DIR):
		return []
	try:
		return [d for d in sorted(os.listdir(DATA_BASE_DIR)) if os.path.isdir(os.path.join(DATA_BASE_DIR, d))]
	except Exception as e:
		print(f"[WARNING] Failed to list reductions: {e}")
		return []


@app.route('/api/emissions_reductions', methods=['GET'])
def emissions_reductions():
	"""List available NOx reduction percentages (top-level folders)."""
	return jsonify(_list_reductions())


@app.route('/api/emissions_metrics', methods=['GET'])
def emissions_metrics():
	"""List available metrics (subdirectories under a reduction folder)."""
	reduction = request.args.get('reduction')
	if not reduction:
		return jsonify([])
	reduction_path = os.path.join(DATA_BASE_DIR, reduction)
	if not os.path.isdir(reduction_path):
		return jsonify([])
	try:
		metrics = [d for d in sorted(os.listdir(reduction_path)) if os.path.isdir(os.path.join(reduction_path, d))]
		return jsonify(metrics)
	except Exception as e:
		print(f"[WARNING] Failed to list metrics for reduction {reduction}: {e}")
		return jsonify([])


@app.route('/api/emissions_cases', methods=['GET'])
def emissions_cases():
	"""List available cases using canonical labels (base, increase, difference)."""
	reduction = request.args.get('reduction')
	metric = request.args.get('metric')
	if not reduction or not metric:
		return jsonify([])
	metric_path = os.path.join(DATA_BASE_DIR, reduction, metric)
	if not os.path.isdir(metric_path):
		return jsonify([])
	try:
		case_files = _scan_case_files(metric_path)
		return jsonify(sorted(case_files.keys()))
	except Exception as e:
		print(f"[WARNING] Failed to list cases in {metric_path}: {e}")
		return jsonify([])


@app.route('/api/emissions_image', methods=['GET'])
def emissions_image():
	"""Return base64 overlay image and bounds for a selected reduction, metric, and case.

	Response: {
	  image_data: <base64 or null>,
	  bounds: {lat-min, lat-max, lon-min, lon-max},
	  colorbar: { type: 'sequential'|'diverging', units: str }
	}
	"""
	reduction = request.args.get('reduction')
	metric = request.args.get('metric')
	case = request.args.get('case')
	canonical = _canonical_case(case)
	include_b64 = True

	if not reduction or not metric or not case:
		return jsonify({'image_data': None, 'image_url': None, 'bounds': DEFAULT_BOUNDS, 'colorbar': None})

	png_path = _resolve_case_png_path(reduction, metric, canonical or case)
	image_b64 = None
	image_url = None

	if png_path and os.path.isfile(png_path):
		# Lightweight delivery via URL; cache-bust so client refreshes when selection changes
		ts = int(time.time())
		# Include the frontend proxy prefix so the Vite proxy forwards correctly.
		image_url = f"/api/emissions/api/emissions_image_file?reduction={quote_plus(reduction)}&metric={quote_plus(metric)}&case={quote_plus(case)}&ts={ts}"

		try:
			with open(png_path, 'rb') as f:
				image_b64 = base64.b64encode(f.read()).decode('utf-8')
		except Exception as e:
			print(f"[WARNING] Failed to read image for {metric}/{case}: {e}")

	# Derive bounds from the NetCDF grid (fallback to default on failure)
	bounds = _compute_bounds_from_nc()

	# Colorbar metadata: diverging for differences, sequential otherwise
	metric_lower = metric.lower()
	units = UNITS_BY_METRIC.get(metric_lower, '')
	canonical_label = canonical or case
	cbar_type = 'diverging' if canonical_label == 'difference' else 'sequential'
	cbar_min, cbar_max = _read_colorbar_metadata(reduction, metric, canonical_label)
	cbar_min = _round_color_value(cbar_min)
	cbar_max = _round_color_value(cbar_max)

	return jsonify({
		'image_data': image_b64,
		'image_url': image_url,
		'bounds': bounds,
		'colorbar': {
			'type': cbar_type,
			'units': units,
			'min': cbar_min,
			'max': cbar_max
		}
	})


@app.route('/api/emissions_image_file', methods=['GET'])
def emissions_image_file():
	"""Stream the PNG overlay directly (prefer this over base64 JSON)."""
	reduction = request.args.get('reduction')
	metric = request.args.get('metric')
	case = request.args.get('case')
	if not reduction or not metric or not case:
		abort(400)

	png_path = _resolve_case_png_path(reduction, metric, case)
	if not png_path or not os.path.isfile(png_path):
		abort(404)

	return send_file(png_path, mimetype='image/png')


if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=4005)

