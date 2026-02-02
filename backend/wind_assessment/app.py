import re 
import os
import base64
import numpy as np
import matplotlib 
matplotlib.use('Agg') 
import cartopy.crs as ccrs
from flask_cors import CORS
from pyproj import Transformer, CRS
from flask import Flask, request, jsonify

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_BASE_DIR = os.path.abspath(os.path.join(APP_ROOT, "..", "..", "backend", "wind_assessment", "data"))
PLOT_OUTPUT_DIR = os.path.abspath(os.path.join("data", "output_pngs_overlay"))

CRS_RD_NEW = CRS("EPSG:28992")
CRS_WGS84 = CRS("EPSG:4326")

try:
    transformer_rd_to_wgs = Transformer.from_crs(CRS_RD_NEW, CRS_WGS84, always_xy=True)
    transformer_wgs_to_rd = Transformer.from_crs(CRS_WGS84, CRS_RD_NEW, always_xy=False)
except Exception as e:
    print(f"[FATAL] Failed to initialize pyproj Transformers: {e}")
    exit(1)


app = Flask(__name__, static_folder=PLOT_OUTPUT_DIR, static_url_path='/static/plots')
CORS(app)

CITY_INFO = {
    "TUDelft Campus": {"center_latlon": [52.001, 4.372], "default_zoom": 15, "radius_m": 500},
    "Denhaag": {"center_latlon": [52.07746, 4.3150], "default_zoom": 14, "radius_m": 1100}
}

PARAMETER_MAPPING = {
    "Wind Speed": "Umag",
    "Turbulence Level": "TKE"
}

if not os.path.isdir(DATA_BASE_DIR):
     print(f"[WARNING] DATA_BASE_DIR not found: {DATA_BASE_DIR}")
if not os.path.isdir(app.static_folder):
     print(f"[WARNING] PLOT_OUTPUT_DIR (static folder) not found: {app.static_folder}")


@app.route("/api/available_combinations", methods=["GET"])
def available_combinations():
    """
    Scans the PLOT_OUTPUT_DIR for available pre-generated PNGs
    and returns the available LODs, Cities, parameters, z-locations,
    and the list of available winds (indices) for each combo.
    Includes city center metadata for map initialization.
    
    New folder structure:
    output_pngs_overlay/LoD X.X/City Name/Parameter Display Name/zXXm/overlay_PARAM_zXX_N.png
    """
    results = {}
    print(f"API: /available_combinations - Scanning PLOT_OUTPUT_DIR: {PLOT_OUTPUT_DIR}")

    if not os.path.isdir(PLOT_OUTPUT_DIR):
        print(f"  Error: Plot output directory not found.")
        return jsonify({"error": f"Plot output directory not found: {PLOT_OUTPUT_DIR}"}), 404

    filename_pattern = re.compile(r"overlay_([^_]+)_z(\d+)_(\d+)\.png")
    print(os.listdir(PLOT_OUTPUT_DIR))
    
    for lod_name in sorted(os.listdir(PLOT_OUTPUT_DIR)):
        lod_path = os.path.join(PLOT_OUTPUT_DIR, lod_name)
        if not os.path.isdir(lod_path): 
            continue

        results[lod_name] = {}
        print(f"  Scanning LOD: {lod_name} at {lod_path}")
        
        for city_name in sorted(os.listdir(lod_path)):
            print(f"    Scanning City: {city_name}")
            city_path = os.path.join(lod_path, city_name)
            if not os.path.isdir(city_path): 
                continue
            print(f"      City Path: {city_path}")
            
            city_meta = CITY_INFO.get(city_name, {})
            combos_winds = {}

            for param_display_name in sorted(os.listdir(city_path)):
                param_display_path = os.path.join(city_path, param_display_name)
                if not os.path.isdir(param_display_path): 
                    continue
                
                param_code = PARAMETER_MAPPING.get(param_display_name)
                if not param_code:
                    print(f"      Warning: Unknown parameter display name '{param_display_name}', skipping")
                    continue
                
                print(f"        Scanning Parameter: {param_display_name} (code: {param_code})")

                for zloc_folder_name in sorted(os.listdir(param_display_path)):
                    zloc_path = os.path.join(param_display_path, zloc_folder_name)
                    if not os.path.isdir(zloc_path): 
                        continue

                    zloc_match = re.match(r"z(\d+)m?", zloc_folder_name)
                    if not zloc_match: 
                        continue
                    zloc_num_str = zloc_match.group(1)
                    print(f"          Scanning Z-level: {zloc_folder_name} (z{zloc_num_str})")

                    for fname in os.listdir(zloc_path):
                        match = filename_pattern.match(fname)
                        if match:
                            file_param_code = match.group(1)
                            file_zloc = match.group(2) 
                            wind_index = int(match.group(3))
                            
                            if file_param_code == param_code and file_zloc == zloc_num_str:
                                combo_key = (param_display_name, zloc_num_str)
                                if combo_key not in combos_winds:
                                    combos_winds[combo_key] = []
                                combos_winds[combo_key].append(wind_index)
                                print(f"            Found: {fname} -> param={param_display_name}, z={zloc_num_str}, wind={wind_index}")

            if combos_winds:
                city_combinations_list = []
                for (param_display, zloc), winds in sorted(combos_winds.items(), key=lambda item: (item[0][0], int(item[0][1]))):
                    winds.sort()
                    city_combinations_list.append({
                        "param": param_display,
                        "zloc": zloc,
                        "winds": winds
                    })

                if city_combinations_list:
                    results[lod_name][city_name] = {
                        "combinations": city_combinations_list,
                        "metadata": city_meta
                    }

    final_results = { lod: cities for lod, cities in results.items() if cities }
    print(f"API: /available_combinations - Found {len(final_results)} LODs with data.")
    return jsonify(final_results)

@app.route("/api/image_info", methods=["GET"])
def image_info():
    """
    Provides necessary info (image as base64, APPROXIMATE Lat/Lon bounds from CITY_INFO, data range)
    to display a specific pre-rendered plot image on the map.
    
    New folder structure:
    output_pngs_overlay/LoD X.X/City Name/Parameter Display Name/zXXm/overlay_PARAM_zXX_N.png
    """
    lod = request.args.get("lod")
    city = request.args.get("city")
    param_display = request.args.get("param")
    zloc = request.args.get("zloc") 
    wind = request.args.get("wind") 
    print(f"API: /image_info - Request: lod={lod}, city={city}, param={param_display}, zloc={zloc}, wind={wind}")

    if not all([lod, city, param_display, zloc, wind]):
        return jsonify({"error": "Missing one or more required query parameters (lod, city, param, zloc, wind)"}), 400
    try:
        wind_int = int(wind)
    except ValueError:
        return jsonify({"error": f"Invalid wind format: '{wind}'. Must be an integer."}), 400

    param_code = PARAMETER_MAPPING.get(param_display)
    if not param_code:
        return jsonify({"error": f"Unknown parameter display name: '{param_display}'"}), 400

    plot_filename = f"overlay_{param_code}_z{zloc}_{wind}.png"
    print(f"  Looking for plot file: {plot_filename}")
    plot_rel_path = os.path.join(lod, city, param_display, f"z{zloc}m", plot_filename)
    plot_abs_path = os.path.join(app.static_folder, plot_rel_path)
    
    if not os.path.isfile(plot_abs_path):
        return jsonify({"error": f"Plot image '{plot_filename}' not found at path: {plot_abs_path}"}), 404

    with open(plot_abs_path, 'rb') as img_file:
        img_bytes = img_file.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

    bounds_latlon = None
    city_meta = CITY_INFO.get(city)
    if not city_meta or "center_latlon" not in city_meta or "radius_m" not in city_meta:
        return jsonify({"error": f"Incomplete configuration for city '{city}'."}), 404

    center_lat, center_lon = city_meta["center_latlon"]
    radius_m = city_meta["radius_m"]
    try:
        center_x_rd, center_y_rd = transformer_wgs_to_rd.transform(center_lat, center_lon)
        min_x_rd, max_x_rd = center_x_rd - radius_m, center_x_rd + radius_m
        min_y_rd, max_y_rd = center_y_rd - radius_m, center_y_rd + radius_m
        lon_sw, lat_sw = transformer_rd_to_wgs.transform(min_x_rd, min_y_rd)
        lon_ne, lat_ne = transformer_rd_to_wgs.transform(max_x_rd, max_y_rd)
        if not all(np.isfinite(val) for val in [lon_sw, lat_sw, lon_ne, lat_ne]):
             raise ValueError("Coordinate transformation resulted in non-finite values.")
        bounds_latlon = [[lat_sw, lon_sw], [lat_ne, lon_ne]]
    except Exception as e:
        return jsonify({"error": f"Coordinate transformation/bounds calculation failed: {e}"}), 500

    min_val, max_val = 0.0, 1.0
    return jsonify({
        "image_data": img_base64,
        "bounds": bounds_latlon,
        "minVal": min_val,
        "maxVal": max_val
    })

if __name__ == "__main__":
    print("\nStarting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=4002)