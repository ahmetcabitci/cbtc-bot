"""CBTC Bot ses seviyesi yonetimi."""


class AudioController:
    def __init__(self, volume=50, max_volume=100):
        if type(max_volume) is not int or not 0 <= max_volume <= 100:
            raise ValueError("Maksimum ses 0 ile 100 arasinda olmalidir.")
        self.max_volume = max_volume
        self.volume = 0
        self.set_volume(volume)

    def get_volume(self):
        return self.volume

    def set_volume(self, value):
        if type(value) is not int or not 0 <= value <= self.max_volume:
            raise ValueError("0 ila 100 arasında değer girilmelidir.")

        self.volume = value
        return self.volume
