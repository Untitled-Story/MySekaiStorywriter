from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QSizePolicy, QStackedWidget
from qfluentwidgets import ListWidget, Pivot, \
    TitleLabel, HorizontalSeparator, VerticalSeparator, SubtitleLabel, EditableComboBox, PushButton, PrimaryPushButton

from app.components import Live2DWidget
from app.utils import FuzzyCompleter


class ModelManageFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 0, 0, 0)
        main_layout.setSpacing(5)

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 5, 0, 0)
        h_layout.setSpacing(5)

        main_layout.addLayout(h_layout)

        l_layout = QVBoxLayout()
        h_layout.addLayout(l_layout, 2)

        h_layout.addWidget(VerticalSeparator())

        r_layout = QVBoxLayout()
        h_layout.addLayout(r_layout, 8)

        title1 = SubtitleLabel(text='Online Model List')
        title1.setStyleSheet("padding-bottom:3px;")
        l_layout.addWidget(title1)

        l_v_layout = QVBoxLayout()
        l_layout.addLayout(l_v_layout)

        self.online_model_combo_box = EditableComboBox()
        self.online_model_combo_box.returnPressed.disconnect()
        l_v_layout.addWidget(self.online_model_combo_box)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 7, 0, 7)
        buttons_layout.setSpacing(10)
        l_v_layout.addLayout(buttons_layout)

        preview_button = PushButton(text='Preview')
        buttons_layout.addWidget(preview_button)

        add_button = PrimaryPushButton(text='Add')
        buttons_layout.addWidget(add_button)

        l_v_layout.addWidget(HorizontalSeparator())


        self.listWidget2 = ListWidget()

        self.listWidget2.addItems(['1', '2', '3'])


        l_v_layout.addWidget(self.listWidget2)

        l_v_layout.setStretch(0, 1)
        l_v_layout.setStretch(1, 1)

        live2d_preview = Live2DWidget(self)
        r_layout.addWidget(live2d_preview)

        # 添加拉伸项，使内容居上
        l_layout.addStretch(1)

    def update_data(self, model_list: list):
        completer = FuzzyCompleter(model_list)
        completer.setMaxVisibleItems(20)
        self.online_model_combo_box.setCompleter(completer)
        self.online_model_combo_box.addItems(model_list)


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

        self.model_list = []

    def on_data_loaded(self, model_list: list):
        self.model_list = model_list

        model_display_names = sorted([model['modelName'] for model in self.model_list])

        self.model_manage_frame.update_data(model_display_names)

    def add_sub_interface(self, widget: QFrame, object_name: str, text: str):
        widget.setObjectName(object_name)
        self.stacked_widget.addWidget(widget)

        self.pivot.addItem(
            routeKey=object_name,
            text=text,
            onClick=lambda: self.stacked_widget.setCurrentWidget(widget)
        )
