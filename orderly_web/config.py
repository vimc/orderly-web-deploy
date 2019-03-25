import yaml

class OrderlyWebConfig:
    def __init__(self, dat):
        self.data = dat
        self.network = config_string(dat, ["network"])
        self.volumes = {
            "orderly": config_string(dat, ["volumes", "orderly"])
        }
        self.orderly_image = config_string(dat, ["orderly", "image"])
    @staticmethod
    def from_file(path):
        path_yml = "{}/orderly-web.yml".format(path)
        with open(path_yml, "r") as f:
            dat = yaml.load(f)
        return OrderlyWebConfig(dat);


# Utility function for centralising control over pulling information
# out of the configuration.
def config_string(data, path):
    if type(path) is str:
        path = [path]
    for i, p in enumerate(path):
        try:
            data = data[p]
        except KeyError as e:
            e.args = (":".join(path[:(i + 1)]), )
    if type(data) is not str:
        raise ValueError("Expected string for {}".format(path))
    return data
