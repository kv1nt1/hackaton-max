from datetime import date, datetime, time, timedelta
import unittest

from Generators.generate_bookings import generate_bookings


class BookingGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.meeting = dict(id=1, meeting_date=date(2026, 10, 1),
                            available_from=time(18), available_until=time(23),
                            group_size=4, status="planning")
        self.place = dict(id=1, min_group_size=2, max_group_size=8,
                          avg_duration_minutes=60,
                          opening_hours={"thu": ["18:30", "22:00"]})

    def test_reproducible_multiple_visits_fit_windows_and_do_not_overlap(self):
        meetings = [dict(self.meeting, id=i) for i in range(1, 21)]
        bookings = generate_bookings(meetings, [self.place])
        self.assertEqual(bookings, generate_bookings(list(reversed(meetings)), [self.place]))
        self.assertGreater(len(bookings), len(meetings))
        last_end = {}
        for booking in bookings:
            self.assertEqual(booking["group_size"], 4)
            self.assertGreaterEqual(booking["starts_at"], datetime(2026, 10, 1, 18, 30))
            self.assertLessEqual(booking["ends_at"], datetime(2026, 10, 1, 22))
            self.assertEqual(booking["ends_at"] - booking["starts_at"], timedelta(hours=1))
            if booking["meeting_id"] in last_end:
                self.assertGreaterEqual(booking["starts_at"], last_end[booking["meeting_id"]] + timedelta(minutes=15))
            last_end[booking["meeting_id"]] = booking["ends_at"]

    def test_unsuitable_places_and_empty_intersection_are_skipped(self):
        for place in (dict(self.place, max_group_size=3),
                      dict(self.place, min_group_size=5),
                      dict(self.place, opening_hours={"thu": None}),
                      dict(self.place, avg_duration_minutes=600)):
            self.assertEqual(generate_bookings([self.meeting], [place]), [])
        meeting = dict(self.meeting, available_from=time(22), available_until=time(21))
        self.assertEqual(generate_bookings([meeting], [self.place]), [])

    def test_previous_day_overnight_hours(self):
        meeting = dict(self.meeting, available_from=time(0, 30), available_until=time(2))
        place = dict(self.place, opening_hours={"wed": ["20:00", "02:00"], "thu": []})
        bookings = generate_bookings([meeting], [place])
        self.assertTrue(bookings)
        self.assertGreaterEqual(bookings[0]["starts_at"], datetime(2026, 10, 1, 0, 30))
        self.assertLessEqual(bookings[-1]["ends_at"], datetime(2026, 10, 1, 2))

    def test_meeting_status_is_respected(self):
        for status in ("cancelled", "completed"):
            bookings = generate_bookings([dict(self.meeting, status=status)], [self.place])
            self.assertTrue(bookings)
            self.assertTrue(all(booking["status"] == status for booking in bookings))

    def test_invalid_maximum(self):
        with self.assertRaises(ValueError):
            generate_bookings([self.meeting], [self.place], max_per_meeting=0)


if __name__ == "__main__":
    unittest.main()
