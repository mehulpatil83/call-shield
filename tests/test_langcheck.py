from core.langcheck import check_language
from tests.cases import BENIGN, SCAM, WRONG_LANGUAGE


def test_wrong_language_is_flagged():
    assert check_language(WRONG_LANGUAGE["mr_clinic_as_en"], "en") == "not_english"
    assert check_language(WRONG_LANGUAGE["mr_clinic_as_en"], "mr") == "not_devanagari"


def test_right_language_is_not_flagged():
    for key in ("en_scam", "en_exec"):
        assert check_language(SCAM[key], "en") is None
    assert check_language(BENIGN["en_benign"], "en") is None
    assert check_language(SCAM["mr_scam"], "mr") is None
    assert check_language(SCAM["hinglish_scam_deva"], "hi") is None


def test_short_text_hinglish_and_auto_are_never_flagged():
    assert check_language("hello", "en") is None
    assert check_language(WRONG_LANGUAGE["mr_clinic_as_en"], "hinglish") is None
    assert check_language(WRONG_LANGUAGE["mr_clinic_as_en"], "auto") is None
