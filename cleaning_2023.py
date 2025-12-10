import re
import json

# =========================================================
# FILE INPUT/OUTPUT
# =========================================================
INPUT_FILE = "output_ocr/Peraturan_Akademik_2023.txt"
OUTPUT_FILE = "output_cleaning/cleaning_peraturan_2023.json"

# =========================================================
# CLEANING DASAR + NORMALISASI OCR
# =========================================================
def clean_text(text):
    text = re.sub(r"[^\S\r\n]+", " ", text)   # hapus spasi ganda
    text = re.sub(r"—", "-", text)            # ganti em-dash
    text = re.sub(r"\n{2,}", "\n", text)      # hapus empty line beruntun
    # normalisasi OCR: ganti (l) atau (I) jadi (1)
    text = re.sub(r"\(\s*[lI]\s*\)", "(1)", text)
    # normalisasi BAB OCR error
    text = re.sub(r"\bBABI\b", "BAB I", text, flags=re.IGNORECASE)
    return text.strip()

# =========================================================
# REMOVE PEMBUKA — MULAI DARI BAB PERTAMA
# =========================================================
def remove_pembukaan(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.search(r"\bBAB\s+[IVXLC]+\b", line, flags=re.I):
            return "\n".join(lines[i:])
    return text  # jika tidak ketemu BAB, kembalikan utuh

# =========================================================
# ROMAN → INT
# =========================================================
def roman_to_int(roman):
    mapping = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    prev = 0
    for ch in roman[::-1]:
        val = mapping.get(ch.upper(), 0)
        total = total - val if val < prev else total + val
        prev = val
    return total

# =========================================================
# FIX JUDUL BAB MULTI-BARIS
# =========================================================
def fix_bab_title_lines(lines, start_index):
    kategori_lines = []
    for i in range(start_index, len(lines)):
        line = lines[i].strip()
        if re.match(r"^Bagian\s+", line, re.I): break
        if re.match(r"^Pasal\s+\d+\s*$", line, re.I): break
        if re.match(r"^\(\d+\)", line): break
        if re.match(r"^BAB\s+[IVXLC]+$", line, re.I): break
        if line:
            kategori_lines.append(line)
        else:
            break
    joined = " ".join(kategori_lines).lower()
    # gabungkan kata terputus
    tokens = joined.split()
    new_tokens = []
    temp = []
    for t in tokens:
        if len(t) == 1:
            temp.append(t)
        else:
            if temp:
                new_tokens.append("".join(temp))
                temp = []
            new_tokens.append(t)
    if temp:
        new_tokens.append("".join(temp))
    return " ".join(new_tokens)

# =========================================================
# SIMPAN AYAT
# =========================================================
def save_ayat(results, buffer, bab, pasal, ayat, chunk_index, kategori):
    text = " ".join(buffer).strip()
    # hapus titik atau spasi di awal
    text = re.sub(r"^[\.\s]+", "", text)
    if not text:
        return
    
    results.append({
        "metadata": {
            "sumber": "Peraturan_Akademik_2023",
            "bab": bab,
            "pasal": pasal,
            "ayat": ayat,
            "tahun_terbit": 2023,
            "status": "berlaku",
            "chunk_index": chunk_index,
            "kategori": kategori
        },
        "page_content": text
    })

# =========================================================
# PARSER UTAMA
# =========================================================
def parse_document(text):
    lines = text.split("\n")
    current_bab = None
    kategori = ""
    current_pasal = None
    current_ayat = None
    results = []
    buffer = []
    chunk_index = 1

    # Regex Ayat: Menangkap angka diikuti ) atau . atau spasi
    REGEX_AYAT = r"^\(?(\d+)[)\.]?\s*(.+)"

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        # ===================== STOPPER KHUSUS PENUTUP =====================
        # Jika ketemu baris "Ditetapkan di...", simpan buffer terakhir dan STOP.
        if re.match(r"^Ditetapkan\s+di", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
            break

        # ===================== NORMALISASI OCR AYAT =====================
        # ubah (S5) menjadi (5)
        line = re.sub(r"^\(S(\d+)\)", r"(\1)", line)
        # ubah KM) menjadi (4)
        line = re.sub(r"^KM\)", "(4)", line)

        # DETEKSI BAB
        if re.match(r"^BAB\s+[IVXLC]+\s*$", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                buffer = []
                chunk_index += 1
            roman = re.findall(r"[IVXLC]+", line, flags=re.I)[0]
            current_bab = roman_to_int(roman)
            kategori = fix_bab_title_lines(lines, idx + 1)
            current_pasal = None
            current_ayat = None
            continue

        # DETEKSI BAGIAN (skip)
        if re.match(r"^Bagian\s+", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                buffer = []
                chunk_index += 1
            current_ayat = None
            continue

        # DETEKSI PASAL
        pasal_match = re.match(r"^Pasal\s+(\d+)\s*$", line, re.I)
        if pasal_match:
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                buffer = []
                chunk_index += 1
            current_pasal = int(pasal_match.group(1))
            current_ayat = None
            buffer = []
            continue

        # DETEKSI AYAT (Pertama kali dalam pasal)
        ayat_match = re.match(REGEX_AYAT, line)
        if ayat_match and current_ayat is None:
            num = int(ayat_match.group(1))
            # Fix Pasal 50: Jika awal pasal terdeteksi angka 4, paksa jadi 1
            if num == 4:
                num = 1
            
            current_ayat = num
            buffer.append(ayat_match.group(2).strip())
            continue

        # LANJUTAN AYAT ATAU AYAT BARU
        if current_ayat is not None:
            # hentikan buffer jika ketemu Bagian baru atau Pasal baru
            if re.match(r"^Bagian\s+", line, re.I) or re.match(r"^Pasal\s+\d+", line, re.I):
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                buffer = []
                chunk_index += 1
                current_ayat = None
                continue
            
            # Cek apakah line ini potensi ayat baru?
            ayat_match = re.match(REGEX_AYAT, line)
            
            if ayat_match:
                potential_num = int(ayat_match.group(1))
                content_text = ayat_match.group(2).strip()
                
                is_real_new_ayat = True

                # 1. Cek Huruf Kecil: Jika konten dimulai huruf kecil, biasanya lanjutan kalimat
                if content_text and content_text[0].islower():
                    is_real_new_ayat = False

                # 2. Cek Konteks Baris Sebelumnya
                if buffer:
                    last_line_clean = buffer[-1].strip().lower()
                    if last_line_clean.endswith("ayat") or last_line_clean.endswith("huruf") or last_line_clean.endswith("angka"):
                        is_real_new_ayat = False
                
                # 3. Cek Urutan Angka (Safety Net)
                if potential_num <= current_ayat:
                    is_real_new_ayat = False

                if is_real_new_ayat:
                    # Simpan ayat sebelumnya
                    save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                    buffer = []
                    chunk_index += 1
                    # Mulai ayat baru
                    current_ayat = potential_num
                    buffer.append(content_text)
                else:
                    # Anggap sebagai teks biasa (lanjutan ayat sebelumnya)
                    buffer.append(line)
            else:
                # Bukan pola ayat, append biasa
                buffer.append(line)
            continue


    # SIMPAN AYAT TERAKHIR
    if buffer and current_ayat is not None:
        save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)

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