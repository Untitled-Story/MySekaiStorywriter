from PySide6.QtCore import Signal
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qframelesswindow.webengine import FramelessWebEngineView


class Live2DWidget(QWidget):
    webview_loaded = Signal()

    def __init__(self, server_host: str, parent=None):
        super().__init__(parent)
        self.server_host = server_host

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.webview = FramelessWebEngineView(self)
        self.webview.setStyleSheet("background-color: #F9FAFB;")

        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        self.layout.addWidget(self.webview)

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <script src="[[SERVER_HOST]]/get/https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
            <script src="[[SERVER_HOST]]/get/https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js"></script>
            <script src="[[SERVER_HOST]]/get/https://cdn.jsdelivr.net/npm/pixi.js@7.4.3/dist/pixi.min.js"></script>
            <script src="[[SERVER_HOST]]/get/https://cdn.jsdelivr.net/npm/@pixi/gif@2.1.1/dist/pixi-gif.js"></script>
            <script src="[[SERVER_HOST]]/get/https://cdn.jsdelivr.net/npm/pixi-live2d-display-advanced/dist/index.min.js"></script>
            <style>
                html, body {margin:0; padding:0; overflow:hidden; height:100%; background-color: #F9FAFB;}
                #canvas {width:100vw; height:100vh; display:block; background-color: #F9FAFB;}
            </style>
        </head>
        <body>
            <canvas id="canvas"></canvas>
            <script>
            let app = null;
            let currentModel = null;
            let ring = null;

            function initializeApp() {
                if (!app) {
                    app = new PIXI.Application({
                        view: document.getElementById("canvas"),
                        autoStart: true,
                        resizeTo: window,
                        transparent: true,
                        backgroundAlpha: 0
                    });

                    window.addEventListener('resize', () => {
                        if (currentModel) {
                            currentModel.x = app.screen.width / 2;
                            currentModel.y = app.screen.height / 2;
                        }
                    });
                }
            }

            function replaceLive2DModel(modelUrl) {
                initializeApp();

                if (currentModel) {
                    app.stage.removeChild(currentModel);
                    currentModel = null;
                }

                (async function main() {
                    if (!ring) {
                        ring = await PIXI.Assets.load('[[SERVER_HOST]]/resources/ring.gif');
                    }
                
                    ring.anchor.set(0.5);
                    ring.x = app.screen.width / 2;
                    ring.y = app.screen.height / 2;
                    app.stage.addChild(ring);
                
                    const model = await PIXI.live2d.Live2DModel.from(modelUrl, {
                        autoFocus: false,
                        autoHitTest: false,
                        breathDepth: 0.5
                    });

                    app.stage.addChild(model);

                    model.anchor.set(0.5);
                    model.scale.set(0.25);

                    model.x = app.screen.width / 2;
                    model.y = app.screen.height / 2;

                    currentModel = model;
                    
                    app.stage.removeChild(ring);
                })();
            }
            </script>
        </body>
        </html>
        """.replace("[[SERVER_HOST]]", self.server_host)
        self.webview.setHtml(html)

        self.webview.loadFinished.connect(self.on_load_finished)

    def replace_model(self, model_url):
        self.webview.page().runJavaScript(f'replaceLive2DModel("{model_url}");')

    def on_load_finished(self):
        self.webview_loaded.emit()
