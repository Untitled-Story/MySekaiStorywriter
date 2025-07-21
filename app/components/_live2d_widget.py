from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qframelesswindow.webengine import FramelessWebEngineView


class Live2DWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.webview = FramelessWebEngineView(self)
        self.webview.setStyleSheet("background: white;")
        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.layout.addWidget(self.webview)

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Live2D Pixi.js WebView Example</title>
            <script src="http://127.0.0.1:4521/get-md5/https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
            <script src="https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/pixi.js@6.5.2/dist/browser/pixi.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/pixi-live2d-display/dist/index.min.js"></script>
            <style>
                html, body {margin:0; padding:0; overflow:hidden; height:100%; background: #f4fbfb;}
                #canvas {width:100vw; height:100vh; display:block; background: #f4fbfb;}
            </style>
        </head>
        <body>
            <canvas id="canvas"></canvas>
            <script>
            const cubism4Model =
                "http://127.0.0.1:4521/cache/v2_21miku_night/v2_21miku_night_t01.model3.json";
            
            (async function main() {
                const app = new PIXI.Application({
                    view: document.getElementById("canvas"),
                    autoStart: true,
                    resizeTo: document.getElementById("canvas"),
                    backgroundColor: 0xf4fbfb
                });
            
                const model4 = await PIXI.live2d.Live2DModel.from(cubism4Model);
            
                app.stage.addChild(model4);
                
                model4.anchor.set(0.5);
                model4.scale.set(0.25);
            
                model4.x = app.screen.width / 2;
                model4.y = app.screen.height / 2;
            })();
            </script>
        </body>
        </html>
        """
        self.webview.setHtml(html)
