from flask import Flask, request, jsonify, render_template_string
import os
import traceback
import json
from datetime import datetime

UPLOAD_FOLDER = os.path.dirname(__file__)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Signal Analyzer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;
        }
        .container {
            background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px; width: 100%; padding: 40px; animation: slideUp 0.5s ease-out;
        }
        @keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        h1 { color: #333; margin-bottom: 10px; font-size: 28px; text-align: center; }
        .subtitle { color: #666; text-align: center; margin-bottom: 30px; font-size: 14px; }

        .upload-area {
            border: 2px dashed #667eea; border-radius: 12px; padding: 40px 20px; text-align: center;
            background: #f8f9ff; margin-bottom: 20px; transition: all 0.3s ease; cursor: pointer;
        }
        .upload-area:hover { border-color: #764ba2; background: #f0f2ff; }
        .upload-area.dragover { border-color: #764ba2; background: #e8ebff; transform: scale(1.02); }
        .upload-icon { font-size: 48px; margin-bottom: 10px; color: #667eea; }
        .upload-text { color: #555; margin-bottom: 5px; font-weight: 500; }
        .upload-hint { color: #999; font-size: 12px; }
        input[type="file"] { display: none; }

        .file-info {
            background: #e8f5e9; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px;
            display: none; align-items: center; gap: 10px;
        }
        .file-info.show { display: flex; }
        .file-name {
            flex: 1; color: #2e7d32; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .remove-file {
            background: none; border: none; color: #d32f2f; cursor: pointer; font-size: 18px;
            padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
        }

        button[type="submit"] {
            width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        button[type="submit"]:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5); }
        button[type="submit"]:active { transform: translateY(0); }
        button[type="submit"]:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

        .status-slots {
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 25px;
        }
        .slot {
            padding: 12px; border-radius: 8px; text-align: center; font-size: 13px; font-weight: 500;
            background: #f5f5f5; color: #999; border: 2px solid transparent; transition: all 0.3s ease;
            cursor: pointer; position: relative;
        }
        .slot:hover:not(.uploaded) { background: #e3f2fd; border-color: #667eea; transform: translateY(-2px); }
        .slot.uploaded { background: #e8f5e9; color: #2e7d32; border-color: #4caf50; }
        .slot.uploaded::after { content: '✓'; position: absolute; top: 4px; right: 8px; font-size: 16px; color: #4caf50; }
        .slot.selected {
            background: #e3f2fd; border-color: #667eea; color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
        }

        .result { margin-top: 20px; padding: 15px; border-radius: 8px; display: none; white-space: pre-line; }
        .result.show { display: block; animation: slideUp 0.3s ease-out; }
        .result.success { background: #e8f5e9; border-left: 4px solid #4caf50; color: #2e7d32; }
        .result.error { background: #ffebee; border-left: 4px solid #f44336; color: #c62828; }

        .spinner {
            display: none; width: 20px; height: 20px; border: 3px solid rgba(255, 255, 255, 0.3);
            border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto;
        }
        .spinner.show { display: block; }
        @keyframes spin { to { transform: rotate(360deg); } }
        select { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Trading Signal Analyzer</h1>
        <p class="subtitle">Sube capturas de tus gráficos para análisis técnico</p>

        <div class="status-slots">
            <div class="slot" id="slot-m1" data-slot="m1">M1</div>
            <div class="slot selected" id="slot-m5" data-slot="m5">M5</div>
            <div class="slot" id="slot-m15" data-slot="m15">M15</div>
        </div>

        <form id="uploadForm" method="post" enctype="multipart/form-data" action="/upload">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <div class="upload-text">Haz clic o arrastra tu imagen aquí</div>
                <div class="upload-hint">PNG, JPG, JPEG o BMP (máx. 10MB)</div>
                <input type="file" name="file" id="fileInput" accept=".png,.jpg,.jpeg,.bmp">
            </div>

            <div class="file-info" id="fileInfo">
                <span class="file-name" id="fileName"></span>
                <button type="button" class="remove-file" id="removeFile">✕</button>
            </div>

            <select name="slot" id="slotSelect">
                <option value="m1">M1 - 1 Minuto</option>
                <option value="m5" selected>M5 - 5 Minutos</option>
                <option value="m15">M15 - 15 Minutos</option>
            </select>

            <button type="submit" id="submitBtn">
                <span id="btnText">Subir y Analizar</span>
                <div class="spinner" id="spinner"></div>
            </button>
        </form>

        <div class="result" id="result"></div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const removeFile = document.getElementById('removeFile');
        const uploadForm = document.getElementById('uploadForm');
        const result = document.getElementById('result');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const spinner = document.getElementById('spinner');
        const slotSelect = document.getElementById('slotSelect');
        const slots = document.querySelectorAll('.slot');

        fetch('/status')
            .then(r => r.json())
            .then(data => {
                if (data.m1) document.getElementById('slot-m1').classList.add('uploaded');
                if (data.m5) document.getElementById('slot-m5').classList.add('uploaded');
                if (data.m15) document.getElementById('slot-m15').classList.add('uploaded');
            })
            .catch(() => {});

        slots.forEach(slot => {
            slot.addEventListener('click', () => {
                slots.forEach(s => s.classList.remove('selected'));
                slot.classList.add('selected');
                const slotValue = slot.getAttribute('data-slot');
                slotSelect.value = slotValue;

                const slotName = slot.textContent.trim().split('✓')[0];
                showResult(`Timeframe ${slotName} seleccionado. Ahora sube tu archivo.`, 'success');
                setTimeout(() => { result.classList.remove('show'); }, 2000);
            });
        });

        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
        uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('dragover'); });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length) {
                fileInput.files = files;
                showFileInfo(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) showFileInfo(e.target.files[0]);
        });

        removeFile.addEventListener('click', () => {
            fileInput.value = '';
            fileInfo.classList.remove('show');
        });

        function showFileInfo(file) {
            fileName.textContent = file.name;
            fileInfo.classList.add('show');
        }

        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!fileInput.files.length) {
                showResult('Por favor selecciona un archivo', 'error');
                return;
            }

            submitBtn.disabled = true;
            btnText.style.display = 'none';
            spinner.classList.add('show');
            result.classList.remove('show');

            const formData = new FormData(uploadForm);

            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const data = await response.json();

                if (response.ok) {
                    const slot = formData.get('slot');
                    const slotElement = document.getElementById(`slot-${slot}`);
                    slotElement.classList.add('uploaded');
                    slotElement.classList.remove('selected');

                    let msg = `✓ Archivo subido: ${data.saved}`;
                    if (data.signal) {
                        msg += `\n\n📊 Señal: ${data.signal.signal}\n🎯 Confianza: ${data.signal.confidence}%`;
                        if (data.message) msg += `\n\n${data.message}`;
                    } else {
                        msg += `\n\n⏳ Sube los timeframes restantes para obtener una señal completa.`;
                    }
                    showResult(msg, 'success');

                    fileInput.value = '';
                    fileInfo.classList.remove('show');

                    const nextSlot = Array.from(slots).find(s => !s.classList.contains('uploaded'));
                    if (nextSlot) {
                        setTimeout(() => {
                            slots.forEach(s => s.classList.remove('selected'));
                            nextSlot.classList.add('selected');
                            slotSelect.value = nextSlot.getAttribute('data-slot');
                        }, 500);
                    }
                } else {
                    showResult(`Error: ${data.error || 'Error desconocido'}`, 'error');
                }
            } catch (err) {
                showResult(`Error de conexión: ${err.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                btnText.style.display = 'inline';
                spinner.classList.remove('show');
            }
        });

        function showResult(message, type) {
            result.textContent = message;
            result.className = `result show ${type}`;
        }
    </script>
</body>
</html>
'''

def allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/status", methods=["GET"])
def status():
    m1_exists = os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], "m1.png"))
    m5_exists = os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], "m5.png"))
    m15_exists = os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], "m15.png"))
    return jsonify({"m1": m1_exists, "m5": m5_exists, "m15": m15_exists})

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file part"}), 400

    file = request.files["file"]
    slot = request.form.get("slot", "m1")

    if file.filename == "":
        return jsonify({"error": "no selected file"}), 400

    if not allowed(file.filename):
        return jsonify({"error": "file type not allowed"}), 400

    filename = f"{slot}.png"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    m1_path = os.path.join(app.config["UPLOAD_FOLDER"], "m1.png")
    m5_path = os.path.join(app.config["UPLOAD_FOLDER"], "m5.png")
    m15_path = os.path.join(app.config["UPLOAD_FOLDER"], "m15.png")

    try:
        if os.path.exists(m1_path) and os.path.exists(m5_path) and os.path.exists(m15_path):
            from image_analyzer import analyze_image
            # Si tú ya tienes strategy.py / signal_generator.py, déjalos como están:
            # from strategy import trading_strategy
            # from signal_generator import generate_signal

            m1 = analyze_image(m1_path)
            m5 = analyze_image(m5_path)
            m15 = analyze_image(m15_path)

            # Si no tienes strategy.py, aquí puedes devolver diagnóstico simple
            # (si ya lo tienes, reemplaza esto por tu trading_strategy real)
            result = {
                "signal": "COMPRA" if str(m15.get("trend","")).lower() == "alcista" else "VENTA",
                "confidence": int((float(m1.get("strength",50))+float(m5.get("strength",50))+float(m15.get("strength",50))) / 3),
                "details": {"m1": m1, "m5": m5, "m15": m15}
            }
            message = "✅ Listo. Sube nuevas capturas cuando cambie el mercado."

            # Log
            try:
                entry = {
                    "timestamp": datetime.now().isoformat(sep=" ", timespec="seconds"),
                    "signal": result.get("signal"),
                    "confidence": result.get("confidence"),
                    "details": result.get("details", {}),
                    "message": message
                }
                with open(os.path.join(app.config["UPLOAD_FOLDER"], "signals.log"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass

            return jsonify({
                "saved": filename,
                "signal": result,
                "message": message
            }), 200

    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({
            "saved": filename,
            "error": str(e),
            "trace": tb
        }), 500

    return jsonify({"saved": filename}), 200

if __name__ == "__main__":
    # Mantengo tu configuración local
    app.run(host="0.0.0.0", port=5000, debug=True)
