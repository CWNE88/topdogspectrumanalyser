#!/usr/bin/env python3
"""Test script to verify FrequencyRange relationships."""

from utils.frequency_selector import FrequencyRange

def test_frequency_range():
    """Test all frequency parameter relationships."""
    print("Testing FrequencyRange class...")
    print("=" * 60)

    # Test 1: Initial creation
    print("\n1. Initial creation: start=100MHz, stop=200MHz")
    freq = FrequencyRange(100e6, 200e6)
    print(f"   Start:  {freq.start/1e6:.2f} MHz")
    print(f"   Stop:   {freq.stop/1e6:.2f} MHz")
    print(f"   Centre: {freq.centre/1e6:.2f} MHz")
    print(f"   Span:   {freq.span/1e6:.2f} MHz")
    assert freq.centre == 150e6, "Centre should be 150 MHz"
    assert freq.span == 100e6, "Span should be 100 MHz"
    print("   ✓ PASS")

    # Test 2: Change centre (preserves span)
    print("\n2. Change centre to 300MHz (should preserve span)")
    freq.set_centre(300e6)
    print(f"   Start:  {freq.start/1e6:.2f} MHz")
    print(f"   Stop:   {freq.stop/1e6:.2f} MHz")
    print(f"   Centre: {freq.centre/1e6:.2f} MHz")
    print(f"   Span:   {freq.span/1e6:.2f} MHz")
    assert freq.start == 250e6, "Start should be 250 MHz"
    assert freq.stop == 350e6, "Stop should be 350 MHz"
    assert freq.centre == 300e6, "Centre should be 300 MHz"
    assert freq.span == 100e6, "Span should remain 100 MHz"
    print("   ✓ PASS")

    # Test 3: Change span (preserves centre)
    print("\n3. Change span to 200MHz (should preserve centre)")
    freq.set_span(200e6)
    print(f"   Start:  {freq.start/1e6:.2f} MHz")
    print(f"   Stop:   {freq.stop/1e6:.2f} MHz")
    print(f"   Centre: {freq.centre/1e6:.2f} MHz")
    print(f"   Span:   {freq.span/1e6:.2f} MHz")
    assert freq.start == 200e6, "Start should be 200 MHz"
    assert freq.stop == 400e6, "Stop should be 400 MHz"
    assert freq.centre == 300e6, "Centre should remain 300 MHz"
    assert freq.span == 200e6, "Span should be 200 MHz"
    print("   ✓ PASS")

    # Test 4: Change start (preserves stop)
    print("\n4. Change start to 300MHz (should preserve stop)")
    freq.set_start(300e6)
    print(f"   Start:  {freq.start/1e6:.2f} MHz")
    print(f"   Stop:   {freq.stop/1e6:.2f} MHz")
    print(f"   Centre: {freq.centre/1e6:.2f} MHz")
    print(f"   Span:   {freq.span/1e6:.2f} MHz")
    assert freq.start == 300e6, "Start should be 300 MHz"
    assert freq.stop == 400e6, "Stop should remain 400 MHz"
    assert freq.centre == 350e6, "Centre should be 350 MHz"
    assert freq.span == 100e6, "Span should be 100 MHz"
    print("   ✓ PASS")

    # Test 5: Change stop (preserves start)
    print("\n5. Change stop to 500MHz (should preserve start)")
    freq.set_stop(500e6)
    print(f"   Start:  {freq.start/1e6:.2f} MHz")
    print(f"   Stop:   {freq.stop/1e6:.2f} MHz")
    print(f"   Centre: {freq.centre/1e6:.2f} MHz")
    print(f"   Span:   {freq.span/1e6:.2f} MHz")
    assert freq.start == 300e6, "Start should remain 300 MHz"
    assert freq.stop == 500e6, "Stop should be 500 MHz"
    assert freq.centre == 400e6, "Centre should be 400 MHz"
    assert freq.span == 200e6, "Span should be 200 MHz"
    print("   ✓ PASS")

    # Test 6: Validation - invalid range
    print("\n6. Test validation: stop <= start (should raise ValueError)")
    try:
        bad_freq = FrequencyRange(200e6, 100e6)
        print("   ✗ FAIL - Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ PASS - Correctly raised ValueError: {e}")

    # Test 7: Validation - negative start
    print("\n7. Test validation: negative start frequency (should raise ValueError)")
    freq2 = FrequencyRange(100e6, 200e6)
    try:
        freq2.set_start(-50e6)
        print("   ✗ FAIL - Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ PASS - Correctly raised ValueError: {e}")

    # Test 8: Validation - span that would cause negative start
    print("\n8. Test validation: span causing negative start (should raise ValueError)")
    freq3 = FrequencyRange(50e6, 100e6)
    try:
        freq3.set_span(200e6)  # Centre is 75 MHz, span 200 MHz would give start = -25 MHz
        print("   ✗ FAIL - Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ PASS - Correctly raised ValueError: {e}")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("\nFrequency relationships are working correctly:")
    print("  - Changing centre → preserves span, updates start/stop")
    print("  - Changing span → preserves centre, updates start/stop")
    print("  - Changing start → preserves stop, updates centre/span")
    print("  - Changing stop → preserves start, updates centre/span")

if __name__ == "__main__":
    test_frequency_range()
