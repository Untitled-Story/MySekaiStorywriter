import asyncio
import json
import os
import shutil
from collections import OrderedDict

import httpx
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy, QListWidgetItem, QFileDialog
from httpx_retries import RetryTransport, Retry
from qfluentwidgets import CommandBar, setFont, Action, TransparentToolButton, FluentIcon, HorizontalSeparator, \
    ListWidget

from app.components import SnippetPropertiesWidget, InputMetadataMessageBox, SaveFileMessageBox
from app.data_model import MetaData
from app.snippets import SNIPPETS, BaseSnippet, get_snippet, LayoutModes, Sides, MoveSpeed
from app.utils import extract_url_path, get_motions, to_ordered_dict


class BuildStoryThread(QThread):
    built = Signal(OrderedDict, str)

    def __init__(self, file_path: str, metadata: MetaData, title: str, snippets: list[BaseSnippet], parent):
        super().__init__(parent)
        self.snippets = snippets
        self.title = title
        self.file_path = file_path
        self.metadata = metadata
        self.models = metadata.models
        self.base_path = os.path.dirname(self.file_path)
        self.retry = Retry(total=5, backoff_factor=0.5)
        self.client = httpx.Client(transport=RetryTransport(retry=self.retry))

    def download(self, path: str, filename: str, url: str) -> bytes:
        full_path = os.path.join(path, filename)
        with open(full_path, "wb+") as file:
            resp = self.client.get(url)
            file.write(resp.content)
            return resp.content

    @staticmethod
    def gen_motion_urls(info_url: str, motions_result: dict, type_: str) -> list:
        result = []
        base = extract_url_path(info_url)

        if type_ == 'model':
            base_motion = '/'.join(base.split('/')[:-2]) + "/motions"
            base_facial = base_motion
        else:
            base_motion = base + "motion"
            base_facial = base + "facial"

        if 'motions' in motions_result[type_]:
            for motion in motions_result[type_]['motions']:
                result.append(f"{base_motion}/{motion}.motion3.json")
        if 'expressions' in motions_result[type_]:
            for expression in motions_result[type_]['expressions']:
                result.append(f"{base_facial}/{expression}.motion3.json")
        return result

    @staticmethod
    async def download_motion_and_save(client: httpx.AsyncClient, url: str, motion_path: str, main_data: dict):
        r = await client.get(url)
        m_file_name_ext = os.path.basename(r.url.path)
        m_file_name = m_file_name_ext.split('.')[0]
        file_path = os.path.join(motion_path, m_file_name_ext)
        main_data["FileReferences"]["Motions"][m_file_name] = [{
            "FadeInTime": 0.5,
            "FadeOutTime": 0.5,
            "File": f"motions/{m_file_name_ext}"
        }]
        with open(file_path, "wb") as file:
            file.write(r.content)

    async def download_motions(self, urls: list, motion_path: str, main_data: dict):
        async with httpx.AsyncClient(transport=RetryTransport(retry=self.retry)) as client:
            tasks = [self.download_motion_and_save(client, url, motion_path, main_data) for url in urls]
            await asyncio.gather(*tasks)

    def run(self):
        models_data = []
        for model in self.models:
            rel_model_path = str(os.path.join(
                model['model_name'],
                model['model_name'] + ".model3.json"
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

                if motions_result['model']:
                    url = motions_result['model_url']
                    urls.extend(self.gen_motion_urls(url, motions_result, 'model'))

                if motions_result['special']:
                    url = motions_result['special_url']
                    urls.extend(self.gen_motion_urls(url, motions_result, 'special'))

                if motions_result['common_url']:
                    url = motions_result['common_url']
                    urls.extend(self.gen_motion_urls(url, motions_result, 'common'))

                motion_path = os.path.join(model_dir, 'motions')
                os.makedirs(motion_path, exist_ok=True)

                main_data["FileReferences"]["Motions"] = {}
                for i in range(0, len(urls), 40):
                    chunk = urls[i:i + 40]
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

        snippets_data = [snippet.build() for snippet in self.snippets]
        self.built.emit(to_ordered_dict({
            '$schema': 'https://raw.githubusercontent.com/Untitled-Story/MySekaiStoryteller/refs/heads/master/sekai-story.schema.json',
            'title': self.title,
            'models': models_data,
            'images': images_data,
            'snippets': snippets_data,
        }), self.file_path)


class MainView(QFrame):
    def __init__(self, metadata: MetaData, server_host: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('MainView')

        self.server_host = server_host
        self.meta_data = metadata
        self.meta_data.model_updated.connect(self._on_model_update)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        snippets_layout = QHBoxLayout()
        self._main_layout.addLayout(snippets_layout)

        command_bar = CommandBar()
        command_bar.setSpaing(0)
        command_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        setFont(command_bar, fontSize=14)

        snippets = [snippet_type.type for snippet_type in SNIPPETS]

        for snippet_type in snippets:
            action = Action(text=snippet_type)
            action.triggered.connect(lambda _, t=snippet_type: self._add_snippet(t))
            command_bar.addAction(action)

        command_bar.addSeparator()

        up_button = TransparentToolButton(FluentIcon.UP, parent=self)
        up_button.clicked.connect(self._on_up_clicked)
        down_button = TransparentToolButton(FluentIcon.DOWN, parent=self)
        down_button.clicked.connect(self._on_down_clicked)
        delete_button = TransparentToolButton(FluentIcon.DELETE, parent=self)
        delete_button.clicked.connect(self._on_delete_clicked)

        command_bar.addWidget(up_button)
        command_bar.addWidget(down_button)
        command_bar.addWidget(delete_button)

        command_bar.addSeparator()

        load_button = TransparentToolButton(FluentIcon.FOLDER, parent=self)
        load_button.clicked.connect(self._on_load_clicked)
        command_bar.addWidget(load_button)

        save_button = TransparentToolButton(FluentIcon.SAVE, parent=self)
        save_button.clicked.connect(self._on_save_clicked)
        command_bar.addWidget(save_button)

        snippets_layout.addWidget(command_bar, 1)

        # Top Separator
        top_separator = HorizontalSeparator()
        self._main_layout.addWidget(top_separator)

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
        if 0 <= index1 < count and 0 <= index2 < count and index1 != index2:
            if index1 < index2:
                item2 = self._list_widget.takeItem(index2)
                item1 = self._list_widget.takeItem(index1)
            else:
                item1 = self._list_widget.takeItem(index1)
                item2 = self._list_widget.takeItem(index2)

            item1_name, item1_num = item1.text().split(' #')
            item2_name, item2_num = item2.text().split(' #')
            item1.setText(f'{item1_name} #{item2_num}')
            item2.setText(f'{item2_name} #{item1_num}')

            self._list_widget.insertItem(index1, item2)
            self._list_widget.insertItem(index2, item1)

            self.current_snippets[index1], self.current_snippets[index2] = \
                self.current_snippets[index2], self.current_snippets[index1]

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

    def _on_save_clicked(self) -> None:
        metadata_message_box = InputMetadataMessageBox(self)
        if metadata_message_box.exec():
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save your story",
                "",
                "Sekai Story File (*.sekai-story.json)"
            )

            if file_path is None or file_path == '':
                return

            self.save_message_box = SaveFileMessageBox(self)
            self.save_message_box.show()

            build_thread = BuildStoryThread(
                file_path,
                self.meta_data,
                metadata_message_box.title_edit.text(),
                self.current_snippets,
                self
            )
            build_thread.built.connect(self._on_story_built)
            build_thread.start()

    def _on_story_built(self, data: OrderedDict, file_path: str) -> None:
        with open(file_path, 'w+', encoding='utf-8') as f:
            data_json = json.dumps(data, indent=2, ensure_ascii=False)
            f.write(data_json)
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
            model_name = model['model'].split('/')[-1].split('.')[0]
            self.meta_data.add_model(
                model_name,
                os.path.join(
                    base_path,
                    "models",
                    model['model']
                ),
                True,
                id_=model['id']
            )

        for image in images_def:
            image_name = image['image'].split('/')[-1].split('.')[0]
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

            snippet_instance.properties = new_properties
            self._add_snippet_instance(snippet_instance)
