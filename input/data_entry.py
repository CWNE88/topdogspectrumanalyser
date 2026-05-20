from PyQt6 import QtWidgets, QtCore
import sys

class Keypad(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Create a layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Create the QLabel to display input
        self.input_value = QtWidgets.QLabel("", self)
        self.layout.addWidget(self.input_value)

        # Create buttons for digits 0-9
        for i in range(10):
            button = QtWidgets.QPushButton(str(i), self)
            button.pressed.connect(self.button_pressed)
            self.layout.addWidget(button)

        # Create a button for decimal point
        decimal_button = QtWidgets.QPushButton(".", self)
        decimal_button.pressed.connect(self.button_pressed)
        self.layout.addWidget(decimal_button)

        # Set the layout
        self.setLayout(self.layout)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_0, QtCore.Qt.Key.Key_1, QtCore.Qt.Key.Key_2,
                           QtCore.Qt.Key.Key_3, QtCore.Qt.Key.Key_4, QtCore.Qt.Key.Key_5,
                           QtCore.Qt.Key.Key_6, QtCore.Qt.Key.Key_7, QtCore.Qt.Key.Key_8,
                           QtCore.Qt.Key.Key_9):
            character = event.text()
            self.update_input(character)
        elif event.key() == QtCore.Qt.Key.Key_Backspace:
            self.remove_last_character()
        elif event.key() == QtCore.Qt.Key.Key_Period:  
            self.update_input(".")

    def button_pressed(self):
        button = self.sender()
        if button:
            character = button.text()
            self.update_input(character)

    def update_input(self, character):
        current_text = self.input_value.text()

        # Allow only one decimal point
        if character == "." and "." in current_text:
            return

        new_text = current_text + character
        self.input_value.setText(new_text)

    def remove_last_character(self):
        current_text = self.input_value.text()
        new_text = current_text[:-1]  # Remove the last character
        self.input_value.setText(new_text)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    my_app = Keypad()
    my_app.show()
    sys.exit(app.exec())

