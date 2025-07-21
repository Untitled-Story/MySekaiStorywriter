from qfluentwidgets import LineEdit, SubtitleLabel, MessageBoxBase


class InputMetadataMessageBox(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        title_label = SubtitleLabel(text='Saving your story...')

        self.title_edit = LineEdit(self)
        self.title_edit.setPlaceholderText('Input Title')

        self.viewLayout.addWidget(title_label)
        self.viewLayout.addWidget(self.title_edit)

        self.widget.setMinimumWidth(350)
