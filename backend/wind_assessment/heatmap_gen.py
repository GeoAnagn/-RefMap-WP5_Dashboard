import re
import os
import glob
import time
import trimesh
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.tri import Triangulation
from multiprocessing import Pool, cpu_count
import sys

# --- Configuration ---
BASE_DATA_DIR = './data/' 
OUTPUT_DIR = BASE_DATA_DIR + 'output_pngs_overlay'

LOD_LEVELS = ['lod1p2', 'lod2p2']
LOCATIONS = ['denhaag', 'TUDcampus']
PARAMS = ['Umag', 'TKE']
Z_INDICES = [2, 3, 5, 7, 10]

# Mappings for file system directory names
LOD_DIR_NAMES = {
    'lod1p2': 'LoD 1.2',
    'lod2p2': 'LoD 2.2'
}
LOCATION_DIR_NAMES = {
    'denhaag': 'Denhaag',
    'TUDcampus': 'TUDelft Campus'
}

# Mappings for Output Directory Names
OUTPUT_LOD_NAMES = {
    'lod1p2': '1.2',
    'lod2p2': '2.2'
}
OUTPUT_PARAM_NAMES = {
    'Umag': 'Wind Speed',
    'TKE': 'Turbulence Level'
}

Uinf_base = 5.0 
SHOW_BUILDINGS = True 

# --- Helper Functions ---

def read_binary(filename, myd_type=np.float64):
    try:
        with open(filename, 'rb') as f:
            x = np.fromfile(f, dtype=myd_type)
        return x
    except FileNotFoundError:
        # print(f"Error: File not found - {filename}")
        return None
    except Exception as e:
        print(f"Error reading binary file {filename}: {e}")
        return None

def process_chunk_task(args):
    """
    Worker function to process a batch of files.
    args: tuple containing:
      (file_tasks, x, y, levels, cmap, building_verts_list, current_Uinf, vmin, vmax)
    
    file_tasks: list of (data_filepath, output_filepath)
    """
    file_tasks, x, y, levels, cmap, building_verts_list, current_Uinf, vmin, vmax = args
    
    # Initialize expensive objects once per chunk
    try:
        triang = Triangulation(x, y)
    except Exception as e:
        print(f"Error creating triangulation in worker: {e}")
        return 0

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    count = 0
    for data_filepath, output_filepath in file_tasks:
        try:
            param_data = read_binary(data_filepath)
            if param_data is None:
                continue
            
            # Sanity check size
            if len(param_data) != len(x):
                continue
                
            ax.cla() # Clear axis
            
            # Plot
            ax.tricontourf(triang, param_data / current_Uinf,
                           cmap=cmap,
                           levels=levels,
                           vmin=vmin, vmax=vmax)

            # Add buildings if available
            if building_verts_list is not None:
                building_poly_collection = PolyCollection(building_verts_list, 
                                                          facecolors='gray',
                                                          edgecolors='None',
                                                          alpha=1.0,
                                                          zorder=10) 
                # Re-adding collection to clear axis might be needed or recreated
                ax.add_collection(building_poly_collection) 

            ax.set_aspect('equal', adjustable='box')
            ax.set_axis_off() 
            
            fig.savefig(output_filepath,
                        dpi=300,
                        bbox_inches='tight',
                        pad_inches=0,
                        transparent=True)
            
            # print(f"Generated: {os.path.basename(output_filepath)}")
            count += 1
            
        except Exception as e:
            print(f"Error processing {data_filepath}: {e}")
            continue

    plt.close(fig)
    return count

def main():
    total_time_start = time.time()
    total_files_processed = 0
    total_files_skipped = 0

    # Determine CPU cores for pool size (leave one free if possible, or use all)
    num_processes = max(1, cpu_count() - 1)
    print(f"Starting heatmap generation with {num_processes} processes...")

    for lod in LOD_LEVELS:
        for location in LOCATIONS:
            # Prepare paths
            data_dir = os.path.join(BASE_DATA_DIR, LOD_DIR_NAMES.get(lod, lod), LOCATION_DIR_NAMES.get(location, location), 'data')
            building_dir = os.path.join(BASE_DATA_DIR, 'building_data', location)

            print(f"\n--- Processing Set: {lod} / {location} ---")
            if not os.path.isdir(data_dir):
                print(f"Warning: Data directory not found, skipping: {data_dir}")
                continue

            # Load Buildings for this location (once)
            effective_showBuildings = SHOW_BUILDINGS
            if SHOW_BUILDINGS and not os.path.isdir(building_dir):
                print(f"Warning: Building directory not found ({building_dir}), buildings will not be shown.")
                effective_showBuildings = False 
            
            for param in PARAMS:
                for zindex in Z_INDICES:
                    print(f"   Planning: {param}, Z={zindex}...")
                    
                    # 1. Load Geometry (X, Y)
                    x_file = os.path.join(data_dir, f'x_{zindex}.bin')
                    y_file = os.path.join(data_dir, f'y_{zindex}.bin')

                    x = read_binary(x_file)
                    y = read_binary(y_file)

                    if x is None or y is None:
                        # print(f"   Warning: coords missing for z={zindex}")
                        continue
                    if len(x) < 3 or len(y) < 3:
                        # print(f"   Warning: insufficient coords for z={zindex}")
                        continue
                    if len(x) != len(y):
                        continue

                    # 2. Load Buildings (specific to Z)
                    building_verts_list = None 
                    if effective_showBuildings:
                        stl_file = os.path.join(building_dir, f'buildings_z{zindex}.stl')
                        if os.path.exists(stl_file):
                            try:
                                mesh = trimesh.load(stl_file, process=False) 
                                xf = mesh.vertices[:, 0]
                                yf = mesh.vertices[:, 1]
                                # Pre-process vertices list for PolyCollection to pass purely data to workers
                                xf_faces = xf[mesh.faces]
                                yf_faces = yf[mesh.faces]
                                building_verts_list = [np.vstack((xf_row, yf_row)).T for xf_row, yf_row in zip(xf_faces, yf_faces)]
                            except Exception as e:
                                print(f"     Error loading building mesh {stl_file}: {e}")
                    
                    # 3. Configure Plot Params
                    current_Uinf = Uinf_base
                    levels = np.linspace(0, 1.4, 10)
                    vmin, vmax = 0, 1.4             
                    cmap_to_use = 'RdBu_r'            

                    if param == 'TKE':
                        current_Uinf = Uinf_base * Uinf_base
                        levels = np.linspace(0, 0.08, 10)
                        vmin, vmax = 0, 0.08
                        cmap_to_use = 'RdBu_r' 

                    # 4. Find Files
                    file_pattern = os.path.join(data_dir, f'{param}_{zindex}_*.bin')
                    data_files = glob.glob(file_pattern)

                    if not data_files:
                        continue
                    
                    # 5. Prepare Output Paths
                    tasks_for_this_config = []
                    
                    out_lod = OUTPUT_LOD_NAMES.get(lod, lod)
                    out_loc = LOCATION_DIR_NAMES.get(location, location)
                    out_param = OUTPUT_PARAM_NAMES.get(param, param)
                    out_z = f"z{zindex}m"
                    current_output_dir = os.path.join(OUTPUT_DIR, out_lod, out_loc, out_param, out_z)
                    os.makedirs(current_output_dir, exist_ok=True)

                    for data_filepath in data_files:
                        # Extract index
                        match = re.search(r'_(\d+)\.bin$', os.path.basename(data_filepath))
                        if not match: continue
                        myindex = int(match.group(1))

                        fig_name = f'overlay_{param}_z{zindex}_{myindex}.png'
                        output_filepath = os.path.join(current_output_dir, fig_name)

                        if os.path.exists(output_filepath):
                            total_files_skipped += 1
                        else:
                            tasks_for_this_config.append((data_filepath, output_filepath))

                    if not tasks_for_this_config:
                        continue

                    # 6. Batch Tasks and Execute Parallel
                    chunk_size = 20  # Batch size
                    chunks = [tasks_for_this_config[i:i + chunk_size] for i in range(0, len(tasks_for_this_config), chunk_size)]
                    
                    chunk_args = []
                    for chunk in chunks:
                         chunk_args.append((chunk, x, y, levels, cmap_to_use, building_verts_list, current_Uinf, vmin, vmax))
                    
                    print(f"     Launching {len(chunk_args)} batches for {len(tasks_for_this_config)} files...")
                    
                    # Use context manager for Pool to ensure cleanup
                    with Pool(processes=num_processes) as pool:
                        # Use imap_unordered for slightly better parallel responsiveness (processing order irrelevant)
                        results_iter = pool.imap_unordered(process_chunk_task, chunk_args)
                        
                        completed_chunks = 0
                        results = []
                        total_chunks = len(chunk_args)
                        
                        # Initial status
                        sys.stdout.write(f"     Progress: 0/{total_chunks} batches (0.0%)")
                        sys.stdout.flush()
                        
                        for res in results_iter:
                            results.append(res)
                            completed_chunks += 1
                            percent = (completed_chunks / total_chunks) * 100
                            # Overwrite line with progress
                            sys.stdout.write(f"\r     Progress: {completed_chunks}/{total_chunks} batches ({percent:.1f}%)")
                            sys.stdout.flush()
                        
                        print("") # New line after completion
                        total_files_processed += sum(results)

    total_time_end = time.time()
    print(f"\n--- Processing Complete ---")
    print(f"Total files generated: {total_files_processed}")
    print(f"Total files skipped (already existed): {total_files_skipped}")
    print(f"Total time: {total_time_end - total_time_start:.2f} seconds.")

if __name__ == '__main__':
    main()