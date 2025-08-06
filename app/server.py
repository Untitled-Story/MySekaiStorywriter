import json
import os
import socket
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

class FastAPIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host

        if port == 0:
            self.port = get_free_port()
        else:
            self.port = port

        self.app = self.create_app()
        self.config = uvicorn.Config(
            app=self.app,
            host=host,
            port=self.port,
            log_level="info",
            workers=1,
            loop="asyncio"
        )
        self.server = uvicorn.Server(self.config)
        self.thread = None

    @staticmethod
    def create_app() -> FastAPI:
        app = FastAPI()
        cache_map_path = os.path.join("./cache/", "cache_map.json")

        if not os.path.exists(cache_map_path):

            os.makedirs(os.path.dirname(cache_map_path), exist_ok=True)

            caches = {}
            with open(cache_map_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(caches))
        else:
            with open(cache_map_path, "r", encoding="utf-8") as f:
                caches = json.loads(f.read())

        def update_cache_map():
            with open(cache_map_path, "w") as cache_map:
                cache_map.write(
                    json.dumps(caches, indent=2, ensure_ascii=False)
                )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        client = httpx.AsyncClient(verify=False)

        def gen_cache(md5_url: str, resp: httpx.Response):
            etag = resp.headers["etag"]

            etag = quote_plus(etag.split("\"")[1])

            with open(os.path.join("./cache/", f"{etag}.cache"), "wb") as cache_file:
                cache_file.write(resp.content)

            caches[md5_url] = etag

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

            if md5_url not in caches.keys():
                return await get_and_gen_cache(md5_url, url)
            else:
                etag_original = caches[md5_url]
                etag_decoded = unquote_plus(caches[md5_url])

                try:
                    check_resp = await client.get(parsed_url, headers={
                        "If-None-Match": f'\"{etag_decoded}\"'
                    }, timeout=5)
                except httpx.HTTPError:
                    print(f"Error, use cache: {md5_url}")
                    return FileResponse(os.path.join("./cache/", f"{etag_original}.cache"))

                if check_resp.status_code == 304:
                    print(f"Cache hit: {md5_url}")
                    return FileResponse(os.path.join("./cache/", f"{etag_original}.cache"))
                elif check_resp.status_code == 200:
                    os.remove(os.path.join("./cache/", f"{etag_original}.cache"))
                    gen_cache(md5_url, check_resp)
                    return Response(content=check_resp.content, status_code=check_resp.status_code)
                else:
                    return Response(content=check_resp.content, status_code=502)

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
