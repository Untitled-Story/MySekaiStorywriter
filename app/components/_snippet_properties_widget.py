import enum
import json
from typing import Any

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QSizePolicy, QFileDialog
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from qfluentwidgets import (SpinBox, DoubleSpinBox, LineEdit,
                            SwitchButton, ComboBox, EditableComboBox, SmoothScrollArea,
                            ToolButton, BodyLabel)
from qfluentwidgets import StrongBodyLabel, setFont, FluentIcon

from app.data_model import MetaData
from app.snippets import BaseSnippet, Curves
from ._collapsible_property_card import CollapsiblePropertyCard
from ._snippet_property_input_widget import SnippetPropertyInputWidget
from ._voice_property import VoiceProperty
from ..utils import FuzzyCompleter


class SnippetPropertiesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self.setLayout(self._main_layout)

        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea {border: none; background-color: transparent;}")

        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.scroll_widget.setStyleSheet("QWidget#scrollWidget {background-color: transparent;}")

        self._layout = QVBoxLayout(self.scroll_widget)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)

        self.scroll_area.setWidget(self.scroll_widget)
        self._main_layout.addWidget(self.scroll_area)

        self._current_snippet = None
        self._meta_data: MetaData | None = None
        self._widget_map = {}
        self._expanded_keys = set()

        self.clear_properties()

    def reset(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout_recursive(item.layout())
                item.layout().deleteLater()

    def _clear_layout_recursive(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout_recursive(item.layout())

    def clear_properties(self):
        self.reset()
        self._expanded_keys.clear()
        no_snippet_label = StrongBodyLabel(text='Please select or add a Snippet.')
        setFont(no_snippet_label, fontSize=14)
        no_snippet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(no_snippet_label)

    def set_snippet(self, snippet: BaseSnippet, meta_data: MetaData):
        self._current_snippet = snippet
        self._meta_data = meta_data
        self._expanded_keys.clear()
        if self._current_snippet:
            self._expanded_keys.add("data")
        self._update_properties()

    def update_motions(self, widgets: dict[str, Any], model_id: int):
        current_model = None
        if model_id != -1:
            current_model = next((model for model in self._meta_data.models if model['id'] == model_id), None)

        if "data.motion" in widgets:
            motion_widget: EditableComboBox = widgets["data.motion"].subwidget
            motion_widget.clear()
            if current_model:
                motion_widget.addItems(current_model['motions'])

        if "data.facial" in widgets:
            facial_widget: EditableComboBox = widgets["data.facial"].subwidget
            facial_widget.clear()
            if current_model:
                facial_widget.addItems(current_model['expressions'])

    def _on_card_toggled(self, key: str, expanded: bool):
        if expanded:
            self._expanded_keys.add(key)
        else:
            self._expanded_keys.discard(key)

    def _add_params_from_file(self, key_path: str):
        if self._current_snippet is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select .sekai2d file",
            "",
            "Sekai2D Files (*.sekai2d *.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to load file: {e}")
            return

        for param_name, end_value in data.items():
            self._current_snippet.add_list_item(key_path)
            param_list = self._current_snippet.properties
            for key in key_path.split('.')[:-1]:
                param_list = param_list[key]
            last_index = len(param_list[key_path.split('.')[-1]]) - 1
            param_list[key_path.split('.')[-1]][last_index] = {
                "paramId": param_name,
                "start": 0.0,
                "end": float(end_value),
                "curve": Curves.Linear,
                "duration": 0.0
            }

        self._update_properties()

    def _update_properties(self):
        if self._current_snippet is None:
            self.clear_properties()
            return

        self.reset()
        self._widget_map = {}

        def create_input_widget(_key, _value, parent_key="", target_layout=None):
            full_key = f"{parent_key}.{_key}" if parent_key else _key
            layout_to_add = target_layout if target_layout else self._layout

            if isinstance(_value, list):
                group_card = CollapsiblePropertyCard(title=f"{_key} ({len(_value)})")

                is_expanded = full_key in self._expanded_keys
                group_card.set_expanded(is_expanded)
                group_card.toggled.connect(lambda e, k=full_key: self._on_card_toggled(k, e))

                if full_key == "data.params":
                    # noinspection PyTypeChecker
                    import_btn = ToolButton(FluentIcon.FOLDER)
                    import_btn.setFixedSize(24, 24)
                    import_btn.setIconSize(QSize(12, 12))
                    import_btn.clicked.connect(lambda: self._add_params_from_file(full_key))
                    group_card.add_action_widget(import_btn)

                # noinspection PyTypeChecker
                add_btn = ToolButton(FluentIcon.ADD)
                add_btn.setFixedSize(24, 24)
                add_btn.setIconSize(QSize(12, 12))
                add_btn.clicked.connect(lambda: self._add_list_item(full_key))
                group_card.add_action_widget(add_btn)

                layout_to_add.addWidget(group_card)

                for i, item in enumerate(_value):
                    item_container = QFrame()
                    item_container.setStyleSheet("""
                        QFrame { 
                            background-color: transparent; 
                            border: 1px solid rgba(0, 0, 0, 0.06); 
                            border-radius: 6px; 
                        }
                    """)
                    item_layout = QVBoxLayout(item_container)
                    item_layout.setContentsMargins(6, 6, 6, 6)
                    item_layout.setSpacing(2)

                    item_header = QHBoxLayout()
                    item_header.setContentsMargins(0, 0, 0, 2)
                    # noinspection PyTypeChecker
                    item_label = BodyLabel(f"Item #{i + 1}")
                    setFont(item_label, 12)
                    item_label.setStyleSheet("color: gray;")

                    # noinspection PyTypeChecker
                    del_btn = ToolButton(FluentIcon.REMOVE)
                    del_btn.setIconSize(QSize(12, 12))
                    del_btn.setFixedSize(20, 20)
                    del_btn.clicked.connect(lambda c, idx=i: self._remove_list_item(full_key, idx))

                    item_header.addWidget(item_label)
                    item_header.addStretch(1)
                    item_header.addWidget(del_btn)
                    item_layout.addLayout(item_header)

                    if isinstance(item, dict):
                        for sub_k, sub_v in item.items():
                            create_input_widget(sub_k, sub_v, f"{full_key}.{i}", target_layout=item_layout)
                    else:
                        create_input_widget(f"Value", item, full_key, target_layout=item_layout)

                    group_card.content_layout.addWidget(item_container)
                return

            if isinstance(_value, dict):
                group_card = CollapsiblePropertyCard(title=_key)

                is_expanded = full_key in self._expanded_keys
                group_card.set_expanded(is_expanded)
                group_card.toggled.connect(lambda e, k=full_key: self._on_card_toggled(k, e))

                layout_to_add.addWidget(group_card)

                for sub_key, sub_value in _value.items():
                    create_input_widget(sub_key, sub_value, full_key, target_layout=group_card.content_layout)
                return

            sub_widget = None

            def set_model(model_name: str):
                if model_name != 'None':
                    model_id_result = [model['id'] for model in self._meta_data.models if
                                       model['model_name'] == model_name.split(' #')[0]][0]
                    self._current_snippet.set_property(full_key, model_id_result)
                    self.update_motions(self._widget_map, model_id_result)
                else:
                    self._current_snippet.set_property(full_key, -1)
                    self.update_motions(self._widget_map, -1)

            def set_image(image_name: str):
                image_id_result = [image['id'] for image in self._meta_data.images if
                                   image['name'] == image_name.split(' #')[0]][0]
                self._current_snippet.set_property(full_key, image_id_result)

            def model_property_standard_combo_box() -> tuple[EditableComboBox, dict]:
                sub_widget_ = EditableComboBox()
                sub_widget_.setFixedHeight(26)
                sub_widget_.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                current_model_id = self._current_snippet.properties.get('data', {}).get('modelId', -1)
                current_model_ = next((model for model in self._meta_data.models if model['id'] == current_model_id),
                                      None)
                return sub_widget_, current_model_

            if full_key == 'data.motion':
                sub_widget, current_model = model_property_standard_combo_box()
                if current_model:
                    motions = current_model.get('motions', [])
                    completer = FuzzyCompleter(motions)
                    completer.setMaxVisibleItems(15)
                    sub_widget.setCompleter(completer)
                    sub_widget.addItems(motions)
                    if _value == "": _value = "None"
                    if _value in motions: sub_widget.setCurrentText(_value)
                sub_widget.currentTextChanged.connect(
                    lambda val: self._current_snippet.set_property(full_key, val if val != "None" else "")
                )

            elif full_key == 'data.facial':
                sub_widget, current_model = model_property_standard_combo_box()
                if current_model:
                    expressions = current_model.get('expressions', [])
                    completer = FuzzyCompleter(expressions)
                    completer.setMaxVisibleItems(15)
                    sub_widget.setCompleter(completer)
                    sub_widget.addItems(expressions)
                    if _value == "": _value = "None"
                    if _value in expressions: sub_widget.setCurrentText(_value)
                sub_widget.currentTextChanged.connect(
                    lambda val: self._current_snippet.set_property(full_key, val if val != "None" else "")
                )

            elif _key == 'modelId':
                sub_widget = ComboBox()
                sub_widget.addItem('None')
                sub_widget.addItems([f'{model["model_name"]} #{model["id"]}' for model in self._meta_data.models])
                result_list = [f'{model["model_name"]} #{model["id"]}' for model in self._meta_data.models if
                               model['id'] == _value]
                if result_list:
                    sub_widget.setCurrentText(result_list[0])
                else:
                    sub_widget.setCurrentText('None')
                sub_widget.currentTextChanged.connect(lambda model_name: set_model(model_name))

            elif _key == 'imageId':
                sub_widget = ComboBox()
                sub_widget.addItems([f'{model["name"]} #{model["id"]}' for model in self._meta_data.images])
                result_list = [f'{model["name"]} #{model["id"]}' for model in self._meta_data.images if
                               model['id'] == _value]
                if result_list: sub_widget.setCurrentText(result_list[0])
                sub_widget.currentTextChanged.connect(lambda val: set_image(val))

            elif _key == 'voice':
                sub_widget = VoiceProperty()
                sub_widget.val = _value
                sub_widget.text_changed.connect(lambda text: self._current_snippet.set_property(full_key, text))

            elif isinstance(_value, bool):
                sub_widget = SwitchButton()
                sub_widget.setChecked(_value)
                sub_widget.setOnText("On")
                sub_widget.setOffText("Off")
                sub_widget.checkedChanged.connect(lambda checked: self._current_snippet.set_property(full_key, checked))

            elif isinstance(_value, int):
                sub_widget = SpinBox()
                sub_widget.setRange(-32767, 32767)
                sub_widget.setValue(_value)
                sub_widget.wheelEvent = lambda _: None
                sub_widget.valueChanged.connect(lambda val: self._current_snippet.set_property(full_key, val))

            elif isinstance(_value, float):
                sub_widget = DoubleSpinBox()
                sub_widget.setSingleStep(0.1)
                sub_widget.setDecimals(2)
                sub_widget.setRange(-32767, 32767)
                sub_widget.setValue(_value)
                sub_widget.wheelEvent = lambda _: None
                sub_widget.valueChanged.connect(lambda val: self._current_snippet.set_property(full_key, val))

            elif isinstance(_value, str):
                sub_widget = LineEdit()
                sub_widget.setText(_value)
                sub_widget.setClearButtonEnabled(True)
                sub_widget.textChanged.connect(lambda text: self._current_snippet.set_property(full_key, text))

            elif isinstance(_value, enum.Enum):
                sub_widget = ComboBox()
                enum_class = _value.__class__
                members = [name for name in enum_class.__members__]
                sub_widget.addItems(members)
                sub_widget.setCurrentText(_value.name)
                sub_widget.currentTextChanged.connect(
                    lambda val: self._current_snippet.set_property(full_key, enum_class[val])
                )

            if sub_widget:
                sub_widget.setFixedHeight(28)
                if isinstance(sub_widget, (ComboBox, EditableComboBox, LineEdit, SpinBox, DoubleSpinBox)):
                    sub_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                block = SnippetPropertyInputWidget(full_key if not parent_key else _key, sub_widget)
                block.layout().setContentsMargins(2, 2, 2, 2)
                self._widget_map[full_key] = block
                layout_to_add.addWidget(block)

        for key, value in self._current_snippet.properties.items():
            create_input_widget(key, value)

        self._layout.addStretch(1)

    def _add_list_item(self, key_path):
        self._expanded_keys.add(key_path)
        self._current_snippet.add_list_item(key_path)
        self._update_properties()

    def _remove_list_item(self, key_path, index):
        self._current_snippet.remove_list_item(key_path, index)
        self._update_properties()
