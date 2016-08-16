class ResourceTifFilesCount:
    def __init__(self):
        self.tif_count = 0

    def increase(self):
        self.tif_count += 1

    def reset(self):
        self.tif_count = 0

    def get(self):
        return self.tif_count
