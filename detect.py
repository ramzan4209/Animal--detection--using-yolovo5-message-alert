import os
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw
import config

COCO = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]

COLORS = {"human": "red", "domestic": "green", "wild": "orange"}

session = ort.InferenceSession(config.MODEL_PATH, providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name


def group_of(label):
    if label in config.HUMAN_CLASSES:
        return "human"
    if label in config.DOMESTIC_CLASSES:
        return "domestic"
    if label in config.WILD_CLASSES:
        return "wild"
    return None


def letterbox(img, size):
    w, h = img.size
    r = min(size / w, size / h)
    nw, nh = int(round(w * r)), int(round(h * r))
    resized = img.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    px, py = (size - nw) // 2, (size - nh) // 2
    canvas.paste(resized, (px, py))
    return canvas, r, px, py


def nms(boxes, scores, thr):
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / (area_i + area_r - inter + 1e-9)
        order = rest[iou < thr]
    return keep


def detect(image_path):
    img = Image.open(image_path).convert("RGB")
    ow, oh = img.size
    canvas, r, px, py = letterbox(img, config.IMG_SIZE)

    arr = np.asarray(canvas, dtype=np.float32) / 255.0
    arr = arr.transpose(2, 0, 1)[None, ...]

    preds = session.run(None, {input_name: arr})[0][0]
    obj = preds[:, 4]
    cls_scores = preds[:, 5:]
    cls_ids = cls_scores.argmax(axis=1)
    conf = obj * cls_scores[np.arange(len(cls_ids)), cls_ids]

    mask = conf > config.CONF_THRESHOLD
    preds, conf, cls_ids = preds[mask], conf[mask], cls_ids[mask]

    detections = []
    if len(preds):
        cx, cy, w, h = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3]
        boxes = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)
        offset = cls_ids[:, None] * 4096.0
        keep = nms(boxes + offset, conf, config.IOU_THRESHOLD)

        for i in keep:
            label = COCO[int(cls_ids[i])]
            grp = group_of(label)
            if grp is None:
                continue
            x1 = float(np.clip((boxes[i, 0] - px) / r, 0, ow))
            y1 = float(np.clip((boxes[i, 1] - py) / r, 0, oh))
            x2 = float(np.clip((boxes[i, 2] - px) / r, 0, ow))
            y2 = float(np.clip((boxes[i, 3] - py) / r, 0, oh))
            detections.append({
                "label": label,
                "group": grp,
                "confidence": round(float(conf[i]), 3),
                "box": [round(x1), round(y1), round(x2), round(y2)],
            })

    counts = {"human": 0, "domestic": 0, "wild": 0}
    for d in detections:
        counts[d["group"]] += 1

    draw = ImageDraw.Draw(img)
    for d in detections:
        color = COLORS[d["group"]]
        draw.rectangle(d["box"], outline=color, width=4)
        draw.text((d["box"][0] + 4, d["box"][1] + 4),
                  f'{d["label"]} {d["confidence"]:.2f}', fill=color)
    base = os.path.splitext(os.path.basename(image_path))[0]
    annotated_path = os.path.join(config.UPLOAD_DIR, base + "_annotated.jpg")
    img.save(annotated_path, quality=90)

    return {
        "detections": detections,
        "counts": counts,
        "annotated_path": annotated_path,
    }
