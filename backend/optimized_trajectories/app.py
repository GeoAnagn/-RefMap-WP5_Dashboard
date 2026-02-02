import os
from flask import Flask, jsonify, send_from_directory, request, abort
from flask_cors import CORS

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')

app = Flask(__name__)
CORS(app)

def _scan_cases():
    """
    Scans the directory structure:
    data / {Area} / {Turbulence} / {Takeoff} / {Landing} / {filename}.gif
    """
    cases = []
    if not os.path.isdir(DATA_DIR):
        return []

    for area in sorted(os.listdir(DATA_DIR)):
        area_path = os.path.join(DATA_DIR, area)
        if not os.path.isdir(area_path): continue
        
        for turb in sorted(os.listdir(area_path)):
            turb_path = os.path.join(area_path, turb)
            if not os.path.isdir(turb_path): continue
            
            for takeoff in sorted(os.listdir(turb_path)):
                takeoff_path = os.path.join(turb_path, takeoff)
                if not os.path.isdir(takeoff_path): continue
                
                for landing in sorted(os.listdir(takeoff_path)):
                    landing_path = os.path.join(takeoff_path, landing)
                    if not os.path.isdir(landing_path): continue
                    
                    for filename in os.listdir(landing_path):
                        if filename.lower().endswith('.gif'):
                            rel_path = f"{area}/{turb}/{takeoff}/{landing}/{filename}"
                            cases.append({
                                'id': rel_path,
                                'area': area,
                                'turbulence': turb,
                                'takeoff': takeoff,
                                'landing': landing,
                                'filename': filename,
                                'label': f"Case {filename.replace('.gif', '')}"
                            })
    return cases

@app.after_request
def add_no_cache_headers(resp):
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

@app.route('/cases', methods=['GET'])
def list_cases():
    cases = _scan_cases()
    return jsonify({'cases': cases})

@app.route('/gif/<path:rel_path>', methods=['GET'])
def serve_gif(rel_path: str):
    """
    Serves the GIF based on the relative path provided by the frontend.
    """
    full_path = os.path.join(DATA_DIR, rel_path)
    if not os.path.isfile(full_path):
        abort(404)
    
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename, mimetype='image/gif')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4004)