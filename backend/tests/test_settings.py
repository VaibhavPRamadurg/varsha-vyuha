import pytest

from app.settings import LOCAL_FRONTEND_ORIGINS, allowed_frontend_origins


def test_deployed_origin_is_added_without_removing_local_vite_origins() -> None:
    origins = allowed_frontend_origins("https://varshavyuha.vercel.app/")
    assert "https://varshavyuha.vercel.app" in origins
    assert set(LOCAL_FRONTEND_ORIGINS).issubset(origins)


def test_origins_accept_a_comma_separated_allowlist() -> None:
    origins = allowed_frontend_origins("https://one.example, https://two.example")
    assert origins[-2:] == ["https://one.example", "https://two.example"]


@pytest.mark.parametrize("value", ["*", "https://example.com/path", "ftp://example.com", "example.com"])
def test_origins_reject_values_that_are_not_complete_http_origins(value: str) -> None:
    with pytest.raises(ValueError, match="ALLOWED_FRONTEND_ORIGINS"):
        allowed_frontend_origins(value)
