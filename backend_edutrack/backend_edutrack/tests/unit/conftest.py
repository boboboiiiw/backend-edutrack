import pytest
from pyramid import testing
from unittest.mock import MagicMock

@pytest.fixture(scope='function')
def dummy_request():
    """
    Fixture untuk membuat dummy request Pyramid dengan mock dbsession.
    """
    with testing.testConfig() as config:
        # Mock dbsession
        mock_dbsession = MagicMock()
        config.add_request_method(lambda r: mock_dbsession, 'dbsession', reify=True)

        # Tambahkan konfigurasi routes yang relevan jika view memerlukannya
        # Misalnya untuk reverse lookup, walaupun untuk unit test views jarang dibutuhkan
        config.add_route('create_post', '/api/posts')
        config.add_route('list_posts', '/api/posts/all')
        config.add_route('get_post', '/api/posts/{id}')
        config.add_route('like_post', '/api/posts/{id}/like')
        config.add_route('dislike_post', '/api/posts/{id}/dislike')
        config.add_route('comment_add', '/api/comments')
        config.add_route('comment_by_post', '/api/comments/post/{post_id}')
        config.add_route("register", "/api/register")
        config.add_route("login", "/api/login")
        config.add_route("me", "/api/me")
        config.add_route("change_password", "/api/change-password")

        request = testing.DummyRequest()
        # Inisialisasi request.dbsession dengan mock
        request.dbsession = mock_dbsession
        
        # Inisialisasi request.user dengan dictionary kosong secara default,
        # bisa di-override di setiap test jika perlu data user.
        request.user = {} 

        return request

@pytest.fixture(scope='function')
def mock_dbsession(dummy_request):
    """
    Fixture untuk mengembalikan mock dbsession dari dummy_request.
    """
    return dummy_request.dbsession

@pytest.fixture(scope='function')
def mock_bcrypt():
    """
    Fixture untuk mock passlib.hash.bcrypt.
    """
    with MagicMock() as mock_b:
        yield mock_b