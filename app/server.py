import hashlib
import os

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
from urllib.parse import unquote
import json


def calculate_md5_string(text: str) -> str:
    md5_hash = hashlib.md5()
    md5_hash.update(text.encode('utf-8'))
    return md5_hash.hexdigest()


def calculate_md5_file(file_path: str) -> str:
    md5_hash = hashlib.md5()
    try:
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except FileNotFoundError:
        return ""


class FastAPIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 4521):
        self.host = host
        self.port = port
        self.app = self.create_app()
        self.config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
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
            caches = {}
            with open(cache_map_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(caches))
        else:
            with open(cache_map_path, "r", encoding="utf-8") as f:
                caches = json.loads(f.read())

        def update_cache_map():
            with open(cache_map_path, "w") as cache_map:
                cache_map.write(json.dumps(caches))

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        client = httpx.AsyncClient()

        async def sekai_viewer_get_without_cache(md5_url:str, url: str):
            headers = {"Accept-Encoding": "identity"}
            resp = await client.get(url, headers=headers)

            etag = calculate_md5_string(resp.text)

            with open(os.path.join("./cache/", f"{etag}.cache"), "wb") as cache_file:
                cache_file.write(resp.content)

            caches[md5_url] = etag

            update_cache_map()

            return Response(content=resp.text, status_code=resp.status_code, headers=resp.headers)

        @app.get("/get-md5/{url:path}")
        async def get_md5(url: str, _request: Request) -> Response:
            parsed_url = unquote(url)
            md5_url = calculate_md5_string(parsed_url)

            if md5_url not in caches.keys():
                return await sekai_viewer_get_without_cache(md5_url, url)
            else:
                etag = caches[md5_url]

                check_resp = await client.get(parsed_url, headers={
                    "If-None-Match": f'\"{etag}\"'
                })

                if check_resp.status_code == 304:
                    return FileResponse(os.path.join("./cache/", f"{etag}.cache"))
                else:
                    return await sekai_viewer_get_without_cache(md5_url, url)

        @app.get("/cache/{path:path}")
        async def get_cached_file(path: str, _request: Request):
            cache_file = os.path.join("./cache", path)

            if not os.path.isfile(cache_file):
                return Response(content=f"File {path} not found in cache", status_code=404)

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
