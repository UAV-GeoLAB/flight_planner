from .models import Camera
from .storage import save_camera, delete_camera, load_cameras

def get_camera_by_name(name, cameras):
    return next((c for c in cameras if c.name == name), None)

def add_new_camera(name, focal_length, sensor_size, pix_along, pix_across):
    camera = Camera(name, focal_length, sensor_size, pix_along, pix_across)
    save_camera(camera)
    return camera

def remove_camera(camera: Camera):
    delete_camera(camera)

def get_all_cameras():
    return sorted(load_cameras(), key=lambda c: c.name)
