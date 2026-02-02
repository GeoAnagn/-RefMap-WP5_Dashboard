import os
import json
import traceback
import threading
from netCDF4 import Dataset
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

netcdf_lock = threading.Lock()
basedir = os.path.abspath(os.path.dirname(__file__))
DATE_ROOT_DIR = os.path.join(basedir, "data")

def get_data_dir_for_date(date):
    return os.path.join(DATE_ROOT_DIR, date)

def get_heatmap_image_dir_for_date(date):
    return os.path.join(DATE_ROOT_DIR, date, "heatmaps_overlay_cloud_effect")

def infer_file_details(base_name):
    dt = None
    scale = None
    cost_val = ""

    print(f"DEBUG: infer_file_details called with base_name: {base_name}")
    if base_name.startswith("BAU_"):
        scale = "BAU"
        dt = base_name.replace("BAU_", "")
        cost_val = "noCost"
    else:
        print(f"DEBUG: Parsing base_name: {base_name}")
        parts = base_name.split("_")
        if len(parts) > 0:
            scale = parts[0].capitalize()
        else:
            scale = "Default"

        try:
            print(f"DEBUG: Looking for 'cost' in parts: {parts}")
            cost_index = [p.lower() for p in parts].index("cost")
            try:
                scale_word_index = [p.lower() for p in parts].index("scale")
                dt_parts = parts[scale_word_index + 1 : cost_index]
            except ValueError:
                dt_parts = parts[1 : cost_index] if len(parts) > 1 else []

            cost_val = parts[cost_index + 1] if cost_index + 1 < len(parts) else ""

        except ValueError:
            if len(parts) > 1:
                dt_parts = parts[1:]
                dt_parts = [p for p in dt_parts if p.lower() != 'scale']
            else:
                dt_parts = [base_name]

            cost_val = "noCost" 
        
        print(f"DEBUG: Data type parts: {dt_parts}")
        dt = "_".join(dt_parts)
        if not dt or dt.lower() in ['macro', 'micro', 'bau', 'scale', 'cost', '']:
            if len(parts) > 1 and parts[1].lower() not in ['scale', 'cost']:
                dt = parts[1]
            else:
                dt = base_name

        print(f"DEBUG: Final inferred values - dt: {dt}, scale: {scale}, cost_val: {cost_val}")
        scale = scale if scale else "Default"
        dt = dt if dt else "Default"

    return dt, scale, cost_val

def build_filter_info(selected_date):
    """
    Returns (data_types, scales, costs, files_map) for a given date.
    """
    data_dir_for_date = os.path.join(DATE_ROOT_DIR, selected_date)
    if not os.path.exists(data_dir_for_date):
        return [], {}, {}, {}
    netcdf_files = [f for f in os.listdir(data_dir_for_date) if f.endswith('.nc')]
    data_types = set()
    scales = {}
    costs = {}
    files_map = {}
    for file_name in netcdf_files:
        base_name = os.path.splitext(file_name)[0]
        dt, scale, cost_val = infer_file_details(base_name)
        data_types.add(dt)
        if dt not in scales: scales[dt] = set()
        scales[dt].add(scale)
        if dt not in costs: costs[dt] = {}
        if scale not in costs[dt]: costs[dt][scale] = set()
        if cost_val and cost_val != "noCost":
            costs[dt][scale].add(cost_val)
        if dt not in files_map: files_map[dt] = {}
        if scale not in files_map[dt]: files_map[dt][scale] = {}
        files_map[dt][scale][cost_val] = base_name
    data_types = sorted(list(data_types))
    for dt in scales:
        scales[dt] = sorted(list(scales[dt]))
    for dt in costs:
        for sc in costs[dt]:
            costs[dt][sc] = sorted(list(costs[dt][sc]))
    for dt in files_map:
        for sc in files_map[dt]:
            if "noCost" in files_map[dt][sc] and "noCost" not in costs[dt].get(sc, []):
                if dt not in costs: costs[dt] = {}
                if sc not in costs[dt]: costs[dt][sc] = []
                if "noCost" not in costs[dt][sc]:
                    costs[dt][sc].append("noCost")
                    costs[dt][sc].sort()
    return data_types, scales, costs, files_map

@app.route('/api/get-dates', methods=['GET'])
def get_dates():
    """Returns available date folders."""
    try:
        if not os.path.exists(DATE_ROOT_DIR):
            date_folders = []
        else:
            date_folders = [f for f in os.listdir(DATE_ROOT_DIR) if os.path.isdir(os.path.join(DATE_ROOT_DIR, f))]
            date_folders.sort()
        return jsonify({"dates": date_folders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-data-types', methods=['GET'])
def get_data_types():
    """Returns data types for a given date."""
    date = request.args.get('date', None)
    if not date:
        return jsonify({'error': 'No date specified'}), 400
    data_types, _, _, _ = build_filter_info(date)
    return jsonify({'dataTypes': data_types})

@app.route('/api/get-scales', methods=['GET'])
def get_scales():
    """Returns scales for a given date and data type."""
    date = request.args.get('date', None)
    data_type = request.args.get('dataType', None)
    if not date or not data_type:
        return jsonify({'error': 'No date or dataType specified'}), 400
    _, scales, _, _ = build_filter_info(date)
    scale_list = scales.get(data_type, [])
    return jsonify({'scales': scale_list})

@app.route('/api/get-costs', methods=['GET'])
def get_costs():
    """Returns costs for a given date, data type, and scale."""
    date = request.args.get('date', None)
    data_type = request.args.get('dataType', None)
    scale = request.args.get('scale', None)
    if not date or not data_type or not scale:
        return jsonify({'error': 'No date, dataType, or scale specified'}), 400
    _, _, costs, _ = build_filter_info(date)
    cost_list = costs.get(data_type, {}).get(scale, [])
    return jsonify({'costs': cost_list})

@app.route('/api/get-netcdf-metadata', methods=['GET'])
def get_netcdf_metadata():
    """
    Returns metadata (altitudes, times, lon/lat bounds, overall min/max) for a given NetCDF file.
    Query params: date, dataType, scale, cost
    """
    try:
        selected_date = request.args.get('date', '')
        data_type = request.args.get('dataType', '')
        scale = request.args.get('scale', '')
        cost = request.args.get('cost', '')
        if not selected_date or not data_type or not scale:
            return jsonify({'error': 'Missing required filter(s)'}), 400
        _, _, _, files_map = build_filter_info(selected_date)
        file_base = ''
        if files_map.get(data_type, {}).get(scale, {}):
            cost_key = cost if cost in files_map[data_type][scale] else 'noCost'
            file_base = files_map[data_type][scale].get(cost_key, '')
        if not file_base:
            return jsonify({'error': 'No matching NetCDF file for the selected filters'}), 404
        data_dir = get_data_dir_for_date(selected_date)
        nc_path = os.path.join(data_dir, file_base + '.nc')
        if not os.path.exists(nc_path):
            return jsonify({'error': f"NetCDF file not found: {file_base}.nc"}), 404
        
        with netcdf_lock:
            with Dataset(nc_path, 'r') as ds:
                alt_keys = [k for k in ds.variables.keys() if k.lower() in ['altitude', 'alt', 'level', 'lev', 'flightlevel', 'fl']]
                time_keys = [k for k in ds.variables.keys() if k.lower() in ['time', 't']]
                altitudes = ds.variables[alt_keys[0]][:].tolist() if alt_keys else []
                times = ds.variables[time_keys[0]][:].tolist() if time_keys else []
                lon_keys = [k for k in ds.variables.keys() if k.lower() in ['lon', 'longitude']]
                lat_keys = [k for k in ds.variables.keys() if k.lower() in ['lat', 'latitude']]
                lon_min = float(ds.variables[lon_keys[0]][:].min()) if lon_keys else None
                lon_max = float(ds.variables[lon_keys[0]][:].max()) if lon_keys else None
                lat_min = float(ds.variables[lat_keys[0]][:].min()) if lat_keys else None
                lat_max = float(ds.variables[lat_keys[0]][:].max()) if lat_keys else None
                main_var = None
                for vname, var in ds.variables.items():
                    if vname.lower() in ['time', 'altitude', 'alt', 'level', 'lev', 'flightlevel', 'fl', 'lon', 'longitude', 'lat', 'latitude']:
                        continue
                    if hasattr(var, 'ndim') and var.ndim >= 2:
                        main_var = var
                        break
                overall_min_value = float(main_var[:].min()) if main_var is not None else None
                overall_max_value = float(main_var[:].max()) if main_var is not None else None
        return jsonify({
            'altitudes': altitudes,
            'times': times,
            'lon_min': lon_min,
            'lon_max': lon_max,
            'lat_min': lat_min,
            'lat_max': lat_max,
            'overall_min_value': overall_min_value,
            'overall_max_value': overall_max_value,
            'file_base': file_base
        })
    except Exception as e:
        print('Exception in get_netcdf_metadata:', e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-heatmap-overlay', methods=['GET'])
def get_heatmap_overlay():
    """
    Serves a pre-generated heatmap overlay image using send_file.
    Requires ?file=<base_filename>&time=<time_idx>&altitude=<alt_idx>&date=<date>
    """
    try:
        requested_file_base = request.args.get('file', '')
        time_idx_str = request.args.get('time', '0')
        alt_idx_str = request.args.get('altitude', '0')
        selected_date = request.args.get('date', '')
        if not requested_file_base or not selected_date:
            return jsonify({'error': 'No file or date specified'}), 400
        try:
            time_idx = int(time_idx_str)
            alt_idx = int(alt_idx_str)
            time_idx_padded = f"{time_idx:03d}"
            alt_idx_padded = f"{alt_idx:03d}"
        except ValueError:
            return jsonify({'error': 'Invalid time or altitude index'}), 400
        image_filename = f"{requested_file_base}_t{time_idx_padded}_alt{alt_idx_padded}_cloud_overlay.png"
        heatmap_image_dir = get_heatmap_image_dir_for_date(selected_date)
        full_image_path = os.path.join(heatmap_image_dir, image_filename)

        print(f"DEBUG (send_file): Attempting to serve full path: {full_image_path}")
        print(f"DEBUG (send_file): Does the file exist at this path? {os.path.exists(full_image_path)}")


        if not os.path.exists(full_image_path):
             print(f"Error (send_file): Image file not found at expected path: {full_image_path}")
             image_filename_for_error = f"{requested_file_base}_t{time_idx_padded}_alt{alt_idx_padded}_cloud_overlay.png"
             return jsonify({'error': f"Image file not found: {image_filename_for_error}"}), 404 

        return send_file(full_image_path, mimetype='image/png') 


    except Exception as e:
        image_filename_for_error = f"{requested_file_base}_t{time_idx_padded}_alt{alt_idx_padded}_cloud_overlay.png"
        print(f"Unexpected error in get_heatmap_overlay for {image_filename_for_error}: {e}")
        return jsonify({'error': f"An unexpected server error occurred: {str(e)}"}) , 500

@app.route('/api/get-atr-percentage-increase', methods=['GET'])
def get_atr_percentage_increase():
    """
    Returns the percentage increase/decrease of each metric (Net_ATR, NOx, H2O, CO2, AIC)
    with respect to BAU for each cost/scale, for a given date and scale.
    Query params: date=25022025&scale=Micro|Macro
    """
    try:
        selected_date = request.args.get('date', '')
        selected_scale = request.args.get('scale', '')
        if not selected_date or not selected_scale:
            return jsonify({'error': 'No date or scale specified'}), 400
        data_dir = get_data_dir_for_date(selected_date)
        file_path = os.path.join(data_dir, 'ATR_Information.json')
        if not os.path.exists(file_path):
            return jsonify({'error': f"ATR_Information.json not found for date {selected_date}"}), 404
        with open(file_path, 'r') as f:
            atr_data = json.load(f)
        bau_entry = None
        for k, v in atr_data.items():
            if isinstance(v, dict) and str(v.get('Type', '')).strip().lower() == 'bau':
                bau_entry = v
                print(f"Found BAU entry at key: {k}")
                break
        if not bau_entry:
            print("No BAU entry found! Available types:", [v.get('Type', '') for v in atr_data.values() if isinstance(v, dict)])
            return jsonify({'error': 'BAU entry not found in ATR_Information.json'}), 500
        results = []
        print(f"ATR_Information.json keys: {list(atr_data.keys())}")
        print(f"Selected scale: {selected_scale}")
        for k, v in atr_data.items():
            if not isinstance(v, dict):
                print(f"Skipping key {k}: not a dict")
                continue
            v_type = str(v.get('Type', '')).strip().lower()
            if v_type == 'bau':
                continue
            if v_type != selected_scale.strip().lower():
                print(f"Skipping key {k}: type '{v_type}' != selected_scale '{selected_scale.strip().lower()}'")
                continue
            cost_increase = v.get('Increase in Cost')
            if cost_increase is None:
                print(f"Skipping key {k}: no 'Increase in Cost' field")
                continue
            try:
                cost_increase = float(cost_increase)
            except Exception as ex:
                print(f"Skipping key {k}: invalid 'Increase in Cost' value: {cost_increase} ({ex})")
                continue
            entry = {'cost_increase': cost_increase}
            for metric in ['Net_ATR', 'NOx', 'H2O', 'CO2', 'AIC']:
                bau_val = bau_entry.get(metric)
                val = v.get(metric)
                if bau_val is not None and val is not None and bau_val != 0:
                    pct = ((val - bau_val) / bau_val) * 100
                else:
                    pct = None
                entry[metric] = pct
                print(f"    Metric: {metric} | BAU: {bau_val} | Value: {val} | %: {pct}")
            results.append(entry)
        print(f"Final results: {results}")
        results.sort(key=lambda x: x['cost_increase'])
        
        return jsonify({'data': results})
    except Exception as e:
        print('Exception in get_atr_percentage_increase:', e)
        traceback.print_exc()
        
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4001)