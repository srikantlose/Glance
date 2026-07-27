from app.governance.pii_guard import redact, scan


def test_detects_email():
    findings = scan("reach me at sam@example.com please")
    assert any(f.type == "email" and f.text == "sam@example.com" for f in findings)


def test_detects_indian_phone():
    findings = scan("call me on 9876543210 tomorrow")
    assert any(f.type == "phone" for f in findings)


def test_detects_aadhaar_pattern():
    findings = scan("my aadhaar is 1234 5678 9123")
    assert any(f.type == "id" for f in findings)


def test_detects_pan_pattern():
    findings = scan("pan number ABCDE1234F on file")
    assert any(f.type == "id" for f in findings)


def test_detects_valid_card_number_luhn_ok():
    # well-known Luhn-valid test visa number
    findings = scan("card: 4111 1111 1111 1111")
    assert any(f.type == "card" for f in findings)


def test_rejects_non_luhn_digit_run():
    # 16 digits that fail the luhn checksum -- should not be flagged as a card
    findings = scan("reference number 1234 5678 9012 3456")
    assert not any(f.type == "card" for f in findings)


def test_redact_uses_expected_tokens():
    text = "email me at sam@example.com"
    redacted = redact(text, scan(text))
    assert "[redacted-email]" in redacted
    assert "sam@example.com" not in redacted
