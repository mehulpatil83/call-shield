import pytest

from core.rules import analyse_text, merge_results
from tests.cases import BENIGN, HARD, SCAM


@pytest.mark.parametrize("name", SCAM)
def test_scams_are_high(name):
    r = analyse_text(SCAM[name])
    assert r.level == "high", (name, r.level, [(h.category, h.quote) for h in r.hits])


@pytest.mark.parametrize("name", BENIGN)
def test_benign_calls_stay_low(name):
    r = analyse_text(BENIGN[name])
    assert r.level == "low", (name, r.level, [(h.category, h.quote) for h in r.hits])


def test_hard_negative_is_elevated_not_high():
    r = analyse_text(HARD["en_delivery_otp"])
    assert r.level == "elevated", (r.level, [(h.category, h.quote) for h in r.hits])


def test_never_share_otp_is_a_warning_not_a_request():
    r = analyse_text("Please never share your OTP with anyone.")
    kinds = {h.kind for h in r.hits}
    assert "warning" in kinds and "request" not in kinds


def test_evidence_quotes_come_from_the_transcript():
    text = SCAM["en_scam"]
    r = analyse_text(text)
    assert r.hits
    for h in r.hits:
        assert text[h.start:h.end] == h.quote


def test_spoken_digits_are_reported():
    r = analyse_text(SCAM["en_scam"])
    assert "472910" in [d["digits"] for d in r.digit_runs]
    r2 = analyse_text(SCAM["hinglish_scam"])
    assert "123456" in [d["digits"] for d in r2.digit_runs]


def test_spelling_variants_of_kyc_and_otp_are_found():
    for text in ["aapka kyc update pending hai", "आपका के वाई सी अपडेट बाकी है", "तुमचे केवायसी अपडेट बाकी आहे", "आपका केवाईसी"]:
        r = analyse_text(text)
        assert any(h.category == "kyc_pretext" for h in r.hits), text
    r = analyse_text("please tell me the o t p now")
    assert any(h.category == "otp_request" for h in r.hits)


def test_merge_prefers_warning_over_request():
    a = analyse_text("kisi ko OTP share na karein")
    b = analyse_text("kisi ko OTP share karein abhi")
    merged = merge_results([a, b], ["", ""])
    assert not any(h.kind == "request" and h.category == "otp_request" for h in merged.hits)


def test_empty_text():
    assert analyse_text("").level == "low"


def test_kabhi_is_not_urgency():
    r = analyse_text("bank kabhi phone par OTP nahi maangta")
    assert not any(h.category == "urgency" for h in r.hits)


def test_marathi_now_is_not_urgency_but_rightnow_is():
    assert not any(h.category == "urgency" for h in analyse_text("ठीक आहे आत्ता काळजी करू नका").hits)
    assert any(h.category == "urgency" for h in analyse_text("तुम्ही आत्ताच पडताळणी करा").hits)


def test_clinic_conversation_has_no_indicators_at_all():
    r = analyse_text(BENIGN["mr_clinic"])
    assert r.level == "low" and r.hits == []
