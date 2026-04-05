import os
import uuid
import json
import subprocess
import tempfile
import threading
import time
from flask import Flask, request, jsonify, send_file, render_template, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

TEMP_DIR = "/tmp/gif_maker"
UPLOAD_DIR = os.path.join(TEMP_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

jobs = {}
video_files = {}

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'flv'}

YTDLP_BYPASS_FLAGS = [
    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    '--add-header', 'Accept-Language:en-US,en;q=0.9',
    '--no-check-certificates',
    '--extractor-retries', '3',
    '--sleep-requests', '1',
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_file(path, delay=600):
    def run():
        time.sleep(delay)
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
    threading.Thread(target=run, daemon=True).start()

@app.route('/')
def index():
    return "API GIF Maker Online"

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
    
    if file and allowed_file(file.filename):
        video_id = str(uuid.uuid4())
        filename = secure_filename(f"{video_id}_{file.filename}")
        path = os.path.join(UPLOAD_DIR, filename)
        file.save(path)
        
        video_files[video_id] = path
        cleanup_file(path, 3600)
        
        return jsonify({'video_id': video_id})
    
    return jsonify({'error': 'Formato não suportado'}), 400

@app.route('/api/process-url', methods=['POST'])
def process_url():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL não fornecida'}), 400
    
    video_id = str(uuid.uuid4())
    output_template = os.path.join(UPLOAD_DIR, f"{video_id}_%(title)s.%(ext)s")
    
    try:
        cmd = ['yt-dlp'] + YTDLP_BYPASS_FLAGS + [
            '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            '--merge-output-format', 'mp4',
            '-o', output_template,
            url
        ]
        
        subprocess.run(cmd, check=True, timeout=300)
        
        files = os.listdir(UPLOAD_DIR)
        video_path = next((os.path.join(UPLOAD_DIR, f) for f in files if f.startswith(video_id)), None)
        
        if not video_path:
            return jsonify({'error': 'Falha no download'}), 500
            
        video_files[video_id] = video_path
        cleanup_file(video_path, 3600)
        
        return jsonify({'video_id': video_id})
        
    except Exception as e:
        return jsonify({'error': f'Erro ao baixar vídeo: {str(e)}'}), 500

@app.route('/api/generate-gif', methods=['POST'])
def generate_gif():
    data = request.json
    video_id = data.get('video_id')
    start = float(data.get('start', 0))
    end = float(data.get('end', 5))
    fps = int(data.get('fps', 10))
    width = int(data.get('width', 320))
    
    video_path = video_files.get(video_id)
    if not video_path or not os.path.exists(video_path):
        return jsonify({'error': 'Vídeo não encontrado'}), 404
        
    job_id = str(uuid.uuid4())
    gif_path = os.path.join(TEMP_DIR, f"{job_id}.gif")
    jobs[job_id] = {'status': 'processing', 'path': gif_path}

    def process():
        try:
            jobs[job_id]['status'] = 'converting'
            duration = end - start
            
            r = subprocess.run([
                'ffmpeg', '-y', 
                '-ss', str(start), 
                '-t', str(duration), 
                '-i', video_path,
                '-vf', f'fps={fps},scale={width}:-1',
                '-threads', '1',
                '-preset', 'ultrafast',
                gif_path
            ], capture_output=True, timeout=600)

            if r.returncode != 0:
                error_msg = r.stderr.decode() if r.stderr else "Erro de memória"
                jobs[job_id] = {'status': 'error', 'error': f'Falha: {error_msg[:50]}'}
                return

            jobs[job_id] = {'status': 'done', 'path': gif_path}
            
            if video_id in video_files:
                try: os.remove(video_path)
                except: pass
            cleanup_file(gif_path, 600)

        except Exception as e:
            jobs[job_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=process, daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/api/status/<job_id>')
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    return jsonify({k: v for k, v in job.items() if k != 'path'})

@app.route('/api/download/<job_id>')
def download_gif(job_id):
    job = jobs.get(job_id)
    if not job or job.get('status') != 'done':
        return jsonify({'error': 'GIF não disponível'}), 404
    path = job.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'error': 'Arquivo expirou'}), 404
    return send_file(path, mimetype='image/gif', as_attachment=True, download_name='clip.gif')

@app.route('/api/preview/<job_id>')
def preview_gif(job_id):
    job = jobs.get(job_id)
    if not job or job.get('status') != 'done':
        return jsonify({'error': 'GIF não disponível'}), 404
    path = job.get('path')
    return send_file(path, mimetype='image/gif')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
