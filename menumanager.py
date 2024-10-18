class MenuManager:
    def __init__(self):
        self.current_menu = None
        self.current_submenu = None
        self.current_sub_submenu = None

        # Define submenu options
        self.submenus = {
            'frequency1': {
                'options': ['Centre\nFrequency', 
                            'Start\nFrequency', 
                            'Stop\nFrequency', 
                            'CF Step\nAuto/Man', 
                            'Frequency\nOffset', 
                            'CF/2 to\nCentre Freq', 
                            'CF*2 to\nCentre Freq'],
                'submenus': {
                    'Start Frequency': {
                        'options': ['Set Start', 
                                    'Start Info'],
                    },
                    'Stop Frequency': {
                        'options': ['Set Stop', 
                                    'Stop Info'],
                    },
                    'CF Step\nAuto/Man': {
                        'options': ['Set sfam', 'Stop sfam'],
                    },
                    'Frequency\nOffset': {
                        'options': ['Set freq_offset', 'Stop freq_offset'],
                    },
                    'CF/2 to\nCentre Freq': {
                        'options': ['Set cfdivided2', 'Stop Info'],
                    },
                    'CF*2 to\nCentre Freq': {
                        'options': ['Set cftimes2', 'Stop Info'],
                    }

                }
            },
            'span1': {
                'options': ['Full Span', 
                            'Last Span', 
                            'Span Zoom',
                            'Zero Span'],
                'submenus': {
                    'Full Span': {
                        'options': ['Set Full', 'Full Info'],
                    },
                    'Last Span': {
                        'options': ['Set Last', 'Last Info'],
                    },
                    'Span Zoom': {
                        'options': ['Set Zoom', 'Zoom Info'],
                    },
                    'Zero Span': {
                        'options': ['Set Zoom', 'Zoom Info'],
                    }
                }
            },
            'amplitude1': {
                'options': ['Reference\nLevel', 'Attenuation\nAuto/Man', 'Log dB /\nDivision',
                 'Lin / Log', 'Range\nLevel', 'Ref Level\nOffset',
                  'Max Mixer\nLevel', 'More (1 of 2)'],
                'submenus': {
                    'Reference\nLevel': {
                        'options': ['Set Ref', 'Ref Info'],
                    },
                    'Attenuation\nAuto/Man': {
                        'options': ['Set Attenuation', 'Attenuation Info'],
                    },
                    'Log dB /\nDivision': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'Lin / Log': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'Range\nLevel': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'Ref Level\nOffset': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'Max Mixer\nLevel': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'More (1 of 2)': {
                        'options': ['Set Linear', 'Linear Info'],
                    }
                }
            },     
            'amplitude2': {
                'options': ['Amplitude\nUnits', 
                            'Coupling\nAC/DC', 
                            'Norm\nRef Position',
                            'Presel\nAuto Peak', 
                            'Presel\nMan Adj',
                            'Gain',
                            'Squelch',
                              'More (2 of 2)'],
                'submenus': {
                    'Amplitude\nUnits': {
                        'options': ['dBm', 'dBµV', 'dBmV', 'Volts', 'Watts'],
                    },
                    'Coupling\nAC/DC': {
                        'options': ['Set Attenuation', 'Attenuation Info'],
                    },
                    'Norm\nRef Position': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'Presel\nAuto Peak': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'Presel\nMan Adj': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    '': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    '': {
                        'options': ['Set Linear', 'Linear Info'],
                    },
                    'More (2 of 2)': {
                        'options': ['Set Linear', 'Linear Info'],
                    }
                }
            },       
            'rtlfft1': {
                'options': ['Device\nNumber', 
                            'Direct\nSamp', 
                            'Bias T'],
                'submenus': {
                    'Device\nNumber': {
                        'options': ['Some\nList'],
                    },
                    'Direct\nSamp': {
                        'options': ['On', 'Off'],
                    },
                    'Bias T': {
                        'options': ['On', 'Off'],
                    },

                }
            },
            'hackrffft1': {
                'options': ['Device\nNumber', 
                            'Direct\nSamp'],
                'submenus': {
                    'Device\nNumber': {
                        'options': ['Some\nList'],
                    },
                    'Direct\nSamp': {
                        'options': ['On', 'Off'],
                    },
                    'Bias T': {
                        'options': ['On', 'Off'],
                    },

                }
            },            
            'audio1': {
                'options': ['Device', 
                            'Mono', 
                            'Stereo', 
                            'Left', 
                            'Right'],
                'submenus': {
                    'Device': {
                        'options': ['Some\nList'],
                    }

                }
            },
            'config1': {
                'options': ['Calibrate', 
                            'Gqrx device', 
                            'Default\nOrientation',
                            ],
                'submenus': {
                    'Calibrate': {
                        'options': ['Some\nList'],
                    },
                    'Gqrx device': {
                        'options': ['IP Address'],
                    },
                    'Default\nOrientation': {
                        'options': ['Horizontal', 'Vertical'],
                    }
                }
            },            
            'mode1': {
                'options': ['General', 'Wi-Fi', 'Audio', 'Digital'],
                'submenus': {
                    'Wi-Fi': {
                        'options': ['2.4 GHz', 'U-NII-1', 'U-NII-2', 'U-NII-3', '5GHz\nFull', '6GHz\nFull'],
                    },
                    'Audio': {
                        'options': [''],
                    },
                    'Digital': {
                        'options': [],
                    }
                }
            }
            
        }

    def show_submenu(self, menu_name):
        """Show the specified submenu."""
        self.current_menu = menu_name
        self.current_submenu = None
        self.current_sub_submenu = None  # Reset sub-submenu

    def show_sub_submenu(self, submenu_name):
        """Show the specified sub-submenu."""
        self.current_submenu = submenu_name
        self.current_sub_submenu = None  # Reset sub-sub-submenu

    def show_sub_sub_submenu(self, sub_submenu_name):
        """Show the specified sub-sub-submenu."""
        self.current_sub_submenu = sub_submenu_name

    def get_button_labels(self):
        """Get the current button labels based on the menu state."""
        if self.current_menu is None:
            return ['', '', '']

        menu_data = self.submenus[self.current_menu]
        options = menu_data['options']

        if self.current_submenu is None:
            return options + [''] * (3 - len(options))
        else:
            sub_options = menu_data['submenus'][self.current_submenu]['options']
            return sub_options + [''] * (3 - len(sub_options))

    def handle_button_press(self, button_index):
        """Handle button actions based on current menu and submenu state."""
        if self.current_submenu is None:
            if self.current_menu == 'frequency1':
                self.handle_frequency1_menu(button_index)
            elif self.current_menu == 'span1':
                self.handle_span1_menu(button_index)
            elif self.current_menu == 'amplitude1':
                self.handle_amplitude1_menu(button_index)
            elif self.current_menu == 'rtlfft1':
                self.handle_rtlfft1_menu(button_index)
            elif self.current_menu == 'hackrffft1':
                self.handle_hackrffft1_menu(button_index)
            elif self.current_menu == 'rtlsweep1':
                self.handle_rtlsweep1_menu(button_index)
            elif self.current_menu == 'hackrfsweep1':
                self.handle_hackrfsweep1_menu(button_index)
            elif self.current_menu == 'audio1':
                self.handle_audio1_menu(button_index)
            elif self.current_menu == 'mode1':
                self.handle_mode1_menu(button_index)
        elif self.current_submenu is not None:
            self.handle_submenu_action(button_index)

    def handle_frequency1_menu(self, button_index):
        if button_index < len(self.submenus['frequency1']['options']):
            self.show_sub_submenu(self.submenus['frequency1']['options'][button_index])

    def handle_span1_menu(self, button_index):
        if button_index < len(self.submenus['span1']['options']):
            self.show_sub_submenu(self.submenus['span1']['options'][button_index])

    def handle_amplitude1_menu(self, button_index):
        if button_index < len(self.submenus['amplitude1']['options']):
            self.show_sub_submenu(self.submenus['amplitude1']['options'][button_index])

    def handle_rtlfft1_menu(self, button_index):
        if button_index < len(self.submenus['rtlfft1']['options']):
            self.show_sub_submenu(self.submenus['rtlfft1']['options'][button_index])

    def handle_audio1_menu(self, button_index):
        if button_index < len(self.submenus['audio1']['options']):
            self.show_sub_submenu(self.submenus['audio1']['options'][button_index])            
    def handle_mode1_menu(self, button_index):
        if button_index < len(self.submenus['mode1']['options']):
            self.show_sub_submenu(self.submenus['mode1']['options'][button_index])            



    def handle_submenu_action(self, button_index):
        print(f"Selected {self.current_submenu} - Option {button_index + 1} selected")

        



        # Optionally handle further actions or sub-submenu selections here

