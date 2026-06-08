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
            <script src="[[SERVER_HOST]]/get/https://cdn.jsdelivr.net/npm/pixi.js@8.19.0/dist/pixi.min.js"></script>
            <script>
                PIXI.sound = { disableAutoPause: true };
                PIXI.Sound = {
                    from() {
                        throw new Error("Sound is disabled in Live2D preview.");
                    }
                };
                PIXI.webaudio = { WebAudioMedia: class WebAudioMedia {} };
            </script>
            <script src="[[SERVER_HOST]]/get/https://cdn.jsdelivr.net/npm/untitled-pixi-live2d-engine@1.2.0/dist/index.min.js"></script>
            <style>
                html, body {margin:0; padding:0; overflow:hidden; height:100%; background-color: #F9FAFB;}
                #canvas {width:100vw; height:100vh; display:block; background-color: #F9FAFB;}
                #loading-ring {
                    position: fixed;
                    left: 50%;
                    top: 50%;
                    transform: translate(-50%, -50%);
                    width: 96px;
                    height: 96px;
                    display: none;
                    pointer-events: none;
                }
            </style>
        </head>
        <body>
            <canvas id="canvas"></canvas>
            <img id="loading-ring" src="[[SERVER_HOST]]/resources/ring.gif" alt="">
            <script>
            let app = null;
            let currentModel = null;

            let appInitPromise = null;
            const loadingRing = document.getElementById("loading-ring");

            function showLoadingRing() {
                loadingRing.style.display = "block";
            }

            function hideLoadingRing() {
                loadingRing.style.display = "none";
            }

            async function initializeApp() {
                if (!app) {
                    if (PIXI.live2d.config) {
                        PIXI.live2d.config.sound = false;
                    }

                    if (PIXI.extensions && PIXI.live2d.Live2DPlugin) {
                        PIXI.extensions.add(PIXI.live2d.Live2DPlugin);
                    }

                    app = new PIXI.Application();
                    appInitPromise = app.init({
                        canvas: document.getElementById("canvas"),
                        autoStart: true,
                        resizeTo: window,
                        preference: "webgl",
                        autoDensity: true,
                        resolution: window.devicePixelRatio,
                        transparent: true,
                        backgroundAlpha: 0
                    });
                    await appInitPromise;

                    window.addEventListener('resize', () => {
                        if (currentModel) {
                            currentModel.position.set(app.screen.width / 2, app.screen.height / 2);
                        }
                    });
                } else if (appInitPromise) {
                    await appInitPromise;
                }
            }

            function replaceLive2DModel(modelUrl) {
                (async function main() {
                    await initializeApp();

                    if (currentModel) {
                        app.stage.removeChild(currentModel);
                        currentModel.destroy();
                        currentModel = null;
                    }

                    showLoadingRing();
                    let model = null;

                    try {
                        model = await PIXI.live2d.Live2DModel.from(modelUrl, {
                            autoFocus: false,
                            autoHitTest: false,
                            breathDepth: 0.5
                        });
                    } finally {
                        hideLoadingRing();
                    }

                    app.stage.addChild(model);

                    model.anchor.set(0.5);
                    model.scale.set(0.25);

                    model.position.set(app.screen.width / 2, app.screen.height / 2);

                    currentModel = model;
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
