import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import ttk, messagebox
import PIL.Image, PIL.ImageTk
import numpy as np
import time
import csv
from datetime import datetime

class JariCounterApp:
    def __init__(self, window, window_title):
        # Inisialisasi window tkinter
        self.window = window
        self.window.title(window_title)
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Inisialisasi MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,   # Deteksi maksimum 2 tangan
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Inisialisasi variabel
        self.warna = {
            0: (255, 0, 0),    # Merah
            1: (0, 255, 0),    # Hijau
            2: (0, 0, 255),    # Biru
            3: (255, 255, 0),  # Kuning
            4: (255, 0, 255),  # Magenta
            5: (0, 255, 255),  # Cyan
            6: (128, 0, 0),    # Maroon
            7: (0, 128, 0),    # Green (Dark)
            8: (0, 0, 128),    # Navy
            9: (128, 128, 0),  # Olive
            10: (128, 0, 128)  # Purple
        }
        
        self.is_on = True
        self.jumlah_jari = 0
        self.fps = 0
        self.prev_time = 0
        self.frame_count = 0
        self.skip_frames = 0  # Untuk optimasi performa
        
        # Untuk menyimpan data ke CSV
        self.csv_data = []
        self.last_detection_time = time.time()
        self.detection_interval = 1.0  # Rekam data setiap 1 detik
        
        # Setup kamera
        self.setup_camera()
        
        # Setup GUI
        self.setup_gui()
        
        # Mulai update kamera
        self.update()
        
        self.window.mainloop()
    
    def setup_camera(self):
        # Coba buka kamera
        self.vid = cv2.VideoCapture(0)
        if not self.vid.isOpened():
            messagebox.showerror("Error", "Tidak dapat membuka kamera. Pastikan kamera terhubung dan tidak digunakan oleh aplikasi lain.")
            self.window.destroy()
            return
        
        # Set resolusi kamera
        self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    def setup_gui(self):
        # Frame utama
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame untuk kamera
        self.camera_frame = ttk.Frame(main_frame)
        self.camera_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas untuk menampilkan video
        self.canvas = tk.Canvas(self.camera_frame, width=640, height=480)
        self.canvas.pack()
        
        # Frame untuk kontrol dan info
        control_frame = ttk.Frame(main_frame, padding=(10, 0, 0, 0))
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Label untuk jumlah jari
        self.lbl_jari = ttk.Label(control_frame, text="Jumlah Jari: 0", font=("Arial", 14))
        self.lbl_jari.pack(pady=10)
        
        # Frame untuk kotak warna
        color_frame = ttk.Frame(control_frame, padding=5)
        color_frame.pack(pady=10)
        
        self.color_canvas = tk.Canvas(color_frame, width=100, height=100, bg="black")
        self.color_canvas.pack()
        
        # Label FPS
        self.lbl_fps = ttk.Label(control_frame, text="FPS: 0")
        self.lbl_fps.pack(pady=5)
        
        # Tombol simpan CSV
        btn_save = ttk.Button(control_frame, text="Simpan CSV", command=self.save_csv)
        btn_save.pack(pady=5)
        
        # Tombol keluar
        btn_exit = ttk.Button(control_frame, text="Keluar", command=self.on_closing)
        btn_exit.pack(pady=5)
    
    def count_fingers(self, hand_landmarks):
        # Mendapatkan koordinat setiap landmark
        coordinates = []
        for landmark in hand_landmarks.landmark:
            # Mengkonversi koordinat relatif (0.0-1.0) menjadi koordinat piksel
            coordinates.append((landmark.x, landmark.y))
        
        # Menghitung jari yang terangkat
        fingers = 0
        
        # Deteksi ibu jari yang lebih akurat
        # Ibu jari: perbandingan jarak antara ujung ibu jari (4) dengan sendi jari (2)
        # Bandingkan dengan jarak antara sendi dasar (17) dan sendi ibu jari (2)
        thumb_tip = coordinates[4]
        thumb_ip = coordinates[3]  # IP = Interphalangeal joint
        thumb_mcp = coordinates[2]  # MCP = Metacarpophalangeal joint
        wrist = coordinates[0]      # Pergelangan tangan
        
        # Tentukan apakah tangan kanan atau kiri berdasarkan posisi ibu jari relatif terhadap jari kelingking
        is_right_hand = coordinates[4][0] < coordinates[17][0]
        
        # Hitung jarak untuk deteksi ibu jari
        # Untuk tangan kanan, cek apakah ibu jari bergerak ke arah dalam (x semakin besar)
        # Untuk tangan kiri, cek apakah ibu jari bergerak ke arah dalam (x semakin kecil)
        if is_right_hand:
            # Jika tangan kanan
            if thumb_tip[0] < thumb_ip[0] - 0.03:  # Toleransi untuk keakuratan
                fingers += 1
        else:
            # Jika tangan kiri
            if thumb_tip[0] > thumb_ip[0] + 0.03:  # Toleransi untuk keakuratan
                fingers += 1
        
        # Untuk jari lainnya, gunakan perbandingan posisi y dengan titik referensi tambahan
        # Tips: 8, 12, 16, 20 (ujung jari)
        # PIP joints: 6, 10, 14, 18 (sendi tengah)
        # MCP joints: 5, 9, 13, 17 (sendi dasar) 
        tips = [8, 12, 16, 20]  # Landmark untuk ujung jari
        pips = [6, 10, 14, 18]  # Landmark untuk sendi tengah (PIP)
        mcps = [5, 9, 13, 17]   # Landmark untuk sendi dasar (MCP)
        
        # Tambahkan threshold untuk memperketat deteksi
        threshold = 0.02  # Nilai threshold yang bisa disesuaikan
        
        for i in range(4):
            # Jari dianggap terangkat jika ujung jari (tips) berada lebih tinggi (nilai y lebih kecil) 
            # dari sendi tengah (pips) dengan margin threshold
            # Dan pastikan jari benar-benar terangkat, bukan hanya sedikit bergerak
            # Syarat: 1) Ujung jari harus lebih tinggi dari sendi tengah
            #         2) Sendi tengah harus lebih tinggi dari sendi dasar
            if (coordinates[tips[i]][1] < coordinates[pips[i]][1] - threshold and 
                coordinates[pips[i]][1] < coordinates[mcps[i]][1]):
                fingers += 1
        
        return fingers
    
    def update(self):
        if not self.is_on:
            return
        
        # Hitung FPS
        current_time = time.time()
        self.frame_count += 1
        
        if current_time - self.prev_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.prev_time = current_time
            self.lbl_fps.config(text=f"FPS: {self.fps}")
        
        # Skip frame untuk optimasi jika perlu
        if self.skip_frames > 0:
            self.skip_frames -= 1
            ret, frame = self.vid.read()
            if ret:
                self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            self.window.after(15, self.update)
            return
        
        # Baca frame dari kamera
        ret, frame = self.vid.read()
        
        if ret:
            # Flip frame secara horizontal untuk tampilan mirror
            frame = cv2.flip(frame, 1)
            
            # Konversi BGR ke RGB untuk MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Proses deteksi tangan
            results = self.hands.process(rgb_frame)
            
            # Inisialisasi total jari
            total_fingers = 0
            
            # Jika ada tangan yang terdeteksi
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Gambar landmark tangan
                    self.mp_draw.draw_landmarks(
                        frame, 
                        hand_landmarks, 
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                        self.mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
                    
                    # Hitung jari yang terangkat untuk tangan ini
                    fingers = self.count_fingers(hand_landmarks)
                    total_fingers += fingers
            
            # Batasi total jari ke maksimum 10 (untuk 2 tangan)
            self.jumlah_jari = min(total_fingers, 10)
            
            # Update teks jumlah jari
            self.lbl_jari.config(text=f"Jumlah Jari: {self.jumlah_jari}")
            
            # Perbarui kotak warna
            warna_bgr = self.warna.get(self.jumlah_jari, (200, 200, 200))
            warna_rgb = (warna_bgr[2], warna_bgr[1], warna_bgr[0])  # Konversi BGR ke RGB
            self.color_canvas.config(bg='#{:02x}{:02x}{:02x}'.format(*warna_rgb))
            
            # Gambar kotak warna di frame
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (100, 100), warna_bgr, -1)
            cv2.putText(overlay, str(self.jumlah_jari), (45, 65), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            # Tambahkan overlay dengan transparansi
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            
            # Catat data ke CSV pada interval tertentu
            if current_time - self.last_detection_time >= self.detection_interval:
                self.last_detection_time = current_time
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.csv_data.append([timestamp, self.jumlah_jari])
            
            # Konversi frame ke format yang bisa ditampilkan di Tkinter
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        
        # Panggil update lagi setelah 15ms (sekitar 60fps)
        self.window.after(15, self.update)
    
    def save_csv(self):
        if not self.csv_data:
            messagebox.showinfo("Info", "Tidak ada data untuk disimpan.")
            return
        
        try:
            filename = f"deteksi_jari_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Jumlah Jari"])
                writer.writerows(self.csv_data)
            messagebox.showinfo("Info", f"Data berhasil disimpan ke {filename}")
            self.csv_data = []  # Reset data setelah disimpan
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan data: {str(e)}")
    
    def on_closing(self):
        # Konfirmasi keluar
        if messagebox.askokcancel("Keluar", "Apakah Anda yakin ingin keluar?"):
            self.is_on = False
            if hasattr(self, 'vid') and self.vid.isOpened():
                self.vid.release()
            self.window.destroy()

if __name__ == "__main__":
    try:
        # Buat window Tkinter
        root = tk.Tk()
        app = JariCounterApp(root, "Deteksi Jumlah Jari")
    except Exception as e:
        # Tangani error umum
        messagebox.showerror("Error", f"Terjadi kesalahan: {str(e)}") 