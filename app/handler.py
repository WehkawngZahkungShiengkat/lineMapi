import json
import os
import random
import string

from .connection import user_collection
from .settings import (
    alarm_alert, alarm_snooze, oven_fix, oven_error)

script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, 'alarm_noti_template.json')
with open(file_path, 'r') as f:
    data = json.load(f)


def password_generator(size=16, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


async def get_line_template(uid, msg, url):
    _return_payload = {
        "to": [
            uid
        ],
        "messages": [
            {
                "type": "flex",
                "altText": "My Account Menu Button",
                "contents": {
                    "type": "bubble",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "ยินดีต้อนรับสู่ AIIndustries",
                                "weight": "bold",
                                "size": "xl"
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "margin": "lg",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "baseline",
                                        "spacing": "sm",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": msg,
                                                "wrap": True,
                                                "color": "#666666",
                                                "size": "sm"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "height": "sm",
                                "action": {
                                    "type": "uri",
                                    "label": "My Account",
                                    "uri": url
                                },
                                "adjustMode": "shrink-to-fit"
                            },
                            {
                                "type": "spacer",
                                "size": "sm"
                            }
                        ],
                        "flex": 0
                    }
                }
            }
        ]
    }
    return _return_payload


async def get_related_template(posted_data):
    _status = posted_data.get("status")
    _oven = posted_data.get("oven")
    _msg = posted_data.get("msg")
    _ids_cursor = user_collection.find({"factory": posted_data.get("factory")})
    _ids = await _ids_cursor.to_list(length=100)
    _ids = [_id.get("line_id") for _id in _ids if _id.get("line_id")]
    _altTes = None
    _icon = None

    if _status == "alert":
        _icon = alarm_alert
        _altTes = _oven + " (แจ้งเตือน)"
    if _status == "snoozed":
        _icon = alarm_snooze
        _altTes = _oven + " (ต่อเวลาการแจ้งเตือน)"
    if _status == "monitoring":
        _icon = oven_fix
        _altTes = _oven + " (ได้ยุติการแจ้งเตือน)"
    if _status == "error":
        _icon = oven_error
        _altTes = _oven + " (ขัดข้อง)"

    _return_payload = {
        "to": _ids,
        "messages": [
            {
                "type": "flex",
                "altText": _altTes,
                "contents": {
                    "type": "bubble",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                    {
                                        "type": "icon",
                                        "url": _icon,
                                        "size": "4xl",
                                        "position": "relative"
                                    },
                                    {
                                        "type": "text",
                                        "text": _oven,
                                        "size": "xxl",
                                        "weight": "bold",
                                        "position": "relative",
                                        "offsetBottom": "xxl",
                                        "wrap": True,
                                        "align": "end"
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "separator"
                                    },
                                    {
                                        "type": "text",
                                        "text": _msg,
                                        "size": "lg",
                                        "wrap": True
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        ]
    }

    return _return_payload
