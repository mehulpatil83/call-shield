from core.normalize import find_digit_runs, tok_match, tokenize


def test_tokens_keep_original_offsets():
    text = "Share the  OTP, please!"
    for t in tokenize(text):
        assert text[t.start:t.end].lower().strip("!,.") == t.norm


def test_spelled_letters_join():
    assert [t.norm for t in tokenize("my o t p is")] == ["my", "otp", "is"]


def test_devanagari_not_damaged():
    assert [t.norm for t in tokenize("ओटीपी सांगा।")] == ["ओटीपी", "सांगा"]


def test_fuzzy_match_rules():
    assert tok_match("केवाईसी", "केवायसी")
    assert not tok_match("pin", "pen")      # short tokens must match exactly
    assert not tok_match("bank", "back")


def test_digit_runs_multilingual():
    runs = find_digit_runs(tokenize("ek do teen char"))
    assert runs[0].digits == "1234"
    assert find_digit_runs(tokenize("एक दोन तीन चार पाच सहा"))[0].digits == "123456"
    assert find_digit_runs(tokenize("my code is 4721 ok"))[0].digits == "4721"
    assert find_digit_runs(tokenize("two lakh rupees")) == []


def test_kabhi_does_not_match_abhi():
    assert not tok_match("kabhi", "abhi")
    assert not tok_match("abhi", "kabhi")
