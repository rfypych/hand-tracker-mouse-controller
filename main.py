import cv2
import time
import numpy as np
import threading

# Impor modul custom kita
from hand_tracker import HandTracker
from gesture_detector import GestureDetector, Gesture
from mouse_controller import MouseController
# Impor modul GUI dan Suara
from calibration_gui import CalibrationGUI
from sound_feedback import SoundFeedback

def main():
    print("Starting Virtual Mouse...")

    # --- Pengaturan Awal ---
    cap_width, cap_height = 640, 480
    pTime = 0
    # Nilai default, akan diambil dari instance setelah inisialisasi jika GUI tidak mengubahnya
    # smoothing = 5 
    # click_threshold = 30 
    # fist_threshold = 150 

    # --- Inisialisasi Komponen ---
    tracker = HandTracker(maxHands=1, detectionCon=0.7, trackCon=0.7)
    # Ambil nilai default dari controller/detector setelah dibuat
    controller = MouseController() # Gunakan default smoothing awal
    detector = GestureDetector() # Gunakan default threshold awal
    sound_feedback = SoundFeedback() # Inisialisasi sound

    # --- Jalankan GUI di Thread Terpisah ---
    def run_gui():
        # Kirim instance controller & detector ke GUI agar bisa diubah
        calibration_gui = CalibrationGUI(controller, detector) 
        calibration_gui.run()
        
    print("Starting Calibration GUI in a separate thread...")
    gui_thread = threading.Thread(target=run_gui, daemon=True) 
    # Daemon=True agar thread GUI otomatis keluar saat main thread (OpenCV loop) keluar
    gui_thread.start()

    # --- Buka Webcam ---
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sound_feedback.quit() # Pastikan mixer berhenti jika kamera gagal
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cap_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cap_height)
    print(f"Webcam opened ({cap_width}x{cap_height}). Press 'q' to quit.")

    # --- Loop Utama ---
    try:
        while True:
            # Periksa apakah thread GUI masih berjalan (opsional, daemon=True harusnya cukup)
            # if not gui_thread.is_alive():
            #     print("GUI thread has stopped. Exiting main loop.")
            #     break
                
            success, img = cap.read()
            if not success:
                print("Error: Could not read frame from webcam. Exiting.")
                break

            # Balik gambar secara horizontal (efek cermin)
            img = cv2.flip(img, 1)
            frame_shape = img.shape # (height, width, channels)

            # 1. Deteksi Tangan & Landmark
            img = tracker.find_hands(img, draw=True) # Gambar tangan di frame
            lmList = tracker.find_position(img, handNo=0, draw=False) # Dapatkan posisi landmark (tanpa menggambar lagi)

            gesture = Gesture.NONE # Default gesture

            if lmList:
                # 2. Deteksi Status Jari & Gesture
                fingers = tracker.fingers_up()
                if fingers: # Pastikan fingers tidak empty
                    # print(f"Fingers: {fingers}") # Debug
                    gesture = detector.detect(lmList, fingers)
                    # print(f"Detected Gesture: {gesture}") # Debug

                    # 3. Update Kontrol Mouse berdasarkan Gesture
                    controller.update(gesture, lmList, frame_shape)

                    # 4. Mainkan Feedback Suara
                    sound_feedback.play(gesture)

                    # Visualisasi tambahan (opsional)
                    # Gambar lingkaran di ujung telunjuk (landmark 8)
                    index_tip_id = 8
                    if len(lmList) > index_tip_id:
                        cv2.circle(img, (lmList[index_tip_id][1], lmList[index_tip_id][2]), 10, (0, 255, 0), cv2.FILLED)
                    
                    # Tampilkan status gesture di layar
                    cv2.putText(img, f'Gesture: {gesture}', (20, 100), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
                    if controller.is_dragging:
                        cv2.putText(img, 'DRAGGING', (20, 140), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                else:
                    # print("Could not determine finger state.") # Debug jika fingers_up() gagal
                    # Jika status jari tidak bisa dideteksi, mungkin reset mouse state?
                    controller.update(Gesture.NONE, lmList, frame_shape) # Kirim NONE jika jari tidak jelas
            else:
                # Jika tidak ada tangan terdeteksi, pastikan status drag direset jika sebelumnya aktif
                if controller.is_dragging:
                    controller.update(Gesture.DRAG_END, [], frame_shape) # Kirim DRAG_END jika tangan hilang saat dragging


            # --- Tampilkan FPS ---
            cTime = time.time()
            fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
            pTime = cTime
            cv2.putText(img, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 0), 3)

            # --- Tampilkan Frame ---
            cv2.imshow("Virtual Mouse", img)

            # --- Keluar ---
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Exiting...")
                break
            # Tambahkan key lain jika perlu, misal untuk kalibrasi, dll.

    finally:
        # --- Cleanup ---
        print("Releasing webcam and destroying windows...")
        cap.release()
        cv2.destroyAllWindows()
        # Hentikan mixer pygame
        sound_feedback.quit() 
        print("Virtual Mouse stopped.")

if __name__ == "__main__":
    main() 