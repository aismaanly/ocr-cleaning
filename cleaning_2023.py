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
# CLEANING DASAR
# =========================================================
def clean_text(text: str) -> str:
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = text.replace("—", "-")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\(\s*[lI]\s*\)\s+(?=[A-Za-z])","(1) ", text, flags=re.MULTILINE)
    return text.strip()

# REMOVE PEMBUKA
def remove_pembukaan(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.search(r"\bBAB\s+[IVXLC]+\b", line, re.I):
            return "\n".join(lines[i:])
    return text

# =========================================================
# UTIL
# =========================================================
def roman_to_int(roman: str) -> int:
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    total = prev = 0
    for c in roman.upper()[::-1]:
        curr = values.get(c, 0)
        total += -curr if curr < prev else curr
        prev = curr
    return total

def save_ayat(results, buffer, bab, pasal, ayat, chunk_index, kategori):
    text = " ".join(buffer).strip()
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
# PARSER
# =========================================================
def parse_document(text: str) -> list[dict]:
    lines = text.split("\n")

    current_bab = None
    current_pasal = None
    current_ayat = None
    kategori = ""

    buffer = []
    results = []
    chunk_index = 1

    sudah_disimpan = False

    REGEX_AYAT = r"^\(\s*(\d+)\s*\)\s*(.*)"
    REGEX_AYAT_DOT = r"^(\d+)\.\s+(.*)"
    REGEX_DEFINISI = r"^(\d+)\.\s*(.*)"

    collecting_kategori = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # STOPPER FOOTER
        if re.match(r"^Ditetapkan\s+di", line, re.I):
            is_footer = True
            if buffer:
                if not re.search(r"[.;:]$", buffer[-1].strip()):
                    is_footer = False

            if is_footer and buffer and current_ayat is not None and not sudah_disimpan:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                sudah_disimpan = True
            break

        # NORMALISASI OCR
        line = re.sub(r"^\(\s*[sS]\s*(\d+)\s*\)", r"(\1)", line)
        line = re.sub(r"^\(\s*(\d+)\s*[sS]\s*\)", r"(\1)", line)
        line = re.sub(r"^\(\s*(\d+)\s+(?=\S)", r"(\1) ", line)
        line = re.sub(r"^KM\)", "(4)", line)
        line = re.sub(r"^8\.\s+(?=[a-z])", "g. ", line)

        # BAB
        if re.match(r"^BAB\s+[IVXLC]+\s*$", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                chunk_index += 1

            buffer = []
            roman = re.findall(r"[IVXLC]+", line, re.I)[0]
            current_bab = roman_to_int(roman)
            current_pasal = None
            current_ayat = None
            sudah_disimpan = False

            kategori = ""
            collecting_kategori = True
            continue

        # KATEGORI BAB
        if collecting_kategori:
            if re.match(r"^(Pasal\s+\d+|Bagian\s+)", line, re.I):
                collecting_kategori = False
            else:
                if line.strip():
                    kategori = (kategori + " " + line.strip()).strip()
                continue

        kategori = kategori.lower()

        # PASAL
        pasal_match = re.match(r"^Pasal\s+(\d+)\s*$", line, re.I)
        if pasal_match:
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                chunk_index += 1

            buffer = []
            current_pasal = int(pasal_match.group(1))
            current_ayat = None
            sudah_disimpan = False
            continue

        # KHUSUS PASAL 1
        if current_pasal == 1 and re.match(
            r"Dalam\s+Peraturan\s+Rektor\s+ini\s+yang\s+dimaksud\s+dengan\s*:",
            line,
            re.I
        ):
            continue

        if current_pasal == 1:
            definisi_match = re.match(REGEX_DEFINISI, line)
            if definisi_match:
                nomor = int(definisi_match.group(1))
                isi = definisi_match.group(2)

                if current_ayat is not None:
                    save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                    chunk_index += 1

                current_ayat = nomor
                buffer = [isi]
                continue

        if current_pasal == 1:
            koma_def = re.match(r"^(\d+)\s*,\s*(.*)", line)
            if koma_def:
                nomor = int(koma_def.group(1))
                isi = koma_def.group(2).strip()

                if current_ayat is not None:
                    save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                    chunk_index += 1

                current_ayat = nomor
                buffer = [isi]
                continue

        # AYAT (FORMAT (1))
        ayat_match = re.match(REGEX_AYAT, line)
        if ayat_match:
            num = int(ayat_match.group(1))
            content = ayat_match.group(2).strip()

            if current_ayat is None and num != 1:
                num = 1

            if current_ayat is not None and num < current_ayat:
                buffer.append(line)
                continue

            if content.lower().startswith("di atas"):
                buffer.append(line)
                continue

            if content == "" and len(line) < 6:
                buffer.append(line)
                continue

            if current_ayat is not None:
                save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                chunk_index += 1

            current_ayat = num
            buffer = [content]
            sudah_disimpan = False
            continue

        # huruf a, b, c 
        if re.match(r"^[abc]\.\s+", line, re.I):
            buffer.append(line)
            continue

        # ============================================
        # sub poin (1., 2., 3.)  → PERBAIKAN PASAL 2
        # ============================================
        ayat_dot_match = re.match(REGEX_AYAT_DOT, line)
        if ayat_dot_match:
            num = int(ayat_dot_match.group(1))
            content = ayat_dot_match.group(2).strip()

            if current_ayat is None:
                current_ayat = num
                buffer = [content]
                sudah_disimpan = False

            else:
                if num > current_ayat:
                    save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)
                    chunk_index += 1
                    current_ayat = num
                    buffer = [content]
                    sudah_disimpan = False
                else:
                    buffer.append(line)

            continue

        # PASAL TANPA AYAT
        if current_pasal is not None and current_ayat is None:
            current_ayat = 1
            buffer = [line]
            sudah_disimpan = False
            continue

        # LANJUTAN AYAT
        if current_ayat is not None:
            buffer.append(line)

    if buffer and current_ayat is not None and not sudah_disimpan:
        save_ayat(results, buffer, current_bab, current_pasal, current_ayat, chunk_index, kategori)

    return results

# =========================================================
# UBAH KE JSON
# =========================================================
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw = f.read()

cleaned = clean_text(raw)
cleaned = remove_pembukaan(cleaned)
parsed = parse_document(cleaned)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2, ensure_ascii=False)

print("✅ Cleaning selesai! Output tersimpan di: →", OUTPUT_FILE)
