import os

from PySide6.QtCore import Signal, QThread
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QSizePolicy, QStackedWidget, QFileDialog, \
    QListWidgetItem
from qfluentwidgets import Pivot, \
    HorizontalSeparator, VerticalSeparator, SubtitleLabel, EditableComboBox, PushButton, PrimaryPushButton, \
    Flyout, InfoBarIcon, FlyoutAnimationType, ComboBox, FluentIcon, TeachingTip, \
    TeachingTipTailPosition, ListWidget

from app.components import Live2DWidget, DownloadingFlyout, ImageDisplayWidget
from app.data_model import MetaData
from app.utils import FuzzyCompleter, build_model_base_json


class AddModelThread(QThread):
    model_added = Signal(str)

    def __init__(self, meta_data, model_, model_list, server_host: str, parent=None):
        super().__init__(parent)
        self.server_host = server_host
        self.meta_data = meta_data
        self.model = model_
        self.model_list = model_list

    def run(self):
        data = self.meta_data.add_model(self.model,
                                        build_model_base_json(self.server_host, self.model_list, self.model), False)
        self.model_added.emit(f'{self.model} #{data["id"]}')


class ModelManageFrame(QFrame):
    def __init__(self, metadata: MetaData, server_host: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.server_host = server_host
        self.meta_data = metadata
        self.meta_data.model_updated.connect(self.on_model_updated)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 0, 0, 0)
        main_layout.setSpacing(5)

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 5, 0, 0)
        h_layout.setSpacing(5)

        main_layout.addLayout(h_layout)

        self.l_layout = QVBoxLayout()
        h_layout.addLayout(self.l_layout, 2)

        h_layout.addWidget(VerticalSeparator())

        self.r_layout = QVBoxLayout()
        h_layout.addLayout(self.r_layout, 8)

        title1 = SubtitleLabel(text='Online Model List')
        title1.setStyleSheet("padding-bottom:3px;")
        self.l_layout.addWidget(title1)

        l_v_layout = QVBoxLayout()
        self.l_layout.addLayout(l_v_layout)

        self.online_model_combo_box = EditableComboBox()
        self.online_model_combo_box.returnPressed.disconnect()
        l_v_layout.addWidget(self.online_model_combo_box)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 7, 0, 7)
        buttons_layout.setSpacing(10)
        l_v_layout.addLayout(buttons_layout)

        self.preview_button = PushButton(text='Preview')
        self.preview_button.clicked.connect(self.preview_model)
        buttons_layout.addWidget(self.preview_button)

        self.add_button = PrimaryPushButton(text='Add')
        buttons_layout.addWidget(self.add_button)
        self.add_button.clicked.connect(self.add_model)

        l_v_layout.addWidget(HorizontalSeparator())

        l_v_layout.addWidget(SubtitleLabel(text='Your Models'))

        self.model_list_widget = ComboBox()
        l_v_layout.addWidget(self.model_list_widget)

        buttons_layout_2 = QHBoxLayout()
        buttons_layout_2.setContentsMargins(0, 7, 0, 7)
        buttons_layout_2.setSpacing(10)

        self.delete_button = PushButton(icon=FluentIcon.DELETE, text='Delete')
        self.delete_button.clicked.connect(self.delete_model)
        buttons_layout_2.addWidget(self.delete_button)

        self.add_local_button = PushButton(icon=FluentIcon.ADD, text='Add from local')
        self.add_local_button.clicked.connect(self.add_model_from_local)
        buttons_layout_2.addWidget(self.add_local_button)

        l_v_layout.addLayout(buttons_layout_2)

        l_v_layout.setStretch(0, 1)
        l_v_layout.setStretch(1, 1)

        self.live2d_preview = Live2DWidget(self.server_host, self)
        self.r_layout.addWidget(self.live2d_preview)

        self.l_layout.addStretch(1)

        self.model_list = []
        self.display_model_list = []

        self.teaching_tip = None
        self.need_update = False

    def on_model_updated(self):
        self.need_update = True

    def showEvent(self, event, /):
        super().showEvent(event)
        if self.need_update:
            self.model_list_widget.clear()
            self.model_list_widget.addItems([f'{data["model_name"]} #{data["id"]}' for data in self.meta_data.models])

    def add_model_from_local(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select your model file.",
            "",
            "Model Files (*.model3.json *.model.json)"
        )

        if not file_path:
            return

        filename = os.path.basename(file_path).split('.')[0]
        if filename in [model['model_name'] for model in self.meta_data.models]:
            Flyout.create(
                icon=InfoBarIcon.INFORMATION,
                title='Info',
                content=f"The model {filename} is already existed in models.",
                target=self.add_local_button,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )

            return

        data = self.meta_data.add_model(filename, file_path, True)
        self.model_list_widget.addItem(f'{filename} #{data["id"]}')
        self.model_list_widget.setCurrentIndex(len(self.meta_data.models) - 1)

    def renumber_models(self):
        for i in range(self.model_list_widget.count()):
            item = self.model_list_widget.items[i]
            text_raw = item.text.split(' ')[0]
            item.text = f"{text_raw} #{i}"

        self.model_list_widget.setText(self.model_list_widget.currentText())

    def delete_model(self):
        if len(self.meta_data.models) > 0 and len(self.model_list_widget.items) > 0:
            index = self.model_list_widget.currentIndex()

            self.model_list_widget.removeItem(index)
            self.meta_data.remove_model(index)

            self.renumber_models()
            self.model_list_widget.setCurrentIndex(index)

    def add_model(self):
        model = self.online_model_combo_box.currentText()

        if not model in self.display_model_list:
            Flyout.create(
                icon=InfoBarIcon.ERROR,
                title='Error',
                content=f"The model {model} is not existed.",
                target=self.add_button,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            return

        if model in [model['model_name'] for model in self.meta_data.models]:
            Flyout.create(
                icon=InfoBarIcon.INFORMATION,
                title='Info',
                content=f"The model {model} is already existed in models.",
                target=self.add_button,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            return

        self.add_button.setDisabled(True)
        self.teaching_tip = TeachingTip.make(
            DownloadingFlyout(),
            self.add_button,
            duration=-1,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            parent=self,
        )

        add_model_thread = AddModelThread(
            meta_data=self.meta_data,
            model_=model,
            model_list=self.model_list,
            server_host=self.server_host,
            parent=self
        )
        add_model_thread.model_added.connect(self.on_model_added)
        add_model_thread.start()

    def on_model_added(self, result):
        self.model_list_widget.addItem(result)
        self.model_list_widget.setCurrentIndex(len(self.meta_data.models) - 1)
        self.teaching_tip.hide()
        self.add_button.setDisabled(False)

    def update_data(self, model_list: list):
        self.model_list = model_list
        self.display_model_list = sorted([model['modelName'] for model in self.model_list])

        completer = FuzzyCompleter(self.display_model_list)
        completer.setMaxVisibleItems(20)
        self.online_model_combo_box.setCompleter(completer)
        self.online_model_combo_box.addItems(self.display_model_list)

    def preview_model(self):
        model = self.online_model_combo_box.currentText()

        if not model in self.display_model_list:
            Flyout.create(
                icon=InfoBarIcon.ERROR,
                title='Error',
                content=f"The modelInfo {model} is not existed.",
                target=self.preview_button,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            return

        model_url = build_model_base_json(self.server_host, self.model_list, model)
        self.live2d_preview.replace_model(model_url)


class ImageManageFrame(QFrame):
    def __init__(self, meta_data: MetaData, parent=None):
        super().__init__(parent)
        self.meta_data = meta_data
        self.meta_data.image_updated.connect(self.on_image_updated)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 0, 20, 0)
        main_layout.setSpacing(5)

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 5, 0, 0)
        h_layout.setSpacing(5)
        main_layout.addLayout(h_layout)

        self.l_layout = QVBoxLayout()
        h_layout.addLayout(self.l_layout, 2)

        h_layout.addWidget(VerticalSeparator())

        self.r_layout = QHBoxLayout()
        self.r_layout.setContentsMargins(5, 0, 0, 0)
        h_layout.addLayout(self.r_layout, 8)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        self.l_layout.addLayout(top_layout)

        add_btn = PrimaryPushButton(text="Add Image", icon=FluentIcon.ADD, parent=self)
        add_btn.clicked.connect(self.add_image)
        top_layout.addWidget(add_btn)

        delete_btn = PushButton(text="Delete Selected", icon=FluentIcon.DELETE, parent=self)
        delete_btn.clicked.connect(self.remove_image)
        top_layout.addWidget(delete_btn)

        top_layout.addStretch(1)

        self.image_list_widget = ListWidget(self)
        self.image_list_widget.itemClicked.connect(self.on_image_clicked)
        self.l_layout.addWidget(self.image_list_widget)

        self.image_widget = ImageDisplayWidget()
        self.r_layout.addWidget(self.image_widget, 1)
        self.l_layout.addStretch(1)

        self.images = []

        self.need_update = False

    def on_image_updated(self):
        self.need_update = True

    def showEvent(self, event):
        super().showEvent(event)
        if self.need_update:
            self.images = []
            for image in self.meta_data.images:
                filename = os.path.basename(image['path'])
                self.images.append({
                    'name': f'{filename} {image["id"]}',
                    'path': image['path'],
                    'index': image["id"]
                })

            current_row = self.image_list_widget.currentRow()
            self.image_list_widget.clear()
            self.image_list_widget.addItems([f'{data["name"]} #{data["id"]}' for data in self.meta_data.images])
            if current_row == -1 and self.image_list_widget.count() > 0:
                i = [data['path'] for data in self.images if data['index'] == 0][0]
                self.image_list_widget.setCurrentRow(0)
                self.image_widget.display_image(i)
            elif current_row <= self.image_list_widget.count() - 1:
                i = [data['path'] for data in self.images if data['index'] == current_row][0]
                self.image_list_widget.setCurrentRow(current_row)
                self.image_widget.display_image(i)

    def renumber_images(self):
        images_new = []
        for i in range(self.image_list_widget.count()):
            item = self.image_list_widget.item(i)
            text_raw = item.text().split(' ')[0]
            num_raw = int(item.text().split(' #')[1])

            image_data = self.images[num_raw]
            image = [image for image in self.meta_data.images if image['id'] == i][0]

            show_name = f'{text_raw} #{image["id"]}'
            images_new.append({
                'name': show_name,
                'path': image_data['path'],
                'index': i
            })
            item.setText(show_name)
        self.images = images_new

    def remove_image(self):
        if len(self.meta_data.images) > 0 and self.image_list_widget.count() > 0:
            index = self.image_list_widget.currentRow()

            i = [image for image in self.images if image['index'] == index][0]

            self.image_list_widget.takeItem(index)

            self.image_list_widget.setCurrentRow(index)

            self.renumber_images()
            self.meta_data.remove_image(i['index'])
            self.image_widget.clear()

    def on_image_clicked(self, item: QListWidgetItem):
        index = self.image_list_widget.row(item)
        if 0 <= index < len(self.images):
            i = [image['path'] for image in self.images if image['index'] == index][0]
            self.image_widget.display_image(i)

    def add_image_instance(self, path: str):
        filename = os.path.basename(path)
        data = self.meta_data.add_image(filename, path)
        self.image_widget.display_image(path)
        insert_pos = data["id"]
        show_name = f'{filename} #{insert_pos}'

        self.image_list_widget.insertItem(insert_pos, show_name)
        self.images.append({
            'name': show_name,
            'path': path,
            'index': insert_pos
        })

        self.image_list_widget.setCurrentRow(insert_pos)

    def add_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a image file",
            "",
            "Image File (*.jpg *.jpeg *.png *.avif *.webp *.gif)"
        )

        if not file_path:
            return

        self.add_image_instance(file_path)


class DataView(QFrame):
    def __init__(self, metadata: MetaData, server_host: str, parent=None):
        super().__init__(parent)
        self.setObjectName('DataView')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.server_host = server_host
        self.meta_data = metadata

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.pivot = Pivot(self)
        self.pivot.setMaximumHeight(20)
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.model_manage_frame = ModelManageFrame(self.meta_data, self.server_host, self)
        self.image_manage_frame = ImageManageFrame(self.meta_data, self)

        self.add_sub_interface(self.model_manage_frame, 'modelInterface', 'Models')
        self.add_sub_interface(self.image_manage_frame, 'imageInterface', 'Images')

        main_layout.addWidget(self.pivot)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.stacked_widget, 1)

        self.stacked_widget.setCurrentWidget(self.model_manage_frame)
        self.pivot.setCurrentItem(self.model_manage_frame.objectName())
        self.pivot.currentItemChanged.connect(
            lambda k: self.stacked_widget.setCurrentWidget(self.findChild(QFrame, k))
        )

    def on_data_loaded(self, model_list: list):
        self.model_manage_frame.update_data(model_list)

    def add_sub_interface(self, widget: QFrame, object_name: str, text: str):
        widget.setObjectName(object_name)
        self.stacked_widget.addWidget(widget)

        self.pivot.addItem(
            routeKey=object_name,
            text=text,
            onClick=lambda: self.stacked_widget.setCurrentWidget(widget)
        )
