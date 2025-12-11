# 📘 README — Pipeline Cleaning & Parsing Peraturan Akademik (2023 & 2025)

Dokumen ini menjelaskan alur kerja, tujuan, struktur folder, serta catatan penting dalam proses **OCR → Cleaning → Normalisasi → Parsing → JSON Chunking** untuk dokumen *Peraturan Akademik Universitas*.

---

## 🚀 Tujuan Proyek

Proyek ini bertujuan untuk:

* Membersihkan teks hasil OCR agar konsisten dengan format hukum resmi.
* Memperbaiki struktur **pasal**, **ayat**, dan **cabang huruf**.
* Menangani ketidakkonsistenan yang muncul akibat kesalahan OCR.
* Menghasilkan **JSON chunk** yang terstruktur rapi dan siap digunakan untuk keperluan *retrieval*, *embedding*, dan *RAG*.

---

## 🔧 Alur Kerja

### 1. **OCR Extraction**

File PDF diekstraksi menjadi teks mentah melalui OCR. Kendala umum:

* Teks patah-patah
* Hilangnya tanda kurung penomoran ayat
* Cabang huruf sulit terbaca (a., b., c.)
* Tabel tidak terstruktur

### 2. **Cleaning**

Proses meliputi:

* Normalisasi spasi, newline, dan karakter rusak
* Penyatuan ayat bercabang
* Perbaikan penomoran ayat
* Menghapus artefak OCR seperti angka terpisah, bullet acak, dan huruf salah baca

### 3. **Parsing Struktur Pasal & Ayat**

Parser akan:

* Mendeteksi pola "Pasal X"
* Menentukan batas ayat
* Menggabungkan ayat bercabang menjadi entitas yang benar
* Menangani pasal tanpa penomoran ayat (contoh: Pasal 34 & 42)

### 4. **Chunking JSON**

Setiap ayat diubah menjadi objek JSON seperti:

```
{
  "metadata": {
    "sumber": "Peraturan_Akademik_2023",
    "bab": 1,
    "pasal": 1,
    "ayat": 1,
    "status": "berlaku",
    "chunk_index": 1
  },
  "page_content": "isi ayat"
}
```

---

## 📌 Permasalahan Cleaning Pasal pada Pertor 2023

Berikut daftar isu spesifik yang ditemukan pada masing-masing pasal dalam dokumen 2023:

* **Pasal 1** → Sebelum ayat pertama terdapat kalimat; terdapat ayat koma ("ayat 37,39").
* **Pasal 2** → Penomoran ayat tidak menggunakan format (1)
* **Pasal 12** → Di dalam ayat 3 salah terbaca sebagai ayat 2, membuat parser menganggap sebagai ayat baru.
* **Pasal 17** → Ayat bercabang dua kali.
* **Pasal 28** → Terdapat tabel nilai yang mengganggu struktur ayat.
* **Pasal 34** → Hanya ada 1 ayat.
* **Pasal 44** → Memuat tabel nilai serta typo huruf "8".
* **Pasal 47** → Di dalam ayat 3 salah terbaca sebagai ayat 2, membuat parser menganggap sebagai ayat baru.
* **Pasal 50** → Cabang huruf tidak terbaca jelas oleh OCR.
* **Pasal 59** → Terdapat cabang huruf.
* **Pasal 60** → Di dalam ayat 4 salah terbaca sebagai ayat 3, membuat parser menganggap sebagai ayat baru.

---

## 📊 Total Ayat per Pasal — Pertor 2023

Daftar di bawah membantu memastikan jumlah ayat setelah cleaning sesuai struktur dokumen asli.

* Pasal 1: 68 Ayat
* Pasal 2: 3 Ayat
* Pasal 3: 6 Ayat
* Pasal 4: 4 Ayat
* Pasal 5: 2 Ayat
* Pasal 6: 6 Ayat
* Pasal 7: 3 Ayat
* Pasal 8: 5 Ayat
* Pasal 9: 2 Ayat
* Pasal 10: 3 Ayat
* Pasal 11: 6 Ayat
* Pasal 12: 5 Ayat
* Pasal 13: 6 Ayat
* Pasal 14: 10 Ayat
* Pasal 15: 4 Ayat
* Pasal 16: 2 Ayat
* Pasal 17: 4 Ayat
* Pasal 18: 7 Ayat
* Pasal 19: 2 Ayat
* Pasal 20: 5 Ayat
* Pasal 21: 6 Ayat
* Pasal 22: 5 Ayat
* Pasal 23: 3 Ayat
* Pasal 24: 12 Ayat
* Pasal 25: 3 Ayat
* Pasal 26: 8 Ayat
* Pasal 27: 6 Ayat
* Pasal 28: 16 Ayat
* Pasal 29: 10 Ayat
* Pasal 30: 16 Ayat
* Pasal 31: 6 Ayat
* Pasal 32: 4 Ayat
* Pasal 33: 8 Ayat
* Pasal 34: 1 Ayat *(tanpa penomoran)*
* Pasal 35: 5 Ayat
* Pasal 36: 12 Ayat
* Pasal 37: 3 Ayat
* Pasal 38: 2 Ayat
* Pasal 39: 10 Ayat
* Pasal 40: 5 Ayat
* Pasal 41: 5 Ayat
* Pasal 42: 1 Ayat *(tanpa penomoran)*
* Pasal 43: 6 Ayat
* Pasal 44: 9 Ayat
* Pasal 45: 5 Ayat
* Pasal 46: 3 Ayat
* Pasal 47: 10 Ayat
* Pasal 48: 6 Ayat
* Pasal 49: 2 Ayat
* Pasal 50: 3 Ayat
* Pasal 51: 5 Ayat
* Pasal 52: 11 Ayat
* Pasal 53: 8 Ayat
* Pasal 54: 9 Ayat
* Pasal 55: 3 Ayat
* Pasal 56: 5 Ayat
* Pasal 57: 4 Ayat
* Pasal 58: 3 Ayat
* Pasal 59: 3 Ayat
* Pasal 60: 9 Ayat
* Pasal 61: 2 Ayat

---

## 📊 Total Ayat per Pasal — Pertor 2025

Untuk dokumen perubahan tahun 2025 (tanpa bab/bagian), hasil cleaning menunjukkan:

* Pasal 3: 6 Ayat
* Pasal 4: 5 Ayat
* Pasal 9: 2 Ayat
* Pasal 12: 5 Ayat
* Pasal 17: 4 Ayat
* Pasal 21: 6 Ayat
* Pasal 28: 16 Ayat
* Pasal 30: 15 Ayat
* Pasal 33: 8 Ayat
* Pasal 47: 10 Ayat
* Pasal 48: 6 Ayat
* Pasal 52: 10 Ayat
* Pasal 53: 8 Ayat