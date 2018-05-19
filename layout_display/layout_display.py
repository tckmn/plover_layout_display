from pathlib import Path

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QFileDialog

from plover import system
from plover.config import CONFIG_DIR
from plover.engine import StenoEngine
from plover.steno import Stroke
from plover.gui_qt.i18n import get_gettext
from plover.gui_qt.tool import Tool

from layout_display.layout_display_ui import Ui_LayoutDisplay
from layout_display.steno_layout import StenoLayout


_ = get_gettext()

class LayoutDisplay(Tool, Ui_LayoutDisplay):
    ''' Steno layout display of strokes '''

    TITLE = _('Layout Display')
    ROLE = 'layout_display'
    ICON = ':/layout_display/steno_key.svg'

    def __init__(self, engine: StenoEngine):
        super(LayoutDisplay, self).__init__(engine)
        self.setupUi(self)

        self._stroke = []
        self._numbers = set()
        self._numbers_to_keys = {}
        self._number_key = ''
        self._system_name = ''
        self._system_file_map = {}

        self._layout = StenoLayout()
        self._layout_file_path = ''

        self.restore_state()

        self.button_reset.clicked.connect(self.on_reset)
        self.button_load.clicked.connect(self.on_load)
        engine.signal_connect('config_changed', self.on_config_changed)
        self.on_config_changed(engine.config)
        engine.signal_connect('stroked', self.on_stroke)

        self.layout_display_view.update_view(self._layout)

    def _save_state(self, settings: QSettings):
        '''
        Save state to settings.
        Called via save_state through plover.qui_qt.utils.WindowState
        '''

        settings.setValue('system_file_map', self._system_file_map)

    def _restore_state(self, settings: QSettings):
        '''
        Restore state from settings.
        Called via restore_state through plover.qui_qt.utils.WindowState
        '''

        self._system_file_map = settings.value('system_file_map', {}, dict)

    def on_config_changed(self, config):
        ''' Updates state based off of the new Plover configuration '''

        # TODO: when does this actually happen...?
        if 'system_name' not in config:
            return

        self._stroke = []
        self._numbers = set(system.NUMBERS.values())
        self._numbers_to_keys = {v: k for k, v in system.NUMBERS.items()}
        self._number_key = system.NUMBER_KEY
        self._system_name = config['system_name']

        # If the user has no valid preference then fall back to the default
        preferred_layout_file = self.get_preferred_layout(self._system_name)
        if not preferred_layout_file:
            self.on_reset()
        else:
            self._layout_file_path = preferred_layout_file
            self._system_file_map[self._system_name] = self._layout_file_path
            self.save_state()

            self._layout.load_from_file(preferred_layout_file)
            self.label_layout_name.setText(self._layout.name)
            self.layout_display_view.update_view(self._layout)

    def on_stroke(self, stroke: Stroke):
        ''' Updates state based off of the latest stroke by the user '''

        keys = stroke.steno_keys[:]

        # Handle converting numbers in the stroke to the actual key values
        if any(key in self._numbers for key in keys):
            keys.append(self._number_key)
        keys = [self._numbers_to_keys[x] if x in self._numbers_to_keys else x for x in keys]

        self._stroke = keys
        self.layout_display_view.update_view(self._layout, keys)

    def on_reset(self):
        ''' Resets the layout to the built-in default layout '''

        self._layout_file_path = ''
        if self._system_name in self._system_file_map:
            self._system_file_map.pop(self._system_name)
            self.save_state()

        self._layout.load_from_resource(':/layout_display/english_stenotype.json')
        self.label_layout_name.setText(self._layout.name)
        self.layout_display_view.update_view(self._layout)

    def on_load(self):
        ''' Gets a layout file from the user to load '''

        # The API says this should return a string, but it returns a tuple
        file_path, _ = QFileDialog.getOpenFileName(self, 'Open Layout File', CONFIG_DIR, '(*.json)')

        # If the user cancelled out of the dialog then we will have a null string
        if not file_path:
            return

        self._layout_file_path = file_path
        self._system_file_map[self._system_name] = self._layout_file_path
        self.save_state()

        self._layout.load_from_file(file_path)
        self.label_layout_name.setText(self._layout.name)
        self.layout_display_view.update_view(self._layout)

    def get_preferred_layout(self, system_name: str) -> str:
        ''' Gets the user's preferred layout file for the given system '''

        # Restore state to make sure our system to file mapping is up to date
        self.restore_state()

        file_path = ''
        if system_name in self._system_file_map:
            file_path = self._system_file_map[system_name]

        # At least validate the file exists
        if file_path and not Path(file_path).is_file():
            file_path = ''
            if self._system_name in self._system_file_map:
                self._system_file_map.pop(self._system_name)
                self.save_state()

        return file_path
