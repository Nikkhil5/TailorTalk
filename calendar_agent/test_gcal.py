# test_gcal.py
from gcal import check_availability, book_appointment

# Test slots
test_slots = {
    "start": "2025-06-27T14:00:00",
    "end": "2025-06-27T15:00:00",
    "timezone": "Asia/Kolkata"
}

if __name__ == "__main__":
    print("=== Testing Calendar API Integration ===")
    
    # Test availability check
    print("\n[1] Testing availability check...")
    available = check_availability(test_slots)
    print(f"Available: {available}")
    
    # Test booking (only if available)
    if available:
        print("\n[2] Testing appointment booking...")
        booked = book_appointment(test_slots)
        print(f"Booking success: {booked}")
    else:
        print("\n[2] Skipping booking test - slot not available")
