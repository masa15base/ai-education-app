from app.character_local_gen import build_character_data_url


def test_build_character_data_url():
    # 1x1 black pixel PNG
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    url = build_character_data_url(b64)
    assert url.startswith("data:image/png;base64,")
