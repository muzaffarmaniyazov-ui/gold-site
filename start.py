import cv2
import time

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Kamera ochilmadi")
    exit()

print("✅ Kamera ishga tushdi. Oyna ochilmaydi. To‘xtatish uchun CTRL+C bosing.")

try:
    while True:
        # Kameradan kadr o‘qib turamiz, shunda kamera “band” bo‘lib turadi (chiroq yonadi)
        ret, frame = cap.read()
        if not ret:
            print("❌ Kadr olinmadi")
            break

        time.sleep(0.01)  # CPU ko‘p ishlamasin
except KeyboardInterrupt:
    print("\n⛔ To‘xtatildi (CTRL+C).")
finally:
    cap.release()
