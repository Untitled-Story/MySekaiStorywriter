import json
from typing import Optional

from PySide6.QtCore import Signal, QObject

from app.utils import get_motions


class MetaData(QObject):
    model_updated = Signal(dict)
    image_updated = Signal(dict)

    def __init__(self, models: Optional[list] = None, images: Optional[list] = None):
        super().__init__()
        if images is None:
            images = []
        if models is None:
            models = []
        self._models = models
        self._images = images

    @property
    def models(self):
        return self._models

    @property
    def images(self):
        return self._images

    def remove_model(self, id_: int):
        i = [model for model in self._models if model['id'] == id_][0]
        self._models.remove(i)
        self.renumber_models()
        self.model_updated.emit(i)

    def renumber_models(self):
        result = []
        i = 0
        for model in self._models:
            result.append({
                "id": i,
                "model_name": model['model_name'],
                "path": model['path'],
                "downloaded": model['downloaded'],
                "motions": model['motions'],
                "version": model['version'],
                "expressions": model['expressions'],
                "normal_scale": model.get("normal_scale", 2.1),
                "small_scale": model.get("small_scale", 1.8),
                "anchor": model.get("anchor", 0.5),
            })
            i += 1
        self._models = result

    def add_model(self, model_name: str, path: str, downloaded: bool, id_: Optional[int] = None) -> dict:
        self.renumber_models()

        motions = ["None"]
        expressions = ["None"]

        if not downloaded:
            result = get_motions(path)

            if result['model']:
                if 'motions' in result['model']:
                    motions.extend(result['model']['motions'])
                if 'expressions' in result['model']:
                    expressions.extend(result['model']['expressions'])
            if result['special']:
                if 'motions' in result['special']:
                    motions.extend(result['special']['motions'])
                if 'expressions' in result['special']:
                    expressions.extend(result['special']['expressions'])
            if result['common']:
                if 'motions' in result['common']:
                    motions.extend(result['common']['motions'])
                if 'expressions' in result['common']:
                    expressions.extend(result['common']['expressions'])
            model_version = 3
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

                if 'motions' in data:
                    # Cubism2
                    motions_data: dict = data.get('motions')
                    if motions_data:
                        local_motions = motions_data.keys()
                        for motion in local_motions:
                            motions.append(motion)
                    model_version = 2
                else:
                    # Cubism4
                    motions_data: dict = data["FileReferences"].get('Motions')

                    if motions_data:
                        local_motions = motions_data.keys()
                        for motion in local_motions:
                            if motion.startswith("face_"):
                                expressions.append(motion)
                            else:
                                motions.append(motion)
                    model_version = 3

        if not id_:
            id_ = len(self._models)

        data = {
            "id": id_,
            "model_name": model_name,
            "path": path,
            "downloaded": downloaded,
            "motions": motions,
            "expressions": expressions,
            "version": model_version,
            "normal_scale": 2.1,
            "small_scale": 1.8,
            "anchor": 0.5,
        }
        self.model_updated.emit(data)
        self._models.append(data)
        return data

    def renumber_images(self):
        result = []
        i = 0
        for image in self._images:
            result.append({
                "id": i,
                "name": image['name'],
                "path": image['path'],
            })
            i += 1
        self._images = result

    def remove_image(self, id_: int):
        i = [image for image in self._images if image['id'] == id_][0]
        self._images.remove(i)
        self.renumber_images()
        self.image_updated.emit(i)

    def add_image(self, image_name: str, image_path: str, id_: Optional[int] = None) -> dict:
        if not id_:
            id_ = len(self._images)

        self.renumber_images()
        data = {
            "id": id_,
            "name": image_name,
            "path": image_path
        }

        self.image_updated.emit(data)
        self._images.append(data)

        return data

    def reset_model(self) -> None:
        self._models = []

    def reset_image(self) -> None:
        self._images = []

    def reset_all(self) -> None:
        self.reset_model()
        self.reset_image()
