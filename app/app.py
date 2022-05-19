import asyncio

from fastapi import FastAPI, Request, Response, status, HTTPException, Body

from fastapi.encoders import jsonable_encoder

from fastapi.logger import logger

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
from .connection import user_collection

from .handler import password_generator

import aiohttp as http

import redis

import json

import os

from fastapi.middleware.cors import CORSMiddleware

from .handler import get_related_template, get_line_template

from .settings import access_token, secret_key, aii_my_account_url, line_multicast, for_linked_line_id, for_new_line_id

script_dir = os.path.dirname(__file__)
file_path = os.path.join(script_dir, 'line_template.json')
with open(file_path, 'r') as f:
    data = json.load(f)

file_path = os.path.join(script_dir, 'alarm_noti_template.json')
with open(file_path, 'r') as f:
    alarm_noti = json.load(f)

file_path = os.path.join(script_dir, 'greeting.json')
with open(file_path, 'r') as f:
    greeting = json.load(f)

_r = redis.Redis()

session_timeout = http.ClientTimeout(total=60)
http_session = http.ClientSession(timeout=session_timeout)

app = FastAPI()

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_origin_regex='http?://.*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

line_bot_api = LineBotApi(access_token)
handler = WebhookHandler(secret_key)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/register/{user_id}/{random_code}")
async def user_registration(user_id, random_code):
    username = None
    checker = False
    otp = random_code
    user = await user_collection.find_one({"line_id": user_id})
    if user:
        username = user.get("user")
        checker = True
    return {"username": username, "checker": checker, "otp": otp, "uid": user_id}


@app.post("/register/{user_id}/{random_code}", status_code=409)
async def check_registration(user_id, random_code, response: Response, req = Body(...)):
    payload = jsonable_encoder(req)
    check = _r.get(user_id)
    check = check.decode("utf-8") if check else None
    if check == random_code:
        user = await user_collection.find_one({"user": payload["username"]})
        if user:
            if user.get("line_id") == user_id:
                update = await user_collection.update_one({"_id": user["_id"]}, {"$set": {"password": payload["password"]}})
                if update:
                    _r.delete(user_id)
                    response.status_code = status.HTTP_200_OK
                    return {"response": "Ok"}
                return {"response": "Error"}
            update = await user_collection.update_one({"_id": user["_id"]},
                                                      {"$set": {"line_id": user_id, "password": payload["password"]}})
            if update:
                _r.delete(user_id)
                response.status_code = status.HTTP_200_OK
                return "ok"
            return "Error"
    response.status_code = status.HTTP_401_UNAUTHORIZED
    return {"response": "Unauthorized"}


@app.post("/longan/oven/alert", status_code=200)
async def alarm_notification(response: Response, req = Body(...)):
    a = jsonable_encoder(req)
    a = json.loads(a)
    headers = {'content-type': 'application/json', "Authorization": f"Bearer {access_token}"}
    # to_post = get_related_temp(a)
    to_post = await get_related_template(a)
    # to_post["to"] = ["Ue264f1475f688a0104f2e087ac52a226"]
    to_post = json.dumps(to_post)
    async with http_session.post(line_multicast, data=to_post, headers=headers) as resp:
        if resp.status == 200:
            print("Message send successful.")
        else:
            print(resp.status)
            print(resp)
    pass


@app.post("/webhook", status_code=200)
async def webhook(request: Request):
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    _json = await request.json()
    _body = await request.body()
    _body = _body.decode("utf-8")

    logger.info("Request body: " + _body)
    try:
        handler.handle(_body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        raise HTTPException(status_code=400)

    return "rich_menu_list"


async def _myaccount_response(userid, otp, e_type, text):
    unique_url = aii_my_account_url + f"/{userid}/{otp}"
    headers = {'content-type': 'application/json', "Authorization": f"Bearer {access_token}"}

    # todo: the type option are [message , follow].
    #  Option "follow" - which can only receive when new user add the official account.
    if e_type == "message":
        user = await user_collection.find_one({"line_id": userid})
        if user:
            resp_text = for_linked_line_id
        else:
            resp_text = for_new_line_id
        if text == "myaccount@aiindustries":
            to_post = await get_line_template(userid,resp_text,unique_url)
            to_post = json.dumps(to_post)
            async with http_session.post(line_multicast, data=to_post, headers=headers) as resp:
                if resp == "200":
                    print("ok")
    elif e_type == "follow":
        to_post = alarm_noti
        to_post["to"] = [userid]
        to_post = json.dumps(to_post)
        async with http_session.post(line_multicast, data=to_post, headers=headers) as resp:
            if resp == "200":
                pass
    print(_r.get(userid))


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    pre_get_userid = str(event.source)
    pre_get_userid = json.loads(pre_get_userid)
    userid = pre_get_userid.get("userId")
    e = event
    e_type = e.type
    text_received = None
    if e_type == "message":
        message = str(e.message)
        message = json.loads(message)
        text_received = message.get("text")
    # return (userid, e_type)
    # todo: generate otp
    otp = password_generator()
    _r.set(userid, otp)
    asyncio.create_task(_myaccount_response(userid, otp, e_type, text_received))


    # userIds.append(userId)
    # line_bot_api.broadcast(TextSendMessage(text="aiindustries.3bbddns.com:48815"))
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     TextSendMessage(text="aiindustries.3bbddns.com:48815"))
        # TextSendMessage(text=event.message.text))
