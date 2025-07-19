import copy
import enum
import json
from enum import Enum


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


class BaseSnippet:
    def __init__(self, snippet_type: str, properties: dict):
        self._type = snippet_type
        self._properties: dict = {
            'wait': True,
            'delay': 0
        }
        if properties:
            self._properties['data'] = properties

    @property
    def type(self):
        return self._type

    @property
    def properties(self):
        return self._properties

    def set_property(self, key, value):
        if '.' in key:
            keys = key.split('.')
            current_dict = self._properties
            for k in keys[:-1]:
                if k in current_dict:
                    current_dict = current_dict[k]
                else:
                    return
            current_dict[keys[-1]] = value
        else:
            self._properties[key] = value

    def copy(self):
        new_properties = copy.deepcopy(self._properties)
        new_snippet = BaseSnippet(self._type, {})
        new_snippet._properties = new_properties
        return new_snippet

    def build(self) -> dict:
        def process_data(data_dict: dict):
            result = {}
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    result[key] = process_data(value)
                elif isinstance(value, list):
                    new_list = []
                    for item in value:
                        if isinstance(item, dict):
                            new_list.append(process_data(item))
                        elif isinstance(item, enum.Enum):
                            new_list.append(item.value)
                        else:
                            new_list.append(item)
                    result[key] = new_list
                elif isinstance(value, enum.Enum):
                    result[key] = value.value
                else:
                    result[key] = value
            return result

        data = {
            'type': self.type
        }
        properties = process_data(self._properties)
        data.update(properties)
        return data


class ChangeBackgroundImageSnippet(BaseSnippet):
    def __init__(self, image_id: int):
        super().__init__(
            'ChangeBackgroundImage',
            {
                'imageId': image_id
            }
        )


class ChangeLayoutModeSnippet(BaseSnippet):
    def __init__(self, mode: LayoutModes):
        super().__init__(
            'ChangeLayoutMode',
            {
                'mode': mode
            }
        )


class HideTalkSnippet(BaseSnippet):
    def __init__(self):
        super().__init__(
            'HideTalk',
            {}
        )


class LayoutAppearSnippet(BaseSnippet):
    def __init__(self, model_id: int, from_side: Sides, from_offset: float, to_side: Sides, to_offset: float,
                 motion: str, facial: str, move_speed: MoveSpeed):
        super().__init__(
            'LayoutAppear',
            {
                'modelId': model_id,
                'from': {
                    'side': from_side,
                    'offset': from_offset
                },
                'to': {
                    'side': to_side,
                    'offset': to_offset
                },
                'motion': motion,
                'facial': facial,
                'moveSpeed': move_speed
            }
        )


class LayoutClearSnippet(BaseSnippet):
    def __init__(self, model_id: int, from_side: Sides, from_offset: float, to_side: Sides, to_offset: float,
                 move_speed: MoveSpeed):
        super().__init__(
            'LayoutClear',
            {
                'modelId': model_id,
                'from': {
                    'side': from_side,
                    'offset': from_offset
                },
                'to': {
                    'side': to_side,
                    'offset': to_offset
                },
                'moveSpeed': move_speed
            }
        )


class MotionSnippet(BaseSnippet):
    def __init__(self, model_id: int, motion: str, facial: str):
        super().__init__(
            'Motion',
            {
                'modelId': model_id,
                'motion': motion,
                'facial': facial
            }
        )


class MoveSnippet(BaseSnippet):
    def __init__(self, model_id: int, from_side: Sides, from_offset: float, to_side: Sides, to_offset: float,
                 move_speed: MoveSpeed):
        super().__init__(
            'Move',
            {
                'modelId': model_id,
                'from': {
                    'side': from_side,
                    'offset': from_offset
                },
                'to': {
                    'side': to_side,
                    'offset': to_offset
                },
                'moveSpeed': move_speed
            }
        )


class TalkSnippet(BaseSnippet):
    def __init__(self, speaker: str, content: str):
        super().__init__(
            'Talk',
            {
                'speaker': speaker,
                'content': content
            }
        )


class TelopSnippet(BaseSnippet):
    def __init__(self, content: str):
        super().__init__(
            'Telop',
            {
                'content': content
            }
        )


class BlackInSnippet(BaseSnippet):
    def __init__(self, duration: int):
        super().__init__(
            'BlackIn',
            {
                'duration': duration
            }
        )

class BlackOutSnippet(BaseSnippet):
    def __init__(self, duration: int):
        super().__init__(
            'BlackOut',
            {
                'duration': duration
            }
        )


SNIPPETS = [
    ChangeBackgroundImageSnippet(0),
    ChangeLayoutModeSnippet(LayoutModes.Normal),
    HideTalkSnippet(),
    LayoutAppearSnippet(0, Sides.Center, 0.0, Sides.Center, 0.0, '', '', MoveSpeed.Normal),
    LayoutClearSnippet(0, Sides.Center, 0.0, Sides.Center, 0.0, MoveSpeed.Normal),
    MotionSnippet(0, '', ''),
    MoveSnippet(0, Sides.Center, 0.0, Sides.Center, 0.0, MoveSpeed.Normal),
    TalkSnippet('', ''),
    TelopSnippet(''),
    BlackInSnippet(500),
    BlackOutSnippet(500),
]


def get_snippet(snippet_type: str) -> BaseSnippet:
    return next((snippet for snippet in SNIPPETS if snippet.type == snippet_type), None)
