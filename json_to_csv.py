import json
import csv

# =========================================================
# KONFIGURASI FILE
# =========================================================
INPUT_FILE = "output_cleaning/cleaning_peraturan_2025.json"
OUTPUT_FILE = "output2025.csv" 

# =========================================================
# FUNGSI KONVERSI
# =========================================================
def json_to_csv(json_path, csv_path):
    # Baca file JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Tentukan header CSV dari metadata + page_content
    fieldnames = list(data[0]["metadata"].keys()) + ["page_content"]

    # Tulis CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            row = item["metadata"]
            row["page_content"] = item["page_content"]
            writer.writerow(row)

    print("✅ Konversi selesai! File CSV tersimpan di:", csv_path)

# =========================================================
# EKSEKUSI
# =========================================================
if __name__ == "__main__":
    json_to_csv(INPUT_FILE, OUTPUT_FILE)
