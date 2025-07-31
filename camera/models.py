import numpy as np

class Camera():
    def __init__(self, name, focal_length, sensor_size,
                 pixels_along_track, pixels_across_track) -> None:
        self.name = name
        self.focal_length = focal_length
        self.sensor_size = sensor_size
        self.pixels_along_track = pixels_along_track
        self.pixels_across_track = pixels_across_track

    def image_corners(self):
        """Return array of x, y, z coordinates of image corners in image space."""
        x = self.sensor_size * self.pixels_along_track / 2
        y = self.sensor_size * self.pixels_across_track / 2
        image_corners_coordinates = np.array([
            [-x,  y, -self.focal_length],
            [-x, -y, -self.focal_length],
            [ x, -y, -self.focal_length],
            [ x,  y, -self.focal_length]
        ])
        return image_corners_coordinates
