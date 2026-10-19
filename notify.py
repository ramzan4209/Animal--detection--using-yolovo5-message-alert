import requests
import config


def _set(value):
    return bool(value) and not value.startswith("your_") and "XXXX" not in value


def should_alert(counts):
    return counts.get("wild", 0) > 0


def build_message(counts, verdict=None):
    lines = ["WILDLIFE CORRIDOR ALERT"]
    lines.append(
        f"Humans: {counts['human']} | Domestic: {counts['domestic']} | Wild: {counts['wild']}"
    )
    if verdict and verdict.get("status") == "ok":
        lines.append(f"Claude check: {verdict.get('summary', '')}")
        lines.append(f"Risk: {verdict.get('risk_level', 'unknown').upper()}")
        if verdict.get("corrections"):
            lines.append(f"Correction: {verdict['corrections']}")
    else:
        lines.append("Claude check: not available")
    return "\n".join(lines)


def send_telegram(text, photo_path=None):
    token, chat = config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID
    if not (_set(token) and _set(chat)):
        return {"channel": "telegram", "status": "skipped"}
    base = f"https://api.telegram.org/bot{token}"
    try:
        if photo_path:
            with open(photo_path, "rb") as f:
                r = requests.post(
                    base + "/sendPhoto",
                    data={"chat_id": chat, "caption": text[:1000]},
                    files={"photo": f},
                    timeout=30,
                )
        else:
            r = requests.post(
                base + "/sendMessage",
                data={"chat_id": chat, "text": text},
                timeout=30,
            )
        if r.ok:
            return {"channel": "telegram", "status": "ok"}
        desc = r.json().get("description", "") if r.content else ""
        return {"channel": "telegram", "status": "error", "reason": f"{r.status_code} {desc}"}
    except Exception as e:
        return {"channel": "telegram", "status": "error", "reason": type(e).__name__}


def _twilio(channel, sender, to, text):
    sid, tok = config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN
    if not (_set(sid) and _set(tok) and _set(sender) and _set(to)):
        return {"channel": channel, "status": "skipped"}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        r = requests.post(
            url,
            auth=(sid, tok),
            data={"From": sender, "To": to, "Body": text[:1500]},
            timeout=30,
        )
        if r.ok:
            return {"channel": channel, "status": "ok"}
        return {"channel": channel, "status": "error", "reason": f"{r.status_code}"}
    except Exception as e:
        return {"channel": channel, "status": "error", "reason": type(e).__name__}


def send_whatsapp(text):
    return _twilio("whatsapp", config.TWILIO_WHATSAPP_FROM, config.ALERT_TO_WHATSAPP, text)


def send_sms(text):
    return _twilio("sms", config.TWILIO_SMS_FROM, config.ALERT_TO_SMS, text)


def notify_all(counts, verdict=None, photo_path=None):
    text = build_message(counts, verdict)
    return [
        send_telegram(text, photo_path),
        send_whatsapp(text),
        send_sms(text),
    ]


# ---- Voice call via CallMeBot (Telegram Voice Call) ----
import os


def send_call(text):
    user = os.getenv("CALLMEBOT_USER", "")
    if not _set(user):
        return {"channel": "call", "status": "skipped"}
    params = {"user": user, "text": text[:250], "rpt": 2}
    lang = os.getenv("CALLMEBOT_LANG", "")
    if lang:
        params["lang"] = lang
    try:
        r = requests.get("http://api.callmebot.com/start.php", params=params, timeout=90)
        if r.ok:
            return {"channel": "call", "status": "ok"}
        return {"channel": "call", "status": "error", "reason": str(r.status_code)}
    except Exception as e:
        return {"channel": "call", "status": "error", "reason": type(e).__name__}


def should_call(counts, verdict=None):
    if counts.get("wild", 0) == 0:
        return False
    if verdict and verdict.get("status") == "ok":
        return str(verdict.get("risk_level", "")).lower() == "high"
    return counts.get("human", 0) > 0 or counts.get("domestic", 0) > 0


def notify_all(counts, verdict=None, photo_path=None):
    text = build_message(counts, verdict)
    results = [
        send_telegram(text, photo_path),
        send_whatsapp(text),
        send_sms(text),
    ]
    if should_call(counts, verdict):
        spoken = (
            f"Wildlife alert. {counts['wild']} wild animals detected "
            f"with {counts['human']} humans and {counts['domestic']} domestic animals nearby."
        )
        results.append(send_call(spoken))
    return results


# ---- Voice call via CallMeBot (Telegram Voice Call) ----
import os


def send_call(text):
    user = os.getenv("CALLMEBOT_USER", "")
    if not _set(user):
        return {"channel": "call", "status": "skipped"}
    params = {"user": user, "text": text[:250], "rpt": 2}
    lang = os.getenv("CALLMEBOT_LANG", "")
    if lang:
        params["lang"] = lang
    try:
        r = requests.get("http://api.callmebot.com/start.php", params=params, timeout=90)
        if r.ok:
            return {"channel": "call", "status": "ok"}
        return {"channel": "call", "status": "error", "reason": str(r.status_code)}
    except Exception as e:
        return {"channel": "call", "status": "error", "reason": type(e).__name__}


def should_call(counts, verdict=None):
    if counts.get("wild", 0) == 0:
        return False
    if verdict and verdict.get("status") == "ok":
        return str(verdict.get("risk_level", "")).lower() == "high"
    return counts.get("human", 0) > 0 or counts.get("domestic", 0) > 0


def notify_all(counts, verdict=None, photo_path=None):
    text = build_message(counts, verdict)
    results = [
        send_telegram(text, photo_path),
        send_whatsapp(text),
        send_sms(text),
    ]
    if should_call(counts, verdict):
        spoken = (
            f"Wildlife alert. {counts['wild']} wild animals detected "
            f"with {counts['human']} humans and {counts['domestic']} domestic animals nearby."
        )
        results.append(send_call(spoken))
    return results


import threading as _threading

_orig_send_call = send_call


def send_call(text):
    _threading.Thread(target=_orig_send_call, args=(text,), daemon=True).start()
    return {"channel": "call", "status": "ok"}


def should_call(counts, verdict=None):
    return False
