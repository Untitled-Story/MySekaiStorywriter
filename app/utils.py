import os
from urllib.parse import urlparse

import httpx
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


def build_model_base_json(model_list: list, model_name: str):
    model_info: dict = [model for model in model_list if model['modelName'] == model_name][0]
    model_url = f"https://storage.sekai.best/sekai-live2d-assets/live2d/model/{model_info['modelPath']}"
    return f"http://127.0.0.1:4521/get/{model_url}/{model_info['modelFile']}"


def extract_url_path(url):
    parsed = urlparse(url)

    path = parsed.path

    if not path:
        return url

    dirname, _ = os.path.split(path)

    scheme = parsed.scheme
    netloc = parsed.netloc
    query = parsed.query
    fragment = parsed.fragment

    new_path = dirname + '/' if dirname else '/'

    new_url = scheme + '://' + netloc + new_path

    if query:
        new_url += '?' + query
    if fragment:
        new_url += '#' + fragment

    return new_url

def get_motions(main_path) -> dict:
    result = {
        "model": {},
        "special": {},
        "common": {},
        "model_url": '',
        "special_url": '',
        "common_url": ''
    }

    model_motion_url = extract_url_path(main_path) + "motions/BuildMotionData.json"

    motion_url_base = extract_url_path(main_path).replace("live2d/model", "live2d/motion")[:-1]

    special_motions_url = motion_url_base + "_motion_base/BuildMotionData.json"
    common_motions_url = '_'.join(motion_url_base.split("_")[:-1]) + "_motion_base/BuildMotionData.json"

    result['model_url'] = model_motion_url
    result['special_url'] = special_motions_url
    result['common_url'] = common_motions_url

    model_motion_result = httpx.get(model_motion_url)
    special_motions_result = httpx.get(special_motions_url)
    common_motions_result = httpx.get(common_motions_url)

    if model_motion_result.status_code == 200:
        model_motion_data = model_motion_result.json()
        result['model'] = model_motion_data

    if special_motions_result.status_code == 200:
        special_motions_data = special_motions_result.json()
        result['special'] = special_motions_data

    if common_motions_result.status_code == 200:
        common_motions_data = common_motions_result.json()
        result['common'] = common_motions_data

    return result