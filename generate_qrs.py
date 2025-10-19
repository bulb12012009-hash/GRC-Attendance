import pandas as pd
import qrcode
import os

# --- Configuration ---
CSV_FILE = 'students.csv'
OUTPUT_FOLDER = 'qrcodes'
# ---------------------

def generate_qr_codes():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created directory: {OUTPUT_FOLDER}")
    try:
        df = pd.read_csv(CSV_FILE)
        if 'GRC_ID' not in df.columns or 'Name' not in df.columns:
            print("Error: CSV file must contain 'GRC_ID' and 'Name' columns.")
            return
        for index, row in df.iterrows():
            grc_id = str(row['GRC_ID']).strip()
            name = str(row['Name']).strip()
            if not grc_id or not name:
                print(f"Skipping row {index+1} due to missing data.")
                continue
            safe_filename = "".join(c for c in name if c.isalnum() or c in (' ', '_')).rstrip()
            filename = f"{OUTPUT_FOLDER}/{safe_filename}_{grc_id}.png"
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(grc_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(filename)
        print(f"\nSuccessfully generated {len(df)} QR codes in the '{OUTPUT_FOLDER}' folder.")
    except FileNotFoundError:
        print(f"Error: The file '{CSV_FILE}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    generate_qr_codes()
