import os
import re
from flask import Flask, jsonify, send_from_directory, request, abort
from flask_cors import CORS


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')

app = Flask(__name__)
CORS(app)


def _scan_cases():
	"""Scan DATA_DIR for available trajectory gif files.

	Returns a list of dicts: { id, filename, label, number? }
	"""
	if not os.path.isdir(DATA_DIR):
		return []
	cases = []
	for name in os.listdir(DATA_DIR):
		if not name.lower().endswith('.gif'):
			continue
		# Expect names like trajectory_case1.gif, but be tolerant
		m = re.match(r"^trajectory_case(\d+)\.gif$", name, re.IGNORECASE)
		if m:
			num = int(m.group(1))
			case_id = f"case{num}"
			label = f"Case {num}"
			cases.append({
				'id': case_id,
				'filename': name,
				'label': label,
				'number': num,
			})
		else:
			# Fallback generic name -> use stem as id
			stem = os.path.splitext(name)[0]
			cases.append({
				'id': stem,
				'filename': name,
				'label': stem.replace('_', ' ').title(),
			})
	# Sort by numeric when available, then by filename
	cases.sort(key=lambda x: (x.get('number') is None, x.get('number', 0), x['filename']))
	return cases


@app.after_request
def add_no_cache_headers(resp):
	# Encourage browser to revalidate gifs during development
	resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
	resp.headers['Pragma'] = 'no-cache'
	resp.headers['Expires'] = '0'
	return resp


@app.route('/health', methods=['GET'])
def health():
	return jsonify({'status': 'ok'}), 200


@app.route('/cases', methods=['GET'])
def list_cases():
	cases = _scan_cases()
	if not cases:
		return jsonify({'cases': [], 'default': None}), 200
	default_id = cases[0]['id']
	# Only expose id, label, filename minimal info
	payload = [{
		'id': c['id'],
		'label': c['label'],
		'filename': c['filename'],
	} for c in cases]
	return jsonify({'cases': payload, 'default': default_id})


def _resolve_filename_from_case(case):
	"""Map a case identifier to an actual filename in DATA_DIR.

	Accepted inputs:
	- 'caseN' or 'N' -> trajectory_caseN.gif
	- exact filename ending with .gif if present
	Returns filename or None if not found/invalid.
	"""
	if not case:
		return None
	# Direct filename (no path separators allowed)
	if case.lower().endswith('.gif') and '/' not in case and '\\' not in case:
		fname = case
		if os.path.isfile(os.path.join(DATA_DIR, fname)):
			return fname
		return None
	# caseN
	m = re.match(r"^case(\d+)$", case, re.IGNORECASE)
	if m:
		n = int(m.group(1))
		fname = f"trajectory_case{n}.gif"
		if os.path.isfile(os.path.join(DATA_DIR, fname)):
			return fname
		return None
	# numeric
	if case.isdigit():
		fname = f"trajectory_case{int(case)}.gif"
		if os.path.isfile(os.path.join(DATA_DIR, fname)):
			return fname
		return None
	return None


@app.route('/gif/<path:case>', methods=['GET'])
def serve_gif(case: str):
	# Also allow query param ?name=filename.gif
	name = request.args.get('name')
	fname = _resolve_filename_from_case(name or case)
	if not fname:
		abort(404)
	# Safe serve from data directory
	return send_from_directory(DATA_DIR, fname, mimetype='image/gif', as_attachment=False)


if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=4004)
