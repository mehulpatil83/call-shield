from eval.benchmark_eval import clean, find_labels, is_test, prefix


def test_speaker_labels_are_removed_inline_and_per_line():
    assert clean("Suspect: Hello sir. Innocent: Who is this? Suspect: The bank.") == "Hello sir. Who is this? The bank."
    assert clean("Caller: hi\nReceiver: hello") == "hi hello"
    assert clean("A: hi") == "A: hi"                                              # only known labels are removed
    assert clean("The OTP: 1234 is private") == "The OTP: 1234 is private"      # a colon inside speech is kept


def test_split_is_stable_and_roughly_half():
    ids = list(range(1000))
    assert [is_test(i) for i in ids] == [is_test(i) for i in ids]
    assert 400 < sum(is_test(i) for i in ids) < 600


def test_prefix_keeps_at_least_one_word():
    assert prefix("a b c d", 0.5) == "a b" and prefix("a b c d", 0.01) == "a" and prefix("a b c d", 1.0) == "a b c d"


def test_labels_are_detected_from_the_data():
    texts = ["Suspect: hi Innocent: yes"] * 9 + ["Suspect: ok. Note: x"]
    assert find_labels(texts) == ["Innocent", "Suspect"]
    assert clean("Suspect: hi Innocent: yes", ["Innocent", "Suspect"]) == "hi yes"
