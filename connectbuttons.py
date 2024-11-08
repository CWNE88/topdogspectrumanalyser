def connect_buttons(self):
        self.button_frequency.pressed.connect(
            lambda: self.handle_menu_button("frequency1")
        )
        self.button_span.pressed.connect(lambda: self.handle_menu_button("span1"))
        self.button_amplitude.pressed.connect(
            lambda: self.handle_menu_button("amplitude1")
        )
        self.buttonsoft1.pressed.connect(lambda: self.handle_soft_button(0))
        self.buttonsoft2.pressed.connect(lambda: self.handle_soft_button(1))
        self.buttonsoft3.pressed.connect(lambda: self.handle_soft_button(2))
        self.button_mode.pressed.connect(lambda: self.handle_menu_button("mode1"))
        self.button_rtl_fft.pressed.connect(lambda: self.handle_menu_button("rtlfft1"))
        self.button_hackrf_fft.pressed.connect(
            lambda: self.handle_menu_button("hackrffft1")
        )
        self.button_audio_fft.pressed.connect(lambda: self.handle_menu_button("audio1"))

