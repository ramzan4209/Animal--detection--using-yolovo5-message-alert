import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODEL_PATH = os.path.join(BASE_DIR, "yolov5s.onnx")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Detection settings
IMG_SIZE = 640
CONF_THRESHOLD = 0.40
IOU_THRESHOLD = 0.45

# COCO class groups (YOLOv5 pretrained model)
HUMAN_CLASSES = ["person"]
DOMESTIC_CLASSES = ["cow", "horse", "sheep", "dog", "cat"]
WILD_CLASSES = ["elephant", "bear", "zebra", "giraffe", "bird"]

# Upload settings
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_UPLOAD_MB = 10

# Claude cross-verification
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-5-5"

# Notifications
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")
ALERT_TO_WHATSAPP = os.getenv("ALERT_TO_WHATSAPP", "")
TWILIO_SMS_FROM = os.getenv("TWILIO_SMS_FROM", "")
ALERT_TO_SMS = os.getenv("ALERT_TO_SMS", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
