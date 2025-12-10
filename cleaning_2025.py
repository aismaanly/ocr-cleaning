import re
import json

# =========================================================
# KONFIGURASI FILE
# =========================================================
INPUT_FILE = "output_ocr/Peraturan_Akademik_2025.txt"
OUTPUT_FILE = "output_cleaning/cleaning_peraturan_2025.json"

SOURCE_NAME = "Peraturan_Akademik_2025"
TAHUN_TERBIT = 2025
STATUS = "revisi"

# =========================================================
# CLEANING DASAR
# =========================================================
def clean_text(text: str) -> str:
    text = re.sub(r"[^\S\r\n]+", " ", text)                                 # spasi ganda
    text = text.replace("—", "-")                                           # em-dash
    text = re.sub(r"\n{3,}", "\n\n", text)                                  # enter beruntun ekstrem
    text = re.sub(r"^\(\s*[lI]\s*\)","(1)", text, flags=re.MULTILINE)       # OCR error (l) / (I) → (1) hanya di awal baris
    return text.strip()

# REMOVE PEMBUKA (DOKUMEN REVISI → LANGSUNG PASAL)
def remove_pembukaan(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^Pasal\s+\d+\s*$", line, re.I):
            return "\n".join(lines[i:])
    return text

# =========================================================
# UTIL
# =========================================================
def save_ayat(results, buffer, pasal, ayat, chunk_index):
    text = " ".join(buffer).strip()
    text = re.sub(r"^[\.\s]+", "", text)

    if not text:
        return

    results.append({
        "metadata": {
            "sumber": SOURCE_NAME,
            "bab": None,
            "pasal": pasal,
            "ayat": ayat,
            "tahun_terbit": TAHUN_TERBIT,
            "status": STATUS,
            "chunk_index": chunk_index,
            "kategori": ""
        },
        "page_content": text
    })


# =========================================================
# PARSER
# =========================================================
def parse_document(text: str) -> list[dict]:
    lines = text.split("\n")

    current_pasal = None
    current_ayat = None
    buffer = []

    results = []
    chunk_index = 1

    sudah_disimpan = False

    REGEX_AYAT = r"^\(?(\d+)[\)\.]?\s*(.+)"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # STOPPER 1: FOOTER
        if re.match(r"^Ditetapkan\s+di", line, re.I):
            is_footer = True
            if buffer:
                if not re.search(r"[.;]$", buffer[-1].strip()):
                    is_footer = False

            if is_footer:
                if buffer and current_ayat is not None:
                    save_ayat(results, buffer, current_pasal, current_ayat, chunk_index)
                sudah_disimpan = True
                break

        # STOPPER 2: PASAL ROMAWI (KETENTUAN AKHIR)
        if re.match(r"^Pasal\s+[IVX]+\s*$", line, re.I) and current_pasal is not None:
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_pasal, current_ayat, chunk_index)
            sudah_disimpan = True
            break

        # STOPPER 3: TRANSISI REVISI
        if re.match(r"^\d+\.\s+Ketentuan", line, re.I):
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_pasal, current_ayat, chunk_index)
            buffer = []
            current_ayat = None
            current_pasal = None
            continue

        # NORMALISASI OCR PENOMORAN AYAT
        line = re.sub(r"^\((S|H)?(\d+)\)", r"(\2)", line)
        line = re.sub(r"^\(H\)", "(4)", line)

        # PASAL (ANGKA ARAB SAJA)
        pasal_match = re.match(r"^Pasal\s+(\d+)\s*$", line, re.I)
        if pasal_match:
            if buffer and current_ayat is not None:
                save_ayat(results, buffer, current_pasal, current_ayat, chunk_index)
                buffer = []
                chunk_index += 1

            current_pasal = int(pasal_match.group(1))
            current_ayat = None
            continue

        # AYAT PERTAMA
        ayat_match = re.match(REGEX_AYAT, line)
        if ayat_match and current_ayat is None:
            current_ayat = int(ayat_match.group(1))
            buffer.append(ayat_match.group(2).strip())
            continue

        # LANJUTAN AYAT
        if current_ayat is not None:
            ayat_match = re.match(REGEX_AYAT, line)

            if ayat_match:
                potential_num = int(ayat_match.group(1))
                content = ayat_match.group(2).strip()

                is_new_ayat = True

                # Heuristik 1: huruf kecil
                if content and content[0].islower():
                    is_new_ayat = False

                # Heuristik 2: konteks hukum
                if buffer and buffer[-1].lower().endswith(("ayat", "huruf", "angka")):
                    is_new_ayat = False

                # Heuristik 3: nomor mundur / sama
                if potential_num <= current_ayat:
                    is_new_ayat = False

                # Heuristik 4: toleransi lompat max +2
                if potential_num > current_ayat + 2:
                    continue 

                if is_new_ayat:
                    save_ayat(results, buffer, current_pasal, current_ayat, chunk_index)
                    buffer = []
                    chunk_index += 1
                    current_ayat = potential_num
                    buffer.append(content)
                else:
                    buffer.append(line)
            else:
                buffer.append(line)

    if not sudah_disimpan and buffer and current_ayat is not None:
        save_ayat(results, buffer, current_pasal, current_ayat, chunk_index)

    return results

# =========================================================
# EKSEKUSI
# =========================================================
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw_text = f.read()

cleaned = clean_text(raw_text)
cleaned = remove_pembukaan(cleaned)
parsed = parse_document(cleaned)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2, ensure_ascii=False)

print("✅ Cleaning selesai. Output tersimpan di: ", OUTPUT_FILE)
