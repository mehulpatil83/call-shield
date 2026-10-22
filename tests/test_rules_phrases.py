from core.rules import analyse_text

SOFT_SCAM = ("Hello, this is John from the insurance department. We noticed some discrepancies in your policy and need to update your "
             "information. I wasn't aware of any issues. Can you elaborate on the discrepancies? Yes, we detected some errors in your recent "
             "premium payments. Can you confirm your position at the insurance department and provide a direct line to your office? "
             "Due to security protocols, I cannot share personal details. Time is of the essence, and we need to rectify this promptly.")


def test_pressure_without_any_request_is_elevated_by_two_pressure_types():
    r = analyse_text(SOFT_SCAM)
    assert r.level == "elevated"
    assert {h.category for h in r.hits} >= {"urgency", "verification_bypass"}


def test_one_pressure_type_alone_stays_low():
    assert analyse_text("Please decide soon, time is of the essence for the offer.").level == "low"
    assert analyse_text("Due to company policy, refunds take five working days. Thank you for calling.").level == "low"


def test_ordinary_calls_stay_low():
    assert analyse_text("Hi, your parcel is out for delivery. Please be home by five, we will call again if you miss it.").level == "low"
    assert analyse_text("Hello, this is the clinic. Your appointment is tomorrow at four. Please bring your earlier reports.").level == "low"
