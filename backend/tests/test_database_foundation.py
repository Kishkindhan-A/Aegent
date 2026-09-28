from app.core.config import get_settings
from app.database.base import Base
from app.database.session import SessionLocal
from app.main import app


def test_settings_loads():
    settings = get_settings()
    assert settings.app_name == 'Aegent'
    assert settings.app_version == '0.1.0'


def test_database_url_is_loaded():
    settings = get_settings()
    assert 'postgresql' in settings.database_url
    assert '5432' in settings.database_url


def test_sqlalchemy_base_imports():
    assert Base is not None


def test_session_factory_imports():
    assert SessionLocal is not None


def test_fastapi_app_imports():
    assert app is not None
