import asyncio
import json
import os
import shutil
import uuid
from collections import OrderedDict
from pathlib import Path

import httpx
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy, QListWidgetItem, QFileDialog, \
    QLabel
from httpx_retries import RetryTransport, Retry
from qfluentwidgets import TransparentToolButton, FluentIcon, ListWidget, PushButton, FlowLayout

from app.components import SnippetPropertiesWidget, SaveFileMessageBox
from app.data_model import MetaData
from app.snippets import SNIPPETS, BaseSnippet, get_snippet, LayoutModes, Sides, MoveSpeed
from app.utils import HTTP_HEADERS, extract_url_path, get_motions, to_ordered_dict


class BuildStoryThread(QThread):
    built = Signal(OrderedDict, str)

    def __init__(self, file_path: str, metadata: MetaData, snippets: list[BaseSnippet], parent):
        super().__init__(parent)
        self.snippets = snippets
        self.file_path = file_path
        self.metadata = metadata
        self.models = metadata.models
        self.base_path = os.path.dirname(self.file_path)
        self.retry = Retry(total=10, backoff_factor=0.5)
        self.client = httpx.Client(headers=HTTP_HEADERS, transport=RetryTransport(retry=self.retry))

    def cancel(self):
        self.terminate()
        print('Canceled')
        for model in [model for model in self.models if model['downloaded'] == False]:
            model_path = os.path.join(
                self.base_path,
                'models',
                model['model_name'],
            )

            if not os.path.exists(model_path):
                continue

            print(f'Remove downloaded: {model_path}')
            shutil.rmtree(model_path)

    def download(self, path: str, filename: str, url: str) -> bytes:
        full_path = os.path.join(path, filename)
        with open(full_path, "wb+") as file:
            resp = self.client.get(url)
            file.write(resp.content)
            return resp.content

    @staticmethod
    def gen_motion_urls(motions_result: dict) -> list:
        result = []

        asset_url_base = motions_result["asset_url_base"]
        motion_base_path = motions_result["motionBasePath"]
        if motion_base_path:
            motion_base_url = f"{asset_url_base}/motion/{motion_base_path}"

            for motion in motions_result["motions"]:
                result.append(f"{motion_base_url}/motion/{motion}.motion3.json")
            for expression in motions_result["facials"]:
                result.append(f"{motion_base_url}/facial/{expression}.motion3.json")

        if motions_result["model_path"]:
            additional_motion_url = f"{asset_url_base}/model/{motions_result['model_path']}/motions"
            for motion in motions_result["additionalMotions"]:
                result.append(f"{additional_motion_url}/{motion}.motion3.json")

        return result

    @staticmethod
    async def download_motion_and_save(client: httpx.AsyncClient, url: str, motion_path: str, main_data: dict):
        r = await client.get(url)
        m_file_name_ext = os.path.basename(r.url.path)
        m_file_name = m_file_name_ext.split('.motion3.json')[0]
        file_path = os.path.join(motion_path, m_file_name_ext)
        main_data["FileReferences"]["Motions"][m_file_name] = [{
            "FadeInTime": 0.5,
            "FadeOutTime": 0.5,
            "File": f"motions/{m_file_name_ext}"
        }]
        with open(file_path, "wb") as file:
            file.write(r.content)

    async def download_motions(self, urls: list, motion_path: str, main_data: dict):
        async with httpx.AsyncClient(headers=HTTP_HEADERS, transport=RetryTransport(retry=self.retry)) as client:
            tasks = [self.download_motion_and_save(client, url, motion_path, main_data) for url in urls]
            await asyncio.gather(*tasks)

    def run(self):
        models_data = []
        for model in self.models:
            print(f"Saving: {model}")
            suffix = '.model3.json' if model['version'] == 3 else '.model.json'

            rel_model_path = str(os.path.join(
                model['model_name'],
                model['model_name'] + suffix
            )).replace("\\", "/")

            model_path = os.path.join(
                self.base_path,
                'models',
                rel_model_path
            )

            model_dir = os.path.dirname(model_path)
            file_name = os.path.basename(model_path)

            models_data.append({
                "id": model['id'],
                "model": rel_model_path,
                "normal_scale": round(model['normal_scale'], 2),
                "small_scale": round(model['small_scale'], 2),
                "anchor": round(model['anchor'], 2),
            })

            if not model['downloaded']:
                if os.path.exists(model_path):
                    print(f"{model_path} already exists, skipping.")
                    model['downloaded'] = True
                    continue

                os.makedirs(model_dir, exist_ok=True)
                base_url = extract_url_path(model['path'])

                main = self.download(
                    model_dir,
                    file_name,
                    model['path']
                ).decode('utf-8')

                main_data = json.loads(main)
                for file_type in main_data['FileReferences'].keys():
                    if file_type == 'Moc' or file_type == 'Physics':
                        path = os.path.join(model_dir, main_data['FileReferences'][file_type])
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        self.download(
                            os.path.dirname(path),
                            main_data['FileReferences'][file_type],
                            base_url + main_data['FileReferences'][file_type]
                        )
                    elif file_type == 'Textures':
                        for texture in main_data['FileReferences'][file_type]:
                            path = os.path.join(model_dir, texture)
                            os.makedirs(os.path.dirname(path), exist_ok=True)
                            self.download(
                                os.path.dirname(path),
                                os.path.basename(texture),
                                base_url + texture
                            )

                urls = []

                motions_result = get_motions(model['path'])

                urls.extend(self.gen_motion_urls(motions_result))

                motion_path = os.path.join(model_dir, 'motions')
                os.makedirs(motion_path, exist_ok=True)

                main_data["FileReferences"]["Motions"] = {}
                for i in range(0, len(urls), 50):
                    chunk = urls[i:i + 50]
                    asyncio.run(
                        self.download_motions(chunk, motion_path, main_data)
                    )

                with open(model_path, "w+") as file:
                    file.write(json.dumps(main_data, indent=2, ensure_ascii=False))

                model['downloaded'] = True
            else:
                if os.path.exists(model_path):
                    print(f"{model_path} already exists, skipping.")
                    continue

                shutil.copytree(os.path.dirname(model['path']), model_dir, dirs_exist_ok=True)

        images_data = []
        image_dir = os.path.join(self.base_path, 'images')
        os.makedirs(image_dir, exist_ok=True)
        for image in self.metadata.images:
            file_name_ext = os.path.basename(image['path'])
            img_path = os.path.join(image_dir, file_name_ext)
            if os.path.exists(img_path):
                print(f"{img_path} already exists, skipping.")
            else:
                shutil.copy(image['path'], img_path)
            images_data.append({
                "id": image['id'],
                "image": f'{file_name_ext}'
            })

        os.makedirs(os.path.join(self.base_path, 'voices'), exist_ok=True)

        snippets_data = []
        for snippet in self.snippets:
            data = snippet.build()
            if 'data' in data:
                if 'voice' in data['data'] and data['data']['voice']:
                    voice_path = Path(data['data']['voice'])

                    if voice_path.parent == Path(os.path.abspath(os.path.join(self.base_path, 'voices/'))):
                        print(f'{voice_path} already exists, skipping.')
                        data['data']['voice'] = voice_path.name
                    else:
                        new_voice_name = f'{str(uuid.uuid4().hex)}{voice_path.suffix}'
                        new_voice_path = os.path.abspath(
                            os.path.join(self.base_path, 'voices', new_voice_name)
                        )
                        shutil.copy(voice_path, new_voice_path)
                        data['data']['voice'] = new_voice_name
                        snippet.set_property('data.voice', new_voice_path)

            snippets_data.append(data)

        self.built.emit(to_ordered_dict({
            '$schema': 'https://raw.githubusercontent.com/Untitled-Story/MySekaiStoryteller/refs/heads/master/sekai-story.schema.json',
            'models': models_data,
            'images': images_data,
            'snippets': snippets_data,
        }), self.file_path)


PRIMARY_SNIPPETS = {"Talk", "Motion", "Move", "LayoutAppear"}


class MainView(QFrame):
    def __init__(self, metadata: MetaData, server_host: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('MainView')

        self.server_host = server_host
        self.meta_data = metadata
        self.meta_data.model_updated.connect(self._on_model_update)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        toolbar_frame = QFrame(self)
        toolbar_frame.setObjectName("editorToolbar")
        toolbar_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        top_layout = QHBoxLayout(toolbar_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)
        self._main_layout.addWidget(toolbar_frame)

        snippets = [snippet_type.type for snippet_type in SNIPPETS]

        snippets_panel = QFrame(toolbar_frame)
        snippets_panel.setObjectName("snippetsPanel")
        snippets_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        snippets_panel_layout = QVBoxLayout(snippets_panel)
        snippets_panel_layout.setContentsMargins(0, 0, 0, 0)
        snippets_panel_layout.setSpacing(6)

        snippets_title = QLabel("Snippets", snippets_panel)
        snippets_title.setObjectName("toolbarSectionTitle")
        snippets_title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        snippets_panel_layout.addWidget(snippets_title)

        snippets_widget = QFrame(self)
        snippets_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        snippets_flow_layout = FlowLayout(snippets_widget, needAni=False, isTight=False)
        snippets_flow_layout.setContentsMargins(0, 0, 0, 0)
        snippets_flow_layout.setHorizontalSpacing(6)
        snippets_flow_layout.setVerticalSpacing(6)

        for snippet_type in snippets:
            snippet_button = PushButton(text=snippet_type, parent=snippets_widget)
            snippet_button.setObjectName("snippetChip")
            snippet_button.setProperty("tone", "primary" if snippet_type in PRIMARY_SNIPPETS else "neutral")
            snippet_button.setToolTip(f"Add {snippet_type}")
            snippet_button.setCursor(Qt.CursorShape.PointingHandCursor)
            snippet_button.setFixedHeight(28)
            snippet_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            snippet_button.clicked.connect(lambda _, t=snippet_type: self._add_snippet(t))
            snippets_flow_layout.addWidget(snippet_button)

        snippets_panel_layout.addWidget(snippets_widget)

        controls_widget = QFrame(toolbar_frame)
        controls_widget.setObjectName("actionCluster")
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(6, 6, 6, 6)
        controls_layout.setSpacing(4)
        controls_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        up_button = TransparentToolButton(FluentIcon.UP, parent=self)
        up_button.setObjectName("toolbarIconButton")
        up_button.setFixedSize(34, 34)
        up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        up_button.setToolTip("Move up")
        up_button.clicked.connect(self._on_up_clicked)
        down_button = TransparentToolButton(FluentIcon.DOWN, parent=self)
        down_button.setObjectName("toolbarIconButton")
        down_button.setFixedSize(34, 34)
        down_button.setCursor(Qt.CursorShape.PointingHandCursor)
        down_button.setToolTip("Move down")
        down_button.clicked.connect(self._on_down_clicked)
        delete_button = TransparentToolButton(FluentIcon.DELETE, parent=self)
        delete_button.setObjectName("toolbarIconButton")
        delete_button.setFixedSize(34, 34)
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_button.setToolTip("Delete")
        delete_button.clicked.connect(self._on_delete_clicked)
        copy_button = TransparentToolButton(FluentIcon.COPY, parent=self)
        copy_button.setObjectName("toolbarIconButton")
        copy_button.setFixedSize(34, 34)
        copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_button.setToolTip("Copy")
        copy_button.clicked.connect(self._on_copy_clicked)

        def add_action_divider() -> None:
            divider = QFrame(controls_widget)
            divider.setObjectName("toolbarDivider")
            divider.setFixedSize(1, 22)
            controls_layout.addWidget(divider)

        controls_layout.addWidget(up_button)
        controls_layout.addWidget(down_button)
        add_action_divider()
        controls_layout.addWidget(delete_button)
        controls_layout.addWidget(copy_button)
        add_action_divider()

        load_button = TransparentToolButton(FluentIcon.FOLDER, parent=self)
        load_button.setObjectName("toolbarIconButton")
        load_button.setFixedSize(34, 34)
        load_button.setCursor(Qt.CursorShape.PointingHandCursor)
        load_button.setToolTip("Load")
        load_button.clicked.connect(self._on_load_clicked)
        controls_layout.addWidget(load_button)

        save_button = TransparentToolButton(FluentIcon.SAVE, parent=self)
        save_button.setObjectName("toolbarIconButton")
        save_button.setFixedSize(34, 34)
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setToolTip("Save")
        save_button.clicked.connect(self._on_save_clicked)
        controls_layout.addWidget(save_button)

        controls_widget.adjustSize()
        controls_widget.setMinimumWidth(controls_widget.sizeHint().width())

        top_layout.addWidget(snippets_panel, 1)
        top_layout.addWidget(controls_widget, 0, Qt.AlignmentFlag.AlignTop)

        self.setStyleSheet("""
            QFrame#editorToolbar {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px 12px;
            }

            QFrame#snippetsPanel {
                background: transparent;
                border: none;
            }

            QLabel#toolbarSectionTitle {
                color: #64748B;
                font-size: 12px;
                font-weight: 600;
                padding-left: 2px;
            }

            QPushButton#snippetChip {
                background: #FFFFFF;
                border: 1px solid #D7DFEA;
                border-radius: 6px;
                color: #1F2937;
                font-size: 12px;
                font-weight: 500;
                padding: 2px 9px;
            }

            QPushButton#snippetChip:hover {
                background: #F2F6FB;
                border-color: #B8C5D6;
            }

            QPushButton#snippetChip:pressed {
                background: #E7EDF5;
            }

            QPushButton#snippetChip[tone="primary"] {
                background: #E8F7FA;
                border-color: #A6DAE2;
                color: #075B66;
            }

            QPushButton#snippetChip[tone="primary"]:hover {
                background: #DDF2F6;
                border-color: #76C8D4;
            }

            QFrame#actionCluster {
                background: #FFFFFF;
                border: 1px solid #DDE5EF;
                border-radius: 8px;
            }

            #toolbarIconButton {
                border-radius: 6px;
            }

            #toolbarIconButton:hover {
                background: #EEF3F8;
            }

            #toolbarIconButton:pressed {
                background: #E2EAF3;
            }

            QFrame#toolbarDivider {
                background: #D9E1EC;
                border: none;
            }
        """)

        # Center
        center_layout = QHBoxLayout()
        self._main_layout.addLayout(center_layout)

        central_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout.addWidget(central_splitter)

        # Left list
        self._list_widget = ListWidget()
        self._list_widget.itemClicked.connect(self._on_snippet_selected)
        central_splitter.addWidget(self._list_widget)

        # Center
        # live2d_widget = Live2DWidget()
        # central_splitter.addWidget(live2d_widget)

        # Right
        self._property_widget = SnippetPropertiesWidget(self)
        central_splitter.addWidget(self._property_widget)

        # Final
        central_splitter.setSizes([150, 500, 250])

        self.current_snippets: list[BaseSnippet] = []

        self.need_update = False
        self.save_message_box = None

    def _renumber_snippets(self) -> None:
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            snippet = self.current_snippets[i]
            item.setText(f"{snippet.type} #{i + 1}")

    def _on_model_update(self):
        self.need_update = True

    def showEvent(self, event, /):
        super().showEvent(event)
        if self.need_update:
            index = self._list_widget.currentRow()
            if 0 <= index < len(self.current_snippets):
                self._property_widget.set_snippet(self.current_snippets[index], self.meta_data)
            self.need_update = False

    def _add_snippet_instance(self, snippet: BaseSnippet) -> None:
        current_row = self._list_widget.currentRow()

        if current_row >= 0:
            insert_position = current_row + 1
            snippet_show_name = f'{snippet.type} #{insert_position + 1}'
            self.current_snippets.insert(insert_position, snippet)
            self._list_widget.insertItem(insert_position, snippet_show_name)
            self._list_widget.setCurrentRow(insert_position)

            self._renumber_snippets()
        else:
            snippet_show_name = f'{snippet.type} #1'
            self.current_snippets.append(snippet)
            self._list_widget.addItem(snippet_show_name)
            self._list_widget.setCurrentRow(len(self.current_snippets) - 1)

        self._property_widget.set_snippet(snippet, self.meta_data)

    def _add_snippet(self, snippet: str) -> None:
        new_snippet = get_snippet(snippet).copy()
        self._add_snippet_instance(new_snippet)

    def _on_snippet_selected(self, item: QListWidgetItem) -> None:
        index = self._list_widget.row(item)
        if 0 <= index < len(self.current_snippets):
            self._property_widget.set_snippet(self.current_snippets[index], self.meta_data)

    def swap_items(self, index1: int, index2: int) -> None:
        count = self._list_widget.count()
        if not (0 <= index1 < count and 0 <= index2 < count) or index1 == index2:
            return

        min_index = min(index1, index2)
        max_index = max(index1, index2)

        item_max = self._list_widget.takeItem(max_index)
        item_min = self._list_widget.takeItem(min_index)

        self._list_widget.insertItem(min_index, item_max)
        self._list_widget.insertItem(max_index, item_min)

        self.current_snippets[min_index], self.current_snippets[max_index] = \
            self.current_snippets[max_index], self.current_snippets[min_index]

        self._renumber_snippets()

    def _on_up_clicked(self) -> None:
        current_row = self._list_widget.currentRow()
        if current_row > 0:
            self.swap_items(current_row, current_row - 1)
            self._list_widget.setCurrentRow(current_row - 1)

    def _on_down_clicked(self) -> None:
        current_row = self._list_widget.currentRow()
        if current_row < self._list_widget.count() - 1:
            self.swap_items(current_row, current_row + 1)
            self._list_widget.setCurrentRow(current_row + 1)

    def _on_delete_clicked(self) -> None:
        current_row = self._list_widget.currentRow()
        if current_row >= 0:
            self._list_widget.takeItem(current_row)

            if 0 <= current_row < len(self.current_snippets):
                del self.current_snippets[current_row]

            self._renumber_snippets()

            if self._list_widget.count() > 0 and len(self.current_snippets) > 0:
                next_row = min(current_row, self._list_widget.count() - 1)
                self._list_widget.setCurrentRow(next_row)
                self._property_widget.set_snippet(self.current_snippets[next_row], self.meta_data)
            else:
                self._property_widget.clear_properties()

    def _on_copy_clicked(self) -> None:
        current_row = self._list_widget.currentRow()
        if current_row < 0:
            return

        snippet_to_copy = self.current_snippets[current_row]
        new_snippet = snippet_to_copy.copy()
        self._add_snippet_instance(new_snippet)
        self._renumber_snippets()

    def _on_save_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save your story",
            "",
            "Sekai Story File (*.sekai-story.json)"
        )

        if file_path is None or file_path == '':
            return

        self.save_message_box = SaveFileMessageBox(self)

        build_thread = BuildStoryThread(
            file_path,
            self.meta_data,
            self.current_snippets,
            self
        )

        self.save_message_box.cancelButton.clicked.connect(build_thread.cancel)
        self.save_message_box.show()

        build_thread.built.connect(self._on_story_built)
        build_thread.start()

    def _on_story_built(self, data: OrderedDict, file_path: str) -> None:
        with open(file_path, 'w+', encoding='utf-8') as f:
            data_json = json.dumps(data, indent=2, ensure_ascii=False)
            f.write(data_json)
        self._property_widget.reset()
        current_index = self._list_widget.currentRow()
        if len(self.current_snippets) > 0:
            self._property_widget.set_snippet(self.current_snippets[current_index], self.meta_data)
        self.save_message_box.close()

    def _on_load_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load your story",
            "",
            "Sekai Story File (*.sekai-story.json)"
        )

        if file_path is None or file_path == '':
            return

        base_path = os.path.dirname(file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            data_json = json.loads(f.read())
            models_def = data_json['models']
            images_def = data_json['images']
            snippets: list = data_json['snippets']

        self.current_snippets = []
        self._list_widget.clear()
        self._property_widget.reset()
        self.meta_data.reset_all()

        for model in models_def:
            file_name_with_ext = model['model'].split('/')[-1]

            if '.model3.json' in file_name_with_ext:
                model_name = file_name_with_ext.split('.model3.json')[0]
            elif '.model.json' in file_name_with_ext:
                model_name = file_name_with_ext.split('.model.json')[0]
            elif file_name_with_ext == 'model.json':
                model_name = 'model'
            else:
                raise RuntimeError(f"What is the model name: {file_name_with_ext}")

            normal_scale = model.get("normal_scale")
            small_scale = model.get("small_scale")
            anchor = model.get("anchor")

            added_model_data = self.meta_data.add_model(
                model_name,
                os.path.join(
                    base_path,
                    "models",
                    model['model']
                ),
                True,
                id_=model['id']
            )

            if normal_scale is not None:
                added_model_data['normal_scale'] = normal_scale
            if small_scale is not None:
                added_model_data['small_scale'] = small_scale
            if anchor is not None:
                added_model_data['anchor'] = anchor

        for image in images_def:
            image_name = Path(image['image'].split('/')[-1]).stem
            self.meta_data.add_image(
                image_name,
                os.path.join(
                    base_path,
                    "images",
                    image['image']
                ),
                image['id']
            )

        for snippet in snippets:
            snippet_type = snippet['type']
            snippet_instance = get_snippet(snippet_type).copy()
            properties = snippet.copy()
            del properties['type']

            original_order = list(snippet_instance.properties.keys())
            new_properties = {}

            for key in original_order:
                if key in properties:
                    if isinstance(properties[key], dict) and isinstance(snippet_instance.properties[key], dict):
                        merged_nested = {**snippet_instance.properties[key], **properties[key]}
                        new_properties[key] = merged_nested
                    else:
                        new_properties[key] = properties[key]

            for key in properties.keys():
                if key not in original_order:
                    new_properties[key] = properties[key]

            if snippet_instance.type == 'ChangeLayoutMode':
                new_properties['data']['mode'] = LayoutModes(new_properties['data']['mode'])

            if "data" in new_properties:
                data = new_properties['data']
                if "from" in data:
                    data['from']['side'] = Sides(data['from']['side'])
                if "to" in data:
                    data['to']['side'] = Sides(data['to']['side'])
                if "moveSpeed" in data:
                    data['moveSpeed'] = MoveSpeed(data['moveSpeed'])
                if 'voice' in data:
                    if data['voice']:
                        data['voice'] = os.path.abspath(os.path.join(
                            base_path,
                            "voices",
                            data['voice']
                        )).replace("\\", "/")

            snippet_instance.properties = new_properties
            self._add_snippet_instance(snippet_instance)
