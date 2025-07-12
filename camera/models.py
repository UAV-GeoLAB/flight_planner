class Camera():
    def __init__(self, name, focal_length, sensor_size,
                 pixels_along_track, pixels_across_track) -> None:
        self.name = name
        self.focal_length = focal_length
        self.sensor_size = sensor_size
        self.pixels_along_track = pixels_along_track
        self.pixels_across_track = pixels_across_track
