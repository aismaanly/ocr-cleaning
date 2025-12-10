from pdf2image import convert_from_path
import pytesseract

# =============================
# KONFIGURASI PATH WINDOWS
# =============================
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler\Library\bin"


INPUT_PDF_PATH = "data_pdf/Peraturan_Akademik_2025.pdf"
OUTPUT_OCR_TXT = "output_ocr/Peraturan_Akademik_2025.txt"

# =============================
# PROSES OCR
# =============================

print("📄 Mulai konversi PDF ke gambar ...")

pages = convert_from_path(
    INPUT_PDF_PATH,
    dpi=300,
    poppler_path=POPPLER_PATH
)

print(f"✅ Total halaman terdeteksi: {len(pages)}\n")

with open(OUTPUT_OCR_TXT, "w", encoding="utf-8") as f:

    for i, page in enumerate(pages, start=1):
        print(f"🔎 OCR halaman {i} ...")

        try:
            text = pytesseract.image_to_string(
                page,
                lang="ind",
                config="--psm 6"
            )
            f.write(text)

        except Exception as e:
            print(f"❌ Gagal OCR halaman {i}: {e}")

print("\n✅ OCR selesai. Hasil disimpan di:", OUTPUT_OCR_TXT)
