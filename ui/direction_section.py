class DirectionSectionHandler:
    """Handler for synchronizing a dial and spin box representing direction in degrees."""
    def __init__(self, dial, spinBox):
        self.dial = dial
        self.spinBox = spinBox
        self.dial.valueChanged.connect(self.on_dial_valueChanged)
        self.spinBox.valueChanged.connect(self.on_spinBoxDirection_valueChanged)

    def on_dial_valueChanged(self):
        """Handle changes in the dial and update the spin box"""
        v = self.dial.value()
        self.spinBox.setValue(v - 180 if v > 180 else v + 180)

    def on_spinBoxDirection_valueChanged(self):
        """Handle changes in the spin box and update the dial"""
        v = self.spinBox.value()
        self.dial.setValue(v - 180 if v > 180 else v + 180)