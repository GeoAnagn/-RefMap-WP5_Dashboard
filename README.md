# RefMap WP5 Dashboard

An interactive dashboard for RefMap WP5 that combines a Vue 3 + Vite frontend (Vuetify UI) with multiple Flask-based backend microservices for domain-specific analyses:

- Climate Impact
- Emissions 
- Atmospheric Pollution 
- Noise Assessment 
- Wind Risk Assessment 
- Airflow Trajectory Optimization 


## Overview

- Frontend dev server runs on `:4000` and proxies `/api/*` routes to backend services.
- Backend microservices run on fixed ports:
	- climate_impact → `:4001`
	- wind_assessment → `:4002`
	- noise_assessment → `:4003`
	- optimized_trajectories → `:4004`
	- emissions → `:4005`


## Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (venv or conda recommended)
- For wind and netCDF functionality you may need native libs:
	- GEOS/PROJ for Cartopy/PyProj
	- HDF5/NetCDF libs (often bundled via wheels; only needed if builds fail)

Example (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y libgeos-dev geos proj-bin libproj-dev proj-data
```


## Repository Layout

```
backend/
	climate_impact/            # Flask app (port 4001); expects NetCDF + overlays in data/
	wind_assessment/           # Flask app (port 4002); uses pre-rendered overlay PNGs
	noise_assessment/          # Flask app (port 4003); structured PNG overlays + coordinates.csv
	optimized_trajectories/    # Flask app (port 4004); serves GIFs from data/
	emissions/                 # Flask app (port 4005); structured PNG overlays
	services/                  # systemd unit files (adjust paths before installing)
src/                         # Vue 3 app (Vuetify, Leaflet/Plotly integrations)
vite.config.js               # Dev host/port + proxy to backends
package.json                 # Vite scripts
```


## Frontend Setup

Install dependencies:

```bash
cd -RefMap-WP5_Dashboard
npm install
```

Dev server scripts (from `package.json`):

- `npm run dev` → start Vite dev server
- `npm run build` → production build to `dist/`
- `npm run preview` → preview built assets locally

Dev server config (`vite.config.js`):

- Host is currently set to `147.102.37.172` and port `4000`.
- Proxies route `/api/<service>` to the corresponding backend port.

If you develop on your own machine, change `server.host` to `localhost` (or your machine’s IP) and, if needed, the proxy targets to match where your backends run.


## Python Environment

Create and activate a virtual environment (example with venv):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install common dependencies used across services:

```bash
pip install flask flask-cors numpy netCDF4 xarray cartopy pyproj matplotlib
```

Notes:
- Some services only need a subset of the above; installing all simplifies setup.
- If Cartopy/PyProj installation fails, install GEOS/PROJ system packages (see prerequisites).


## Backends: Data Expectations

- climate_impact (`backend/climate_impact/data/<DATE>/`)
	- NetCDF files: `*.nc`
	- Overlays: `heatmaps_overlay_cloud_effect/`
	- KPIs: `ATR_Information.json`
- wind_assessment (`backend/wind_assessment/data/output_pngs_overlay/LoD X.X/<City>/<Parameter Display Name>/zXXm/*.png`)
- noise_assessment (`backend/noise_assessment/data/<City>/<Time>/<Zone>/<FlightsPerHour>/*.png` + optional `coordinates.csv` for global bounds)
- emissions (`backend/emissions/data/contour_maps/<Metric>/*.png`)
- optimized_trajectories (`backend/optimized_trajectories/data/*.gif`)


## Run: Backend Services (local)

Open separate terminals, activate your Python env, then start each service from its folder:

```bash
# Climate Impact (port 4001)
cd backend/climate_impact
python app.py

# Wind Assessment (port 4002)
cd ../wind_assessment
python app.py

# Noise Assessment (port 4003)
cd ../noise_assessment
python app.py

# Optimized Trajectories (port 4004)
cd ../optimized_trajectories
python app.py

# Emissions (port 4005)
cd ../emissions
python app.py
```

All services bind to `0.0.0.0` by default. Ensure the expected `data/` contents exist in each service directory.


## Run: Frontend (local)

In a new terminal:

```bash
cd -RefMap-WP5_Dashboard
npm run dev
```

By default, the dev server runs on `http://147.102.37.172:4000` per `vite.config.js`. For local development, update:

```js
// vite.config.js
server: {
	host: 'localhost',
	port: 4000,
	proxy: {
		'/api/climate_impact': { target: 'http://localhost:4001', changeOrigin: true, rewrite: p => p.replace(/^\/api\/climate_impact/, '') },
		'/api/wind_assessment': { target: 'http://localhost:4002', changeOrigin: true, rewrite: p => p.replace(/^\/api\/wind_assessment/, '') },
		'/api/noise_assessment': { target: 'http://localhost:4003', changeOrigin: true, rewrite: p => p.replace(/^\/api\/noise_assessment/, '') },
		'/api/optimized_trajectories': { target: 'http://localhost:4004', changeOrigin: true, rewrite: p => p.replace(/^\/api\/optimized_trajectories/, '') },
		'/api/emissions': { target: 'http://localhost:4005', changeOrigin: true, rewrite: p => p.replace(/^\/api\/emissions/, '') },
	}
}
```


## API Glance (selected)

- Climate Impact (4001):
	- `GET /api/get-dates`
	- `GET /api/get-data-types?date=...`
	- `GET /api/get-scales?date=...&dataType=...`
	- `GET /api/get-costs?date=...&dataType=...&scale=...`
	- `GET /api/get-netcdf-metadata?date=...&dataType=...&scale=...&cost=...`
	- `GET /api/get-heatmap-overlay?file=...&time=...&altitude=...&date=...`
	- `GET /api/get-atr-percentage-increase?date=...&scale=...`

- Wind Assessment (4002):
	- `GET /api/available_combinations`
	- `GET /api/image_info?lod=...&city=...&param=...&zloc=...&wind=...`

- Noise Assessment (4003):
	- `GET /api/noise_available_combinations`
	- `GET /api/noise_image_info?city=...&time=...&flight_zone=...&flights_per_hour=...&metric=...`

- Emissions (4005):
	- `GET /api/emissions_metrics`
	- `GET /api/emissions_cases?metric=...`
	- `GET /api/emissions_image?metric=...&case=...`

- Optimized Trajectories (4004):
	- `GET /health`
	- `GET /cases`
	- `GET /gif/<caseOrFilename>?name=...`


## Systemd Services (optional deployment)

Unit files are provided in `backend/services/`. Before installing, edit each file to match your actual paths. The current samples point to another folder (`/home/refmap-imafusa/Documents/RefMap`) and a specific Python path.

Typical steps:

```bash
sudo cp backend/services/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start individual services
sudo systemctl enable refmap_climate_impact.service
sudo systemctl start  refmap_climate_impact.service

sudo systemctl enable refmap_wind_assessment.service
sudo systemctl start  refmap_wind_assessment.service

sudo systemctl enable refmap_noise_assessment.service
sudo systemctl start  refmap_noise_assessment.service

sudo systemctl enable refmap_optimized_trajectories.service
sudo systemctl start  refmap_optimized_trajectories.service

sudo systemctl enable refmap_emissions.service
sudo systemctl start  refmap_emissions.service

# (Optional) Frontend
sudo systemctl enable refmap-frontend.service
sudo systemctl start  refmap-frontend.service
```

Notes:
- For production, run a built frontend behind a proper web server (Nginx) instead of `npm run dev`.
- Ensure `WorkingDirectory` and `ExecStart` in each service reflect your environment (repo path, Python/conda path).


## Troubleshooting

- Ports already in use: change ports in backends or `vite.config.js`.
- CORS errors: use the Vite proxy (`/api/...` paths) or ensure Flask has CORS enabled (it is via `flask-cors`).
- Missing data: verify the expected `data/` folder structure for each service.
- Cartopy/PyProj install issues: install GEOS/PROJ libs (see prerequisites).
- NetCDF loading issues: ensure `.nc` files are valid and accessible; the service logs will print helpful debug lines.


## Development Tips

- Frontend components live under `src/components/` (Vuetify, Leaflet, Plotly integrations).
- Adjust `vite.config.js` `server.host`/`proxy` when moving between local dev and a remote server.
- Keep the backends stateless; all heavy assets come from `data/` folders.


## License

Internal project materials. If you need a formal license, add it here.

