import os
import base64
from flask import Flask, jsonify, request
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

@app.route('/api/emissions_metrics', methods=['GET'])
def emissions_metrics():
	"""List available metrics (subdirectories under contour_maps)."""
	if not os.path.isdir(DATA_BASE_DIR):
		return jsonify([])
	try:
		metrics = [d for d in sorted(os.listdir(DATA_BASE_DIR)) if os.path.isdir(os.path.join(DATA_BASE_DIR, d))]
		return jsonify(metrics)
	except Exception as e:
		print(f"[WARNING] Failed to list metrics: {e}")
		return jsonify([])


@app.route('/api/emissions_cases', methods=['GET'])
def emissions_cases():
	"""List available cases (PNG basenames) for a given metric."""
	metric = request.args.get('metric')
	if not metric:
		return jsonify([])
	metric_path = os.path.join(DATA_BASE_DIR, metric)
	if not os.path.isdir(metric_path):
		return jsonify([])
	cases = []
	try:
		for fname in sorted(os.listdir(metric_path)):
			if fname.lower().endswith('.png'):
				cases.append(os.path.splitext(fname)[0])
	except Exception as e:
		print(f"[WARNING] Failed to list cases in {metric_path}: {e}")
	return jsonify(cases)


@app.route('/api/emissions_image', methods=['GET'])
def emissions_image():
	"""Return base64 overlay image and bounds for a selected metric and case.

	Response: {
	  image_data: <base64 or null>,
	  bounds: {lat-min, lat-max, lon-min, lon-max},
	  colorbar: { type: 'sequential'|'diverging', units: str }
	}
	"""
	metric = request.args.get('metric')
	case = request.args.get('case')
	if not metric or not case:
		return jsonify({'image_data': None, 'bounds': DEFAULT_BOUNDS, 'colorbar': None})

	metric_path = os.path.join(DATA_BASE_DIR, metric)
	if not os.path.isdir(metric_path):
		return jsonify({'image_data': None, 'bounds': DEFAULT_BOUNDS, 'colorbar': None})

	target_base = case.lower()
	image_b64 = None
	try:
		for fname in os.listdir(metric_path):
			base, ext = os.path.splitext(fname)
			if ext.lower() != '.png':
				continue
			if base.lower() == target_base:
				with open(os.path.join(metric_path, fname), 'rb') as f:
					image_b64 = base64.b64encode(f.read()).decode('utf-8')
				break
	except Exception as e:
		print(f"[WARNING] Failed to read image for {metric}/{case}: {e}")

	# Fixed diverging colorbar for all cases with defined min/max
	cbar_type = 'diverging'
	units = ''
	cbar_min = -0.5
	cbar_max = 0.5

	return jsonify({
		'image_data': image_b64,
		'bounds': DEFAULT_BOUNDS,
		'colorbar': {
			'type': cbar_type,
			'units': units,
			'min': cbar_min,
			'max': cbar_max
		}
	})


if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=4005)

