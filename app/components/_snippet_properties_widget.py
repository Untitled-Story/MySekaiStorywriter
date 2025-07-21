import enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import StrongBodyLabel, setFont, SpinBox, SubtitleLabel, DoubleSpinBox, LineEdit, \
    SwitchButton, ComboBox, MessageBoxBase

from app.components import SnippetPropertyInputWidget
from app.snippets import BaseSnippet


class SnippetPropertiesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)

        self.clear_properties()
        self._current_snippet = None
        self._current_data = {}

    def _reset(self):
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
        self._reset()

        no_snippet_label = StrongBodyLabel(
            text='Please select or add a Snippet.'
        )
        setFont(no_snippet_label, fontSize=14)
        no_snippet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(no_snippet_label)

    def set_snippet(self, snippet: BaseSnippet):
        self._current_snippet = snippet
        self._update_properties()

    def _update_properties(self):
        if self._current_snippet is None:
            self.clear_properties()
            return

        self._reset()

        properties_layout = QVBoxLayout()
        properties_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        properties_layout.setContentsMargins(0, 0, 0, 0)
        properties_layout.setSpacing(2)

        self._layout.addLayout(properties_layout)

        def create_input_widget(_key, _value, parent_key=""):
            full_key = f"{parent_key}.{_key}" if parent_key else _key
            if isinstance(_value, bool):
                widget = SwitchButton()
                widget.setChecked(_value)
                widget.checkedChanged.connect(lambda checked: self._current_snippet.set_property(full_key, checked))
            elif isinstance(_value, int):
                widget = SpinBox()
                widget.setSingleStep(1)
                widget.setFixedHeight(26)
                widget.setRange(-10000, 10000)
                widget.setValue(_value)
                widget.valueChanged.connect(lambda val: self._current_snippet.set_property(full_key, val))
            elif isinstance(_value, float):
                widget = DoubleSpinBox()
                widget.setSingleStep(0.01)
                widget.setFixedHeight(26)
                widget.setDecimals(2)
                widget.setRange(-10000, 10000)
                widget.setValue(_value)
                widget.valueChanged.connect(lambda val: self._current_snippet.set_property(full_key, val))
            elif isinstance(_value, str):
                widget = LineEdit()
                widget.setFixedHeight(26)
                widget.setText(_value)
                widget.textChanged.connect(lambda text: self._current_snippet.set_property(full_key, text))
            elif isinstance(_value, dict):
                for sub_key, sub_value in _value.items():
                    create_input_widget(sub_key, sub_value, full_key)
                return
            elif isinstance(_value, enum.Enum):
                widget = ComboBox()
                enum_class = _value.__class__
                members = [f'{enum_class.__name__}.{name}' for name in enum_class.__members__]
                widget.addItems(members)
                widget.setCurrentIndex(members.index(f'{enum_class.__name__}.{_value.name}'))
                widget.currentTextChanged.connect(
                    lambda val: self._current_snippet.set_property(full_key, enum_class(val.split('.')[1]))
                )
            else:
                print(type(_value))
                return

            block = SnippetPropertyInputWidget(full_key, widget)
            properties_layout.addWidget(block)

        for key, value in self._current_snippet.properties.items():
            create_input_widget(key, value)