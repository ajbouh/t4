from collections import Mapping, Sequence, Set, OrderedDict
import datetime
import json
import os

# backports
from six.moves import urllib
try:
    import pathlib2 as pathlib
except ImportError:
    import pathlib

# Third-Party
import ruamel.yaml
from appdirs import user_data_dir


APP_NAME = "Helium"
APP_AUTHOR = "QuiltData"
BASE_DIR = user_data_dir(APP_NAME, APP_AUTHOR)
BASE_PATH = pathlib.Path(BASE_DIR)
CONFIG_PATH = BASE_PATH / 'config.yml'

AWS_SEPARATOR = '/'

## CONFIG_TEMPLATE
# Must contain every permitted config key, as well as their default values (which can be 'null'/None).
# Comments are retained and added to local config, unless overridden by autoconfig via `api.config(<url>)`
CONFIG_TEMPLATE = """
# Helium configuration file

# navigator_url: <url string, default: null>
#
# Used for autoconfiguration
# navigator_url: https://example.com
navigator_url:

# elastic_search_url: <url string, default: null>
#
# Used to satisfy search queries
# elastic_search_url: https://example.com/es
elastic_search_url:
"""


class HeliumException(Exception):
    def __init__(self, message, **kwargs):
        # We use NewError("Prefix: " + str(error)) a lot.
        # To be consistent across Python 2.7 and 3.x:
        # 1) This `super` call must exist, or 2.7 will have no text for str(error)
        # 2) This `super` call must have only one argument (the message) or str(error) will be a repr of args
        super(HeliumException, self).__init__(message)
        self.message = message
        for k, v in kwargs.items():
            setattr(self, k, v)


def split_path(path, require_subpath=False):
    """
    Split bucket name and intra-bucket path. Returns: (bucket, path)
    """

    result = path.split(AWS_SEPARATOR, 1)
    if len(result) != 2:
        raise ValueError("Invalid path: %r; expected BUCKET/PATH..." % path)
    if require_subpath and not all(result):
        raise ValueError("Invalid path: %r; expected BUCKET/PATH... (BUCKET and PATH both required)"
                         % path)

    return result


def read_yaml(yaml_stream):
    yaml = ruamel.yaml.YAML()
    try:
        return yaml.load(yaml_stream)
    except ruamel.yaml.parser.ParserError as error:
        raise HeliumException(str(error), original_error=error)


# If we won't be using YAML for anything but config.yml, we can drop keep_backup and assume True.
def write_yaml(data, yaml_path, keep_backup=False):
    """Write `data` to `yaml_path`

    :param data: Any yaml-serializable data
    :param yaml_path: Destination. Can be a string or pathlib path.
    :param keep_backup: If set, a timestamped backup will be kept in the same dir.
    """
    yaml = ruamel.yaml.YAML()
    path = pathlib.Path(yaml_path)
    now = str(datetime.datetime.now())

    # XXX unicode colon for Windows/NTFS -- looks prettier, but could be confusing. We could use '_' instead.
    if os.name == 'nt':
        now = now.replace(':', '\ua789')

    backup_path = path.with_name(path.name + '.backup.' + now)

    if path.exists():
        backup_path.write_bytes(path.read_bytes())

    try:
        if path.exists():
            path.rename(backup_path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        with path.open('w') as config_file:
            yaml.dump(data, config_file)
    except Exception:     #! intentionally wide catch -- reraised immediately.
        if backup_path.exists():
            if path.exists():
                path.unlink()
            backup_path.rename(path)
        raise

    if backup_path.exists() and not keep_backup:
        backup_path.unlink()


def yaml_has_comments(parsed):
    """Determine if parsed YAML data has comments.

    Any object can be given, but only objects based on `ruamel.yaml`'s
    `CommentedBase` class can be True.

    :returns: True if object has retained comments, False otherwise
    """
    # Is this even a parse result object that stores comments?
    if not isinstance(parsed, ruamel.yaml.comments.CommentedBase):
        return False

    # Are there comments on this object?
    if parsed.ca.items or parsed.ca.comment or parsed.ca.end:
        return True

    # Is this a container that might have values with comments?
    values = ()
    if isinstance(parsed, (Sequence, Set)):
        values = parsed
    if isinstance(parsed, Mapping):
        values = parsed.values()
    # If so, do any of them have comments?
    for value in values:
        if yaml_has_comments(value):
            return True
    # no comments found.
    return False


def validate_url(url):
    """A URL must have scheme and host, at minimum."""
    parsed_url = urllib.parse.urlparse(url)

    # require scheme and host at minimum, like config_path'http://foo'
    if not all((parsed_url.scheme, parsed_url.netloc)):
        raise HeliumException("Invalid URL -- Requires at least scheme and host: {}".format(url))
    try:
        parsed_url.port
    except ValueError:
        raise HeliumException("Invalid URL -- Port must be a number: {}".format(url))


# Although displaying the config may seem not to warrant a class, it's pretty important
# for good UX. A lot of points were considered in making this -- retaining order,
# user's usage in an interpreted environment like Jupyter, and keeping the displayed
# information concise.  Given the limitations of the other options, making a class with
# custom repr panned out to be the best (and shortest) option.
class HeliumConfig(OrderedDict):
    def __init__(self, filepath, *args, **kwargs):
        self.filepath = pathlib.Path(filepath)
        super(HeliumConfig, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<{} at {!r} {}>".format(type(self).__name__, str(self.filepath), json.dumps(self, indent=4))
