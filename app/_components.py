import enum
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame
from qfluentwidgets import isDarkTheme, StrongBodyLabel, setFont, SpinBox, SubtitleLabel, DoubleSpinBox, LineEdit, \
    SwitchButton, ComboBox, MessageBoxBase, IndeterminateProgressRing, CaptionLabel

from app._snippets import BaseSnippet


class Live2DWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class SnippetPropertyInputWidget(QWidget):
    def __init__(self, title: str, widget: QWidget, parent=None):
        super().__init__(parent)

        self._layout = QHBoxLayout()
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setLayout(self._layout)

        title_widget = SubtitleLabel(text=f'{title}: ')
        setFont(title_widget, fontSize=16)
        self._layout.addWidget(title_widget)
        self._layout.addWidget(widget)


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


class InputMetadataMessageBox(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        title_label = SubtitleLabel(text='Saving your story...')

        self.title_edit = LineEdit(self)
        self.title_edit.setPlaceholderText('Input Title')

        self.version_edit = LineEdit(self)
        self.version_edit.setPlaceholderText('Input Version')

        self.warning_label = CaptionLabel(text="Version is not validated (X.X.X)")
        self.warning_label.setTextColor("#cf1010", QColor(255, 28, 32))

        self.viewLayout.addWidget(title_label)
        self.viewLayout.addWidget(self.title_edit)
        self.viewLayout.addWidget(self.version_edit)
        self.viewLayout.addWidget(self.warning_label)
        self.warning_label.hide()

        self.widget.setMinimumWidth(350)

    def validate(self):
        is_valid = bool(re.match(r'^\d+\.\d+\.\d+$', self.version_edit.text()))
        self.warning_label.setHidden(is_valid)
        return is_valid


class SaveFileMessageBox(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.buttonLayout.removeWidget(self.cancelButton)
        self.cancelButton.hide()
        self.cancelButton.clicked.disconnect()
        self.cancelButton.setParent(None)
        self.cancelButton.deleteLater()
        self.buttonLayout.update()
        self.update()

        title_label = SubtitleLabel(text='Saving your story...')

        progress_ring_layout = QHBoxLayout()
        progress_ring_layout.setContentsMargins(0, 20, 0, 20)
        progress_ring_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        progress_ring = IndeterminateProgressRing()
        progress_ring_layout.addWidget(progress_ring)

        self.yesButton.setDisabled(True)

        self.viewLayout.addWidget(title_label)
        self.viewLayout.addLayout(progress_ring_layout)

        self.widget.setMinimumWidth(350)
