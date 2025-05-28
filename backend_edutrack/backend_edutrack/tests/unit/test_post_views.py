import pytest
from unittest.mock import MagicMock, patch
from pyramid.response import Response
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import joinedload # Tetap import untuk mock

from datetime import datetime

from backend_edutrack.views.post import (
    create_post,
    list_posts,
    get_post,
    like_post,
    dislike_post,
    post_to_dict
)
from backend_edutrack.models.post import Post, PostInteraction
from backend_edutrack.models.user import User
from backend_edutrack.models.url import URL

from .conftest import dummy_request, mock_dbsession


# --- FIXTURES ---
@pytest.fixture
def mock_user_mahasiswa():
    user = MagicMock(spec=User)
    user.id = 1
    user.name = "Mahasiswa Test"
    user.email = "mahasiswa@example.com"
    user.role = "Mahasiswa"
    user.prodi = "Teknik Informatika"
    user._sa_instance_state = MagicMock() # FIX: Add _sa_instance_state
    return user

@pytest.fixture
def mock_user_dosen():
    user = MagicMock(spec=User)
    user.id = 2
    user.name = "Dosen Test"
    user.email = "dosen@example.com"
    user.role = "Dosen"
    user.prodi = None
    user._sa_instance_state = MagicMock() # FIX: Add _sa_instance_state
    return user

@pytest.fixture
def mock_url_obj():
    url = MagicMock(spec=URL)
    url.id = 1
    url.url = "http://example.com/reference"
    url._sa_instance_state = MagicMock() # FIX: Add _sa_instance_state
    return url

@pytest.fixture
def mock_post(mock_user_mahasiswa):
    post = MagicMock(spec=Post)
    post.id = 101
    post.title = "Test Post Title"
    post.content = "This is a test post content."
    post.created_at = datetime(2025, 5, 27, 10, 0, 0)
    post.author_id = mock_user_mahasiswa.id
    post.author = mock_user_mahasiswa
    post.likes = 5
    post.dislikes = 2
    post.references = [MagicMock(spec=URL, url="http://existing.com/ref1", _sa_instance_state=MagicMock())] # FIX: Add _sa_instance_state for URL in references
    post._sa_instance_state = MagicMock() # FIX: Add _sa_instance_state
    return post

@pytest.fixture
def mock_post_interaction():
    interaction = MagicMock(spec=PostInteraction)
    interaction.id = 1
    interaction.user_id = 1
    interaction.post_id = 101
    interaction.interaction_type = 'like'
    interaction.created_at = datetime.utcnow()
    interaction._sa_instance_state = MagicMock() # FIX: Add _sa_instance_state
    return interaction


# --- TEST UNTUK create_post VIEW ---
class TestCreatePostView:

    def test_create_post_success(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role, "name": mock_user_mahasiswa.name}
        dummy_request.json_body = {
            "title": "Judul Post Baru",
            "content": "Isi konten post.",
            "references": ["http://new.example.com/ref1", "http://new.example.com/ref2"]
        }

        user_query_mock = MagicMock()
        user_query_mock.get.return_value = mock_user_mahasiswa

        url_query_mock = MagicMock()
        url_query_mock.filter_by.return_value.first.return_value = None

        post_query_mock = MagicMock()
        post_query_mock.count.return_value = 0
        post_query_mock.filter_by.return_value.first.return_value = None
        post_query_mock.options.return_value = post_query_mock
        post_query_mock.order_by.return_value = post_query_mock
        post_query_mock.offset.return_value = post_query_mock
        post_query_mock.limit.return_value = post_query_mock
        post_query_mock.all.return_value = []

        def mock_query_side_effect(model):
            if model is User:
                return user_query_mock
            elif model is URL:
                return url_query_mock
            elif model is Post:
                return post_query_mock
            return MagicMock()

        mock_dbsession.query.side_effect = mock_query_side_effect

        with patch('backend_edutrack.models.post.Post') as MockPost, \
            patch('backend_edutrack.models.url.URL') as MockURL:
            
            created_post_mock = MagicMock(spec=Post)
            created_post_mock.id = 201
            created_post_mock.title = dummy_request.json_body['title']
            created_post_mock.content = dummy_request.json_body['content']
            created_post_mock.author_id = mock_user_mahasiswa.id
            created_post_mock.created_at = datetime.utcnow()
            created_post_mock.likes = 0
            created_post_mock.dislikes = 0
            created_post_mock.author = mock_user_mahasiswa
            created_post_mock._sa_instance_state = MagicMock() # FIX: Tambahkan ini
            
            mock_url_1 = MagicMock(spec=URL, url="http://new.example.com/ref1", _sa_instance_state=MagicMock()) # FIX: Tambahkan
            mock_url_2 = MagicMock(spec=URL, url="http://new.example.com/ref2", _sa_instance_state=MagicMock()) # FIX: Tambahkan
            created_post_mock.references = [mock_url_1, mock_url_2]
            
            MockPost.return_value = created_post_mock
            MockURL.side_effect = [mock_url_1, mock_url_2]

            response = create_post(dummy_request)

            assert isinstance(response, dict)
            assert response["message"] == "Post berhasil dibuat"
            assert "post" in response
            assert response["post"]["title"] == dummy_request.json_body['title']
            assert response["post"]["author_id"] == mock_user_mahasiswa.id
            assert response["post"]["author_name"] == mock_user_mahasiswa.name
            assert sorted(response["post"]["references"]) == sorted(["http://new.example.com/ref1", "http://new.example.com/ref2"])

            mock_dbsession.add.assert_any_call(created_post_mock)
            mock_dbsession.add.assert_any_call(mock_url_1)
            mock_dbsession.add.assert_any_call(mock_url_2)
            
            mock_dbsession.flush.assert_called_once()
            # mock_dbsession.commit.assert_called_once() # Dihapus

    def test_create_post_success_existing_references(self, dummy_request, mock_dbsession, mock_user_mahasiswa, mock_url_obj):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role, "name": mock_user_mahasiswa.name}
        dummy_request.json_body = {
            "title": "Post dengan Referensi Existing",
            "content": "Konten.",
            "references": [mock_url_obj.url]
        }
        
        def mock_query_side_effect(model):
            query_chain_mock = MagicMock()
            if model is User:
                query_chain_mock.get.return_value = mock_user_mahasiswa
            elif model is URL:
                query_chain_mock.filter_by.return_value.first.return_value = mock_url_obj
            
            query_chain_mock.filter_by.return_value = query_chain_mock
            return query_chain_mock

        mock_dbsession.query.side_effect = mock_query_side_effect

        with patch('backend_edutrack.models.post.Post') as MockPost, \
             patch('backend_edutrack.models.url.URL') as MockURL:
            
            created_post_mock = MagicMock(spec=Post)
            created_post_mock.id = 201
            created_post_mock.title = dummy_request.json_body['title']
            created_post_mock.content = dummy_request.json_body['content']
            created_post_mock.author_id = mock_user_mahasiswa.id
            created_post_mock.created_at = datetime.utcnow()
            created_post_mock.likes = 0
            created_post_mock.dislikes = 0
            created_post_mock.author = mock_user_mahasiswa
            created_post_mock.references = [mock_url_obj]
            created_post_mock._sa_instance_state = MagicMock() # FIX: Tambahkan ini
            
            MockPost.return_value = created_post_mock

            response = create_post(dummy_request)

            assert isinstance(response, dict)
            assert response["message"] == "Post berhasil dibuat"
            assert response["post"]["references"] == [mock_url_obj.url]
            assert response["post"]["author_name"] == mock_user_mahasiswa.name
            
            mock_dbsession.add.assert_called_once_with(created_post_mock)
            MockURL.assert_not_called()
            mock_dbsession.flush.assert_called_once()
            # mock_dbsession.commit.assert_called_once() # Dihapus


    def test_create_post_success_no_references(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role, "name": mock_user_mahasiswa.name}
        dummy_request.json_body = {
            "title": "Post Tanpa Referensi",
            "content": "Konten."
        }
        
        def mock_query_side_effect(model):
            query_chain_mock = MagicMock()
            if model is User:
                query_chain_mock.get.return_value = mock_user_mahasiswa
            elif model is URL:
                query_chain_mock.filter_by.return_value.first.return_value = None
            
            query_chain_mock.filter_by.return_value = query_chain_mock
            return query_chain_mock

        mock_dbsession.query.side_effect = mock_query_side_effect

        with patch('backend_edutrack.models.post.Post') as MockPost, \
             patch('backend_edutrack.models.url.URL') as MockURL:
            
            created_post_mock = MagicMock(spec=Post)
            created_post_mock.id = 201
            created_post_mock.title = dummy_request.json_body['title']
            created_post_mock.content = dummy_request.json_body['content']
            created_post_mock.author_id = mock_user_mahasiswa.id
            created_post_mock.created_at = datetime.utcnow()
            created_post_mock.likes = 0
            created_post_mock.dislikes = 0
            created_post_mock.author = mock_user_mahasiswa
            created_post_mock.references = []
            created_post_mock._sa_instance_state = MagicMock() # FIX: Tambahkan ini
            
            MockPost.return_value = created_post_mock

            response = create_post(dummy_request)

            assert isinstance(response, dict)
            assert response["message"] == "Post berhasil dibuat"
            assert response["post"]["references"] == []
            assert response["post"]["author_name"] == mock_user_mahasiswa.name

            mock_dbsession.add.assert_called_once_with(created_post_mock)
            MockURL.assert_not_called()
            mock_dbsession.flush.assert_called_once()
            # mock_dbsession.commit.assert_called_once() # Dihapus

    def test_create_post_invalid_references_data_types(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role, "name": mock_user_mahasiswa.name}
        dummy_request.json_body = {
            "title": "Valid Title",
            "content": "Valid Content",
            "references": ["http://valid.com", "", None, 123, "   "]
        }
        
        def mock_query_side_effect(model):
            query_chain_mock = MagicMock()
            if model is User:
                query_chain_mock.get.return_value = mock_user_mahasiswa
            elif model is URL:
                query_chain_mock.filter_by.return_value.first.return_value = None
            
            query_chain_mock.filter_by.return_value = query_chain_mock
            return query_chain_mock

        mock_dbsession.query.side_effect = mock_query_side_effect

        with patch('backend_edutrack.models.post.Post') as MockPost, \
             patch('backend_edutrack.models.url.URL') as MockURL:
            
            created_post_mock = MagicMock(spec=Post)
            created_post_mock.id = 201
            created_post_mock.title = dummy_request.json_body['title']
            created_post_mock.content = dummy_request.json_body['content']
            created_post_mock.author_id = mock_user_mahasiswa.id
            created_post_mock.created_at = datetime.utcnow()
            created_post_mock.likes = 0
            created_post_mock.dislikes = 0
            created_post_mock.author = mock_user_mahasiswa
            created_post_mock._sa_instance_state = MagicMock() # FIX: Tambahkan ini

            mock_valid_url = MagicMock(spec=URL, url="http://valid.com", _sa_instance_state=MagicMock()) # FIX: Tambahkan _sa_instance_state
            created_post_mock.references = [mock_valid_url]
            
            MockPost.return_value = created_post_mock
            MockURL.return_value = mock_valid_url # Pastikan ini mengembalikan mock yang memiliki _sa_instance_state

            response = create_post(dummy_request)
            assert isinstance(response, dict)
            assert response["message"] == "Post berhasil dibuat"
            assert response["post"]["references"] == ["http://valid.com"] 
            
            mock_dbsession.add.assert_any_call(created_post_mock)
            mock_dbsession.add.assert_any_call(mock_valid_url)
            
            mock_dbsession.flush.assert_called_once()
            # mock_dbsession.commit.assert_called_once() # Dihapus

    def test_create_post_unauthenticated(self, dummy_request):
        dummy_request.user = {}
        dummy_request.json_body = {"title": "Test", "content": "Test"}
        
        response = create_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 401
        assert response.json_body["error"] == "Autentikasi diperlukan untuk membuat post."

    def test_create_post_forbidden_role(self, dummy_request, mock_user_dosen):
        dummy_request.user = {"id": mock_user_dosen.id, "role": mock_user_dosen.role}
        dummy_request.json_body = {"title": "Test", "content": "Test"}
        
        response = create_post(dummy_request)

        assert isinstance(response, Response)
        assert response.status_code == 403
        assert response.json_body["error"] == "Hanya mahasiswa yang diizinkan membuat post."

    def test_create_post_missing_fields(self, dummy_request, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role}
        dummy_request.json_body = {"title": "Test"} # Missing content
        
        response = create_post(dummy_request)

        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.json_body["error"] == "Judul dan konten harus diisi."

    def test_create_post_integrity_error(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role}
        dummy_request.json_body = {"title": "Judul Konflik", "content": "Konten Konflik"}

        mock_dbsession.add.side_effect = IntegrityError("Simulated integrity error", {}, MagicMock())

        response = create_post(dummy_request)

        assert isinstance(response, Response)
        assert response.status_code == 409
        assert response.json_body["error"] == "Terjadi konflik data. Mungkin ada duplikat."
        # mock_dbsession.rollback.assert_called_once() # Dihapus karena rollback ditangani oleh TM

    def test_create_post_db_api_error(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role}
        dummy_request.json_body = {"title": "Judul DB Error", "content": "Konten DB Error"}

        mock_dbsession.add.side_effect = DBAPIError("Simulated DBAPI error", {}, MagicMock())

        response = create_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 500
        assert response.json_body["error"] == "Terjadi kesalahan database."
        # mock_dbsession.rollback.assert_called_once() # Dihapus

    def test_create_post_key_error_user_data(self, dummy_request, mock_dbsession):
        # Ini menguji kasus di mana request.user tidak memiliki 'id' (KeyError)
        dummy_request.user = {"role": "Mahasiswa"} # Tidak ada 'id'
        dummy_request.json_body = {"title": "Test", "content": "Test"}

        response = create_post(dummy_request)

        assert isinstance(response, Response)
        assert response.status_code == 401
        # FIX: Pesan error yang benar adalah "Autentikasi diperlukan untuk membuat post."
        # karena logika di view: `if not user_id: return error_response(...)`
        assert response.json_body["error"] == "Autentikasi diperlukan untuk membuat post."

    def test_create_post_unexpected_error(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id, "role": mock_user_mahasiswa.role}
        
        # FIX: Patch error_response dan picu exception di tempat yang berbeda
        # Simulasikan error yang terjadi setelah data pengguna diambil tapi sebelum post dibuat
        # atau di tengah proses add/flush
        with patch('backend_edutrack.views.post.error_response') as mock_error_response:
            mock_error_response.return_value = Response(
                json={"error": "Terjadi kesalahan server tidak terduga."}, status=500
            )
            # Simulasikan error ketika mencoba mengakses json_body
            dummy_request.json_body = MagicMock(side_effect=Exception("Simulated unexpected error"))

            response = create_post(dummy_request)

            assert isinstance(response, Response)
            assert response.status_code == 500
            assert response.json_body["error"] == "Terjadi kesalahan server tidak terduga."
            mock_error_response.assert_called_once_with(
                dummy_request, "Terjadi kesalahan server tidak terduga.", 500
            )
        # mock_dbsession.rollback.assert_called_once() # Dihapus


# --- TEST UNTUK list_posts VIEW ---
class TestListPostsView:

    @patch('sqlalchemy.orm.joinedload') # FIX: Jangan berikan return_value langsung, biarkan itu mengembalikan fungsi
    def test_list_posts_success_with_pagination(self, mock_joinedload_func, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa, mock_url_obj):
        mock_post.author = mock_user_mahasiswa
        mock_post.references = [mock_url_obj]
        
        def mock_query_factory(model):
            query_chain_mock = MagicMock()
            if model is Post:
                query_chain_mock.count.return_value = 25
                query_chain_mock.all.return_value = [mock_post, mock_post]
                query_chain_mock.options.return_value = query_chain_mock
                query_chain_mock.order_by.return_value = query_chain_mock
                query_chain_mock.offset.return_value = query_chain_mock
                query_chain_mock.limit.return_value = query_chain_mock
            return query_chain_mock

        mock_dbsession.query.side_effect = mock_query_factory


        dummy_request.params = {"page": "2", "per_page": "10"}

        response = list_posts(dummy_request)
        assert isinstance(response, dict)
        assert "posts" in response
        assert len(response["posts"]) == 2
        assert response["posts"][0]["id"] == mock_post.id
        assert response["posts"][0]["author_name"] == mock_user_mahasiswa.name
        assert response["posts"][0]["references"] == [mock_url_obj.url]

        assert response["pagination"]["total_posts"] == 25
        assert response["pagination"]["per_page"] == 10
        assert response["pagination"]["current_page"] == 2
        assert response["pagination"]["total_pages"] == 3
        assert response["pagination"]["has_next"] is True
        assert response["pagination"]["has_prev"] is True
        
        # FIX: joinedload dipanggil dua kali (untuk Post.author dan Post.references)
        assert mock_joinedload_func.call_count == 2
        mock_joinedload_func.assert_any_call(Post.author)
        mock_joinedload_func.assert_any_call(Post.references)


    @patch('sqlalchemy.orm.joinedload')
    def test_list_posts_default_pagination(self, mock_joinedload_func, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa):
        mock_post.author = mock_user_mahasiswa
        
        def mock_query_factory(model):
            query_chain_mock = MagicMock()
            if model is Post:
                query_chain_mock.count.return_value = 5
                query_chain_mock.all.return_value = [mock_post]
                query_chain_mock.options.return_value = query_chain_mock
                query_chain_mock.order_by.return_value = query_chain_mock
                query_chain_mock.offset.return_value = query_chain_mock
                query_chain_mock.limit.return_value = query_chain_mock
            return query_chain_mock

        mock_dbsession.query.side_effect = mock_query_factory

        dummy_request.params = {}

        response = list_posts(dummy_request)
        assert isinstance(response, dict)
        assert response["pagination"]["current_page"] == 1
        assert response["pagination"]["per_page"] == 10
        assert response["pagination"]["total_pages"] == 1
        assert response["pagination"]["has_next"] is False
        assert response["pagination"]["has_prev"] is False
        assert mock_joinedload_func.call_count == 2 # Juga dipanggil 2 kali

    @patch('sqlalchemy.orm.joinedload')
    def test_list_posts_invalid_pagination_params(self, mock_joinedload_func, dummy_request, mock_dbsession):
        dummy_request.params = {"page": "abc", "per_page": "xyz"}
        
        response = list_posts(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.json_body["error"] == "Parameter 'page' atau 'per_page' tidak valid."

        dummy_request.params = {"page": "-1", "per_page": "0"}
        
        def mock_query_factory(model):
            query_chain_mock = MagicMock()
            if model is Post:
                query_chain_mock.count.return_value = 1
                query_chain_mock.all.return_value = [MagicMock(spec=Post, id=1, title="A", content="B", created_at=datetime.utcnow(), author=MagicMock(spec=User, name="Author", _sa_instance_state=MagicMock()), references=[], _sa_instance_state=MagicMock())] # FIX: Tambahkan _sa_instance_state
                query_chain_mock.options.return_value = query_chain_mock
                query_chain_mock.order_by.return_value = query_chain_mock
                query_chain_mock.offset.return_value = query_chain_mock
                query_chain_mock.limit.return_value = query_chain_mock
            return query_chain_mock

        mock_dbsession.query.side_effect = mock_query_factory

        response = list_posts(dummy_request)
        assert isinstance(response, dict)
        assert response["pagination"]["current_page"] == 1
        assert response["pagination"]["per_page"] == 10 # Default ke 10 jika per_page <= 0
        assert mock_joinedload_func.call_count == 2 # Pastikan ini masih dihitung

        dummy_request.params = {"page": "1", "per_page": "200"}
        response = list_posts(dummy_request)
        assert isinstance(response, dict)
        assert response["pagination"]["per_page"] == 100 # FIX: Ini harus 100 karena batasan
        assert mock_joinedload_func.call_count == 4 # Panggilan baru untuk setiap test sub-case

    def test_list_posts_db_api_error(self, dummy_request, mock_dbsession):
        def mock_query_factory(model):
            if model is Post:
                raise DBAPIError("Error during query", {}, MagicMock())
            return MagicMock()
        mock_dbsession.query.side_effect = mock_query_factory

        response = list_posts(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 500
        assert response.json_body["error"] == "Terjadi kesalahan database."

    def test_list_posts_unexpected_error(self, dummy_request):
        # FIX: Perlu memiliki dummy_request.dbsession sebelum mengakses .query
        dummy_request.dbsession = MagicMock() 
        def mock_query_factory(model):
            if model is Post:
                raise Exception("Unexpected error during query")
            return MagicMock()
        dummy_request.dbsession.query.side_effect = mock_query_factory

        response = list_posts(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 500
        assert response.json_body["error"] == "Terjadi kesalahan server tidak terduga."

# --- TEST UNTUK get_post VIEW ---
class TestGetPostView:

    def test_get_post_success(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa, mock_url_obj):
        mock_post.author = mock_user_mahasiswa
        mock_post.references = [mock_url_obj]

        dummy_request.matchdict = {"id": mock_post.id}
        
        mock_query_chain = MagicMock()
        mock_query_chain.filter_by.return_value.first.return_value = mock_post
        mock_dbsession.query.return_value = mock_query_chain
        mock_query_chain.options.return_value = mock_query_chain # Ensure options returns the chain

        response = get_post(dummy_request)
        
        assert isinstance(response, dict)
        assert response["id"] == mock_post.id
        assert response["title"] == mock_post.title
        assert response["content"] == mock_post.content
        assert response["author_name"] == mock_user_mahasiswa.name
        assert response["references"] == [mock_url_obj.url]

    def test_get_post_not_found(self, dummy_request, mock_dbsession):
        dummy_request.matchdict = {"id": 999}
        mock_query_chain = MagicMock()
        mock_query_chain.filter_by.return_value.first.return_value = None
        mock_dbsession.query.return_value = mock_query_chain
        mock_query_chain.options.return_value = mock_query_chain

        response = get_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 404
        assert response.json_body["error"] == "Post tidak ditemukan."

    def test_get_post_invalid_id(self, dummy_request):
        dummy_request.matchdict = {"id": "abc"}
        response = get_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.json_body["error"] == "ID Post tidak valid."

    def test_get_post_db_api_error(self, dummy_request, mock_dbsession):
        dummy_request.matchdict = {"id": 1}
        mock_dbsession.query.side_effect = DBAPIError("Simulated DB error", {}, MagicMock())
        
        response = get_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 500
        assert response.json_body["error"] == "Terjadi kesalahan database."

    def test_get_post_unexpected_error(self, dummy_request):
        # FIX: Patch error_response dan picu exception dari matchdict
        with patch('backend_edutrack.views.post.error_response') as mock_error_response:
            mock_error_response.return_value = Response(
                json={"error": "Terjadi kesalahan server tidak terduga."}, status=500
            )
            dummy_request.matchdict = MagicMock(side_effect=Exception("Simulated unexpected error"))
            
            response = get_post(dummy_request)
            
            assert isinstance(response, Response)
            assert response.status_code == 500
            assert response.json_body["error"] == "Terjadi kesalahan server tidak terduga."
            mock_error_response.assert_called_once_with(
                dummy_request, "Terjadi kesalahan server tidak terduga.", 500
            )


# --- TEST UNTUK like_post VIEW ---
class TestLikePostView:

    def test_like_post_success_new_like(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        
        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = None # No existing interaction

        initial_likes = mock_post.likes
        initial_dislikes = mock_post.dislikes

        response = like_post(dummy_request)

        assert isinstance(response, dict)
        assert response["message"] == "Post berhasil disukai."
        assert response["likes"] == initial_likes + 1
        assert response["dislikes"] == initial_dislikes
        
        assert mock_post.likes == initial_likes + 1
        assert mock_post.dislikes == initial_dislikes
        
        mock_dbsession.add.assert_called_once()
        mock_dbsession.flush.assert_called_once()
        # mock_dbsession.commit.assert_called_once() # Dihapus

    def test_like_post_success_change_dislike_to_like(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa, mock_post_interaction):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        
        mock_post_interaction.interaction_type = 'dislike'

        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = mock_post_interaction

        initial_likes = mock_post.likes
        initial_dislikes = mock_post.dislikes

        response = like_post(dummy_request)

        assert isinstance(response, dict)
        assert response["message"] == "Dislike diubah menjadi like."
        assert response["likes"] == initial_likes + 1
        assert response["dislikes"] == initial_dislikes - 1
        assert mock_post_interaction.interaction_type == 'like'
        
        assert mock_post.likes == initial_likes + 1
        assert mock_post.dislikes == initial_dislikes - 1
        
        mock_dbsession.add.assert_called_once()
        mock_dbsession.flush.assert_called_once()
        # mock_dbsession.commit.assert_called_once() # Dihapus


    def test_like_post_already_liked(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa, mock_post_interaction):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        
        mock_post_interaction.interaction_type = 'like'

        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = mock_post_interaction

        initial_likes = mock_post.likes
        initial_dislikes = mock_post.dislikes
        
        response = like_post(dummy_request)

        assert isinstance(response, dict)
        assert response["message"] == "Anda sudah menyukai post ini."
        assert response["likes"] == initial_likes
        assert response["dislikes"] == initial_dislikes
        
        assert mock_post.likes == initial_likes
        assert mock_post.dislikes == initial_dislikes
        
        mock_dbsession.add.assert_not_called()
        mock_dbsession.flush.assert_not_called() # FIX: Flush tidak boleh dipanggil jika tidak ada perubahan
        # mock_dbsession.commit.assert_not_called() # Dihapus

    def test_like_post_unauthenticated(self, dummy_request):
        dummy_request.user = {}
        dummy_request.matchdict = {"id": 1}
        response = like_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 401
        assert response.json_body["error"] == "Autentikasi diperlukan untuk menyukai post."

    def test_like_post_invalid_post_id(self, dummy_request, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": "abc"}
        response = like_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.json_body["error"] == "ID Post tidak valid."

    def test_like_post_not_found(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": 999}
        mock_dbsession.get.return_value = None

        response = like_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 404
        assert response.json_body["error"] == "Post tidak ditemukan."

    def test_like_post_db_api_error(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = None
        
        mock_dbsession.add.side_effect = DBAPIError("Error during add", {}, MagicMock())

        response = like_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 500
        assert response.json_body["error"] == "Terjadi kesalahan database saat menyukai post."
        # mock_dbsession.rollback.assert_called_once() # Dihapus

    def test_like_post_integrity_error(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = None
        
        mock_dbsession.add.side_effect = IntegrityError("Integrity constraint", {}, MagicMock())

        response = like_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 409
        assert response.json_body["error"] == "Terjadi konflik interaksi. Mungkin Anda sudah berinteraksi dengan post ini."
        # mock_dbsession.rollback.assert_called_once() # Dihapus


    def test_like_post_unexpected_error(self, dummy_request, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        with patch('backend_edutrack.views.post.error_response') as mock_error_response:
            mock_error_response.return_value = Response(
                json={"error": "Terjadi kesalahan server tidak terduga."}, status=500
            )
            # FIX: Pindahkan side_effect ke dbsession.get untuk memicu error di sana
            # karena dbsession.get adalah panggilan DB pertama di like_post
            dummy_request.dbsession = MagicMock()
            dummy_request.dbsession.get.side_effect = Exception("Simulated unexpected error")

            response = like_post(dummy_request)
            
            assert isinstance(response, Response)
            assert response.status_code == 500
            assert response.json_body["error"] == "Terjadi kesalahan server tidak terduga."
            mock_error_response.assert_called_once_with(
                dummy_request, "Terjadi kesalahan server tidak terduga.", 500
            )


# --- TEST UNTUK dislike_post VIEW ---
class TestDislikePostView:

    def test_dislike_post_success_new_dislike(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        
        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = None

        initial_dislikes = mock_post.dislikes
        initial_likes = mock_post.likes

        response = dislike_post(dummy_request)

        assert isinstance(response, dict)
        assert response["message"] == "Post berhasil tidak disukai."
        assert response["dislikes"] == initial_dislikes + 1
        assert response["likes"] == initial_likes
        
        assert mock_post.dislikes == initial_dislikes + 1
        assert mock_post.likes == initial_likes

        mock_dbsession.add.assert_called_once()
        mock_dbsession.flush.assert_called_once()
        # mock_dbsession.commit.assert_called_once() # Dihapus

    def test_dislike_post_success_change_like_to_dislike(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa, mock_post_interaction):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        
        mock_post_interaction.interaction_type = 'like'

        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = mock_post_interaction

        initial_likes = mock_post.likes
        initial_dislikes = mock_post.dislikes

        response = dislike_post(dummy_request)

        assert isinstance(response, dict)
        assert response["message"] == "Like diubah menjadi dislike."
        assert response["likes"] == initial_likes - 1
        assert response["dislikes"] == initial_dislikes + 1
        assert mock_post_interaction.interaction_type == 'dislike'
        
        assert mock_post.likes == initial_likes - 1
        assert mock_post.dislikes == initial_dislikes + 1

        mock_dbsession.add.assert_called_once()
        mock_dbsession.flush.assert_called_once()
        # mock_dbsession.commit.assert_called_once() # Dihapus

    def test_dislike_post_already_disliked(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa, mock_post_interaction):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        
        mock_post_interaction.interaction_type = 'dislike'

        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = mock_post_interaction

        initial_dislikes = mock_post.dislikes
        initial_likes = mock_post.likes
        
        response = dislike_post(dummy_request)

        assert isinstance(response, dict)
        assert response["message"] == "Anda sudah tidak menyukai post ini."
        assert response["dislikes"] == initial_dislikes
        assert response["likes"] == initial_likes
        
        assert mock_post.dislikes == initial_dislikes
        assert mock_post.likes == initial_likes
        
        mock_dbsession.add.assert_not_called()
        mock_dbsession.flush.assert_not_called() # FIX: Flush tidak boleh dipanggil jika tidak ada perubahan
        # mock_dbsession.commit.assert_not_called() # Dihapus

    def test_dislike_post_unauthenticated(self, dummy_request):
        dummy_request.user = {}
        dummy_request.matchdict = {"id": 1}
        response = dislike_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 401
        assert response.json_body["error"] == "Autentikasi diperlukan untuk tidak menyukai post."

    def test_dislike_post_invalid_post_id(self, dummy_request, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": "xyz"}
        response = dislike_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.json_body["error"] == "ID Post tidak valid."

    def test_dislike_post_not_found(self, dummy_request, mock_dbsession, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": 999}
        mock_dbsession.get.return_value = None

        response = dislike_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 404
        assert response.json_body["error"] == "Post tidak ditemukan."

    def test_dislike_post_db_api_error(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = None
        
        mock_dbsession.add.side_effect = DBAPIError("Error during add", {}, MagicMock())

        response = dislike_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 500
        assert response.json_body["error"] == "Terjadi kesalahan database saat tidak menyukai post."
        # mock_dbsession.rollback.assert_called_once() # Dihapus

    def test_dislike_post_integrity_error(self, dummy_request, mock_dbsession, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        dummy_request.matchdict = {"id": mock_post.id}
        mock_dbsession.get.return_value = mock_post
        mock_dbsession.query.return_value.filter_by.return_value.first.return_value = None
        
        mock_dbsession.add.side_effect = IntegrityError("Integrity constraint", {}, MagicMock())

        response = dislike_post(dummy_request)
        
        assert isinstance(response, Response)
        assert response.status_code == 409
        assert response.json_body["error"] == "Terjadi konflik interaksi. Mungkin Anda sudah berinteraksi dengan post ini."
        # mock_dbsession.rollback.assert_called_once() # Dihapus

    def test_dislike_post_unexpected_error(self, dummy_request, mock_post, mock_user_mahasiswa):
        dummy_request.user = {"id": mock_user_mahasiswa.id}
        with patch('backend_edutrack.views.post.error_response') as mock_error_response:
            mock_error_response.return_value = Response(
                json={"error": "Terjadi kesalahan server tidak terduga."}, status=500
            )
            # FIX: Pindahkan side_effect ke dbsession.get untuk memicu error di sana
            dummy_request.dbsession = MagicMock()
            dummy_request.dbsession.get.side_effect = Exception("Simulated unexpected error")

            response = dislike_post(dummy_request)
            
            assert isinstance(response, Response)
            assert response.status_code == 500
            assert response.json_body["error"] == "Terjadi kesalahan server tidak terduga."
            mock_error_response.assert_called_once_with(
                dummy_request, "Terjadi kesalahan server tidak terduga.", 500
            )