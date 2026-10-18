"""Rule additions for fake fraud-department calls and speech-to-text slips (from the first real phone test)."""
import pytest

from core.normalize import apply_slips, stem, tok_match, tokenize
from core.rules import analyse_text
from eval.call_eval import alert_times, evaluate
from eval.call_scripts import CALLS, by_split

# what Gnani heard on the first real phone call (acted, fictional); note the slips "flat" and "diverse"
REAL_CALL = ("good afternoon i am from department i am calling to verify some suspicious activity on your debit card ending 0400 "
             "our system flat two unauthorised charges made less than 10 minutes ago one for 842 dollars at a target in miami "
             "florida and other for three 50 dollars on the crypto exchange website did you authorize this and don't worry we "
             "are holding this transaction but you secure your account and diverse the same charges i need to verify your "
             "identity i am sending a secure authorization token to your mobile device right now please read that six digit "
             "verification code back to me so i can cancel the payment perfect the charges have been blocked")


def cats(text, kinds=("request", "pressure", "context")):
    return {h.category for h in analyse_text(text).hits if h.kind in kinds}


def test_the_real_call_is_high_with_the_new_evidence():
    r = analyse_text(REAL_CALL)
    assert r.level == "high"
    got = {h.category for h in r.hits}
    assert {"otp_request", "account_alert", "kyc_pretext", "urgency"} <= got
    for h in r.hits:                                              # evidence is always what was actually said
        assert REAL_CALL[h.start:h.end] == h.quote


@pytest.mark.parametrize("phrase,category", [
    ("we detected suspicious activity on your account", "account_alert"),
    ("there are two unauthorised charges on it", "account_alert"),
    ("i need to verify your identity", "kyc_pretext"),
    ("your debit card ending 4419", "account_alert"),
    ("we are holding this transaction for now", "account_alert"),
    ("please read me the secure authorization token", "otp_request"),
    ("please share the secure authorisation token", "otp_request"),      # British spelling
    ("tell me the one time code", "otp_request"),
    ("move your money to a safe account", "payment_request"),
])
def test_requested_phrases_are_found(phrase, category):
    assert category in cats(phrase), phrase


def test_the_opening_alone_is_elevated_not_high():
    r = analyse_text("good afternoon i am calling from the fraud prevention team we detected suspicious activity on your debit card")
    assert r.level == "elevated", [(h.category, h.quote) for h in r.hits]
    assert {h.category for h in r.hits} >= {"authority", "account_alert"}


def test_problem_report_plus_identity_check_is_elevated_even_when_the_caller_name_was_not_heard():
    # the first real call: speech-to-text dropped the name of the department, so no authority cue was heard
    opening = REAL_CALL[: REAL_CALL.index("i am sending a secure")]
    r = analyse_text(opening)
    assert r.level == "elevated", [(h.category, h.quote) for h in r.hits]
    t = alert_times(REAL_CALL)
    assert t["elevated"] < t["high"]


def test_a_problem_report_without_authority_is_not_an_alert():
    assert analyse_text("my card shows suspicious activity so i called the bank yesterday").level == "low"


# ------------------------------------------------------------------------------------ speech-to-text slips ---
def test_diverse_is_read_as_reverse_next_to_charges_and_the_quote_keeps_the_heard_words():
    text = "we will diverse the same charges for you"
    hits = [h for h in analyse_text(text).hits if h.category == "account_alert"]
    assert hits and hits[0].quote == "diverse the same charges"


def test_slips_need_a_backing_neighbour_word():
    assert analyse_text("we live in a flat near the park and the diverse crowd is lovely").hits == []
    assert not [h for h in analyse_text("she bought a flat in pune").hits]
    assert "credential_request" in cats("tell me your atm pen number")
    assert not cats("tell me where your pen is")


def test_apply_slips_keeps_positions():
    toks = tokenize("our system flat two unauthorised charges")
    out = apply_slips(toks, [("flat", "flagged", {"unauthorised"})])
    assert [t.norm for t in out][2] == "flagged" and (out[2].start, out[2].end) == (toks[2].start, toks[2].end)


def test_inflections_match():
    assert stem("verifying") == stem("verify") == stem("verified")
    assert stem("charges") == stem("charge") and stem("blocked") == stem("blocking")
    assert tok_match("verifying", "verify")
    assert not tok_match("holding", "hold")                    # short words must match exactly
    assert "kyc_pretext" in cats("i am verifying your identity")


def test_inflection_matching_does_not_confuse_different_words():
    assert not tok_match("charged", "chargers") and not tok_match("verified", "versions")
    assert not tok_match("kabhi", "abhi") and not tok_match("hurry", "worry")


def test_words_the_speech_to_text_split_or_joined_still_match():
    assert "remote_access" in cats("please install any desk on your phone")
    assert "remote_access" in cats("please open team viewer now")
    assert "credential_request" in cats("tell me your net banking pass word")


# ------------------------------------------------------------------------------------ calls that must stay calm ---
FRIENDLY = ("hi are we still meeting for lunch at one i will bring the notes from class let me know if the cafe is too crowded "
            "and we can go somewhere else see you soon")
WARNING = ("this is a reminder from your bank never share your otp pin or password with anyone even if they say they are calling "
           "from the bank if someone asks hang up and call the number on your card")


def test_friendly_and_bank_warning_calls_stay_low():
    assert analyse_text(FRIENDLY).level == "low" and analyse_text(FRIENDLY).hits == []
    r = analyse_text(WARNING)
    assert r.level == "low" and not [h for h in r.hits if h.kind == "request"]


def test_a_genuine_bank_alert_that_tells_you_to_call_back_is_at_most_elevated():
    r = analyse_text("this is your bank we detected suspicious activity on your card please call the number on the back of your card "
                     "we will never ask for your otp or pin")
    assert r.level in ("low", "elevated")
    assert not [h for h in r.hits if h.kind == "request"]


def test_a_delivery_code_request_is_not_high():
    r = analyse_text("hello i am the delivery executive please share the delivery code from your order app")
    assert r.level in ("low", "elevated")


# ------------------------------------------------------------------------------------ the evaluation scripts ----
def test_call_script_bank_is_balanced_and_split():
    assert len(CALLS) == 20 and len(by_split("dev")) == 10 and len(by_split("test")) == 10
    for split in ("dev", "test"):
        labels = [s["label"] for s in by_split(split)]
        assert labels.count("scam") == 5 and labels.count("benign") == 5
    assert sum(s["hard"] for s in CALLS.values()) == 4


def test_every_dev_script_is_rated_as_expected():
    for s in by_split("dev"):
        level = analyse_text(s["text"]).level
        assert level == ("high" if s["label"] == "scam" else "low"), (s["id"], level)


def test_evaluate_counts_and_alert_times():
    res = evaluate(by_split("dev"))
    assert res["scams"] == 5 and res["benign"] == 5 and res["scam_missed"] == 0 and res["false_alarms"] == 0
    t = alert_times(CALLS["c-s1"]["text"])
    assert t["elevated"] is not None and t["high"] is not None and t["elevated"] <= t["high"]
    assert alert_times(CALLS["c-b1"]["text"]) == {"elevated": None, "high": None}
