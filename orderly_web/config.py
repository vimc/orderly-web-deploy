import yaml

class OrderlyWebConfig:
    def __init__(self, dat):
        self.data = dat
        self.network = config_string(dat, ["network"])
        self.volumes = {
            "orderly": config_string(dat, ["volumes", "orderly"])
        }
        self.orderly_image = config_string(dat, ["orderly", "image"])
        self.orderly_name = config_string(dat, ["orderly", "name"])
    @staticmethod
    def from_file(path):
        path_yml = "{}/orderly-web.yml".format(path)
        with open(path_yml, "r") as f:
            dat = yaml.load(f, Loader=yaml.SafeLoader)
        return OrderlyWebConfig(dat);


# Utility function for centralising control over pulling information
# out of the configuration.
def config_value(data, path, data_type, is_optional):
    if type(path) is str:
        path = [path]
    for i, p in enumerate(path):
        try:
            data = data[p]
        except KeyError as e:
            if is_optional:
                return None
            e.args = (":".join(path[:(i + 1)]), )
            raise e

    expected = {"string": str,
                "integer": int,
                "boolean": bool}
    if type(data) is not expected[data_type]:
        raise ValueError("Expected {} for {}".format(data_type, path))
    return data


def config_string(data, path, is_optional=False):
    return config_value(data, path, "string", is_optional)


def config_integer(data, path, is_optional=False):
    return config_value(data, path, "integer", is_optional)


def config_boolean(data, path, is_optional=False):
    return config_value(data, path, "boolean", is_optional)
