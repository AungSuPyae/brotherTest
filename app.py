from flask import Flask, request, jsonify, render_template
import sqlite3
import whisper
import google.generativeai as genai
import json
import os

app = Flask(__name__)

# --- CONFIGURE GEMINI ---
genai.configure(api_key="AIzaSyCudgD8b3DQHHhoQ48U7Z1e7-BbWtc2ULg")
gemini_model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

ffmpeg_path = r"D:\Brother\ffmpeg\bin"
os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]

# --- DATABASE SETUP ---
def create_crm_table():
    conn = sqlite3.connect("dummy_crm.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crm_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT,
        clinic_name TEXT,
        date TEXT,
        contact_prefix TEXT,
        contact_surname TEXT,
        contact_first_name TEXT,
        product TEXT,
        quantity INTEGER,
        shipping_address TEXT,
        eircode TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def insert_crm_data(data):
    conn = sqlite3.connect("dummy_crm.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO crm_orders (
        employee_id, clinic_name, date, contact_prefix, contact_surname,
        contact_first_name, product, quantity, shipping_address, eircode
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['employee_id'], data['clinic_name'], data['date'],
        data['contact_prefix'], data['contact_surname'], data['contact_first_name'],
        data['product'], data['quantity'], data['shipping_address'], data['eircode']
    ))
    conn.commit()
    conn.close()

# --- WHISPER + GEMINI PIPELINE ---
def transcribe_audio(filepath):
    model = whisper.load_model("base")
    result = model.transcribe(filepath)
    return result['text']

def extract_crm_fields_gemini(text):
    prompt = f"""
    Extract the following fields from the transcript of a sales voice note and return them in JSON:
    - employee_id
    - clinic_name
    - date
    - contact_prefix
    - contact_surname
    - contact_first_name
    - product
    - quantity
    - shipping_address
    - eircode

    Transcript:
    \"\"\"{text}\"\"\"
    """
    response = gemini_model.generate_content(prompt)
    cleaned = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)

# --- ROUTES ---
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["audio"]
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filepath = os.path.join("uploads", file.filename)
    file.save(filepath)

    transcript = transcribe_audio(filepath)
    crm_data = extract_crm_fields_gemini(transcript)
    insert_crm_data(crm_data)

    return jsonify({"message": "Uploaded and processed", "transcript": transcript, "data": crm_data})

# --- START ---
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    create_crm_table()
    port = int(os.environ.get("PORT", 10000))  # Render provides this PORT
    app.run(host='0.0.0.0', port=port)
