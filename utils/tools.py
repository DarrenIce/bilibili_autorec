# -*- coding: utf-8 -*-

import base64
import chardet
import functools
import hashlib
import json
import os
import platform
import random
import requests
import rsa
import shutil
import subprocess
import sys
import threading
import time
import toml
from multiprocessing import freeze_support, Manager, Pool, Process
from urllib import parse
from utils.log import Log

logger = Log()()


class Bilibili:
    app_key = "bca7e84c2d947ac6"

    def __init__(self, https=True, queue=None):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': "Mozilla/5.0 BiliDroid/6.4.0 (bbcallen@gmail.com) os/android model/M1903F11I mobi_app/android build/6040500 channel/bili innerVer/6040500 osVer/9.0.0 network/2"})
        self.__queue = queue
        self.get_cookies = lambda: self._session.cookies.get_dict(domain=".bilibili.com")
        self.get_csrf = lambda: self.get_cookies().get("bili_jct", "")
        self.get_sid = lambda: self.get_cookies().get("sid", "")
        self.get_uid = lambda: self.get_cookies().get("DedeUserID", "")
        self.access_token = ""
        self.refresh_token = ""
        self.username = ""
        self.password = ""
        self.info = {
            'ban': False,
            'coins': 0,
            'experience': {
                'current': 0,
                'next': 0,
            },
            'face': "",
            'level': 0,
            'nickname': "",
        }
        self.protocol = "https" if https else "http"
        self.proxy = None
        self.proxy_pool = set()

    def _requests(self, method, url, decode_level=2, enable_proxy=True, retry=10, timeout=15, **kwargs):
        if method in ["get", "post"]:
            for _ in range(retry + 1):
                try:
                    response = getattr(self._session, method)(url, timeout=timeout,
                                                              proxies=self.proxy if enable_proxy else None, **kwargs)
                    return response.json() if decode_level == 2 else response.content if decode_level == 1 else response
                except:
                    if enable_proxy:
                        self.set_proxy()
        return None

    def _solve_captcha(self, image):
        url = "https://bili.dev:2233/captcha"
        payload = {'image': base64.b64encode(image).decode("utf-8")}
        response = self._requests("post", url, json=payload)
        return response['message'] if response and response.get("code") == 0 else None

    def __push_to_queue(self, manufacturer, data):
        if self.__queue:
            self.__queue.put({
                'uid': self.get_uid(),
                'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                'manufacturer': manufacturer,
                'data': data,
            })

    @staticmethod
    def calc_sign(param):
        salt = "60698ba2f68e01ce44738920a0ffe768"
        sign_hash = hashlib.md5()
        sign_hash.update(f"{param}{salt}".encode())
        return sign_hash.hexdigest()

    def set_proxy(self, add=None):
        if isinstance(add, str):
            self.proxy_pool.add(add)
        elif isinstance(add, list):
            self.proxy_pool.update(add)
        if self.proxy_pool:
            proxy = random.sample(self.proxy_pool, 1)[0]
            self.proxy = {self.protocol: f"{self.protocol}://{proxy}"}
            # logger.info(f"使用{self.protocol.upper()}代理: {proxy}")
        else:
            self.proxy = None
        return self.proxy

    # 登录
    def login(self, **kwargs):
        def by_cookie():
            url = f"{self.protocol}://api.bilibili.com/x/space/myinfo"
            headers = {'Host': "api.bilibili.com"}
            response = self._requests("get", url, headers=headers)
            if response and response.get("code") != -101:
                logger.info("Cookie仍有效")
                return True
            else:
                logger.info("Cookie已失效")
                return False

        def by_token(force_refresh=False):
            if not force_refresh:
                param = f"access_key={self.access_token}&appkey={Bilibili.app_key}&ts={int(time.time())}"
                url = f"{self.protocol}://passport.bilibili.com/api/v2/oauth2/info?{param}&sign={self.calc_sign(param)}"
                response = self._requests("get", url)
                if response and response.get("code") == 0:
                    self._session.cookies.set('DedeUserID', str(response['data']['mid']), domain=".bilibili.com")
                    logger.info(
                        f"Token仍有效, 有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + int(response['data']['expires_in'])))}")
                    param = f"access_key={self.access_token}&appkey={Bilibili.app_key}&gourl={self.protocol}%3A%2F%2Faccount.bilibili.com%2Faccount%2Fhome&ts={int(time.time())}"
                    url = f"{self.protocol}://passport.bilibili.com/api/login/sso?{param}&sign={self.calc_sign(param)}"
                    self._requests("get", url, decode_level=0)
                    if all(key in self.get_cookies() for key in
                           ["bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", "SESSDATA"]):
                        logger.info("Cookie获取成功")
                        return True
                    else:
                        logger.info("Cookie获取失败")
            url = f"{self.protocol}://passport.bilibili.com/api/v2/oauth2/refresh_token"
            param = f"access_key={self.access_token}&appkey={Bilibili.app_key}&refresh_token={self.refresh_token}&ts={int(time.time())}"
            payload = f"{param}&sign={self.calc_sign(param)}"
            headers = {'Content-type': "application/x-www-form-urlencoded"}
            response = self._requests("post", url, data=payload, headers=headers)
            if response and response.get("code") == 0:
                for cookie in response['data']['cookie_info']['cookies']:
                    self._session.cookies.set(cookie['name'], cookie['value'], domain=".bilibili.com")
                self.access_token = response['data']['token_info']['access_token']
                self.refresh_token = response['data']['token_info']['refresh_token']
                logger.info(
                    f"Token刷新成功, 有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + int(response['data']['token_info']['expires_in'])))}")
                return True
            else:
                self.access_token = ""
                self.refresh_token = ""
                logger.info("Token刷新失败")
                return False

        def by_password():
            def get_key():
                url = f"{self.protocol}://passport.bilibili.com/api/oauth2/getKey"
                payload = {
                    'appkey': Bilibili.app_key,
                    'sign': self.calc_sign(f"appkey={Bilibili.app_key}"),
                }
                while True:
                    response = self._requests("post", url, data=payload)
                    if response and response.get("code") == 0:
                        return {
                            'key_hash': response['data']['hash'],
                            'pub_key': rsa.PublicKey.load_pkcs1_openssl_pem(response['data']['key'].encode()),
                        }
                    else:
                        time.sleep(1)

            while True:
                key = get_key()
                key_hash, pub_key = key['key_hash'], key['pub_key']
                url = f"{self.protocol}://passport.bilibili.com/api/v2/oauth2/login"
                param = f"appkey={Bilibili.app_key}&password={parse.quote_plus(base64.b64encode(rsa.encrypt(f'{key_hash}{self.password}'.encode(), pub_key)))}&username={parse.quote_plus(self.username)}"
                payload = f"{param}&sign={self.calc_sign(param)}"
                headers = {'Content-type': "application/x-www-form-urlencoded"}
                response = self._requests("post", url, data=payload, headers=headers)
                while True:
                    if response and response.get("code") is not None:
                        if response['code'] == -105:
                            url = f"{self.protocol}://passport.bilibili.com/captcha"
                            headers = {'Host': "passport.bilibili.com"}
                            response = self._requests("get", url, headers=headers, decode_level=1)
                            captcha = self._solve_captcha(response)
                            if captcha:
                                logger.info(f"登录验证码识别结果: {captcha}")
                                key = get_key()
                                key_hash, pub_key = key['key_hash'], key['pub_key']
                                url = f"{self.protocol}://passport.bilibili.com/api/v2/oauth2/login"
                                param = f"appkey={Bilibili.app_key}&captcha={captcha}&password={parse.quote_plus(base64.b64encode(rsa.encrypt(f'{key_hash}{self.password}'.encode(), pub_key)))}&username={parse.quote_plus(self.username)}"
                                payload = f"{param}&sign={self.calc_sign(param)}"
                                headers = {'Content-type': "application/x-www-form-urlencoded"}
                                response = self._requests("post", url, data=payload, headers=headers)
                            else:
                                logger.info(f"登录验证码识别服务暂时不可用, {'尝试更换代理' if self.proxy else '10秒后重试'}")
                                if not self.set_proxy():
                                    time.sleep(10)
                                break
                        elif response['code'] == -449:
                            logger.info("服务繁忙, 尝试使用V3接口登录")
                            url = f"{self.protocol}://passport.bilibili.com/api/v3/oauth2/login"
                            param = f"access_key=&actionKey=appkey&appkey={Bilibili.app_key}&build=6040500&captcha=&challenge=&channel=bili&cookies=&device=phone&mobi_app=android&password={parse.quote_plus(base64.b64encode(rsa.encrypt(f'{key_hash}{self.password}'.encode(), pub_key)))}&permission=ALL&platform=android&seccode=&subid=1&ts={int(time.time())}&username={parse.quote_plus(self.username)}&validate="
                            payload = f"{param}&sign={self.calc_sign(param)}"
                            headers = {'Content-type': "application/x-www-form-urlencoded"}
                            response = self._requests("post", url, data=payload, headers=headers)
                        elif response['code'] == 0 and response['data']['status'] == 0:
                            for cookie in response['data']['cookie_info']['cookies']:
                                self._session.cookies.set(cookie['name'], cookie['value'], domain=".bilibili.com")
                            self.access_token = response['data']['token_info']['access_token']
                            self.refresh_token = response['data']['token_info']['refresh_token']
                            logger.info("登录成功")
                            return True
                        else:
                            logger.info(f"登录失败 {response}")
                            return False
                    else:
                        logger.info(f"当前IP登录过于频繁, {'尝试更换代理' if self.proxy else '1分钟后重试'}")
                        if not self.set_proxy():
                            time.sleep(60)
                        break

        self._session.cookies.clear()
        for name in ["bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", "SESSDATA"]:
            value = kwargs.get(name)
            if value:
                self._session.cookies.set(name, value, domain=".bilibili.com")
        self.access_token = kwargs.get("access_token", "")
        self.refresh_token = kwargs.get("refresh_token", "")
        self.username = kwargs.get("username", "")
        self.password = kwargs.get("password", "")
        force_refresh_token = kwargs.get("force_refresh_token", False)
        if (not force_refresh_token or not self.access_token or not self.refresh_token) and all(
                key in self.get_cookies() for key in
                ["bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", "SESSDATA"]) and by_cookie():
            return True
        elif self.access_token and self.refresh_token and by_token(force_refresh_token):
            return True
        elif self.username and self.password and by_password():
            return True
        else:
            self._session.cookies.clear()
            return False


def detect_charset(file, fallback="utf-8"):
    with open(file, "rb") as f:
        detector = chardet.UniversalDetector()
        for line in f.readlines():
            detector.feed(line)
            if detector.done:
                return detector.result['encoding']
    return fallback


def login():
    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'conf', 'tool.toml')
    try:
        with open(config_file, "r", encoding=detect_charset(config_file)) as f:
            config = toml.load(f)
    except:
        print(f"无法加载{config_file}")
        return
    account = {}
    for line in config['user']['account'].splitlines():
        try:
            if line[0] == "#":
                continue
            for pair in line.strip(";").split(";"):
                if len(pair.split("=")) == 2:
                    key, value = pair.split("=")
                    account[key] = value
        except:
            pass
    bili = Bilibili(config['global']['https'])
    bili.login(force_refresh_token=config['user']['force_refresh_token'], **account)
    return bili.get_cookies()
