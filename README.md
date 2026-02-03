
# RefMap WP5 Dashboard Setup Guide

## 1. Node.js & npm Setup

### Install nvm (Node Version Manager)
```sh
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
```

### Load nvm (if you haven't restarted your shell)
```sh
\. "$HOME/.nvm/nvm.sh"
```

### Install Node.js (version 24)
```sh
nvm install 24
```

### Verify Node.js and npm versions
```sh
node -v   # Should print v24.13.0
npm -v    # Should print 11.6.2
```

## 2. Install Project Dependencies
```sh
npm install
```

## 3. Running the Development Server

### Default (localhost)
```sh
npm run dev
```

### Custom Host and/or Port
```sh
npm run dev -- --host=YOUR_IP --port=YOUR_PORT
```
Replace `YOUR_IP` and `YOUR_PORT` as needed.

> **Note:**
> If you change the base port, you must also update the corresponding backend service or Dockerfile configurations to match the new ports.

---



## 4. Backend Setup

After running the development server, you can set up the backend in one of two ways:


### Option 1: System Services (Recommended for Local/Server)

#### a. Install Miniconda or Anaconda (if not already installed)
Miniconda (Linux):
```sh
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
# Install to /tools/miniconda3 to match the provided service configurations
bash Miniconda3-latest-Linux-x86_64.sh -b -p /tools/miniconda3
```
Initialize conda (adjust path if you installed elsewhere):
```sh
source /tools/miniconda3/etc/profile.d/conda.sh
conda init bash
```

#### b. Create and Activate the Python Environment
From the project root directory, run:
```sh
conda env create -f environment.yaml
conda activate RefMapDashboard
```

#### c. Set Up and Start the Services

**Before copying the service files:**
1. Open the `.service` files in `system_services/` (or `backend/services/` if applicable).
2. Edit each file to match your system configuration:
    - **User**: Change `User=george` to your system username (e.g., `User=ubuntu`).
    - **WorkingDirectory**: Update the path to point to your project location (e.g., `/home/ubuntu/RefMap/-RefMap-WP5_Dashboard/...`).
    - **ExecStart**: Ensure the path to the Python executable matches your Conda environment path (run `which python` inside the env to verify).
    - **ExecStart (Frontend)**: For `refmap-frontend.service`, update the path to your `npm` executable (run `which npm` to verify).

Once configured, copy the service files to your system's `/etc/systemd/system/` directory:
```sh
sudo cp system_services/*.service /etc/systemd/system/
```
Reload systemd and enable/start the services:
```sh
sudo systemctl daemon-reload
sudo systemctl enable --now refmap_atmospheric_pollution.service refmap_climate_impact.service refmap_emissions.service refmap_noise_assessment.service refmap_optimized_trajectories.service refmap_wind_assessment.service refmap-frontend.service
```
Check status:
```sh
sudo systemctl status refmap_wind_assessment.service
# (repeat for other services as needed)
```


### Option 2: Docker with Kubernetes

This option allows you to run all backend services in containers, orchestrated by Kubernetes. Each backend subfolder contains a Dockerfile for its service.


#### a. Prerequisites

- **Docker installed and running**

	- **Ubuntu:**
		- Follow the official guide: [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)
		- Quick steps:
			```sh
			sudo apt-get update
			sudo apt-get install ca-certificates curl gnupg
			sudo install -m 0755 -d /etc/apt/keyrings
			curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
			sudo chmod a+r /etc/apt/keyrings/docker.gpg
			echo \
				"deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
				$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
				sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
			sudo apt-get update
			sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
			```
		- After installation, verify Docker is running:
			```sh
			docker --version
			docker run hello-world
			```
		- Add your user to the `docker` group (optional, for non-root usage):
			```sh
			sudo usermod -aG docker $USER
			# Log out and back in for group changes to take effect
			```
	- For other operating systems, see [Install Docker](https://docs.docker.com/get-docker/).

- **Kubernetes cluster** (choose one):

	- **Minikube** (recommended for local development):
		- Official guide: [Install Minikube](https://minikube.sigs.k8s.io/docs/start/)
		- **Install on Linux (Debian/Ubuntu):**
			```sh
			# Download the latest .deb package
			curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube_latest_amd64.deb
			# Install the package
			sudo dpkg -i minikube_latest_amd64.deb
			# Clean up
			rm minikube_latest_amd64.deb
			```
		- **Start a cluster:**
			```sh
			minikube start
			```
		- **Verify installation:**
			```sh
			minikube status
			kubectl get nodes
			```
	- **Docker Desktop** (macOS/Windows):
		- [Install Docker Desktop](https://docs.docker.com/desktop/)
		- Enable the built-in Kubernetes cluster in Docker Desktop settings.
	- **Remote cluster** (e.g., managed Kubernetes on cloud):
		- Use your provider's documentation to set up and access the cluster.
		- Make sure you have `kubectl` configured to point to your cluster.

#### b. Build Docker Images
From the project root, build each backend service image. For example:
```sh
cd backend/atmospheric_pollution
docker build -t refmap/atmospheric_pollution:latest .

cd ../climate_impact
docker build -t refmap/climate_impact:latest .

cd ../emissions
docker build -t refmap/emissions:latest .

cd ../noise_assessment
docker build -t refmap/noise_assessment:latest .

cd ../optimized_trajectories
docker build -t refmap/optimized_trajectories:latest .

cd ../wind_assessment
docker build -t refmap/wind_assessment:latest .
```

#### c. Push Images to a Registry (if needed)
If your Kubernetes cluster cannot access local Docker images, push them to a registry (e.g., Docker Hub):
```sh
docker tag refmap/atmospheric_pollution:latest yourdockerhub/refmap_atmospheric_pollution:latest
docker push yourdockerhub/refmap_atmospheric_pollution:latest
# Repeat for each service
```


#### d. Deploy with Kubernetes

1. **Start Minikube with required mount:**
   This mounts your current project directory into the specific path the pods are configured to use.
   ```sh
   minikube start --mount --mount-string="$(pwd):/refmap_dashboard"
   ```

2. **Load Docker Images:** 
   If you are using Minikube locally, you must load your locally built images into the Minikube environment.
   ```sh
   minikube image load refmap/atmospheric_pollution:latest
   minikube image load refmap/climate_impact:latest
   minikube image load refmap/emissions:latest
   minikube image load refmap/noise_assessment:latest
   minikube image load refmap/optimized_trajectories:latest
   minikube image load refmap/wind_assessment:latest
   ```

3. **Deploy Services:**
   ```sh
   kubectl apply -f k8s/
   ```

4. **Port Forwarding (Required for Local Development):** 
   Since the frontend runs locally and the backend runs inside Minikube, you must forward the ports to make them accessible.
   
   A helper script is provided for this:
   ```sh
   ./port-forward.sh
   ```
   
   Ensure this script is running in the background while you use the application.

##### Example: Service YAML and Port Matching
Make sure the `targetPort` in your Service YAML matches the port your backend service listens on, and that this matches the port expected by your frontend (see your Vite proxy config and the port used in `npm run dev`).

Example (service.yaml):
```yaml
apiVersion: v1
kind: Service
metadata:
	name: wind-assessment
spec:
	type: NodePort
	selector:
		app: wind-assessment
	ports:
		- protocol: TCP
			port: 4002         # Must match the port in Vite proxy config
			targetPort: 4002   # Must match the port your backend listens on
			nodePort: 30002
```

> **Note:** If you run the frontend with a custom port (e.g., `npm run dev -- --port=5000`), update your Vite proxy config and the corresponding backend service ports to match.

#### e. Verify Deployment
Check pods and services:
```sh
kubectl get pods
kubectl get services
```

> **Note:** You only need to use one of these backend deployment methods.

---

## 5. Data Directory Structure

Each backend service requires specific data files to function correctly. Ensure the `backend/<service_name>/data` directories are populated as follows:

### Atmospheric Pollution
- **Location**: `backend/atmospheric_pollution/data/`
- **Required Content**:
  - **Zarr Store**: A directory ending in `.zarr` (e.g., `NetCDF_to_Zarr.zarr`) containing the pollution dataset. The service recursively searches for this folder.
  - **GeoJSON**: City or region-specific GeoJSON files (e.g., `Amsterdam/Amsterdam_airport.geojson`). These are served directly via the `/data` endpoint.
  - **Note**: The service scans the `data` directory recursively to find these files.

### Climate Impact
- **Location**: `backend/climate_impact/data/`
- **Required Content**:
  - Organized by date, using `DDMMYYYY` format (e.g., `20122018/`).
  - Inside each date directory:
    - `ATR_Information.json`: Meta-information file.
    - **Base Scenario Files**: `BAU_Complexity.nc`, `BAU_Contrails.nc`, `BAU_NET_ATR.nc`.
    - **Macro Scale Costs**: `Macro_scale_Complexity_Cost_1.0.nc`, `Macro_scale_Contrails_Cost_1.0.nc`, `Macro_Scale_NET_ATR_Cost_1.0.nc` (and version `3.0`).
    - **Micro Scale Costs**: `Micro_Scale_Complexity_Cost_1.0.nc`, `Micro_scale_Contrails_Cost_1.0.nc`, `Micro_Scale_NET_ATR_Cost_1.0.nc` (and version `3.0`).
    - **Heatmaps**: A subdirectory named `heatmaps_overlay_cloud_effect/` containing generated heatmap images.

### Emissions
- **Location**: `backend/emissions/data/`
- **Required Content**:
  - **Global Bounds (Optional)**: `latlon_regrid_base.nc4` (or `sens`) at the root of `data/` for calculating dynamic map bounds. If missing, default bounds are used.
  - **Contour Maps**: A directory named `contour_maps/`.
    - **Reduction Level**: Subdirectories representing reduction percentages (e.g., `10/`).
      - **Metric**: Subdirectories for each pollutant (e.g., `NO2/`, `PM25/`, `O3/`).
        - **PNG Files**: `base.png`, `sens.png`, `diff.png` (names are case-insensitive and can be mapped from aliases).
        - **Metadata**: `colorbar.json` defining `vmin` and `vmax` for scaling.

### Noise Assessment
- **Location**: `backend/noise_assessment/data/`
- **Required Content**:
  - `coordinates.csv`: A CSV file at the root defining the global map bounds (`lat-min`, `lat-max`, `lon-min`, `lon-max`).
  - `scale-argb.png`: An image file for the legend color scale.
  - **City Structure**:
    - `{City}/` (e.g., `Prague/`)
      - `{TimePeriod}/` (e.g., `Daytime/`)
        - `{FlightZone}/` (e.g., `Restricted/`, `Unrestricted/`)
          - `{FlightsPerHour}/` (e.g., `100/`)
            - **Metric Images**: `Ambient.png`, `L(AE)eq.png`, `HighAnnoyPerc(ambi).png`, `AnnoyanceShift(ambi).png`.

### Optimized Trajectories
- **Location**: `backend/optimized_trajectories/data/`
- **Required Content**:
  - A strictly nested directory structure:
    - `{Area}/` (e.g., `Custom`)
      - `{Turbulence}/` (e.g., `Medium`)
        - `{Takeoff}/` (e.g., `1`)
          - `{Landing}/` (e.g., `1`)
            - **GIFs**: Trajectory animation files (e.g., `trajectory_case1.gif`).
  - The service automatically scans this hierarchy to build the list of available cases.

### Wind Assessment
- **Location**: `backend/wind_assessment/data/`
- **Required Content**:
  - `output_pngs_overlay/`: The main directory for served plots (configured as a static folder).
    - `{LOD}/` (Level of Detail, e.g., `1.2`, `2.2`)
      - `{City}/` (Must match `CITY_INFO` keys in `app.py`, e.g., `TUDelft Campus`)
        - `{Parameter}/` (Mapped names: `Wind Speed`, `Turbulence Level`)
          - `{Height}/` (e.g., `z10m`, `z2m`)
            - **Overlay Images**: PNG files following the naming convention `overlay_{Param}_{Height}_{Value}.png`.