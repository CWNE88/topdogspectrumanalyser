class FrequencyRange:
    """Manages frequency range with four interdependent parameters: start, stop, centre, and span.

    The four parameters maintain the following relationships:
    - centre = (start + stop) / 2
    - span = stop - start
    - start = centre - span / 2
    - stop = centre + span / 2

    When any parameter is changed, the others are automatically recalculated according to these rules:
    - Changing centre: keeps span constant, updates start and stop
    - Changing span: keeps centre constant, updates start and stop
    - Changing start: keeps stop constant, updates centre and span
    - Changing stop: keeps start constant, updates centre and span

    Example:
        Initial: start=100MHz, stop=200MHz → centre=150MHz, span=100MHz
        Set centre to 300MHz → start=250MHz, stop=350MHz, span=100MHz (preserved)
        Set span to 200MHz → start=200MHz, stop=400MHz, centre=300MHz (preserved)
    """

    def __init__(self, start: float, stop: float):
        """Initialize frequency range with start and stop frequencies.

        Args:
            start: Start frequency in Hz.
            stop: Stop frequency in Hz.

        Raises:
            ValueError: If stop <= start (invalid range).
        """
        if stop <= start:
            raise ValueError(f"Stop frequency ({stop}) must be greater than start frequency ({start})")

        self.start = start
        self.stop = stop
        self.centre = (start + stop) / 2
        self.span = stop - start
        self.res_bw = None

    def set_start_stop(self, start: float, stop: float):
        """Set both start and stop frequencies, recalculating centre and span.

        This is the most direct way to set a frequency range when you know the
        exact start and stop frequencies you want.

        Args:
            start: Start frequency in Hz.
            stop: Stop frequency in Hz.

        Raises:
            ValueError: If stop <= start (invalid range).
        """
        if stop <= start:
            raise ValueError(f"Stop frequency ({stop}) must be greater than start frequency ({start})")

        self.start = start
        self.stop = stop
        self.centre = (start + stop) / 2
        self.span = stop - start

    def set_centre(self, centre: float):
        """Set centre frequency, preserving span and updating start/stop.

        The span remains constant. Start and stop are recalculated to maintain
        the same span around the new centre frequency.

        Example:
            Current: start=100, stop=200, centre=150, span=100
            set_centre(300)
            Result: start=250, stop=350, centre=300, span=100

        Args:
            centre: New centre frequency in Hz.

        Raises:
            ValueError: If centre would result in negative start frequency.
        """
        if self.span is None:
            self.span = 2e6  # Default span if not set (e.g., 2 MHz)

        half_span = self.span / 2
        new_start = centre - half_span

        if new_start < 0:
            raise ValueError(f"Centre frequency {centre} with span {self.span} would result in negative start frequency")

        self.centre = centre
        self.start = new_start
        self.stop = centre + half_span

    def set_start(self, start: float):
        """Set start frequency, updating centre and span.

        If start < stop: stop is preserved, span shrinks/grows.
        If start >= stop: span is preserved and stop is shifted up to start + span.

        Args:
            start: New start frequency in Hz.

        Raises:
            ValueError: If start < 0.
        """
        if start < 0:
            raise ValueError(f"Start frequency must be non-negative, got {start}")

        if self.stop is None:
            self.stop = start + self.span if self.span else start + 2e6

        if start >= self.stop:
            # Slide the window: keep span, move stop up.
            self.start = start
            self.stop = start + self.span
            self.centre = start + self.span / 2
            return

        self.start = start
        self.centre = (start + self.stop) / 2
        self.span = self.stop - start

    def set_stop(self, stop: float):
        """Set stop frequency, updating centre and span.

        If stop > start: start is preserved, span shrinks/grows.
        If stop <= start: span is preserved and start is shifted down to stop - span
        (clamped to 0 if the shift would go negative).

        Args:
            stop: New stop frequency in Hz.

        Raises:
            ValueError: If stop <= 0.
        """
        if stop <= 0:
            raise ValueError(f"Stop frequency must be positive, got {stop}")

        if self.start is None:
            self.start = max(0, stop - self.span if self.span else stop - 2e6)

        if stop <= self.start:
            # Slide the window: keep span, move start down.
            new_start = max(0, stop - self.span)
            self.start = new_start
            self.stop = stop
            self.centre = (new_start + stop) / 2
            self.span = stop - new_start
            return

        self.stop = stop
        self.centre = (self.start + stop) / 2
        self.span = stop - self.start

    def set_span(self, span: float):
        """Set span, preserving centre and updating start/stop.

        The centre frequency remains constant. Start and stop are recalculated
        to maintain the centre while achieving the new span.

        Example:
            Current: start=100, stop=200, centre=150, span=100
            set_span(200)
            Result: start=50, stop=250, centre=150, span=200

        Args:
            span: New span in Hz.

        Raises:
            ValueError: If span <= 0 or would result in negative start frequency.
        """
        if span <= 0:
            raise ValueError(f"Span must be positive, got {span}")

        if self.centre is None:
            self.centre = span / 2  # Default centre to middle of span from 0

        half_span = span / 2
        new_start = self.centre - half_span

        if new_start < 0:
            raise ValueError(f"Span {span} with centre {self.centre} would result in negative start frequency")

        self.span = span
        self.start = new_start
        self.stop = self.centre + half_span
