import cv2
import time
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8000


class CameraManager:
    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps

        self.cap = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.last_read_ok = False

    def start(self):
        if self.running:
            return

        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            raise RuntimeError("Kamera ochilmadi")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.running = True
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        while self.running:
            ok, frame = self.cap.read()
            self.last_read_ok = ok

            if ok:
                ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    with self.lock:
                        self.frame = jpeg.tobytes()

            time.sleep(0.01)

    def get_frame(self):
        with self.lock:
            return self.frame

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)

        if self.cap:
            self.cap.release()
            self.cap = None


camera = CameraManager()


INDEX_HTML = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AKFA + Camera</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }

        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
        }

        #siteFrame {
            position: fixed;
            inset: 0;
            width: 100%;
            height: 100%;
            border: none;
            background: #fff;
            z-index: 1;
        }

        #cameraBox {
            position: fixed;
            right: 20px;
            bottom: 20px;
            width: 340px;
            height: 255px;
            background: #000;
            border: 2px solid #fff;
            border-radius: 16px;
            overflow: hidden;
            
            z-index: -1;
            box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        }

        #cameraFeed {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            background: #000;
            
        }

        #status {
            position: fixed;
            left: 20px;
            bottom: 20px;
            z-index: -1;
            background: rgba(0,0,0,0.75);
            color: #fff;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 14px;
        }

        #topBar {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            gap: 10px;
        }

        .btn {
            text-decoration: none;
            color: white;
            background: rgba(0,0,0,0.7);
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 14px;
            border: 1px solid rgba(255,255,255,0.15);
        }

        .btn:hover {
            background: rgba(0,0,0,0.85);
        }
    </style>
</head>
<body>
    <iframe id="siteFrame" src="https://akfaaluminium.com/"></iframe>

    <div id="topBar">
        <a class="btn" href="/admin" target="_blank">Admin panel</a>
    </div>

    <div id="cameraBox">
        <img id="cameraFeed" src="/stream" alt="Camera stream">
    </div>

    <div id="status">Kamera faol</div>

    <script>
        const img = document.getElementById("cameraFeed");
        const status = document.getElementById("status");

        img.onload = () => {
            status.textContent = "Kamera faol";
        };

        
    </script>
</body>
</html>
"""


ADMIN_HTML = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - Camera Monitor</title>
    <style>
        * {
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }

        body {
            margin: 0;
            background: #0f172a;
            color: white;
            min-height: 100vh;
        }

        .wrap {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        h1 {
            margin: 0;
            font-size: 28px;
        }

        .actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .btn {
            text-decoration: none;
            color: white;
            background: #1e293b;
            padding: 10px 14px;
            border-radius: 10px;
            border: 1px solid #334155;
        }

        .btn:hover {
            background: #334155;
        }

        .grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }

        .card {
            background: #1e293b;
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }

        .card h2 {
            margin-top: 0;
            margin-bottom: 14px;
            font-size: 20px;
        }

        #mainFeed {
            width: 100%;
            border-radius: 14px;
            display: block;
            background: #000;
            min-height: 320px;
            object-fit: cover;
        }

        .meta {
            display: grid;
            gap: 12px;
        }

        .metaBox {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 14px;
        }

        .label {
            color: #94a3b8;
            font-size: 13px;
            margin-bottom: 6px;
        }

        .value {
            font-size: 18px;
            font-weight: bold;
        }

        .ok {
            color: #22c55e;
        }

        .warn {
            color: #f59e0b;
        }

        @media (max-width: 900px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="header">
            <h1>Admin Panel</h1>
            <div class="actions">
                <a class="btn" href="/">Asosiy sahifa</a>
                <a class="btn" href="/admin">Yangilash</a>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Live Camera</h2>
                <img id="mainFeed" src="/stream" alt="Live camera">
            </div>

            <div class="card">
                <h2>Holat</h2>
                <div class="meta">
                    <div class="metaBox">
                        <div class="label">Kamera</div>
                        <div class="value ok" id="cameraStatus">Faol</div>
                    </div>
                    <div class="metaBox">
                        <div class="label">Stream URL</div>
                        <div class="value">/stream</div>
                    </div>
                    <div class="metaBox">
                        <div class="label">Admin URL</div>
                        <div class="value">/admin</div>
                    </div>
                    <div class="metaBox">
                        <div class="label">Sayt</div>
                        <div class="value">AKFA Aluminium</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const feed = document.getElementById("mainFeed");
        const cameraStatus = document.getElementById("cameraStatus");

        feed.onload = () => {
            cameraStatus.textContent = "Faol";
            cameraStatus.className = "value ok";
        };

        feed.onerror = () => {
            cameraStatus.textContent = "Xatolik";
            cameraStatus.className = "value warn";
        };
    </script>
</body>
</html>
"""


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._send_html(INDEX_HTML)
            return

        if self.path == "/admin":
            self._send_html(ADMIN_HTML)
            return

        if self.path == "/stream":
            self._send_stream()
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def _send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_stream(self):
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        try:
            while True:
                frame = camera.get_frame()
                if frame is None:
                    time.sleep(0.03)
                    continue

                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                time.sleep(1 / 30)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print("Stream xatolik:", e)

    def log_message(self, format, *args):
        return


def open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}/")


def run():
    try:
        print("Kamera ishga tushirilmoqda...")
        camera.start()
        print("Kamera tayyor.")
    except Exception as e:
        print("Kamera ochishda xatolik:", e)
        return

    server = ThreadingHTTPServer((HOST, PORT), MyHandler)
    print(f"Server ishga tushdi: http://{HOST}:{PORT}/")
    print(f"Admin panel: http://{HOST}:{PORT}/admin")

    threading.Timer(1.0, open_browser).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer to'xtatildi.")
    finally:
        camera.stop()
        server.server_close()


if __name__ == "__main__":
    run()
