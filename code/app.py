from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import exifread
import os

# Flask app
app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel("gemini-1.5-flash")

# Upload folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_exif_location(filepath):
    """Extract GPS coordinates from image EXIF metadata."""
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f)

    def get_decimal_from_dms(dms, ref):
        degrees = float(dms[0].num) / float(dms[0].den)
        minutes = float(dms[1].num) / float(dms[1].den)
        seconds = float(dms[2].num) / float(dms[2].den)
        dec = degrees + minutes/60 + seconds/3600
        if ref in ['S', 'W']:
            dec = -dec
        return dec

    try:
        lat = get_decimal_from_dms(tags['GPS GPSLatitude'].values,
                                   tags['GPS GPSLatitudeRef'].values)
        lon = get_decimal_from_dms(tags['GPS GPSLongitude'].values,
                                   tags['GPS GPSLongitudeRef'].values)
        return lat, lon
    except Exception:
        return None, None

@app.route("/")
def index():
    return render_template("/index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Open image
    img = Image.open(filepath)

    # Ask Gemini about garbage
    response = model.generate_content(
        ["Does this image show garbage or waste? If yes, describe it briefly.", img]
    )
    result = response.text.strip()

    # Extract GPS metadata
    lat, lon = get_exif_location(filepath)

    if "yes" in result.lower():
        return jsonify({
            "status": "Garbage Detected",
            "description": result,
            "lat": lat,
            "lon": lon
        })
    else:
        return jsonify({
            "status": "No Garbage Found",
            "description": result,
            "lat": lat,
            "lon": lon
        })

if __name__ == "__main__":
    app.run(debug=True)
