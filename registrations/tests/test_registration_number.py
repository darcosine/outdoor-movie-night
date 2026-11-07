import pytest

from registrations.forms import RegistrationForm


@pytest.mark.parametrize("value", ["251FW0202", "251FW020277"])
def test_registration_number_must_be_exactly_ten_characters(value):
    form = RegistrationForm(data={"reg_number": value})
    form.is_valid()
    assert "exactly 10 characters" in form.errors["reg_number"][0]


def test_ten_character_alphanumeric_registration_number_is_accepted():
    form = RegistrationForm(data={"reg_number": "251FW02027"})
    form.is_valid()
    assert "reg_number" not in form.errors
