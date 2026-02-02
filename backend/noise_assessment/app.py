import os
from flask_cors import CORS
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)
CORS(app)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_BASE_DIR = os.path.join(APP_ROOT, 'data')

def _read_global_coordinates():
    """Reads global coordinates from data/coordinates.csv if present.
    Returns a dict like {'lat-min': ..., 'lat-max': ..., 'lon-min': ..., 'lon-max': ...}
    or None if not available or malformed.
    """
    coordinates_path = os.path.join(DATA_BASE_DIR, 'coordinates.csv')
    if not os.path.isfile(coordinates_path):
        return None
    try:
        import csv
        with open(coordinates_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            row = next(reader, None)
            if row:
                bounds = {}
                for k, v in row.items():
                    try:
                        bounds[k] = float(v)
                    except Exception:
                        pass
                return bounds if bounds else None
    except Exception as e:
        print(f"[WARNING] Failed to read global coordinates from {coordinates_path}: {e}")
    return None


@app.route('/scale-argb.png', methods=['GET'])
def serve_color_scale_image():
    """Serve the color scale image from the data directory."""
    try:
        return send_from_directory(DATA_BASE_DIR, 'scale-argb.png')
    except Exception as e:
        print(f"[WARNING] Failed to serve scale-argb.png: {e}")
        return ('', 404)


@app.route('/api/noise_cities', methods=['GET'])
def noise_cities():
    """Return list of available cities (top-level directories under data)."""
    if not os.path.isdir(DATA_BASE_DIR):
        return jsonify([])
    cities = []
    for entry in sorted(os.listdir(DATA_BASE_DIR)):
        if entry.lower() == 'coordinates.csv':
            continue
        path = os.path.join(DATA_BASE_DIR, entry)
        if os.path.isdir(path):
            cities.append(entry)
    return jsonify(cities)


@app.route('/api/noise_times', methods=['GET'])
def noise_times():
    """Return list of time folders (e.g., Daytime, Nighttime) for a given city."""
    city = request.args.get('city')
    if not city:
        return jsonify([])
    city_path = os.path.join(DATA_BASE_DIR, city)
    if not os.path.isdir(city_path):
        return jsonify([])
    times = [d for d in sorted(os.listdir(city_path)) if os.path.isdir(os.path.join(city_path, d))]
    return jsonify(times)


@app.route('/api/noise_flight_zones', methods=['GET'])
def noise_flight_zones():
    """Return list of flight zones for given city and time."""
    city = request.args.get('city')
    time = request.args.get('time')
    if not city or not time:
        return jsonify([])
    time_path = os.path.join(DATA_BASE_DIR, city, time)
    if not os.path.isdir(time_path):
        return jsonify([])
    zones = [d for d in sorted(os.listdir(time_path)) if os.path.isdir(os.path.join(time_path, d))]
    return jsonify(zones)


@app.route('/api/noise_flights_per_hour', methods=['GET'])
def noise_flights_per_hour():
    """Return list of flights-per-hour directories for given city, time and flight zone."""
    city = request.args.get('city')
    time = request.args.get('time')
    zone = request.args.get('flight_zone')
    if not city or not time or not zone:
        return jsonify([])
    zone_path = os.path.join(DATA_BASE_DIR, city, time, zone)
    if not os.path.isdir(zone_path):
        return jsonify([])
    fph = [d for d in sorted(os.listdir(zone_path)) if os.path.isdir(os.path.join(zone_path, d))]
    return jsonify(fph)


@app.route('/api/noise_metrics', methods=['GET'])
def noise_metrics():
    """Return list of metrics (PNG basenames) for given city, time, zone, flights-per-hour."""
    city = request.args.get('city')
    time = request.args.get('time')
    zone = request.args.get('flight_zone')
    fph = request.args.get('flights_per_hour')
    if not city or not time or not zone or not fph:
        return jsonify([])
    metrics_path = os.path.join(DATA_BASE_DIR, city, time, zone, fph)
    if not os.path.isdir(metrics_path):
        return jsonify([])
    metrics = []
    try:
        for fname in sorted(os.listdir(metrics_path)):
            if fname.lower().endswith('.png'):
                metrics.append(os.path.splitext(fname)[0])
    except Exception as e:
        print(f"[WARNING] Failed to list metrics in {metrics_path}: {e}")
    return jsonify(metrics)


@app.route('/api/noise_image_info', methods=['GET'])
def noise_image_info():
    """Return base64 image data and global boundaries for given city, time, zone, fph, and metric."""
    city = request.args.get('city')
    time = request.args.get('time')
    zone = request.args.get('flight_zone')
    fph = request.args.get('flights_per_hour')
    metric = request.args.get('metric')
    if not city or not time or not zone or not fph or not metric:
        return jsonify({})

    img_dir = os.path.join(DATA_BASE_DIR, city, time, zone, fph)
    if not os.path.isdir(img_dir):
        return jsonify({'image_data': None, 'bounds': _read_global_coordinates()})

    image_b64 = None
    try:
        target_base = os.path.splitext(metric)[0].lower()
        for fname in os.listdir(img_dir):
            if os.path.splitext(fname)[0].lower() == target_base and fname.lower().endswith('.png'):
                image_file_path = os.path.join(img_dir, fname)
                import base64
                with open(image_file_path, 'rb') as imgf:
                    image_b64 = base64.b64encode(imgf.read()).decode('utf-8')
                break
    except Exception as e:
        print(f"[WARNING] Failed to read image for {city}/{time}/{zone}/{fph}/{metric}: {e}")

    boundaries = _read_global_coordinates()
    return jsonify({'image_data': image_b64, 'bounds': boundaries})


@app.route('/api/noise_available_combinations', methods=['GET'])
def noise_available_combinations():
    """Scan data folder for City -> Time -> Flight Zones -> FPH -> Metrics."""
    print(f"[INFO] noise_available_combinations called.")
    results = {}
    if not os.path.isdir(DATA_BASE_DIR):
        print(f"[WARNING] DATA_BASE_DIR does not exist: {DATA_BASE_DIR}")
        return jsonify({'combinations': results, 'bounds': None})

    for city in sorted(os.listdir(DATA_BASE_DIR)):
        if city.lower() == 'coordinates.csv':
            continue
        city_path = os.path.join(DATA_BASE_DIR, city)
        if not os.path.isdir(city_path):
            continue
        results[city] = {}
        for time in sorted(os.listdir(city_path)):
            time_path = os.path.join(city_path, time)
            if not os.path.isdir(time_path):
                continue
            results[city][time] = {}
            for zone in sorted(os.listdir(time_path)):
                zone_path = os.path.join(time_path, zone)
                if not os.path.isdir(zone_path):
                    continue
                results[city][time][zone] = {}
                for fph in sorted(os.listdir(zone_path)):
                    fph_path = os.path.join(zone_path, fph)
                    if not os.path.isdir(fph_path):
                        continue
                    metrics = []
                    try:
                        for fname in sorted(os.listdir(fph_path)):
                            if fname.lower().endswith('.png'):
                                metrics.append(os.path.splitext(fname)[0])
                    except Exception as e:
                        print(f"[WARNING] Failed to list metrics in {fph_path}: {e}")
                    results[city][time][zone][fph] = {'metrics': metrics}

    bounds = _read_global_coordinates()
    return jsonify({'combinations': results, 'bounds': bounds})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=4003)
