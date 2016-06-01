import pkg_resources

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = 'unknown'

__author__ = "Bryce Arden and Phillip Lemons"
__copyright__ = "Bryce Arden and Phillip Lemons"
__license__ = "gpl3"

