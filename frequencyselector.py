class FrequencyRange:
    def __init__(self, start: float, stop: float):
        self.start = start
        self.stop = stop
        self.centre = (start + stop) / 2 if start is not None and stop is not None else 0.0
        self.span = stop - start if start is not None and stop is not None else 0.0
        self.res_bw = None

    def set_start_stop(self, start: float, stop: float):
        self.start = start
        self.stop = stop
        self.centre = (start + stop) / 2 if start is not None and stop is not None else 0.0
        self.span = stop - start if start is not None and stop is not None else 0.0

    def set_centre(self, centre: float):
        if self.span is None:
            self.span = 2e6  # Default span if not set (e.g., 2 MHz)
        half_span = self.span / 2
        self.centre = centre
        self.start = centre - half_span
        self.stop = centre + half_span

    def set_start(self, start: float):
        if self.stop is None:
            self.stop = start + 2e6  # Default span if stop is not set
        self.start = start
        self.centre = (start + self.stop) / 2
        self.span = self.stop - start

    def set_stop(self, stop: float):
        if self.start is None:
            self.start = stop - 2e6  # Default span if start is not set
        self.stop = stop
        self.centre = (self.start + stop) / 2
        self.span = stop - self.start

    def set_span(self, span: float):
        if self.centre is None:
            self.centre = 0.0  # Default centre if not set
        half_span = span / 2
        self.span = span
        self.start = self.centre - half_span
        self.stop = self.centre + half_span
