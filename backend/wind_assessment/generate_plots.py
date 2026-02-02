import re
import os
import glob
import time
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

BASE_DATA_DIR = './data/' 
OUTPUT_DIR = 'output_pngs_overlay'

LOD_LEVELS = ['lod1p2', 'lod2p2']
LOCATIONS = ['denhaag', 'TUDcampus']
PARAMS = ['Umag', 'TKE']
Z_INDICES = [2, 3, 5, 7, 10]

Uinf_base = 5.0 
showBuildings = True 

total_files_processed = 0
total_files_skipped = 0 
total_time_start = time.time()

def read_binary(filename,myd_type=np.float64):
    try:
        with open(filename,'rb') as f:
            f.seek(0)
            x = np.fromfile(f,dtype=myd_type)
            f.close()
        return x
    except FileNotFoundError:
        print(f"Error: File not found - {filename}")
        return None
    except Exception as e:
        print(f"Error reading binary file {filename}: {e}")
        return None

for lod in LOD_LEVELS:
    for location in LOCATIONS:
        data_dir = os.path.join(BASE_DATA_DIR, lod, location, 'data')
        building_dir = os.path.join(BASE_DATA_DIR, 'building_data', location)

        print(f"\n--- Processing: {lod} / {location} ---")
        if not os.path.isdir(data_dir):
            print(f"Warning: Data directory not found, skipping: {data_dir}")
            continue

        effective_showBuildings = showBuildings 
        if showBuildings and not os.path.isdir(building_dir):
            print(f"Warning: Building directory not found ({building_dir}), buildings will not be shown for {location}.")
            effective_showBuildings = False 

        for param in PARAMS:
            
            for zindex in Z_INDICES:
                print(f"   Processing Parameter: {param}, Z-Index: {zindex}")
                x_file = os.path.join(data_dir, f'x_{zindex}.bin')
                y_file = os.path.join(data_dir, f'y_{zindex}.bin')

                x = read_binary(x_file)
                y = read_binary(y_file)

                if x is None or y is None:
                    print(f"   Warning: Coordinate files for z={zindex} not found or failed to load. Skipping this z-index.")
                    continue

                mesh = None
                building_verts_list = None 
                buildings_loaded_for_z = False
                if effective_showBuildings:
                    stl_file = os.path.join(building_dir, f'buildings_z{zindex}.stl')
                    try:
                        if os.path.exists(stl_file):
                            mesh = trimesh.load(stl_file, process=False) 
                            xf = mesh.vertices[:, 0]
                            yf = mesh.vertices[:, 1]
                            xf_faces = xf[mesh.faces]
                            yf_faces = yf[mesh.faces]
                            building_verts_list = [np.vstack((xf_row, yf_row)).T for xf_row, yf_row in zip(xf_faces, yf_faces)]
                            buildings_loaded_for_z = True
                            print(f"     Loaded building mesh and prepared vertices: {stl_file}")
                        else:
                            print(f"     Warning: Building STL file not found: {stl_file}. No buildings shown for z={zindex}.")
                    except Exception as e:
                        print(f"     Error loading or processing building mesh {stl_file}: {e}")
                
                current_Uinf = Uinf_base
                levels = np.linspace(0, 1.4, 10)
                vmin, vmax = 0, 1.4             
                cmap_to_use = 'BuRd'            

                if param == 'TKE':
                    current_Uinf = Uinf_base * Uinf_base
                    levels = np.linspace(0, 0.08, 10)
                    vmin, vmax = 0, 0.08
                    cmap_to_use = 'BuRd'

                print(f"     Non-dimensionalising {param} using Uref = {current_Uinf:.2f} with colormap '{cmap_to_use}'")

                file_pattern = os.path.join(data_dir, f'{param}_{zindex}_*.bin')
                data_files = glob.glob(file_pattern)

                if not data_files:
                    print(f"     Warning: No '{param}' data files found for z={zindex} in {data_dir}")
                    continue

                print(f"     Found {len(data_files)} data files for {param}, z={zindex}.")

                for data_filepath in data_files:
                    time1 = time.time()

                    match = re.search(r'_(\d+)\.bin$', os.path.basename(data_filepath))
                    if not match:
                        print(f"     Warning: Could not extract index from filename: {data_filepath}. Skipping.")
                        continue
                    myindex = int(match.group(1))

                    current_output_dir = os.path.join(OUTPUT_DIR, lod, location, param, f'z{zindex}')
                    fig_name = f'overlay_{param}_z{zindex}_{myindex}.png'
                    output_filepath = os.path.join(current_output_dir, fig_name)

                    if os.path.exists(output_filepath):
                        print(f"       Skipping: Output file already exists - {output_filepath}")
                        total_files_skipped += 1
                        continue 

                    param_data = read_binary(data_filepath)
                    if param_data is None:
                        continue

                    if len(param_data) != len(x):
                        print(f"     Warning: Data size mismatch between {data_filepath} ({len(param_data)}) and coordinates ({len(x)}). Skipping.")
                        continue

                    os.makedirs(current_output_dir, exist_ok=True)

                    fig, ax = plt.subplots(1, 1, figsize=(10, 10)) 

                    contour = ax.tricontourf(x, y, param_data / current_Uinf,
                                             cmap=cmap_to_use,
                                             levels=levels,
                                             vmin=vmin, vmax=vmax)

                    if buildings_loaded_for_z and building_verts_list is not None:
                        building_poly_collection = PolyCollection(building_verts_list, 
                                                                  facecolors='gray',
                                                                  edgecolors='None',
                                                                  alpha=1.0,
                                                                  zorder=10) 
                        ax.add_collection(building_poly_collection) 

                    ax.set_aspect('equal', adjustable='box')
                    ax.set_axis_off() 
                    plt.savefig(output_filepath,
                                dpi=300,
                                bbox_inches='tight',
                                pad_inches=0,
                                transparent=True)
                    plt.close(fig)

                    total_files_processed += 1
                    print(f"       Finished: {os.path.basename(data_filepath)} -> {output_filepath} in {time.time()-time1:.2f} seconds.")

total_time_end = time.time()
print(f"\n--- Processing Complete ---")
print(f"Total files generated: {total_files_processed}")
print(f"Total files skipped (already existed): {total_files_skipped}")
print(f"Total time: {total_time_end - total_time_start:.2f} seconds.")