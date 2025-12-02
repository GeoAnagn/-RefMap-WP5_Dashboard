import os
import numpy as np
import matplotlib 
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import xarray as xr
import io
import base64
from flask import Flask, make_response, request, jsonify, send_from_directory
from flask_cors import CORS
from pyproj import Transformer, CRS
import json
import re 
import traceback 

# --- Configuration ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# DATA_BASE_DIR: Location of the *original* .bin files (x, y, Umag, TKE) for TUDelft data
DATA_BASE_DIR = os.path.abspath(os.path.join(APP_ROOT, "..", "..", "backend", "wind_assessment", "data"))

# PLOT_OUTPUT_DIR: Location of the pre-generated *overlay* PNG files for TUDelft data
PLOT_OUTPUT_DIR = os.path.abspath(os.path.join("data", "output_pngs_overlay"))


# Define Coordinate Systems (RD New for Netherlands)
CRS_RD_NEW = CRS("EPSG:28992")
CRS_WGS84 = CRS("EPSG:4326") # WGS84 for Leaflet

# Initialize Transformers
try:
    transformer_rd_to_wgs = Transformer.from_crs(CRS_RD_NEW, CRS_WGS84, always_xy=True)
    transformer_wgs_to_rd = Transformer.from_crs(CRS_WGS84, CRS_RD_NEW, always_xy=False)
    print("Coordinate Transformers Initialized Successfully.")
except Exception as e:
    print(f"[FATAL] Failed to initialize pyproj Transformers: {e}")
    exit(1)

# City specific info (Centers converted to Lat/Lon, Zoom, **Radius for approximate bounds**)
CITY_INFO = {
    "TUDelft Campus": {"center_latlon": [52.001, 4.372], "default_zoom": 15, "radius_m": 500},
    "Denhaag": {"center_latlon": [52.07746, 4.3150], "default_zoom": 14, "radius_m": 1100}
}

# Mapping from display parameter names to actual parameter codes in filenames
PARAMETER_MAPPING = {
    "Wind Speed": "Umag",
    "Turbulence Level": "TKE"
}
# --- End Configuration ---


# --- Initialize Flask ---
app = Flask(__name__, static_folder=PLOT_OUTPUT_DIR, static_url_path='/static/plots')
CORS(app)
print(f"--- TUDelft Flow Analysis Map Server ---")
print(f"Serving pre-generated plots from: {app.static_folder}")
print(f"Plots accessible under URL path: {app.static_url_path}")
print(f"Expecting original data (.bin) in subdirs of: {DATA_BASE_DIR}")

if not os.path.isdir(DATA_BASE_DIR):
     print(f"[WARNING] DATA_BASE_DIR not found: {DATA_BASE_DIR}")
if not os.path.isdir(app.static_folder):
     print(f"[WARNING] PLOT_OUTPUT_DIR (static folder) not found: {app.static_folder}")

# --- Helper Functions (Original) ---
def read_binary_safe(filepath, dtype=np.float64):
    """Safely reads a binary file, returns None on error."""
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, 'rb') as f:
            return np.fromfile(f, dtype=dtype)
    except Exception as e:
        print(f"Error reading binary file {filepath}: {e}")
        return None

# --- Helper functions from the Python script, adapted for Flask (Scientific Plots) ---
def sci_SetGetUnitandTitle(var):
    if (var == 'PM25'):
        unit = r'$\mu g / m^3$' # Raw string for LaTeX
        title = r'$PM_{2.5}$ annual-averaged values for the year 2019'
    else:
        unit = 'ppbv'
        if (var == 'SpeciesConcVV_NO2'):
            title = r'$NO_{2}$ annual-averaged values for the year 2019'
        elif (var == 'SpeciesConcVV_O3'):
            title = r'$O_{3}$ annual-averaged values for the year 2019'
        else: # Default for unknown species if any more are added
            unit = 'unknown'
            title = f'{var} annual-averaged values for the year 2019'
    return title, unit

def sci_SetGetPlotRange(spc):
    # Ensure spc is an xarray DataArray
    # Use .item() to convert numpy scalars to Python scalars for JSON compatibility
    s_max = spc.max().item()
    s_min = spc.min().item()
    vmax = max(s_max, abs(s_min))
    vmin = -vmax
    # Handle cases where min and max are too close or zero
    if np.isclose(vmax, 0.0) and np.isclose(vmin, 0.0): # If all data is zero
        vmax = 1.0
        vmin = 0.0 # Or -1.0 if centered is always desired
    elif np.isclose(vmax, vmin): # If data is constant but not zero
        vmin = vmin - 0.5 # Create a small range
        vmax = vmax + 0.5
    return vmax, vmin


def sci_GetSurfaceValues(var, ds):
    return ds[var].isel(lev=0).squeeze()

# Modified PlotSGCSGrid to plot on a given ax and return the pcm for colorbar
def sci_PlotSGCSGrid_on_ax(ax, ds, spc, vmin, vmax, cmap='seismic'):
    pcm = None # To store the last pcm object, used for the colorbar
    for face_idx in range(6):
        x = ds.corner_lons.isel(nf=face_idx)
        y = ds.corner_lats.isel(nf=face_idx)
        v = spc.isel(nf=face_idx)
        # Use the passed ax and its projection context
        pcm = ax.pcolormesh(x, y, v, transform=ccrs.PlateCarree(), vmin=vmin, vmax=vmax, cmap=cmap)
    return pcm
# --- End Helper Functions ---


# --- API Routes (Original) ---

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

            # Scan parameter display folders (e.g., "Wind Speed", "Turbulence Level")
            for param_display_name in sorted(os.listdir(city_path)):
                param_display_path = os.path.join(city_path, param_display_name)
                if not os.path.isdir(param_display_path): 
                    continue
                
                # Get the actual parameter code used in filenames
                param_code = PARAMETER_MAPPING.get(param_display_name)
                if not param_code:
                    print(f"      Warning: Unknown parameter display name '{param_display_name}', skipping")
                    continue
                
                print(f"        Scanning Parameter: {param_display_name} (code: {param_code})")

                # Scan z-level folders (e.g., "z2m", "z3m", etc.)
                for zloc_folder_name in sorted(os.listdir(param_display_path)):
                    zloc_path = os.path.join(param_display_path, zloc_folder_name)
                    if not os.path.isdir(zloc_path): 
                        continue

                    # Extract z-level number from folder name (e.g., "z10m" -> "10")
                    zloc_match = re.match(r"z(\d+)m?", zloc_folder_name)
                    if not zloc_match: 
                        continue
                    zloc_num_str = zloc_match.group(1)
                    print(f"          Scanning Z-level: {zloc_folder_name} (z{zloc_num_str})")

                    # Scan PNG files in this z-level folder
                    for fname in os.listdir(zloc_path):
                        match = filename_pattern.match(fname)
                        if match:
                            file_param_code = match.group(1)
                            file_zloc = match.group(2) 
                            wind_index = int(match.group(3))
                            
                            # Verify the file matches expected parameter and z-level
                            if file_param_code == param_code and file_zloc == zloc_num_str:
                                combo_key = (param_display_name, zloc_num_str)
                                if combo_key not in combos_winds:
                                    combos_winds[combo_key] = []
                                combos_winds[combo_key].append(wind_index)
                                print(f"            Found: {fname} -> param={param_display_name}, z={zloc_num_str}, wind={wind_index}")

            # Build final combinations list for this city
            if combos_winds:
                city_combinations_list = []
                for (param_display, zloc), winds in sorted(combos_winds.items(), key=lambda item: (item[0][0], int(item[0][1]))):
                    winds.sort()
                    city_combinations_list.append({
                        "param": param_display,  # Use display name instead of code
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
    param_display = request.args.get("param")  # This will be the display name like "Wind Speed"
    zloc = request.args.get("zloc") 
    wind = request.args.get("wind") 
    print(f"API: /image_info - Request: lod={lod}, city={city}, param={param_display}, zloc={zloc}, wind={wind}")

    if not all([lod, city, param_display, zloc, wind]):
        return jsonify({"error": "Missing one or more required query parameters (lod, city, param, zloc, wind)"}), 400
    try:
        wind_int = int(wind)
    except ValueError:
        return jsonify({"error": f"Invalid wind format: '{wind}'. Must be an integer."}), 400

    # Get the parameter code used in filenames from the display name
    param_code = PARAMETER_MAPPING.get(param_display)
    if not param_code:
        return jsonify({"error": f"Unknown parameter display name: '{param_display}'"}), 400

    # Build paths using new structure
    plot_filename = f"overlay_{param_code}_z{zloc}_{wind}.png"
    print(f"  Looking for plot file: {plot_filename}")
    plot_rel_path = os.path.join(lod, city, param_display, f"z{zloc}m", plot_filename)
    plot_abs_path = os.path.join(app.static_folder, plot_rel_path)
    
    # Data file path (this might need to be updated based on actual data file structure)
    # data_sub_dir = os.path.join(DATA_BASE_DIR, lod, city, "data")
    # param_data_path = os.path.join(data_sub_dir, f"{param_code}_{zloc}_{wind}.bin")

    if not os.path.isfile(plot_abs_path):
        return jsonify({"error": f"Plot image '{plot_filename}' not found at path: {plot_abs_path}"}), 404

    # Read image as base64
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
    # param_data = read_binary_safe(param_data_path)
    # if param_data is None:
    #      return jsonify({"error": f"Required data file '{os.path.basename(param_data_path)}' not found or unreadable."}), 404
    # try:
    #     if param_data.size == 0 or np.all(np.isnan(param_data)):
    #         pass # Use default min/max
    #     else:
    #         min_val = float(np.nanmin(param_data))
    #         max_val = float(np.nanmax(param_data))
    #         if not np.isfinite(min_val): min_val = 0.0
    #         if not np.isfinite(max_val) or np.isclose(max_val, min_val):
    #             max_val = min_val + 1.0 if np.isfinite(min_val) else 1.0
    # except Exception as e:
    #     return jsonify({"error": f"Error processing data file for min/max range: {e}"}), 500
    
    # Return image as base64 instead of URL
    return jsonify({
        "image_data": img_base64,
        "bounds": bounds_latlon,
        "minVal": min_val,
        "maxVal": max_val
    })

# --- Main Execution Block ---
if __name__ == "__main__":
    print("\nStarting Flask server...")
    # Check if the scientific data file actually exists where expected
    app.run(debug=True, host='0.0.0.0', port=4002)