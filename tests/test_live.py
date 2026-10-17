"""Hit the real sites. Run with `pytest -m live`. May be flaky by nature."""
import pytest

from handlecheck import Status, check

pytestmark = pytest.mark.live

PLATFORMS = ["tiktok", "instagram", "facebook", "youtube", "x", "github", "reddit"]  # gmail: see below


@pytest.mark.parametrize("platform", PLATFORMS)
def test_known_account_found(platform):
    assert check(platform, "google").status is Status.FOUND


@pytest.mark.parametrize("platform", PLATFORMS)
@pytest.mark.parametrize("name", ["zzqxk93jfhw02", "zz.qxk_93.jfh", "__zzqxk93__"])
def test_random_account_not_found(platform, name):
    # INVALID is fine: some sites don't allow '.', '_' or leading '_' at all
    assert check(platform, name).status in (Status.NOT_FOUND, Status.INVALID)


def test_gmail_live():
    """Needs outbound port 25; skipped where it is blocked (many ISPs and CI runners)."""
    taken = check("gmail", "google.support")
    if taken.status is Status.UNKNOWN:
        pytest.skip(taken.detail)
    assert check("gmail", "zzqxk93jfhw02xyz").status is Status.NOT_FOUND
