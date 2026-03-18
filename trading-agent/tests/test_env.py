import os

from sentra.env import load_dotenv


def test_load_dotenv_sets_missing_values_without_overwriting_existing_ones(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "COINGECKO_DEMO_API_KEY=demo-key\nQUOTED_VALUE='quoted-value'\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("COINGECKO_DEMO_API_KEY", raising=False)
    monkeypatch.setenv("QUOTED_VALUE", "from-env")

    load_dotenv(env_path)

    assert os.environ["COINGECKO_DEMO_API_KEY"] == "demo-key"
    assert os.environ["QUOTED_VALUE"] == "from-env"
