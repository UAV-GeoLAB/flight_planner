class DirectionSectionHandler:
    def __init__(self, dial, spinBox):
        self.dial = dial
        self.spinBox = spinBox
        self.dial.valueChanged.connect(self.on_dial_valueChanged)
        self.spinBox.valueChanged.connect(self.on_spinBoxDirection_valueChanged)

    def on_dial_valueChanged(self):
        v = self.dial.value()
        self.spinBox.setValue(v - 180 if v > 180 else v + 180)

    def on_spinBoxDirection_valueChanged(self):
        v = self.spinBox.value()
        self.dial.setValue(v - 180 if v > 180 else v + 180)