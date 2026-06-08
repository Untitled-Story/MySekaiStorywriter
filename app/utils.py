import os
import re
from collections import OrderedDict
from urllib.parse import unquote, urlparse

import httpx
from PySide6.QtCore import QSortFilterProxyModel, Qt, QStringListModel
from PySide6.QtWidgets import QCompleter
from httpx_retries import Retry, RetryTransport

from .config import SEKAI_LIVE2D_ASSET_BASE_URL

HTTP_USER_AGENT = "MySekaiStorywriter/v0.5.0"
HTTP_HEADERS = {"User-Agent": HTTP_USER_AGENT}


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


def build_model_base_json(server_host: str, model_list: list, model_name: str):
    model_info: dict = [model for model in model_list if model['modelName'] == model_name][0]
    model_url = f"{SEKAI_LIVE2D_ASSET_BASE_URL}/model/{model_info['modelPath']}"
    return f"{server_host}/get/{model_url}/{model_info['modelFile']}"


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


def _empty_motion_data() -> dict:
    return {
        "motionBasePath": "",
        "motions": [],
        "facials": [],
        "additionalMotions": [],
        "asset_url_base": "",
        "model_path": "",
        "motion_base_url": "",
        "additional_url": "",
    }


def _fetch_json(client: httpx.Client, url: str) -> dict | None:
    try:
        response = client.get(url)
        if response.status_code != 200:
            return None
        return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def _strip_model_suffix(filename: str) -> str:
    for suffix in (".model3.json", ".model.json"):
        if filename.endswith(suffix):
            return filename[:-len(suffix)]
    return os.path.splitext(filename)[0]


def _parse_model_entry(main_path: str) -> tuple[str, str, str]:
    decoded_path = unquote(main_path)
    marker = "/model/"
    marker_index = decoded_path.rfind(marker)
    if marker_index < 0:
        raise ValueError(f"Cannot parse model path from URL: {main_path}")

    asset_url_base = decoded_path[:marker_index].rstrip("/")
    model_asset_path = decoded_path[marker_index + len(marker):].strip("/")
    parts = model_asset_path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse model entry from URL: {main_path}")

    entry_path = "/".join(parts[:-1])
    base_name = parts[-2]

    return asset_url_base, entry_path, base_name


def _resolve_model_dir(entry_path: str) -> str:
    parts = entry_path.split("/")
    model_dir = "/".join(parts[:-1])

    if len(parts) >= 3 and parts[1] == "collabo":
        model_folder = parts[-1]
        if re.match(r"^\d+_", model_folder):
            fixed = parts[:]
            fixed[1] = "main"
            return "/".join(fixed[:-1])
        return "/".join(parts[:-2])

    return model_dir


def _generate_base_name_variants(base_name: str) -> list[str]:
    variants = []

    if base_name.startswith("v2_clb"):
        variants.append(re.sub(r"^v2_clb", "v2_", base_name))

    if "_back" in base_name:
        char_match = re.match(r"^(v2_\d+[a-z]+)", base_name)
        if char_match:
            variants.append(f"{char_match.group(1)}_back")

    without_trailing_digits = re.sub(r"_[a-z]?\d+$", "", base_name)
    if without_trailing_digits != base_name:
        variants.append(without_trailing_digits)

    return variants


def _try_motion_base(
        client: httpx.Client,
        asset_url_base: str,
        model_dir: str,
        base_name: str,
) -> tuple[dict, str, str] | None:
    base_path = f"{model_dir}/{base_name}_motion_base" if model_dir else f"{base_name}_motion_base"
    url = f"{asset_url_base}/motion/{base_path}/BuildMotionData.json"
    data = _fetch_json(client, url)
    if data:
        return data, base_path, url
    return None


def _try_stripped_base_names(
        client: httpx.Client,
        asset_url_base: str,
        model_dir: str,
        base_name: str,
) -> tuple[dict, str, str] | None:
    current = base_name
    while "_" in current:
        current = re.sub(r"_[^_]+$", "", current)
        result = _try_motion_base(client, asset_url_base, model_dir, current)
        if result:
            return result
    return None


def get_motions(main_path) -> dict:
    result = _empty_motion_data()

    try:
        asset_url_base, entry_path, base_name = _parse_model_entry(main_path)
    except ValueError:
        return result

    model_dir = _resolve_model_dir(entry_path)
    result["asset_url_base"] = asset_url_base
    result["model_path"] = entry_path

    retry = Retry(total=10, backoff_factor=0.5)
    with httpx.Client(headers=HTTP_HEADERS, transport=RetryTransport(retry=retry)) as client:
        motion_base_result = _try_motion_base(client, asset_url_base, model_dir, base_name)

        if not motion_base_result:
            for variant in _generate_base_name_variants(base_name):
                motion_base_result = _try_motion_base(client, asset_url_base, model_dir, variant)
                if motion_base_result:
                    break

        if not motion_base_result:
            motion_base_result = _try_stripped_base_names(client, asset_url_base, model_dir, base_name)

        if motion_base_result:
            motion_base_data, motion_base_path, motion_base_url = motion_base_result
            result["motionBasePath"] = motion_base_path
            result["motion_base_url"] = motion_base_url
            result["motions"] = motion_base_data.get("motions", [])
            result["facials"] = motion_base_data.get("expressions", [])

        additional_url = f"{asset_url_base}/model/{entry_path}/motions/BuildMotionData.json"
        result["additional_url"] = additional_url
        additional_data = _fetch_json(client, additional_url)
        if additional_data:
            result["additionalMotions"] = additional_data.get("motions", [])

    return result

def to_ordered_dict(obj):
    if isinstance(obj, dict):
        return OrderedDict((k, to_ordered_dict(v)) for k, v in obj.items())
    elif isinstance(obj, list):
        return [to_ordered_dict(item) for item in obj]
    return obj
