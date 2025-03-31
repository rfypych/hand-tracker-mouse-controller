# Aplikasi Deteksi Jumlah Jari

Aplikasi ini menggunakan MediaPipe dan OpenCV untuk mendeteksi jumlah jari yang terangkat melalui kamera, dengan tampilan GUI menggunakan Tkinter.

## Fitur

- Deteksi tangan dan jari secara real-time menggunakan MediaPipe
- Menampilkan warna berbeda untuk setiap jumlah jari (0-5)
- Mendukung deteksi 1-2 tangan
- Menyimpan riwayat deteksi ke file CSV
- Menampilkan FPS (frame per detik)

## Instalasi

1. Pastikan Python (versi 3.7 atau lebih baru) sudah terinstal
2. Kloning repositori ini atau download file-nya
3. Instal dependensi:

```
pip install -r requirements.txt
```

## Cara Penggunaan

1. Jalankan aplikasi:

```
python main.py
```

2. Tampilkan tangan Anda di depan kamera
3. Aplikasi akan mendeteksi jumlah jari dan menampilkan warna yang sesuai
4. Klik "Simpan CSV" untuk menyimpan data riwayat deteksi
5. Klik "Keluar" untuk menutup aplikasi

## Pemetaan Warna

- 0 Jari: Merah
- 1 Jari: Hijau
- 2 Jari: Biru
- 3 Jari: Kuning
- 4 Jari: Magenta
- 5 Jari: Cyan

## Solusi Masalah Umum

### Kamera Tidak Terdeteksi

- Pastikan kamera tidak sedang digunakan oleh aplikasi lain
- Coba gunakan kamera eksternal jika kamera bawaan tidak berfungsi
- Pada Windows, periksa pengaturan privasi untuk akses kamera

### MediaPipe Tidak Mendeteksi Tangan

- Pastikan pencahayaan cukup
- Posisikan tangan dengan jelas di depan kamera
- Jaga jarak tangan dari kamera (tidak terlalu dekat atau jauh)
- Hindari gerakan tangan yang terlalu cepat

### Performa Lambat

- Tutup aplikasi lain yang berat
- Kurangi resolusi kamera dengan mengedit nilai di `setup_camera()`
- Jalankan di komputer dengan spesifikasi lebih tinggi

## Cara Kerja Deteksi Jari

Aplikasi menggunakan MediaPipe untuk mendapatkan 21 landmark pada tangan. Deteksi jari bekerja dengan:

1. Mengidentifikasi posisi ujung jari dan sendi tengah
2. Untuk ibu jari, deteksi berdasarkan posisi horizontal relatif terhadap sendi
3. Untuk jari lainnya, deteksi berdasarkan posisi vertikal (jika ujung jari lebih tinggi dari sendi tengah)
4. Jumlah jari dibatasi maksimum 5 (untuk kasus 2 tangan) 