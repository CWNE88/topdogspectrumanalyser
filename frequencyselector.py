class FrequencyRange:
    start: float
    """
    start frequency in Hz
    """
    stop: float
    """
    stop frequency in Hz
    """
    centre: float
    """
    centre frequency in Hz
    """
    span: float
    """
    span (bandwidth) in Hz
    """
    res_bw: float
    """
    Bandwidth of each bin in Hz
    """

    def __init__(self, start=None, stop=None, centre=None, span=None, res_bw=10000):
        self.start = start
        self.stop = stop
        self.centre = centre
        self.span = span
        self.res_bw = res_bw
        self.update_frequencies()

    def update_frequencies(self):
        """Update frequencies based on the current values."""
        if self.start is not None and self.stop is not None:
            self.centre = (self.start + self.stop) / 2
            self.span = self.stop - self.start
        elif self.start is not None and self.centre is not None:
            self.stop = 2 * self.centre - self.start
            self.span = self.stop - self.start
        elif self.stop is not None and self.centre is not None:
            self.start = 2 * self.centre - self.stop
            self.span = self.stop - self.start
        elif self.span is not None and self.start is not None:
            self.stop = self.start + self.span
            # Centre remains unchanged
        elif self.span is not None and self.stop is not None:
            self.start = self.stop - self.span
            # Centre remains unchanged

        # calc res bw
        # self.res_bw = self.span / self.res_bw

    def set_start(self, start):
        self.start = start
        self.update_frequencies()

    def set_stop(self, stop):
        self.stop = stop
        self.update_frequencies()

    def set_centre(self, centre):
        self.centre = centre
        if self.span is not None:
            self.start = centre - (self.span / 2)
            self.stop = centre + (self.span / 2)
        self.update_frequencies()

    def set_span(self, span):
        self.span = span
        if self.centre is not None:
            self.start = self.centre - (self.span / 2)
            self.stop = self.centre + (self.span / 2)
        elif self.start is not None:
            self.stop = self.start + self.span
        elif self.stop is not None:
            self.start = self.stop - self.span
        self.update_frequencies()

    def __str__(self):
        return f'Start: {self.start}, Stop: {self.stop}, Centre: {self.centre}, Span: {self.span}'


def main():
    # User input for frequency parameters
    print("Enter frequency values:")
    start = input("Start frequency (leave empty if unknown): ")
    stop = input("Stop frequency (leave empty if unknown): ")
    centre = input("Centre frequency (leave empty if unknown): ")
    span = input("Span (leave empty if unknown): ")

    # Convert inputs to floats, or None if empty
    start = float(start) if start else None
    stop = float(stop) if stop else None
    centre = float(centre) if centre else None
    span = float(span) if span else None

    # Create a FrequencyRange instance
    frequency_range = FrequencyRange(start, stop, centre, span)

    # Output the current frequency settings
    print(frequency_range)

    # Allow the user to update one of the parameters
    while True:
        update = input("Would you like to update the Start, Stop, Centre, or Span? (type 'exit' to quit): ").strip().lower()
        if update == 'exit':
            break
        if update in ['start', 'stop', 'centre', 'span']:
            new_value = input(f"Enter new value for {update} frequency: ")
            new_value = float(new_value) if new_value else None
            if update == 'start':
                frequency_range.set_start(new_value)
            elif update == 'stop':
                frequency_range.set_stop(new_value)
            elif update == 'centre':
                frequency_range.set_centre(new_value)
            elif update == 'span':
                frequency_range.set_span(new_value)
            print(frequency_range)
        else:
            print("Invalid input, please enter 'Start', 'Stop', 'Centre', or 'Span'.")

if __name__ == "__main__":
    main()

