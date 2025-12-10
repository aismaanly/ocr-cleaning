import re
import json

# =========================================================
# FILE INPUT/OUTPUT
# =========================================================
INPUT_FILE = "output_ocr/Peraturan_Akademik_2025.txt"
OUTPUT_FILE = "output_cleaning/cleaning_peraturan_2025.json"

# =========================================================
# CLEANING DASAR + NORMALISASI OCR
# =========================================================
def clean_text(text):
    text = re.sub(r"[^\S\r\n]+", " ", text)   # hapus spasi ganda
    text = re.sub(r"—", "-", text)            # ganti em-dash
    text = re.sub(r"\n{2,}", "\n", text)      # hapus empty line beruntun
    # normalisasi OCR: ganti (l) atau (I) jadi (1)
    text = re.sub(r"\(\s*[lI]\s*\)", "(1)", text)
    return text.strip()

# =========================================================
# REMOVE PEMBUKA — mulai dari Pasal pertama
# =========================================================
def remove_pembukaan(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^Pasal\s+\d+\s*$", line, flags=re.I):
            return "\n".join(lines[i:])
    return text  # jika tidak ketemu Pasal, kembalikan utuh

# =========================================================
# SIMPAN AYAT
# =========================================================
def save_ayat(results, buffer, pasal, ayat, chunk_index, kategori):
    text = " ".join(buffer).strip()
    # hapus titik atau spasi di awal
    text = re.sub(r"^[\.\s]+", "", text)
    if not text:
        return
    
    results.append({
        "metadata": {
            "sumber": "Peraturan_Akademik_2025",
            "bab": None,                # tidak ada bab
            "pasal": pasal,
            "ayat": ayat,
            "tahun_terbit": 2025,
            "status": "revisi",
            "chunk_index": chunk_index,
            "kategori": kategori        # bisa kosong
        },
        "page_content": text
    })

# =========================================================
# PARSER UTAMA
# =========================================================
def parse_document(text):
    lines = text.split("\n")
    current_pasal = None
    current_ayat = None
    results = []
    buffer = []
    chunk_index = 1

    REGEX_AYAT = r"^\(?(\d+)[)\.]?\s*(.+)"

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        # ===================== STOPPER KHUSUS PENUTUP =====================
        if re.match(r"^Ditetapkan\s+di", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_pasal, current_ayat, chunk_index, "")
            break

        # NORMALISASI OCR AYAT
        line = re.sub(r"^\(S(\d+)\)", r"(\1)", line)
        line = re.sub(r"^KM\)", "(4)", line)

        # DETEKSI PASAL
        pasal_match = re.match(r"^Pasal\s+(\d+)\s*$", line, re.I)
        if pasal_match:
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_pasal, current_ayat, chunk_index, "")
                buffer = []
                chunk_index += 1
            current_pasal = int(pasal_match.group(1))
            current_ayat = None
            buffer = []
            continue

        # DETEKSI AYAT
        ayat_match = re.match(REGEX_AYAT, line)
        if ayat_match and current_ayat is None:
            current_ayat = int(ayat_match.group(1))
            buffer.append(ayat_match.group(2).strip())
            continue

        # LANJUTAN AYAT ATAU AYAT BARU
        if current_ayat is not None:
            ayat_match = re.match(REGEX_AYAT, line)
            if ayat_match:
                potential_num = int(ayat_match.group(1))
                content_text = ayat_match.group(2).strip()
                
                is_real_new_ayat = True
                if content_text and content_text[0].islower():
                    is_real_new_ayat = False
                if buffer:
                    last_line_clean = buffer[-1].strip().lower()
                    if last_line_clean.endswith("ayat") or last_line_clean.endswith("huruf") or last_line_clean.endswith("angka"):
                        is_real_new_ayat = False
                if potential_num <= current_ayat:
                    is_real_new_ayat = False

                if is_real_new_ayat:
                    save_ayat(results, buffer, current_pasal, current_ayat, chunk_index, "")
                    buffer = []
                    chunk_index += 1
                    current_ayat = potential_num
                    buffer.append(content_text)
                else:
                    buffer.append(line)
            else:
                buffer.append(line)
            continue

    if buffer and current_ayat is not None:
        save_ayat(results, buffer, current_pasal, current_ayat, chunk_index, "")

    return results

# =========================================================
# EKSEKUSI
# =========================================================
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw = f.read()

cleaned = clean_text(raw)
cleaned = remove_pembukaan(cleaned)
parsed = parse_document(cleaned)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2, ensure_ascii=False)

print("✅ Cleaning selesai. Data disimpan di →", OUTPUT_FILE)
