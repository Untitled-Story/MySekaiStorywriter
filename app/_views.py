import json

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy, QListWidgetItem, QFileDialog, \
    QStackedWidget
from qfluentwidgets import CommandBar, Action, setFont, ListWidget, TransparentToolButton, FluentIcon, Pivot, \
    TitleLabel, HorizontalSeparator

from ._components import Live2DWidget, SnippetPropertiesWidget, SaveFileMessageBox, InputMetadataMessageBox
from ._snippets import SNIPPETS, get_snippet, BaseSnippet


class MainView(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('MainView')

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
        live2d_widget = Live2DWidget()
        central_splitter.addWidget(live2d_widget)

        # Right
        self._property_widget = SnippetPropertiesWidget(self)
        central_splitter.addWidget(self._property_widget)

        # Final
        central_splitter.setSizes([150, 500, 250])

        self.current_snippets: list[BaseSnippet] = []

    def _renumber_snippets(self) -> None:
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            snippet = self.current_snippets[i]
            item.setText(f"{snippet.type} #{i + 1}")

    def _add_snippet(self, snippet: str) -> None:
        new_snippet = get_snippet(snippet).copy()

        current_row = self._list_widget.currentRow()

        if current_row >= 0:
            insert_position = current_row + 1
            snippet_show_name = f'{new_snippet.type} #{insert_position + 1}'
            self.current_snippets.insert(insert_position, new_snippet)
            self._list_widget.insertItem(insert_position, snippet_show_name)
            self._list_widget.setCurrentRow(insert_position)

            self._renumber_snippets()
        else:
            snippet_show_name = f'{new_snippet.type} #1'
            self.current_snippets.append(new_snippet)
            self._list_widget.addItem(snippet_show_name)
            self._list_widget.setCurrentRow(len(self.current_snippets) - 1)

        self._property_widget.set_snippet(new_snippet)

    def _on_snippet_selected(self, item: QListWidgetItem) -> None:
        index = self._list_widget.row(item)
        if 0 <= index < len(self.current_snippets):
            self._property_widget.set_snippet(self.current_snippets[index])

    def swap_items(self, index1: int, index2: int) -> None:
        if 0 <= index1 < self._list_widget.count() and 0 <= index2 < self._list_widget.count():
            item1 = self._list_widget.takeItem(index1)
            item2 = self._list_widget.takeItem(index2 - 1 if index2 > index1 else index2)

            item1_name, item1_num = item1.text().split(' #')
            item2_name, item2_num = item2.text().split(' #')

            item1.setText(f'{item1_name} #{item2_num}')
            item2.setText(f'{item2_name} #{item1_num}')

            self._list_widget.insertItem(index1, item2)
            self._list_widget.insertItem(index2, item1)

            self.current_snippets[index1], self.current_snippets[index2] = self.current_snippets[index2], \
                self.current_snippets[index1]

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
            self._renumber_snippets()

            if 0 <= current_row < len(self.current_snippets):
                del self.current_snippets[current_row]

            if self._list_widget.count() > 0:
                next_row = min(current_row, self._list_widget.count() - 1)
                self._property_widget.set_snippet(self.current_snippets[next_row])
                self._list_widget.setCurrentRow(next_row)
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

            message_box = SaveFileMessageBox(self)
            message_box.show()
            with open(file_path, 'w+', encoding='utf-8') as f:
                snippets_data = [snippet.build() for snippet in self.current_snippets]

                data = {
                    '$schema': 'https://raw.githubusercontent.com/GuangChen2333/MySekaiStoryteller/refs/heads/master/sekai-story.schema.json',
                    'title': metadata_message_box.title_edit.text(),
                    'version': f'v{metadata_message_box.version_edit.text()}',
                    'models': [],
                    'images': [],
                    'snippets': snippets_data,
                }

                data_json = json.dumps(data, indent=2, ensure_ascii=False)
                f.write(data_json)
            message_box.close()


class ModelManageFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 0, 0, 15)
        main_layout.setSpacing(5)

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 5, 5, 0)
        h_layout.setSpacing(5)

        main_layout.addLayout(h_layout)

        l_layout = QVBoxLayout()
        h_layout.addLayout(l_layout, 3)

        r_layout = QVBoxLayout()
        h_layout.addLayout(r_layout, 7)

        title1 = TitleLabel(text='123123')
        l_layout.addWidget(title1)

        title2 = TitleLabel(text='121321')
        r_layout.addWidget(title2)

        l_layout.addStretch(1)
        r_layout.addStretch(1)


class ImageManageFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 0, 0, 15)
        layout.setSpacing(5)

        title = TitleLabel(text='Image Manage')
        layout.addWidget(title)

        layout.addStretch(1)


class DataView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('DataView')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.pivot = Pivot(self)
        self.pivot.setMaximumHeight(20)
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.model_manage_frame = ModelManageFrame(self)
        self.image_manage_frame = ImageManageFrame(self)

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

    def add_sub_interface(self, widget: QFrame, object_name: str, text: str):
        widget.setObjectName(object_name)
        self.stacked_widget.addWidget(widget)

        self.pivot.addItem(
            routeKey=object_name,
            text=text,
            onClick=lambda: self.stacked_widget.setCurrentWidget(widget)
        )
