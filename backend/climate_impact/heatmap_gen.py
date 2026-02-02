import os
import numpy as np
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import cartopy.crs as ccrs
from datetime import datetime, timedelta
from scipy.interpolate import griddata

# --- Configuration ---
DATA_DIR = "./data/"
OUTPUT_DIR = "heatmaps_overlay_cloud_effect"

# Define the fixed ranges for specific scenarios (used only when data is constant zero)
FIXED_DIVERGING_ZERO_VMİN = -1.0 # Renamed for clarity
FIXED_DIVERGING_ZERO_VMAX = 1.0  # Renamed for clarity
FIXED_DIVERGING_ZERO_VCENTER = 0.0 # Renamed for clarity

FIXED_COMPLEXITY_ZERO_VMIN = 0.0
FIXED_COMPLEXITY_ZERO_VMAX = 1.0

# Configuration for the output image size/resolution
FIG_WIDTH_INCHES = 10
OUTPUT_DPI = 150

# Resolution for the new grid for interpolation
NEW_GRID_RESOLUTION_X = 500

# --- Ensure Output Directory Exists ---
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created output directory: {OUTPUT_DIR}")

# --- Define Custom Colormaps ---
def create_transparent_red_cmap(name="TransparentRed", N=256):
    cmap_colors = [(1, 0, 0, 0), (1, 0, 0, 1)]
    return colors.LinearSegmentedColormap.from_list(name, cmap_colors, N)

def create_blue_transparent_red_cmap(name="BlueTransparentRed", N=256):
    cmap_colors = [(0, 0, 1, 1),
                   (0.5, 0.5, 0.5, 0),
                   (1, 0, 0, 1)]
    return colors.LinearSegmentedColormap.from_list(name, cmap_colors, N)

cmap_transparent_red = create_transparent_red_cmap()
cmap_blue_transparent_red = create_blue_transparent_red_cmap()

# --- Function to Determine Variable Name ---
def get_variable_name(file_name):
    base_name = os.path.splitext(file_name)[0].lower()
    if 'atr' in base_name:
        return 'Climate_Impact'
    elif 'contrails' in base_name:
        return 'Contrails'
    else:
        return 'Complexity'

# --- Main Script Logic ---
print(f"Scanning directory: {DATA_DIR}")
netcdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.nc')]

if not netcdf_files:
    print("No .nc files found in the specified directory.")
else:
    print(f"Found {len(netcdf_files)} .nc files.")

    total_files_to_process = len(netcdf_files)
    current_file_index = 0

    for file_name in netcdf_files:
        current_file_index += 1
        file_path = os.path.join(DATA_DIR, file_name)
        base_name = os.path.splitext(file_name)[0]
        print(f"\nProcessing file {current_file_index}/{total_files_to_process}: {file_name}...")

        try:
            with Dataset(file_path, 'r') as nc_file:
                latitude = nc_file.variables['latitude'][:]
                longitude = nc_file.variables['longitude'][:]
                altitudes = nc_file.variables['altitude'][:]
                time_seconds = nc_file.variables['Time'][:]

                variable_name = get_variable_name(file_name)

                if variable_name not in nc_file.variables:
                    print(f"  Error: Variable '{variable_name}' not found in {file_name}. Skipping file.")
                    continue

                values = nc_file.variables[variable_name][:] # shape: (nTime, nAlt, nLat, nLon)

                n_time, n_alt, n_lat, n_lon = values.shape
                print(f"  Found {n_time} time steps, {n_alt} altitude levels, Lat={n_lat}, Lon={n_lon}.")

                # Get the geographical extent of the data
                lon_min, lon_max = float(np.nanmin(longitude)), float(np.nanmax(longitude))
                lat_min, lat_max = float(np.nanmin(latitude)), float(np.nanmax(latitude))

                # Calculate figure height based on desired width and data aspect ratio
                data_aspect_ratio = (lat_max - lat_min) / (lon_max - lon_min) if (lon_max - lon_min) != 0 else 1.0
                fig_height_inches = FIG_WIDTH_INCHES * data_aspect_ratio
                NEW_GRID_RESOLUTION_Y = int(NEW_GRID_RESOLUTION_X * data_aspect_ratio)

                # Define the new grid for interpolation target (unconditionally)
                new_lons = np.linspace(lon_min, lon_max, NEW_GRID_RESOLUTION_X)
                new_lats = np.linspace(lat_min, lat_max, NEW_GRID_RESOLUTION_Y)
                new_lon_grid, new_lat_grid = np.meshgrid(new_lons, new_lats)


                # --- Loop through all Time and Altitude slices ---
                for t_idx in range(n_time):
                     for alt_idx in range(n_alt):

                        try:
                            # Extract the 2D slice for the current time and altitude
                            data_slice = values[t_idx, alt_idx, :, :]

                            # Compute slice-specific min/max (ignoring NaNs)
                            slice_min = np.nanmin(data_slice) if not np.all(np.isnan(data_slice)) else None
                            slice_max = np.nanmax(data_slice) if not np.all(np.isnan(data_slice)) else None

                            # Skip plotting if data is all NaN
                            if slice_min is None or slice_max is None:
                                print(f"    Warning: Data slice at t={t_idx}, alt={alt_idx} contains only NaNs. Skipping plot.")
                                continue

                            # Get time string for the selected index
                            try:
                                 selected_time_str = (datetime(2000, 1, 1, 12, 0) + timedelta(seconds=float(time_seconds[t_idx]))).strftime('%H:%M')
                            except (IndexError, ValueError):
                                 selected_time_str = f"Index {t_idx}" # Fallback

                            print(f"    Processing slice T={t_idx} ({selected_time_str}), Alt={alt_idx} ({altitudes[alt_idx]:.1f})...")
                            print(f"      Original Data Slice Range: [{slice_min:.4f}, {slice_max:.4f}]")


                            # Determine colormap and normalization based on variable name and data range
                            if slice_min == slice_max:
                                constant_value = slice_min
                                print(f"      Info: Data slice is a constant value: {constant_value:.4f}.")

                                if constant_value == 0.0:
                                    # --- Case: Constant Zero Data ---
                                    if variable_name == 'Complexity':
                                        selected_cmap = cmap_transparent_red
                                        # Use [0, 1] scale for Complexity constant 0
                                        selected_norm = colors.Normalize(vmin=FIXED_COMPLEXITY_ZERO_VMIN, vmax=FIXED_COMPLEXITY_ZERO_VMAX)
                                        print(f"      Info: Constant 0 Complexity. Using fixed scale [{FIXED_COMPLEXITY_ZERO_VMIN:.1f}, {FIXED_COMPLEXITY_ZERO_VMAX:.1f}].")
                                    elif variable_name in ['Climate_Impact', 'Contrails']:
                                         selected_cmap = cmap_blue_transparent_red
                                         # Use [-1, 1] scale centered at 0 for Diverging constant 0
                                         selected_norm = colors.TwoSlopeNorm(vcenter=FIXED_DIVERGING_ZERO_VCENTER,
                                                                             vmin=FIXED_DIVERGING_ZERO_VMİN,
                                                                             vmax=FIXED_DIVERGING_ZERO_VMAX)
                                         print(f"      Info: Constant 0 Diverging data. Using fixed scale [{FIXED_DIVERGING_ZERO_VMİN:.1f}, {FIXED_DIVERGING_ZERO_VMAX:.1f}] centered at {FIXED_DIVERGING_ZERO_VCENTER:.1f}.")
                                    else:
                                         selected_cmap = plt.get_cmap('viridis')
                                         selected_norm = colors.Normalize(vmin=0.0, vmax=1.0)
                                         print(f"      Warning: Unknown variable '{variable_name}', constant 0. Using default viridis 0-1 scale.")
                                else:
                                     # --- Case: Constant Non-Zero Data ---
                                     constant_value = slice_min # The constant value
                                     selected_cmap = cmap_transparent_red if variable_name == 'Complexity' else cmap_blue_transparent_red

                                     # For constant non-zero, use a narrow Normalize range around the value for display
                                     display_range = abs(constant_value) * 0.1 + 0.1
                                     vmin_display = constant_value - display_range
                                     vmax_display = constant_value + display_range
                                     selected_norm = colors.Normalize(vmin=vmin_display, vmax=vmax_display)
                                     print(f"      Info: Constant non-zero value ({constant_value:.4f}). Using expanded display range [{vmin_display:.4f}, {vmax_display:.4f}].")


                            else: # Data slice is not constant (min != max)
                                # --- Case: Non-Constant Data ---
                                if variable_name in ['Climate_Impact', 'Contrails']:
                                    selected_cmap = cmap_blue_transparent_red
                                    # Use DYNAMIC diverging scale [-slice_min, slice_max] centered at 0
                                    # This is the new rule based on user correction
                                    selected_norm = colors.TwoSlopeNorm(vcenter=0.0, # Still center at 0
                                                                        vmin=slice_min, # Use actual min
                                                                        vmax=slice_max) # Use actual max
                                    print(f"      Info: Diverging data (min != max). Using dynamic scale [{slice_min:.4f}, {slice_max:.4f}] centered at 0.0.")

                                elif variable_name == 'Complexity':
                                    selected_cmap = cmap_transparent_red
                                    # Use dynamic normalization based on slice min/max (same as before)
                                    selected_norm = colors.Normalize(vmin=slice_min, vmax=slice_max)
                                    print(f"      Info: Complexity data (min != max). Using dynamic scale [{slice_min:.4f}, {slice_max:.4f}].")

                                else:
                                    print(f"      Warning: Unknown variable '{variable_name}' (min != max). Using default viridis colormap and dynamic bounds [{slice_min:.4f}, {slice_max:.4f}].")
                                    selected_cmap = plt.get_cmap('viridis')
                                    selected_norm = colors.Normalize(vmin=slice_min, vmax=slice_max)


                            # --- Interpolation or Uniform Grid Creation ---
                            # (This part remains the same as it handles the visual smoothing,
                            # the normalization is handled above)

                            if slice_min == slice_max and constant_value != 0.0:
                                # For constant non-zero data, create a uniform grid filled with the constant value
                                interpolated_data = np.full((NEW_GRID_RESOLUTION_Y, NEW_GRID_RESOLUTION_X), constant_value)
                                print("      Created uniform grid for constant non-zero data.")

                            else:
                                # For non-constant data or constant zero, perform interpolation
                                print("      Performing interpolation...")

                                # Create 2D grids of original longitude and latitude matching data_slice shape
                                lon_grid_orig, lat_grid_orig = np.meshgrid(longitude, latitude) # Shape (nLat, nLon)

                                # Flatten original data slice and original coordinate grids
                                original_values_flat = data_slice.ravel() # Shape (nLat * nLon,)
                                original_lon_flat = lon_grid_orig.ravel() # Shape (nLat * nLon,)
                                original_lat_flat = lat_grid_orig.ravel() # Shape (nLat * nLon,)

                                # Filter out NaN values from values and corresponding points
                                valid_indices = ~np.isnan(original_values_flat)
                                valid_values = original_values_flat[valid_indices] # Shape (Num_Valid_Points,)

                                # Create the points array from the flattened original grids, filtering by valid_indices
                                valid_points = np.vstack((original_lon_flat[valid_indices], original_lat_flat[valid_indices])).T # Shape (Num_Valid_Points, 2)


                                if valid_points.shape[0] < 2:
                                    print(f"      Warning: Not enough valid data points ({valid_points.shape[0]}) for interpolation. Skipping slice.")
                                    continue

                                # Perform the interpolation onto the new grid
                                interpolated_data = griddata(
                                    valid_points,
                                    valid_values,
                                    (new_lon_grid, new_lat_grid),
                                    method='linear' # Or 'nearest', 'cubic'
                                )
                                print("      Interpolation finished.")

                            # --- Plotting for Overlay (using pcolormesh with Gouraud shading) ---

                            fig = plt.figure(figsize=(FIG_WIDTH_INCHES, fig_height_inches))
                            ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
                            fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
                            ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

                            mesh = ax.pcolormesh(new_lon_grid, new_lat_grid, interpolated_data,
                                                 transform=ccrs.PlateCarree(),
                                                 cmap=selected_cmap,
                                                 norm=selected_norm,
                                                 shading='gouraud')

                            ax.set_axis_off()

                            output_file_name = f"{base_name}_t{t_idx:03d}_alt{alt_idx:03d}_cloud_overlay.png"
                            output_path = os.path.join(OUTPUT_DIR, output_file_name)

                            plt.savefig(output_path,
                                        dpi=OUTPUT_DPI,
                                        pad_inches=0,
                                        transparent=True)

                            print(f"      Saved cloud overlay image to {output_path}")
                            print(f"      Geographical Extent (for overlay): Lon [{lon_min:.4f}, {lon_max:.4f}], Lat [{lat_min:.4f}, {lat_max:.4f}]")
                            print(f"      Output Image Size (pixels): {int(FIG_WIDTH_INCHES*OUTPUT_DPI)} x {int(fig_height_inches*OUTPUT_DPI)}")


                            plt.close(fig)

                        except Exception as slice_e:
                            print(f"    An error occurred processing slice T={t_idx}, Alt={alt_idx}: {slice_e}. Skipping slice.")
                            try:
                                if 'fig' in locals() and fig is not None:
                                    plt.close(fig)
                                if 'mesh' in locals() and mesh is not None:
                                     del mesh
                                     mesh = None
                            except:
                                pass


        except FileNotFoundError:
            print(f"  Error: File not found: {file_path}. Skipping file.")
        except KeyError as e:
            print(f"  Error: Variable or dimension '{e}' not found in {file_name}. Skipping file.")
        except Exception as file_e:
            print(f"  An unexpected error occurred while processing file {file_name}: {file_e}. Skipping file.")

print("\nCloud effect heatmap overlay generation finished for all slices.")