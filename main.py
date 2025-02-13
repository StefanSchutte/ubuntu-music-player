#!/usr/bin/env python3
import sys
import os
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, GLib, Gst, GObject, GdkPixbuf
from mutagen import File
import time


class MusicPlayerWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Ubuntu Music Player")

        # Set the application ID to match the desktop file
        self.set_wmclass("ubuntu-music-player", "Ubuntu Music Player")
        self.set_icon_name("ubuntu-music-player")
        # super().__init__(title="Ubuntu Music Player")

        # Initialize GStreamer
        Gst.init(None)

        # Create playbin for audio playback
        self.player = Gst.ElementFactory.make("playbin", "player")

        # Create bus to get events from GStreamer pipeline
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)

        # Initialize player state variables
        self.current_track_index = -1
        self.duration = 0
        self.update_progress_timeout_id = None

        self.set_default_size(800, 600)

        # Create main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.main_box)

        # Create header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "Ubuntu Music Player"

        # Add open file and folder buttons to header
        open_file_button = Gtk.Button.new_from_icon_name("document-open", Gtk.IconSize.LARGE_TOOLBAR)
        open_file_button.connect("clicked", self.on_file_clicked)
        header.pack_start(open_file_button)

        open_folder_button = Gtk.Button.new_from_icon_name("folder-open", Gtk.IconSize.LARGE_TOOLBAR)
        open_folder_button.connect("clicked", self.on_folder_clicked)
        header.pack_start(open_folder_button)

        self.set_titlebar(header)

        # Create stack to hold different views
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(200)

        # Create welcome screen
        self.welcome_screen = self.create_welcome_screen()
        self.stack.add_named(self.welcome_screen, "welcome")

        # Create player view container
        self.player_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.stack.add_named(self.player_view, "player")

        # Add stack to main box
        self.main_box.pack_start(self.stack, True, True, 0)

        # Create UI sections
        self.create_now_playing_section()
        self.create_playlist_view()
        self.create_control_buttons()

        self.player.set_property('volume', 1.0)
        self.previous_volume = 100
        self.is_muted = False

        self.shuffle_enabled = False
        self.repeat_enabled = False

        self.stack.set_visible_child_name("welcome")

    def update_view(self):
        """Switch between welcome screen and player view based on playlist content"""
        if len(self.playlist_store) > 0:
            self.stack.set_visible_child_name("player")
        else:
            self.stack.set_visible_child_name("welcome")

    def create_now_playing_section(self):
        # Create frame for now playing section
        frame = Gtk.Frame(label="Now Playing")
        frame.set_margin_start(10)
        frame.set_margin_end(10)
        frame.set_margin_top(10)

        # Create box for now playing content
        now_playing_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        now_playing_box.set_margin_start(10)
        now_playing_box.set_margin_end(10)
        now_playing_box.set_margin_top(10)
        now_playing_box.set_margin_bottom(10)

        # Album art placeholder
        self.album_art = Gtk.Image()
        self.album_art.set_size_request(200, 200)
        # Create a default gray background for album art
        default_pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 200, 200)
        default_pixbuf.fill(0x7F7F7F7F)  # Fill with gray color
        self.album_art.set_from_pixbuf(default_pixbuf)

        # Info box (title, progress)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        # Create grid for track info
        track_info_grid = Gtk.Grid()
        track_info_grid.set_column_spacing(10)  # Space between label and value
        track_info_grid.set_row_spacing(2)  # Space between rows

        # Create labels for track info
        title_label = Gtk.Label(label="Title:")
        artist_label = Gtk.Label(label="Artist:")
        album_label = Gtk.Label(label="Album:")
        date_label = Gtk.Label(label="Date:")

        # Set alignment for labels
        for label in [title_label, artist_label, album_label, date_label]:
            label.set_halign(Gtk.Align.START)
            label.set_xalign(0)

        # Create value labels
        self.title_value = Gtk.Label(label="")
        self.artist_value = Gtk.Label(label="")
        self.album_value = Gtk.Label(label="")
        self.date_value = Gtk.Label(label="")

        # Set alignment for value labels
        for label in [self.title_value, self.artist_value, self.album_value, self.date_value]:
            label.set_halign(Gtk.Align.START)
            label.set_xalign(0)

        # Attach labels to grid
        track_info_grid.attach(title_label, 0, 0, 1, 1)
        track_info_grid.attach(self.title_value, 1, 0, 1, 1)
        track_info_grid.attach(artist_label, 0, 1, 1, 1)
        track_info_grid.attach(self.artist_value, 1, 1, 1, 1)
        track_info_grid.attach(album_label, 0, 2, 1, 1)
        track_info_grid.attach(self.album_value, 1, 2, 1, 1)
        track_info_grid.attach(date_label, 0, 3, 1, 1)
        track_info_grid.attach(self.date_value, 1, 3, 1, 1)

        # Progress bar
        self.progress_bar = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.progress_bar.set_draw_value(False)
        self.progress_bar.connect('change-value', self.on_progress_changed)

        # Time labels
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.current_time_label = Gtk.Label(label="0:00")
        self.duration_label = Gtk.Label(label="0:00")
        time_box.pack_start(self.current_time_label, False, False, 0)
        time_box.pack_end(self.duration_label, False, False, 0)

        # Pack everything
        info_box.pack_start(track_info_grid, False, False, 0)
        info_box.pack_start(self.progress_bar, True, True, 0)
        info_box.pack_start(time_box, False, False, 0)

        now_playing_box.pack_start(self.album_art, False, False, 0)
        now_playing_box.pack_start(info_box, True, True, 0)

        frame.add(now_playing_box)
        self.player_view.pack_start(frame, False, False, 0)

    def create_playlist_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        # Create ListStore with columns
        self.playlist_store = Gtk.ListStore(str, str, str, str, str, str, str)

        # Create TreeView
        self.playlist_view = Gtk.TreeView(model=self.playlist_store)

        # Connect double-click handler
        self.playlist_view.connect('row-activated', self.on_row_activated)

        self.playlist_view.connect('button-press-event', self.on_playlist_button_press)

        # Add columns
        renderer = Gtk.CellRendererText()

        # Filename column (with track numbers)
        filename_column = Gtk.TreeViewColumn("Filename", renderer, text=1)
        filename_column.set_expand(True)
        filename_column.set_sort_column_id(1)
        self.playlist_view.append_column(filename_column)

        # Title column from metadata
        title_column = Gtk.TreeViewColumn("Title", renderer, text=2)
        title_column.set_expand(True)
        title_column.set_sort_column_id(2)
        self.playlist_view.append_column(title_column)

        # Artist column
        artist_column = Gtk.TreeViewColumn("Artist", renderer, text=3)
        artist_column.set_expand(True)
        artist_column.set_sort_column_id(3)
        self.playlist_view.append_column(artist_column)

        # Album column
        album_column = Gtk.TreeViewColumn("Album", renderer, text=4)
        album_column.set_expand(True)
        album_column.set_sort_column_id(4)
        self.playlist_view.append_column(album_column)

        # Year column
        year_column = Gtk.TreeViewColumn("Year", renderer, text=5)
        year_column.set_sort_column_id(5)
        self.playlist_view.append_column(year_column)

        # Duration column
        duration_column = Gtk.TreeViewColumn("Duration", renderer, text=6)
        duration_column.set_sort_column_id(6)
        self.playlist_view.append_column(duration_column)

        # Add remove button column
        renderer_remove = Gtk.CellRendererPixbuf()
        column_remove = Gtk.TreeViewColumn("", renderer_remove)
        column_remove.set_cell_data_func(renderer_remove, self.remove_button_cell_data_func)
        self.playlist_view.append_column(column_remove)

        scrolled.add(self.playlist_view)
        self.player_view.pack_start(scrolled, True, True, 0)

    def create_welcome_screen(self):
        # Create main container for welcome screen
        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        welcome_box.set_valign(Gtk.Align.CENTER)
        welcome_box.set_halign(Gtk.Align.CENTER)

        # Welcome message
        welcome_label = Gtk.Label()
        welcome_label.set_markup("<span size='large'>Select your audio file or folder to start listening</span>")
        welcome_label.set_margin_bottom(20)
        welcome_box.pack_start(welcome_label, False, False, 0)

        # Buttons container
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)  # Increased spacing between buttons
        buttons_box.set_halign(Gtk.Align.CENTER)

        # Open File button
        open_file_button = Gtk.Button.new_from_icon_name("document-open", Gtk.IconSize.DND)
        open_file_button.set_tooltip_text("Open File")
        open_file_button.connect("clicked", self.on_file_clicked)
        open_file_button.set_size_request(64, 64)  # Make the button bigger

        # Open Folder button
        open_folder_button = Gtk.Button.new_from_icon_name("folder-open", Gtk.IconSize.DND)
        open_folder_button.set_tooltip_text("Open Folder")
        open_folder_button.connect("clicked", self.on_folder_clicked)
        open_folder_button.set_size_request(64, 64)  # Make the button bigger

        # Load Playlist button
        load_playlist_button = Gtk.Button.new_from_icon_name("view-list", Gtk.IconSize.DND)
        load_playlist_button.set_tooltip_text("Load Playlist")
        load_playlist_button.connect("clicked", self.on_load_playlist_clicked)
        load_playlist_button.set_size_request(64, 64)  # Make the button bigger

        # Add buttons to container
        buttons_box.pack_start(open_file_button, False, False, 0)
        buttons_box.pack_start(open_folder_button, False, False, 0)
        buttons_box.pack_start(load_playlist_button, False, False, 0)

        welcome_box.pack_start(buttons_box, False, False, 0)

        return welcome_box

    def create_control_buttons(self):
        # Create outer box for centering with specific spacing
        outer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer_box.set_margin_top(10)
        outer_box.set_margin_bottom(10)

        # Create left box for playlist controls with fixed width
        playlist_box = Gtk.Box(spacing=6)
        playlist_box.set_margin_start(10)
        playlist_box.set_size_request(100, -1)  # Set fixed width

        # Save playlist button
        save_playlist_button = Gtk.Button()
        save_icon = Gtk.Image.new_from_icon_name("document-save", Gtk.IconSize.SMALL_TOOLBAR)
        save_playlist_button.add(save_icon)
        save_playlist_button.set_tooltip_text("Save Playlist")
        save_playlist_button.connect("clicked", self.on_save_playlist_clicked)
        save_playlist_button.set_size_request(25, 25)

        # Load playlist button
        load_playlist_button = Gtk.Button()
        load_icon = Gtk.Image.new_from_icon_name("view-list", Gtk.IconSize.SMALL_TOOLBAR)
        load_playlist_button.add(load_icon)
        load_playlist_button.set_tooltip_text("Load Playlist")
        load_playlist_button.connect("clicked", self.on_load_playlist_clicked)
        load_playlist_button.set_size_request(25, 25)

        # Add playlist buttons to the left box
        playlist_box.pack_start(save_playlist_button, False, False, 0)
        playlist_box.pack_start(load_playlist_button, False, False, 0)

        # Create center box for controls with fixed width
        control_box = Gtk.Box(spacing=6)
        control_box.set_halign(Gtk.Align.CENTER)
        control_box.set_size_request(400, -1)  # Fixed width for control section

        # Shuffle button
        self.shuffle_button = Gtk.ToggleButton()
        self.shuffle_icon = Gtk.Image.new_from_icon_name("media-playlist-shuffle", Gtk.IconSize.LARGE_TOOLBAR)
        self.shuffle_button.add(self.shuffle_icon)
        self.shuffle_button.set_size_request(45, 45)
        self.shuffle_button.connect("toggled", self.on_shuffle_toggled)

        # Repeat button
        self.repeat_button = Gtk.ToggleButton()
        self.repeat_icon = Gtk.Image.new_from_icon_name("media-playlist-repeat", Gtk.IconSize.LARGE_TOOLBAR)
        self.repeat_button.add(self.repeat_icon)
        self.repeat_button.set_size_request(45, 45)
        self.repeat_button.connect("toggled", self.on_repeat_toggled)

        # Previous button
        self.prev_button = Gtk.Button.new_from_icon_name("media-skip-backward", Gtk.IconSize.LARGE_TOOLBAR)
        self.prev_button.set_size_request(45, 45)
        self.prev_button.connect("clicked", self.on_prev)

        # Play/Pause button
        self.play_pause_button = Gtk.Button.new_from_icon_name("media-playback-start", Gtk.IconSize.LARGE_TOOLBAR)
        self.play_pause_button.set_size_request(45, 45)
        self.play_pause_button.connect("clicked", self.on_play_pause_clicked)

        # Stop button
        self.stop_button = Gtk.Button.new_from_icon_name("media-playback-stop", Gtk.IconSize.LARGE_TOOLBAR)
        self.stop_button.set_size_request(45, 45)
        self.stop_button.connect("clicked", self.on_stop)

        # Next button
        self.next_button = Gtk.Button.new_from_icon_name("media-skip-forward", Gtk.IconSize.LARGE_TOOLBAR)
        self.next_button.set_size_request(45, 45)
        self.next_button.connect("clicked", self.on_next)

        # Volume control frame
        volume_frame = Gtk.Frame()
        volume_frame.set_shadow_type(Gtk.ShadowType.IN)
        volume_frame.set_size_request(120, 45)  # Fixed width for volume control

        volume_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        volume_box.set_margin_start(4)
        volume_box.set_margin_end(4)
        volume_box.set_margin_top(2)
        volume_box.set_margin_bottom(2)

        # Volume button
        self.volume_button = Gtk.Button()
        self.volume_icon = Gtk.Image.new_from_icon_name("audio-volume-high", Gtk.IconSize.SMALL_TOOLBAR)
        self.volume_button.add(self.volume_icon)
        self.volume_button.connect("clicked", self.on_volume_button_clicked)

        # Volume slider
        self.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume_scale.set_size_request(80, -1)  # Fixed width for slider
        self.volume_scale.set_value(100)
        self.volume_scale.connect('value-changed', self.on_volume_changed)

        # Pack volume controls
        volume_box.pack_start(self.volume_button, False, False, 0)
        volume_box.pack_start(self.volume_scale, True, True, 0)
        volume_frame.add(volume_box)

        # Create right box for clear playlist with fixed width
        right_box = Gtk.Box(spacing=6)
        right_box.set_margin_end(10)
        right_box.set_size_request(100, -1)  # Fixed width

        # Clear playlist button
        clear_playlist_button = Gtk.Button()
        trash_icon = Gtk.Image.new_from_icon_name("user-trash", Gtk.IconSize.SMALL_TOOLBAR)
        clear_playlist_button.add(trash_icon)
        clear_playlist_button.set_tooltip_text("Clear Playlist")
        clear_playlist_button.connect("clicked", self.on_clear_playlist_clicked)
        clear_playlist_button.set_size_request(25, 25)
        right_box.pack_end(clear_playlist_button, False, False, 0)

        # Pack all control buttons in the center box
        control_box.pack_start(self.shuffle_button, False, False, 0)
        control_box.pack_start(self.repeat_button, False, False, 0)
        control_box.pack_start(self.prev_button, False, False, 0)
        control_box.pack_start(self.play_pause_button, False, False, 0)
        control_box.pack_start(self.stop_button, False, False, 0)
        control_box.pack_start(self.next_button, False, False, 0)
        control_box.pack_start(volume_frame, False, False, 0)

        # Pack everything into the outer box with proper spacing
        outer_box.pack_start(playlist_box, False, False, 0)
        outer_box.pack_start(Gtk.Box(), True, True, 0)  # Flexible spacing
        outer_box.pack_start(control_box, False, False, 0)
        outer_box.pack_start(Gtk.Box(), True, True, 0)  # Flexible spacing
        outer_box.pack_end(right_box, False, False, 0)

        self.player_view.pack_start(outer_box, False, False, 0)

    def on_shuffle_toggled(self, button):
        self.shuffle_enabled = button.get_active()
        if self.shuffle_enabled:
            # Create a shuffled version of the playlist
            import random
            rows = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
                    for row in self.playlist_store]
            random.shuffle(rows)

            # Clear and refill the playlist store
            self.playlist_store.clear()
            for row in rows:
                self.playlist_store.append(row)

            # Update current track index if a track is playing
            if self.current_track_index != -1:
                # Find the current track in the shuffled playlist
                current_uri = self.player.get_property('uri')
                if current_uri:
                    for i, row in enumerate(self.playlist_store):
                        if GLib.filename_to_uri(row[0]) == current_uri:
                            self.current_track_index = i
                            break

    def on_repeat_toggled(self, button):
        self.repeat_enabled = button.get_active()

    def get_metadata(self, file_path):
        try:
            filename = os.path.basename(file_path)
            display_name = os.path.splitext(filename)[0]

            # Initialize metadata values
            title = "Unknown"
            artist = "Unknown"
            album = "Unknown"
            year = ""
            duration = ""
            artwork = None

            audio = File(file_path)

            if audio:
                if hasattr(audio.info, 'length'):
                    duration = self.format_time(audio.info.length)

                # MP3 Files
                if hasattr(audio, 'tags') and hasattr(audio, 'ID3'):
                    tags = audio.tags
                    print("Processing as MP3")

                    if 'TPE1' in tags:
                        artist = str(tags['TPE1'])
                    if 'TIT2' in tags:
                        title = str(tags['TIT2'])
                    if 'TALB' in tags:
                        album = str(tags['TALB'])
                    if 'TDRC' in tags:
                        year = str(tags['TDRC'])

                    # Get MP3 artwork
                    for key in tags.keys():
                        if key.startswith('APIC'):
                            artwork_tag = tags[key]
                            if artwork_tag:
                                artwork = artwork_tag.data
                                print(f"Found MP3 artwork, size: {len(artwork)} bytes")
                                break

                # FLAC Files
                elif hasattr(audio, 'tags') and hasattr(audio.tags, 'get'):
                    tags = audio.tags
                    print("Processing as FLAC")

                    artist = str(tags.get('artist', ['Unknown'])[0])
                    title = str(tags.get('title', [display_name])[0])
                    album = str(tags.get('album', ['Unknown'])[0])
                    year = str(tags.get('date', [''])[0])

                    # Get FLAC artwork
                    if hasattr(audio, 'pictures'):
                        if audio.pictures:
                            picture = audio.pictures[0]
                            artwork = picture.data
                            print(f"Found FLAC artwork, size: {len(artwork)} bytes")

                print(f"Metadata extracted - Title: {title}, Artist: {artist}, Album: {album}")
                if artwork:
                    print(f"Artwork found: {len(artwork)} bytes")
                else:
                    print("No artwork found in file")

            return display_name, title, artist, album, year, duration, artwork

        except Exception as e:
            print(f"Error reading metadata for {file_path}: {e}")
            return os.path.splitext(os.path.basename(file_path))[0], "Unknown", "Unknown", "Unknown", "", "", None

    def add_music_files(self, file_paths):
        for file_path in file_paths:
            if os.path.isfile(file_path):
                filename, title, artist, album, year, duration, artwork = self.get_metadata(file_path)
                self.playlist_store.append([file_path, filename, title, artist, album, year, duration])
        self.update_view()

    def scan_directory(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if self.is_music_file(file):
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        filename, title, artist, album, year, duration, artwork = self.get_metadata(file_path)
                        print(f"Found: {title} by {artist}")  # Debug print
                        self.playlist_store.append([file_path, filename, title, artist, album, year, duration])
        self.update_view()

    def is_music_file(self, filename):
        music_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
        return os.path.splitext(filename)[1].lower() in music_extensions

    def on_file_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Music Files",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )

        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        dialog.set_select_multiple(True)

        music_filter = Gtk.FileFilter()
        music_filter.set_name("Music files")
        music_filter.add_mime_type("audio/mpeg")
        music_filter.add_mime_type("audio/mp3")
        music_filter.add_mime_type("audio/x-wav")
        music_filter.add_mime_type("audio/wav")
        music_filter.add_mime_type("audio/flac")
        music_filter.add_mime_type("audio/x-flac")
        music_filter.add_mime_type("audio/ogg")
        music_filter.add_mime_type("audio/aac")
        music_filter.add_mime_type("audio/m4a")
        music_filter.add_pattern("*.mp3")
        music_filter.add_pattern("*.wav")
        music_filter.add_pattern("*.flac")
        music_filter.add_pattern("*.ogg")
        music_filter.add_pattern("*.m4a")
        music_filter.add_pattern("*.aac")

        dialog.add_filter(music_filter)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            files = dialog.get_filenames()
            music_files = [f for f in files if self.is_music_file(f)]
            self.add_music_files(music_files)

        dialog.destroy()

    def on_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Music Folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )

        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            folder = dialog.get_filename()
            self.scan_directory(folder)

        dialog.destroy()

    def remove_button_cell_data_func(self, column, cell, model, iter, data):
        cell.set_property('icon-name', 'edit-delete')

    def on_playlist_button_press(self, treeview, event):
        if event.button == 1:  # Left click
            path = treeview.get_path_at_pos(int(event.x), int(event.y))
            if path:
                path, column = path[0], path[1]
                if column == treeview.get_columns()[-1]:  # Last column (remove button)
                    self.remove_track(path)
                    return True
        return False

    def remove_track(self, path):
        iter = self.playlist_store.get_iter(path)
        if iter:
            if path.get_indices()[0] == self.current_track_index:
                self.player.set_state(Gst.State.NULL)
                self.update_now_playing_label("No track playing")
                self.update_play_pause_button_icon(False)
                self.current_track_index = -1
            elif path.get_indices()[0] < self.current_track_index:
                self.current_track_index -= 1
            self.playlist_store.remove(iter)
            self.update_view()

    def on_play(self, button):
        self.player.set_state(Gst.State.PLAYING)

    def on_pause(self, button):
        self.player.set_state(Gst.State.PAUSED)

    def on_play_pause_clicked(self, button):
        success, state, pending = self.player.get_state(Gst.CLOCK_TIME_NONE)

        if state == Gst.State.PLAYING:
            self.player.set_state(Gst.State.PAUSED)
            self.update_play_pause_button_icon(False)
        else:
            if self.current_track_index == -1 and len(self.playlist_store) > 0:
                self.current_track_index = 0

                path = Gtk.TreePath.new_from_indices([self.current_track_index])
                selection = self.playlist_view.get_selection()
                selection.unselect_all()
                selection.select_path(path)
                self.playlist_view.scroll_to_cell(path, None, True, 0.5, 0.5)

                self.play_track_at_index(self.current_track_index)
            else:
                self.player.set_state(Gst.State.PLAYING)
                self.update_play_pause_button_icon(True)

    def update_play_pause_button_icon(self, is_playing):
        icon_name = "media-playback-pause" if is_playing else "media-playback-start"
        new_image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        self.play_pause_button.set_image(new_image)
        new_image.show()

    def on_stop(self, button):
        self.player.set_state(Gst.State.NULL)
        self.current_track_index = -1
        self.update_now_playing_label("No track playing")
        self.progress_bar.set_value(0)
        self.current_time_label.set_text("0:00")
        self.duration_label.set_text("0:00")
        default_pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 200, 200)
        default_pixbuf.fill(0x7F7F7F7F)
        self.album_art.set_from_pixbuf(default_pixbuf)
        self.update_play_pause_button_icon(False)

        if self.update_progress_timeout_id:
            GLib.source_remove(self.update_progress_timeout_id)
            self.update_progress_timeout_id = None

        selection = self.playlist_view.get_selection()
        selection.unselect_all()

    def on_next(self, button):
        if len(self.playlist_store) > 0:
            self.player.set_state(Gst.State.NULL)
            self.current_track_index = (self.current_track_index + 1) % len(self.playlist_store)

            path = Gtk.TreePath.new_from_indices([self.current_track_index])
            selection = self.playlist_view.get_selection()
            selection.unselect_all()
            selection.select_path(path)
            self.playlist_view.scroll_to_cell(path, None, True, 0.5, 0.5)

            self.play_track_at_index(self.current_track_index)
            self.player.set_state(Gst.State.PLAYING)

    def on_prev(self, button):
        if len(self.playlist_store) > 0:
            self.player.set_state(Gst.State.NULL)
            self.current_track_index = (self.current_track_index - 1) % len(self.playlist_store)

            path = Gtk.TreePath.new_from_indices([self.current_track_index])
            selection = self.playlist_view.get_selection()
            selection.unselect_all()
            selection.select_path(path)
            self.playlist_view.scroll_to_cell(path, None, True, 0.5, 0.5)

            self.play_track_at_index(self.current_track_index)
            self.player.set_state(Gst.State.PLAYING)

    def update_volume_icon(self):
        volume = self.volume_scale.get_value()
        icon_name = "audio-volume-muted" if self.is_muted else (
            "audio-volume-high" if volume > 66 else
            "audio-volume-medium" if volume > 33 else
            "audio-volume-low" if volume > 0 else
            "audio-volume-muted"
        )
        self.volume_icon.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)

    def on_volume_button_clicked(self, button):
        if self.is_muted:
            self.is_muted = False
            self.volume_scale.set_value(self.previous_volume)
            self.player.set_property('volume', self.previous_volume / 100.0)
        else:
            self.previous_volume = self.volume_scale.get_value()
            self.is_muted = True
            self.volume_scale.set_value(0)
            self.player.set_property('volume', 0)
        self.update_volume_icon()

    def on_volume_changed(self, widget):
        volume = widget.get_value()
        self.player.set_property('volume', volume / 100.0)
        if volume > 0:
            self.is_muted = False
        self.update_volume_icon()

    def play_track_at_index(self, index):
        if 0 <= index < len(self.playlist_store):
            path = Gtk.TreePath.new_from_indices([index])
            self.on_row_activated(self.playlist_view, path, None)

    def on_row_activated(self, treeview, path, column):
        self.current_track_index = path.get_indices()[0]
        model = treeview.get_model()
        file_path = model[path][0]
        self.play_file(file_path)

    def play_file(self, file_path):

        self.player.set_state(Gst.State.NULL)
        self.progress_bar.set_value(0)
        self.current_time_label.set_text("0:00")

        uri = GLib.filename_to_uri(file_path)
        self.player.set_property('uri', uri)
        self.player.set_state(Gst.State.PLAYING)
        self.update_play_pause_button_icon(True)

        display_name, title, artist, album, year, duration, artwork = self.get_metadata(file_path)

        self.title_value.set_text(title)
        self.artist_value.set_text(artist)
        self.album_value.set_text(album)
        self.date_value.set_text(year)

        if artwork:
            try:
                loader = GdkPixbuf.PixbufLoader()

                loader.write(artwork)
                loader.close()

                pixbuf = loader.get_pixbuf()
                if pixbuf:
                    width = pixbuf.get_width()
                    height = pixbuf.get_height()
                    target_size = 200

                    if width > height:
                        new_width = target_size
                        new_height = int(height * (target_size / width))
                    else:
                        new_height = target_size
                        new_width = int(width * (target_size / height))

                    scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
                    self.album_art.set_from_pixbuf(scaled_pixbuf)
                else:
                    print("Failed to get pixbuf from loader")
                    raise Exception("Failed to get pixbuf")

            except Exception as e:
                print(f"Error loading album art: {e}")
                default_pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 200, 200)
                default_pixbuf.fill(0x7F7F7F7F)
                self.album_art.set_from_pixbuf(default_pixbuf)
        else:
            print("No artwork found in metadata")
            default_pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 200, 200)
            default_pixbuf.fill(0x7F7F7F7F)
            self.album_art.set_from_pixbuf(default_pixbuf)

        self.start_progress_update()

    def update_now_playing_label(self, text):
        if text == "No track playing":
            self.title_value.set_text("")
            self.artist_value.set_text("")
            self.album_value.set_text("")
            self.date_value.set_text("")

    def start_progress_update(self):
        if self.update_progress_timeout_id:
            GLib.source_remove(self.update_progress_timeout_id)
        self.update_progress_timeout_id = GLib.timeout_add(1000, self.update_progress)

    def update_progress(self):
        success, duration = self.player.query_duration(Gst.Format.TIME)
        if success:
            self.duration = duration / Gst.SECOND
            self.duration_label.set_text(self.format_time(self.duration))

        success, position = self.player.query_position(Gst.Format.TIME)
        if success:
            position = position / Gst.SECOND
            self.current_time_label.set_text(self.format_time(position))
            if self.duration > 0:
                self.progress_bar.set_value((position / self.duration) * 100)
        return True

    def format_time(self, seconds):
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"

    def on_progress_changed(self, scale, scroll_type, value):
        if self.duration > 0:
            position = (value / 100) * self.duration
            self.player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                position * Gst.SECOND
            )
        return True

    def get_playlists_directory(self):
        """Get or create playlists directory in user's home folder"""
        home = os.path.expanduser("~")
        playlist_dir = os.path.join(home, ".ubuntu_music_player", "playlists")
        os.makedirs(playlist_dir, exist_ok=True)
        return playlist_dir

    def save_playlist(self, filename):
        """Save current playlist to a file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")  # M3U playlist header
                for row in self.playlist_store:
                    # Write file path
                    filepath = row[0]
                    title = row[2]
                    artist = row[3]
                    # Write extended info
                    f.write(f"#EXTINF:-1,{artist} - {title}\n")
                    # Write file path
                    f.write(f"{filepath}\n")
            return True
        except Exception as e:
            print(f"Error saving playlist: {e}")
            return False

    def show_playlist_selection_dialog(self):
        """Show a simple dialog with a list of saved playlists"""
        dialog = Gtk.Dialog(title="Select Playlist", parent=self)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_default_size(300, 400)

        # Create a ScrolledWindow
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_margin_start(10)
        scrolled.set_margin_end(10)
        scrolled.set_margin_top(10)
        scrolled.set_margin_bottom(10)

        # Create ListBox for playlists
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)

        # Get playlists from directory
        playlist_dir = self.get_playlists_directory()
        playlists = [f for f in os.listdir(playlist_dir) if f.endswith('.m3u')]

        for playlist in sorted(playlists):
            # Remove .m3u extension for display
            name = os.path.splitext(playlist)[0]
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=name)
            label.set_margin_start(10)
            label.set_margin_end(10)
            label.set_margin_top(5)
            label.set_margin_bottom(5)
            label.set_halign(Gtk.Align.START)
            row.add(label)
            list_box.add(row)

        scrolled.add(list_box)
        dialog.get_content_area().pack_start(scrolled, True, True, 0)
        dialog.show_all()

        response = dialog.run()
        selected_playlist = None

        if response == Gtk.ResponseType.OK:
            selection = list_box.get_selected_row()
            if selection:
                playlist_name = selection.get_children()[0].get_text()
                selected_playlist = os.path.join(playlist_dir, f"{playlist_name}.m3u")

        dialog.destroy()
        return selected_playlist

    def on_save_playlist_clicked(self, widget):
        # Create a simple dialog for playlist name
        dialog = Gtk.Dialog(title="Save Playlist", parent=self)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )

        # Add a label and entry for the playlist name
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        label = Gtk.Label(label="Playlist Name:")
        box.add(label)

        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box.add(entry)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            playlist_name = entry.get_text().strip()
            if playlist_name:
                playlist_dir = self.get_playlists_directory()
                filename = os.path.join(playlist_dir, f"{playlist_name}.m3u")

                if self.save_playlist(filename):
                    message_dialog = Gtk.MessageDialog(
                        transient_for=self,
                        message_type=Gtk.MessageType.INFO,
                        buttons=Gtk.ButtonsType.OK,
                        text="Playlist saved successfully"
                    )
                    message_dialog.run()
                    message_dialog.destroy()

        dialog.destroy()

    def on_load_playlist_clicked(self, widget):
        playlist_file = self.show_playlist_selection_dialog()
        if playlist_file and os.path.exists(playlist_file):
            if self.load_playlist(playlist_file):
                message_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Playlist loaded successfully"
                )
                message_dialog.run()
                message_dialog.destroy()

    def load_playlist(self, filename):
        """Load playlist from a file"""
        try:
            # Clear current playlist
            self.playlist_store.clear()

            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTINF'):
                    # Skip the extended info line
                    i += 1
                    if i < len(lines):
                        filepath = lines[i].strip()
                        if os.path.isfile(filepath):
                            self.add_music_files([filepath])
                i += 1

            # Start playing the first track if playlist is not empty
            if len(self.playlist_store) > 0:
                self.current_track_index = 0
                path = Gtk.TreePath.new_from_indices([0])
                selection = self.playlist_view.get_selection()
                selection.unselect_all()
                selection.select_path(path)
                self.playlist_view.scroll_to_cell(path, None, True, 0.5, 0.5)
                self.play_track_at_index(0)
                self.update_view()

            return True
        except Exception as e:
            print(f"Error loading playlist: {e}")
            return False

    def on_clear_playlist_clicked(self, button):
        # Create confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Clear Playlist",
            secondary_text="Are you sure you want to empty the playlist?"
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            # Stop playback if playing
            self.player.set_state(Gst.State.NULL)
            # Reset current track index
            self.current_track_index = -1
            # Clear the playlist store
            self.playlist_store.clear()
            # Reset now playing labels
            self.update_now_playing_label("No track playing")
            # Reset progress bar and time labels
            self.progress_bar.set_value(0)
            self.current_time_label.set_text("0:00")
            self.duration_label.set_text("0:00")
            # Reset album art to default
            default_pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 200, 200)
            default_pixbuf.fill(0x7F7F7F7F)
            self.album_art.set_from_pixbuf(default_pixbuf)
            # Update play/pause button icon
            self.update_play_pause_button_icon(False)
            # Update view to show welcome screen
            self.update_view()

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error:", err, debug)
            self.update_now_playing_label("Error playing track")
            self.update_play_pause_button_icon(False)
        elif t == Gst.MessageType.EOS:
            if self.repeat_enabled and self.current_track_index == len(self.playlist_store) - 1:
                self.current_track_index = -1
            self.on_next(None)

win = MusicPlayerWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()