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

TEMP_DIR = tempfile.mkdtemp()
UPLOAD_DIR = os.path.join(TEMP_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

jobs = {}
video_files = {}

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'flv'}

# yt-dlp flags to bypass bot detection on cloud servers
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
    def _delete():
        time.sleep(delay)
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
    threading.Thread(target=_delete, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL é obrigatória'}), 400

    try:
        cmd = ['yt-dlp', '--no-playlist', '--dump-json', '--no-warnings'] + YTDLP_BYPASS_FLAGS + [url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)

        if result.returncode != 0:
            err = result.stderr.strip().split('\n')[-1]
            # Friendly message for bot detection
            if 'Sign in' in err or 'bot' in err.lower():
                return jsonify({'error': 'O YouTube está bloqueando este servidor. Use a aba "Upload" para vídeos do YouTube: baixe o vídeo no seu computador e faça o upload aqui.'}), 400
            if 'Private' in err or 'private' in err:
                return jsonify({'error': 'Este vídeo é privado e não pode ser acessado.'}), 400
            return jsonify({'error': f'Não foi possível obter informações. {err}'}), 400

        info = json.loads(result.stdout)
        return jsonify({
            'duration': info.get('duration', 0),
            'title': info.get('title', 'Vídeo'),
            'thumbnail': info.get('thumbnail', ''),
            'uploader': info.get('uploader', ''),
            'platform': info.get('extractor_key', '').lower(),
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Tempo limite esgotado.'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Formato não suportado. Use mp4, mov, avi, mkv, webm.'}), 400

    file_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower()
    filepath = os.path.join(UPLOAD_DIR, f"{file_id}.{ext}")
    file.save(filepath)

    try:
        probe = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', filepath
        ], capture_output=True, text=True, timeout=15)
        probe_data = json.loads(probe.stdout)
        duration = float(probe_data.get('format', {}).get('duration', 0))
        title = os.path.splitext(secure_filename(file.filename))[0]
    except Exception:
        duration = 0
        title = 'Vídeo enviado'

    video_files[file_id] = filepath
    cleanup_file(filepath, 1800)

    return jsonify({
        'file_id': file_id,
        'duration': duration,
        'title': title,
        'uploader': 'Upload local',
        'thumbnail': '',
        'platform': 'upload',
    })


@app.route('/api/video/<file_id>')
def serve_video(file_id):
    path = video_files.get(file_id)
    if not path or not os.path.exists(path):
        return jsonify({'error': 'Arquivo não encontrado'}), 404

    ext = path.rsplit('.', 1)[-1].lower()
    mime = {'mp4': 'video/mp4', 'mov': 'video/quicktime', 'avi': 'video/x-msvideo',
            'mkv': 'video/x-matroska', 'webm': 'video/webm', 'm4v': 'video/mp4'}.get(ext, 'video/mp4')

    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range')

    if not range_header:
        return send_file(path, mimetype=mime)

    match = range_header.replace('bytes=', '').split('-')
    byte_start = int(match[0]) if match[0] else 0
    byte_end = int(match[1]) if len(match) > 1 and match[1] else file_size - 1
    length = byte_end - byte_start + 1

    with open(path, 'rb') as f:
        f.seek(byte_start)
        data = f.read(length)

    rv = Response(data, 206, mimetype=mime)
    rv.headers['Content-Range'] = f'bytes {byte_start}-{byte_end}/{file_size}'
    rv.headers['Accept-Ranges'] = 'bytes'
    rv.headers['Content-Length'] = str(length)
    return rv


@app.route('/api/stream_url', methods=['POST'])
def get_stream_url():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'stream_url': None})
    try:
        cmd = ['yt-dlp', '--no-playlist', '--no-warnings', '--get-url',
               '--format', 'best[ext=mp4]/best'] + YTDLP_BYPASS_FLAGS + [url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and result.stdout.strip():
            return jsonify({'stream_url': result.stdout.strip().split('\n')[0]})
    except Exception:
        pass
    return jsonify({'stream_url': None})


@app.route('/api/generate', methods=['POST'])
def generate_gif():
    data = request.json
    url = data.get('url', '').strip()
    file_id = data.get('file_id', '').strip()
    start = float(data.get('start', 0))
    end = float(data.get('end', 5))
    width = int(data.get('width', 480))
    fps = int(data.get('fps', 10))

    if not url and not file_id:
        return jsonify({'error': 'URL ou arquivo é obrigatório'}), 400
    if end <= start:
        return jsonify({'error': 'Tempo final deve ser maior que o inicial'}), 400
    if (end - start) > 120:
        return jsonify({'error': 'Duração máxima é 120 segundos'}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {'status': 'starting', 'error': None}

    def process():
        video_path = os.path.join(TEMP_DIR, f"{job_id}_video.mp4")
        gif_path = os.path.join(TEMP_DIR, f"{job_id}.gif")
        palette_path = os.path.join(TEMP_DIR, f"{job_id}_palette.png")
        using_upload = bool(file_id)

        try:
            if file_id:
                src = video_files.get(file_id)
                if not src or not os.path.exists(src):
                    jobs[job_id] = {'status': 'error', 'error': 'Arquivo não encontrado.'}
                    return
                video_path = src
            else:
                jobs[job_id]['status'] = 'downloading'
                dl_cmd = ['yt-dlp', '--no-playlist',
                    '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    '--download-sections', f'*{max(0, start-2)}-{end+2}',
                    '--force-keyframes-at-cuts',
                    '--no-warnings'] + YTDLP_BYPASS_FLAGS + ['-o', video_path, url]

                dl = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=600)

                if dl.returncode != 0 or not os.path.exists(video_path):
                    jobs[job_id]['status'] = 'downloading_full'
                    dl2_cmd = ['yt-dlp', '--no-playlist',
                        '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        '--no-warnings'] + YTDLP_BYPASS_FLAGS + ['-o', video_path, url]
                    dl2 = subprocess.run(dl2_cmd, capture_output=True, text=True, timeout=300)
                    if dl2.returncode != 0 or not os.path.exists(video_path):
                        err = dl2.stderr.strip().split('\n')[-1] if dl2.stderr else 'Falha ao baixar.'
                        if 'Sign in' in err or 'bot' in err.lower():
                            err = 'YouTube bloqueou o download. Use a aba Upload: baixe o vídeo no computador e envie aqui.'
                        jobs[job_id] = {'status': 'error', 'error': err}
                        return

            jobs[job_id]['status'] = 'converting'
            duration = end - start

            subprocess.run([
                'ffmpeg', '-y', '-ss', str(start), '-t', str(duration), '-i', video_path,
                '-vf', f'fps={fps},scale={width}:-1:flags=lanczos,palettegen=stats_mode=full',
                palette_path
            ], capture_output=True, timeout=60)

            r = subprocess.run([
                'ffmpeg', '-y', '-ss', str(start), '-t', str(duration), '-i', video_path,
                '-i', palette_path,
                '-lavfi', f'fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
                gif_path
            ], capture_output=True, timeout=300)

            if r.returncode != 0 or not os.path.exists(gif_path):
                jobs[job_id] = {'status': 'error', 'error': 'Falha ao gerar GIF.'}
                return

            size_mb = os.path.getsize(gif_path) / (1024 * 1024)
            current_fps, current_width = fps, width

            attempts = 0
            while size_mb > 20 and attempts < 6:
                attempts += 1
                if current_fps > 6:
                    current_fps = max(6, current_fps - 2)
                else:
                    current_width = int(current_width * 0.8)
                subprocess.run([
                    'ffmpeg', '-y', '-ss', str(start), '-t', str(duration), '-i', video_path,
                    '-i', palette_path,
                    '-lavfi', f'fps={current_fps},scale={current_width}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
                    gif_path
                ], capture_output=True, timeout=180)
                size_mb = os.path.getsize(gif_path) / (1024 * 1024)

            jobs[job_id] = {
                'status': 'done', 'size_mb': round(size_mb, 2),
                'fps_used': current_fps, 'width_used': current_width,
                'path': gif_path, 'error': None
            }

            for f in [palette_path]:
                try: os.remove(f)
                except: pass
            if not using_upload:
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
    if not path or not os.path.exists(path):
        return jsonify({'error': 'Arquivo expirou'}), 404
    return send_file(path, mimetype='image/gif')


if __name__ == '__main__':
    print("\n🎬 GIF Maker iniciado!")
    print("   Abra http://127.0.0.1:5000 no seu navegador\n")
    app.run(debug=False, port=5000, host='0.0.0.0')
