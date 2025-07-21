from PySide6.QtCore import QSortFilterProxyModel, Qt, QStringListModel
from PySide6.QtWidgets import QCompleter


class FuzzyFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)
        self.pattern = ""

    def set_filter_pattern(self, pattern):
        self.pattern = pattern
        self.invalidateFilter()

    @staticmethod
    def fuzzy_match(pattern, text):
        """Simple fuzzy matching: all pattern chars appear in order in text"""
        pattern = pattern.lower()
        text = text.lower()
        it = iter(text)
        return all(char in it for char in pattern)

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.pattern:
            return True
        model = self.sourceModel()
        index = model.index(source_row, self.filterKeyColumn(), source_parent)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        return self.fuzzy_match(self.pattern, text)


class FuzzyCompleter(QCompleter):
    def __init__(self, model_list: list, parent=None):
        self.proxy_model = FuzzyFilterProxyModel()
        self.proxy_model.setSourceModel(QStringListModel(model_list))
        super().__init__(self.proxy_model, parent)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterMode(Qt.MatchFlag.MatchContains)

    def update(self, pattern):
        self.proxy_model.set_filter_pattern(pattern)
        self.complete()
