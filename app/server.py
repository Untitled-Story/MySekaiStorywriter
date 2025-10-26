import json
import os
import socket
import time
from threading import Thread
from urllib.parse import unquote_plus, quote_plus

import httpx
import mmh3
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response


def calculate_md5_string(text: str) -> str:
    r = mmh3.hash(text, 0, False)
    hs = str(hex(r))
    return hs[2:]


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


CACHE_DIR = "./cache/"
CACHE_MAP_PATH = os.path.join(CACHE_DIR, "cache_map.json")
CACHE_EXPIRE_SECONDS = 15 * 24 * 3600


class FastAPIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port or get_free_port()
        self.app = self.create_app()
        self.config = uvicorn.Config(
            app=self.app,
            host=host,
            port=self.port,
            log_level="info",
            workers=1,
            loop="asyncio",
        )
        self.server = uvicorn.Server(self.config)
        self.thread = None

    @staticmethod
    def create_app() -> FastAPI:
        app = FastAPI()
        os.makedirs(CACHE_DIR, exist_ok=True)

        if not os.path.exists(CACHE_MAP_PATH):
            caches = {}
            with open(CACHE_MAP_PATH, "w", encoding="utf-8") as f:
                f.write(json.dumps(caches))
        else:
            try:
                with open(CACHE_MAP_PATH, "r", encoding="utf-8") as f:
                    caches = json.load(f)
                if not isinstance(caches, dict):
                    raise ValueError("Invalid cache map structure")
            except (json.JSONDecodeError, ValueError):
                caches = {}
                with open(CACHE_MAP_PATH, "w", encoding="utf-8") as f:
                    f.write(json.dumps(caches))
                print("cache_map.json corrupted, recreated empty file.")

        def update_cache_map():
            with open(CACHE_MAP_PATH, "w", encoding="utf-8") as file:
                json.dump(caches, file, indent=2, ensure_ascii=False)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        client = httpx.AsyncClient(verify=False, timeout=10, limits=limits)

        def gen_cache(md5_url: str, resp: httpx.Response):
            etag = resp.headers.get("etag")
            if not etag:
                return
            etag = quote_plus(etag.split("\"")[1])
            file_path = os.path.join(CACHE_DIR, f"{etag}.cache")
            with open(file_path, "wb") as f:
                f.write(resp.content)
            caches[md5_url] = {"etag": etag, "timestamp": int(time.time())}
            update_cache_map()

        async def get_and_gen_cache(md5_url: str, url: str):
            headers = {"Accept-Encoding": "identity"}
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                gen_cache(md5_url, resp)
            return Response(content=resp.content, status_code=resp.status_code)

        @app.head("/get/{url:path}")
        async def get_head(url: str, _request: Request) -> Response:
            r = await client.head(url)
            return Response(headers=r.headers, status_code=r.status_code)

        @app.get("/get/{url:path}")
        async def get_with_cache(url: str, _request: Request) -> Response:
            parsed_url = unquote_plus(url)
            md5_url = calculate_md5_string(parsed_url)

            cache_entry = caches.get(md5_url)

            if cache_entry:
                etag_original = cache_entry["etag"]
                timestamp = cache_entry["timestamp"]
                cache_path = os.path.join(CACHE_DIR, f"{etag_original}.cache")

                if time.time() - timestamp < CACHE_EXPIRE_SECONDS and os.path.exists(cache_path):
                    print(f"Cache valid (within 15 days): {md5_url}")
                    return FileResponse(cache_path)

                etag_decoded = unquote_plus(etag_original)
                try:
                    check_resp = await client.get(parsed_url, headers={
                        "If-None-Match": f"\"{etag_decoded}\""
                    })
                except httpx.HTTPError:
                    print(f"HTTP error, using cache: {md5_url}")
                    return FileResponse(cache_path) if os.path.exists(cache_path) else await get_and_gen_cache(md5_url,
                                                                                                               url)

                if check_resp.status_code == 304:
                    caches[md5_url]["timestamp"] = int(time.time())
                    update_cache_map()
                    print(f"Cache refreshed (304): {md5_url}")
                    return FileResponse(cache_path)
                elif check_resp.status_code == 200:
                    os.remove(cache_path)
                    gen_cache(md5_url, check_resp)
                    return Response(content=check_resp.content, status_code=check_resp.status_code)
                else:
                    return Response(content=check_resp.content, status_code=502)

            return await get_and_gen_cache(md5_url, url)

        @app.get("/resources/{path:path}")
        async def get_cached_file(path: str, _request: Request):
            cache_file = os.path.join("./resources", path)
            if not os.path.isfile(cache_file):
                return Response(content=f"File {path} not found in resources", status_code=404)
            return FileResponse(cache_file)

        return app

    def start(self):
        self.thread = Thread(target=self.server.run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5.0)
