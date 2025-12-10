import re
import json

# =========================================================
# KONFIGURASI FILE
# =========================================================
INPUT_FILE = "output_ocr/Peraturan_Akademik_2023.txt"
OUTPUT_FILE = "output_cleaning/cleaning_peraturan_2023.json"

SOURCE_NAME = "Peraturan_Akademik_2023"
TAHUN_TERBIT = 2023
STATUS_DOKUMEN = "berlaku"

# =========================================================
# CLEANING DASAR & NORMALISASI OCR
# =========================================================
def clean_text(text: str) -> str:
    """
    Membersihkan noise OCR dasar tanpa menghilangkan struktur dokumen.
    """
    # Normalisasi spasi (tetap jaga newline)
    text = re.sub(r"[^\S\r\n]+", " ", text)

    # Normalisasi dash
    text = text.replace("—", "-")

    # Kurangi empty line berlebihan (judul BAB kadang perlu 1 baris kosong)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # OCR error: (l) atau (I) → (1) jika muncul di awal baris
    text = re.sub(r"^\(\s*[lI]\s*\)", "(1)", text, flags=re.MULTILINE)

    # OCR error umum: BABI → BAB I
    text = re.sub(r"\bBAB\s*I\b", "BAB I", text, flags=re.IGNORECASE)

    return text.strip()


# =========================================================
# HAPUS BAGIAN PEMBUKA (SEBELUM BAB I)
# =========================================================
def remove_pembukaan(text: str) -> str:
    """
    Dokumen legal Indonesia selalu dimulai dari BAB I.
    Bagian sebelum itu dibuang.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.search(r"\bBAB\s+[IVXLC]+\b", line, re.I):
            return "\n".join(lines[i:])
    return text


# =========================================================
# KONVERSI ANGKA ROMAWI → INTEGER
# =========================================================
def roman_to_int(roman: str) -> int:
    """
    Aman untuk BAB dokumen hukum (I–XX).
    """
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    total = prev = 0
    for c in roman.upper()[::-1]:
        curr = values.get(c, 0)
        total += -curr if curr < prev else curr
        prev = curr
    return total


# =========================================================
# FIX JUDUL BAB MULTI-BARIS (AKIBAT OCR WRAP)
# =========================================================
def extract_bab_title(lines: list[str], start_idx: int) -> str:
    """
    OCR sering memecah judul BAB ke beberapa baris.
    Fungsi ini menggabungkannya secara aman.
    """
    collected = []

    for i in range(start_idx, len(lines)):
        line = lines[i].strip()

        # Stopper struktur legal
        if re.match(r"^(Bagian|Pasal|\(\d+\)|BAB\s+[IVXLC]+)", line, re.I):
            break

        if not line:
            break

        collected.append(line)

    title = " ".join(collected).lower()
    return title[:150]  # kategori tidak perlu terlalu panjang


# =========================================================
# SIMPAN SATU AYAT
# =========================================================
def save_ayat(results, buffer, bab, pasal, ayat, chunk_index, kategori):
    """
    Menyimpan hasil ayat yang sudah terakumulasi ke JSON.
    """
    text = " ".join(buffer).strip()
    text = re.sub(r"^[\.\s]+", "", text)

    if not text:
        return

    results.append({
        "metadata": {
            "sumber": SOURCE_NAME,
            "bab": bab,
            "pasal": pasal,
            "ayat": ayat,
            "tahun_terbit": TAHUN_TERBIT,
            "status": STATUS_DOKUMEN,
            "chunk_index": chunk_index,
            "kategori": kategori
        },
        "page_content": text
    })


# =========================================================
# PARSER UTAMA DOKUMEN LEGAL
# =========================================================
def parse_document(text: str) -> list[dict]:
    """
    Parsing struktur:
    BAB → Pasal → Ayat
    dengan toleransi tinggi terhadap noise OCR.
    """
    lines = text.split("\n")

    current_bab = None
    current_pasal = None
    current_ayat = None
    kategori = ""

    buffer = []
    results = []
    chunk_index = 1

    REGEX_AYAT = r"^\(?(\d+)[\)\.]?\s*(.+)"

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        # Stop parsing saat bagian penutup dokumen
        if re.match(r"^Ditetapkan\s+di", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
            break

        # Normalisasi OCR ayat
        line = re.sub(r"^\(S(\d+)\)", r"(\1)", line)   # (S5) → (5)
        line = re.sub(r"^KM\)", "(4)", line)           # KM) → (4)

        # ===== DETEKSI BAB =====
        if re.match(r"^BAB\s+[IVXLC]+\s*$", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                buffer = []
                chunk_index += 1

            roman = re.findall(r"[IVXLC]+", line, re.I)[0]
            current_bab = roman_to_int(roman)
            kategori = extract_bab_title(lines, idx + 1)

            current_pasal = None
            current_ayat = None
            continue

        # ===== DETEKSI BAGIAN (DIABAIKAN UNTUK CHUNK AYAT) =====
        if re.match(r"^Bagian\s+", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                buffer = []
                chunk_index += 1
            current_ayat = None
            continue

        # ===== DETEKSI PASAL =====
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

        # ===== AWAL AYAT PERTAMA =====
        ayat_match = re.match(REGEX_AYAT, line)
        if ayat_match and current_ayat is None:
            num = int(ayat_match.group(1))

            # FIX KHUSUS OCR DOKUMEN 2023:
            # Awal pasal kadang terbaca (4) padahal (1)
            if num == 4:
                num = 1

            current_ayat = num
            buffer.append(ayat_match.group(2).strip())
            continue

        # ===== LANJUTAN AYAT / AYAT BARU =====
        if current_ayat is not None:
            ayat_match = re.match(REGEX_AYAT, line)

            if ayat_match:
                potential_num = int(ayat_match.group(1))
                content = ayat_match.group(2).strip()

                is_new_ayat = True

                # Heuristik OCR:
                if content and content[0].islower():
                    is_new_ayat = False

                if buffer:
                    last_line = buffer[-1].lower()
                    if last_line.endswith(("ayat", "huruf", "angka")):
                        is_new_ayat = False

                if potential_num <= current_ayat:
                    is_new_ayat = False

                if is_new_ayat:
                    save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                    buffer = []
                    chunk_index += 1
                    current_ayat = potential_num
                    buffer.append(content)
                else:
                    buffer.append(line)
            else:
                buffer.append(line)

    # Simpan ayat terakhir
    if buffer and current_ayat is not None:
        save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)

    return results


# =========================================================
# EKSEKUSI PIPELINE
# =========================================================
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw_text = f.read()

cleaned_text = clean_text(raw_text)
cleaned_text = remove_pembukaan(cleaned_text)

parsed_data = parse_document(cleaned_text)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(parsed_data, f, indent=2, ensure_ascii=False)

print(f"✅ Cleaning selesai. Output tersimpan di: {OUTPUT_FILE}")
