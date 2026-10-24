"""EDMFormer's labels around a chunk join are marked unreliable before anyone reads them."""
from onset_service.service import mark_chunk_joins


def seg(start, end, label):
    return {"start": start, "end": end, "label": label}


def test_sections_around_a_join_lose_label_trust_and_the_rest_keep_it():
    # La Danza: join at 121 s, mid-track "intro" from 125.5 s; Joya: join at 122 s, "outro" before it.
    danza = [seg(0, 19, "intro"), seg(95, 110.4, "drop"), seg(110.4, 125.5, "drop"),
             seg(125.5, 140.9, "intro"), seg(140.9, 155.9, "breakdown")]
    marked = mark_chunk_joins(danza, [121.0])
    assert [s.get("label_reliable", True) for s in marked] == [True, False, False, False, True]
    joya = mark_chunk_joins([seg(92.4, 106.7, "drop"), seg(106.7, 127.9, "outro"), seg(156.5, 178, "drop")], [122.0])
    assert [s.get("label_reliable", True) for s in joya] == [True, False, True]


def test_a_track_analysed_whole_is_untouched():
    segments = [seg(0, 30, "intro"), seg(30, 60, "drop")]
    assert mark_chunk_joins(segments, []) == segments
