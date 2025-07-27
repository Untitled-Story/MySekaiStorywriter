import enum
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from qfluentwidgets import StrongBodyLabel, setFont, SpinBox, DoubleSpinBox, LineEdit, \
    SwitchButton, ComboBox, EditableComboBox

from app.data_model import MetaData
from app.snippets import BaseSnippet
from ._snippet_property_input_widget import SnippetPropertyInputWidget
from ..utils import FuzzyCompleter


class SnippetPropertiesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)

        self.clear_properties()
        self._current_snippet = None
        self._current_data = {}

        self._meta_data: MetaData | None = None
        self._widget_map = {}

    def reset(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

            elif item.layout() is not None:
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                item.layout().deleteLater()

    def clear_properties(self):
        self.reset()

        no_snippet_label = StrongBodyLabel(
            text='Please select or add a Snippet.'
        )
        setFont(no_snippet_label, fontSize=14)
        no_snippet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(no_snippet_label)

    def set_snippet(self, snippet: BaseSnippet, meta_data: MetaData):
        self._current_snippet = snippet
        self._meta_data = meta_data
        self._update_properties()

    def update_motions(self, widgets: dict[str, Any], model_id: int):
        current_model = next((model for model in self._meta_data.models if model['id'] == model_id), None)
        if "data.motion" in widgets:
            motion_widget: ComboBox = widgets["data.motion"].subwidget
            motion_widget.clear()

            if current_model:
                motion_widget.addItems(current_model['motions'])

        if "data.facial" in widgets:
            facial_widget: ComboBox = widgets["data.facial"].subwidget
            facial_widget.clear()

            if current_model:
                facial_widget.addItems(current_model['expression'])

    def _update_properties(self):
        if self._current_snippet is None:
            self.clear_properties()
            return

        self.reset()

        properties_layout = QVBoxLayout()
        properties_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        properties_layout.setContentsMargins(0, 0, 0, 0)
        properties_layout.setSpacing(2)
        self._widget_map = {}

        def create_input_widget(_key, _value, parent_key=""):
            full_key = f"{parent_key}.{_key}" if parent_key else _key

            def set_model(model_name: str):
                model_id_result = [model['id'] for model in self._meta_data.models if
                                   model['model_name'] == model_name.split(' #')[0]][0]
                self._current_snippet.set_property(full_key, model_id_result)
                self.update_motions(self._widget_map, model_id_result)

            def set_image(image_name: str):
                image_id_result = [image['id'] for image in self._meta_data.images if
                                   image['name'] == image_name.split(' #')[0]][0]

                self._current_snippet.set_property(full_key, image_id_result)

            def model_property_standard_combo_box() -> tuple[EditableComboBox, dict]:
                sub_widget_ = EditableComboBox()
                sub_widget_.returnPressed.disconnect()
                sub_widget_.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
                current_model_id = self._current_snippet.properties.get('data').get('modelId')
                current_model_ = next((model for model in self._meta_data.models if model['id'] == current_model_id),
                                     None)
                return sub_widget_, current_model_

            if full_key == 'data.motion':
                sub_widget, current_model = model_property_standard_combo_box()
                if current_model:
                    motions = current_model.get('motions', [])

                    completer = FuzzyCompleter(motions)
                    completer.setMaxVisibleItems(20)
                    sub_widget.setCompleter(completer)

                    sub_widget.addItems(motions)

                    if _value == "":
                        _value = "None"

                    if _value in motions:
                        sub_widget.setCurrentText(_value)

                sub_widget.currentTextChanged.connect(
                    lambda val: self._current_snippet.set_property(
                        full_key, val if val != "None" else ""
                    )
                )

            elif full_key == 'data.facial':
                sub_widget, current_model = model_property_standard_combo_box()
                if current_model:
                    expressions = current_model.get('expressions', [])

                    completer = FuzzyCompleter(expressions)
                    completer.setMaxVisibleItems(20)
                    sub_widget.setCompleter(completer)

                    sub_widget.addItems(expressions)

                    if _value == "":
                        _value = "None"

                    if _value in expressions:
                        sub_widget.setCurrentText(_value)

                sub_widget.currentTextChanged.connect(
                    lambda val: self._current_snippet.set_property(
                        full_key, val if val != "None" else ""
                    )
                )

            elif _key == 'modelId':
                sub_widget = ComboBox()
                sub_widget.addItems([f'{model["model_name"]} #{model["id"]}' for model in self._meta_data.models])
                result_list = [f'{model["model_name"]} #{model["id"]}' for model in self._meta_data.models if
                               model['id'] == _value]

                sub_widget.currentTextChanged.connect(lambda model_name: set_model(model_name))

                if len(result_list) != 0:
                    sub_widget.setCurrentText(
                        result_list[0],
                    )

            elif _key == 'imageId':
                sub_widget = ComboBox()
                sub_widget.addItems([f'{model["name"]} #{model["id"]}' for model in self._meta_data.images])
                result_list = [f'{model["name"]} #{model["id"]}' for model in self._meta_data.images if
                               model['id'] == _value]

                sub_widget.currentTextChanged.connect(lambda val: set_image(val))

                if len(result_list) != 0:
                    sub_widget.setCurrentText(
                        result_list[0],
                    )

            elif isinstance(_value, bool):
                sub_widget = SwitchButton()
                sub_widget.setChecked(_value)
                sub_widget.checkedChanged.connect(lambda checked: self._current_snippet.set_property(full_key, checked))
            elif isinstance(_value, int):
                sub_widget = SpinBox()
                sub_widget.setSingleStep(1)
                sub_widget.setFixedHeight(26)
                sub_widget.setRange(-10000, 10000)
                sub_widget.setValue(_value)
                sub_widget.valueChanged.connect(lambda val: self._current_snippet.set_property(full_key, val))
            elif isinstance(_value, float):
                sub_widget = DoubleSpinBox()
                sub_widget.setSingleStep(0.01)
                sub_widget.setFixedHeight(26)
                sub_widget.setDecimals(2)
                sub_widget.setRange(-10000, 10000)
                sub_widget.setValue(_value)
                sub_widget.valueChanged.connect(lambda val: self._current_snippet.set_property(full_key, val))
            elif isinstance(_value, str):
                sub_widget = LineEdit()
                sub_widget.setFixedHeight(26)
                sub_widget.setText(_value)
                sub_widget.textChanged.connect(lambda text: self._current_snippet.set_property(full_key, text))
            elif isinstance(_value, dict):
                for sub_key, sub_value in _value.items():
                    create_input_widget(sub_key, sub_value, full_key)
                return
            elif isinstance(_value, enum.Enum):
                sub_widget = ComboBox()
                enum_class = _value.__class__
                members = [f'{enum_class.__name__}.{name}' for name in enum_class.__members__]
                sub_widget.addItems(members)
                sub_widget.setCurrentIndex(members.index(f'{enum_class.__name__}.{_value.name}'))
                sub_widget.currentTextChanged.connect(
                    lambda val: self._current_snippet.set_property(full_key, enum_class(val.split('.')[1]))
                )
            else:
                print(type(_value))
                return

            block = SnippetPropertyInputWidget(full_key, sub_widget)
            self._widget_map[full_key] = block

        for key, value in self._current_snippet.properties.items():
            create_input_widget(key, value)

        for widget in self._widget_map.values():
            properties_layout.addWidget(widget)

        self._layout.addLayout(properties_layout)
