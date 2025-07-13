import json
import os
from ..utils import traceback_error
from .models import Camera

FILE_PATH = os.path.join(os.path.dirname(__file__), 'cameras.json')

def save_camera(camera: Camera):
    try:
        try:
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        updated = False
        for i, c in enumerate(data):
            if c['name'] == camera.name:
                data[i] = camera.__dict__
                updated = True
                break

        if not updated:
            data.append(camera.__dict__)

        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception:
        traceback_error()

def add_new_camera(name, focal_length, sensor_size, pix_along, pix_across):
    camera = Camera(name, focal_length, sensor_size, pix_along, pix_across)
    save_camera(camera)
    return camera

def delete_camera(camera: Camera):
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data = [c for c in data if c['name'] != camera.name]
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception:
        traceback_error()


def load_cameras():
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = f.read().strip()
            if data:
                return [Camera(**c) for c in json.loads(data)]
    except Exception:
        traceback_error()
    return []
