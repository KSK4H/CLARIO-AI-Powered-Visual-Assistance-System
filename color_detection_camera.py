import cv2
import csv
import numpy as np
from gtts import gTTS
from datetime import datetime
import os

# ================= PATH SETUP ================= #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "color_ranges.csv")

# File system path (for saving audio)
AUDIO_DIR = os.path.join(BASE_DIR, "..", "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


# ================= LOAD COLOR RANGES (ONCE) ================= #
def load_color_ranges():
    ranges = []

    if not os.path.exists(CSV_PATH):
        print("❌ color_ranges.csv not found")
        return ranges

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                ranges.append({
                    "color": row["color"].strip().lower(),
                    "lower": np.array([
                        int(row["h_min"]),
                        int(row["s_min"]),
                        int(row["v_min"])
                    ], dtype=np.uint8),
                    "upper": np.array([
                        int(row["h_max"]),
                        int(row["s_max"]),
                        int(row["v_max"])
                    ], dtype=np.uint8)
                })
            except (ValueError, KeyError):
                continue  # safely skip bad rows

    return ranges


# Load once → fast & efficient
COLOR_RANGES = load_color_ranges()


# ================= COLOR DETECTION ================= #
def detect_color(frame):
    if frame is None or not COLOR_RANGES:
        return "unknown"

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    max_pixels = 0
    detected_color = "unknown"

    for r in COLOR_RANGES:
        mask = cv2.inRange(hsv, r["lower"], r["upper"])
        pixel_count = cv2.countNonZero(mask)

        if pixel_count > max_pixels:
            max_pixels = pixel_count
            detected_color = r["color"]

    # Noise rejection
    if max_pixels < 1500:
        return "unknown"

    # Normalize red shades
    if detected_color.startswith("red"):
        return "red"

    return detected_color


# ================= CAMERA WORKFLOW ================= #
def perform_color_detection():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        return "Camera not accessible", None

    captured_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.putText(
            frame,
            "Show object and press C",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv2.imshow("Color Detection", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("c"):
            captured_frame = frame.copy()
            break
        elif key == 27:  # ESC
            cap.release()
            cv2.destroyAllWindows()
            return "Cancelled", None

    cap.release()
    cv2.destroyAllWindows()

    # Detect color
    color = detect_color(captured_frame)

    if color == "unknown":
        text = "No clear color detected"
    else:
        text = f"The detected color is {color}"

    # ================= AUDIO GENERATION ================= #
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"color_{timestamp}.mp3"

    # Save path (filesystem)
    file_system_path = os.path.join(AUDIO_DIR, filename)

    # Web path (for HTML audio tag)
    web_audio_path = f"static/audio/{filename}"

    try:
        tts = gTTS(text=text, lang="en")
        tts.save(file_system_path)
    except Exception as e:
        print("❌ Audio error:", e)
        web_audio_path = None

    return text, web_audio_path
