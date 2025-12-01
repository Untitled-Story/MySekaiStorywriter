import copy
import enum
from enum import Enum
from app.utils import to_ordered_dict


class LayoutModes(Enum):
    Normal = 'Normal'
    Three = 'Three'


class Sides(Enum):
    Center = 'Center'
    Left = 'Left'
    Right = 'Right'


class MoveSpeed(Enum):
    Slow = 'Slow'
    Normal = 'Normal'
    Fast = 'Fast'
    Immediate = 'Immediate'


class Curves(Enum):
    Linear = 'Linear'
    Sine = 'Sine'
    Cosine = 'Cosine'


class BaseSnippet:
    def __init__(self, snippet_type: str, properties: dict):
        self._type = snippet_type
        self.properties: dict = {
            'wait': True,
            'delay': float(0)
        }
        if properties:
            self.properties['data'] = properties

    @property
    def type(self):
        return self._type

    def _get_obj_and_key(self, path):
        keys = path.split('.') if '.' in path else [path]
        current = self.properties

        for i, k in enumerate(keys[:-1]):
            if isinstance(current, dict) and k in current:
                current = current[k]
            elif isinstance(current, list):
                try:
                    idx = int(k)
                    current = current[idx]
                except:
                    return None, None
            else:
                return None, None

        return current, keys[-1]

    def set_property(self, key, value):
        obj, last_key = self._get_obj_and_key(key)
        if obj is not None:
            if isinstance(obj, dict):
                obj[last_key] = value
            elif isinstance(obj, list):
                try:
                    idx = int(last_key)
                    if 0 <= idx < len(obj):
                        obj[idx] = value
                except:
                    pass

    def add_list_item(self, key):
        obj, last_key = self._get_obj_and_key(key)
        if obj is not None and isinstance(obj, dict) and isinstance(obj[last_key], list):
            new_item = self.get_default_item(last_key)
            obj[last_key].append(new_item)

    def remove_list_item(self, key, index):
        obj, last_key = self._get_obj_and_key(key)
        if obj is not None and isinstance(obj, dict):
            lst = obj[last_key]
            if isinstance(lst, list) and 0 <= index < len(lst):
                lst.pop(index)

    def get_default_item(self, key: str):
        return {}

    def copy(self):
        new_properties = copy.deepcopy(self.properties)
        new_snippet = self.__class__.__new__(self.__class__)
        # Hacky init to bypass __init__ logic, then overwrite props
        if hasattr(new_snippet, '__init__'):
            # We need to call init to set basic attrs if any, but safely
            pass

            # Use fresh init based on type if possible, else direct copy
        if self._type == 'DoParam':
            return DoParamSnippet(
                model_id=new_properties['data']['modelId'],
                params=new_properties['data']['params']
            )

        # Fallback generic copy
        new_snippet = BaseSnippet(self._type, {})
        new_snippet.properties = new_properties
        return new_snippet

    def build(self) -> dict:
        def process_data(data_dict: dict):
            result = {}
            for key, value in data_dict.items():
                if isinstance(value, str):
                    if '<br>' in value:
                        value = value.replace('<br>', '\n')
                if isinstance(value, dict):
                    result[key] = process_data(value)
                elif isinstance(value, list):
                    new_list = []
                    for item in value:
                        if isinstance(item, dict):
                            new_list.append(process_data(item))
                        elif isinstance(item, enum.Enum):
                            new_list.append(item.value)
                        elif isinstance(item, float):
                            new_list.append(round(item, 2))
                        else:
                            new_list.append(item)
                    result[key] = new_list
                elif isinstance(value, enum.Enum):
                    result[key] = value.value
                elif isinstance(value, float):
                    result[key] = round(value, 2)
                else:
                    result[key] = value
            return result

        data = {'type': self.type}
        properties = process_data(self.properties)
        data.update(properties)
        data = to_ordered_dict(data)
        return data.copy()


class ChangeBackgroundImageSnippet(BaseSnippet):
    def __init__(self, image_id: int):
        super().__init__('ChangeBackgroundImage', {'imageId': image_id})


class ChangeLayoutModeSnippet(BaseSnippet):
    def __init__(self, mode: LayoutModes):
        super().__init__('ChangeLayoutMode', {'mode': mode})


class HideTalkSnippet(BaseSnippet):
    def __init__(self):
        super().__init__('HideTalk', {})


class LayoutAppearSnippet(BaseSnippet):
    def __init__(self, model_id: int, from_side: Sides, from_offset: float, to_side: Sides, to_offset: float,
                 motion: str, facial: str, move_speed: MoveSpeed, hologram: bool, facial_first: bool):
        super().__init__('LayoutAppear', {
            'modelId': model_id,
            'from': {'side': from_side, 'offset': from_offset},
            'to': {'side': to_side, 'offset': to_offset},
            'motion': motion, 'facial': facial, 'moveSpeed': move_speed, 'hologram': hologram,
            'facialFirst': facial_first
        })


class LayoutClearSnippet(BaseSnippet):
    def __init__(self, model_id: int, from_side: Sides, from_offset: float, to_side: Sides, to_offset: float,
                 move_speed: MoveSpeed):
        super().__init__('LayoutClear', {
            'modelId': model_id,
            'from': {'side': from_side, 'offset': from_offset},
            'to': {'side': to_side, 'offset': to_offset},
            'moveSpeed': move_speed
        })


class MotionSnippet(BaseSnippet):
    def __init__(self, model_id: int, motion: str, facial: str, facial_first: bool):
        super().__init__('Motion',
                         {'modelId': model_id, 'motion': motion, 'facial': facial, 'facial_first': facial_first})


class MoveSnippet(BaseSnippet):
    def __init__(self, model_id: int, from_side: Sides, from_offset: float, to_side: Sides, to_offset: float,
                 move_speed: MoveSpeed):
        super().__init__('Move', {
            'modelId': model_id,
            'from': {'side': from_side, 'offset': from_offset},
            'to': {'side': to_side, 'offset': to_offset},
            'moveSpeed': move_speed
        })


class TalkSnippet(BaseSnippet):
    def __init__(self, speaker: str, content: str, model_id: int, voice: str):
        super().__init__('Talk', {'speaker': speaker, 'content': content, 'modelId': model_id, 'voice': voice})


class TelopSnippet(BaseSnippet):
    def __init__(self, content: str):
        super().__init__('Telop', {'content': content})


class BlackInSnippet(BaseSnippet):
    def __init__(self, duration: int):
        super().__init__('BlackIn', {'duration': duration})


class BlackOutSnippet(BaseSnippet):
    def __init__(self, duration: int):
        super().__init__('BlackOut', {'duration': duration})


class DoParamSnippet(BaseSnippet):
    def __init__(self, model_id: int, params: list = None):
        if params is None:
            params = [{
                'paramId': '',
                'start': 0.0,
                'end': 0.0,
                'curve': Curves.Linear,
                'duration': 0.0
            }]
        super().__init__('DoParam', {'modelId': model_id, 'params': params})

    def get_default_item(self, key: str):
        if key == 'params':
            return {
                'paramId': '',
                'start': 0.0,
                'end': 0.0,
                'curve': Curves.Linear,
                'duration': 0.0
            }
        return {}


SNIPPETS = [
    ChangeBackgroundImageSnippet(0),
    ChangeLayoutModeSnippet(LayoutModes.Normal),
    HideTalkSnippet(),
    LayoutAppearSnippet(-1, Sides.Center, 0.0, Sides.Center, 0.0, '', '', MoveSpeed.Normal, False, True),
    LayoutClearSnippet(-1, Sides.Center, 0.0, Sides.Center, 0.0, MoveSpeed.Normal),
    MotionSnippet(-1, '', '', True),
    MoveSnippet(-1, Sides.Center, 0.0, Sides.Center, 0.0, MoveSpeed.Normal),
    TalkSnippet('', '', -1, ''),
    TelopSnippet(''),
    BlackInSnippet(500),
    BlackOutSnippet(500),
    DoParamSnippet(-1),
]


def get_snippet(snippet_type: str) -> BaseSnippet:
    s = next((snippet for snippet in SNIPPETS if snippet.type == snippet_type), None)
    return s.copy() if s else None
