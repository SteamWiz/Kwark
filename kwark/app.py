from wizlib.app import WizApp
from wizlib.stream_handler import StreamHandler
from wizlib.config_handler import ConfigHandler
from wizlib.ui_handler import UIHandler

from kwark.command import KwarkCommand


class KwarkApp(WizApp):

    base = KwarkCommand
    name = 'kwark'
    handlers = [StreamHandler, ConfigHandler, UIHandler]
