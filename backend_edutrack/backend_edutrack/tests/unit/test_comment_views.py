import pytest
from unittest.mock import MagicMock, patch
from pyramid.response import Response
from sqlalchemy.exc import DBAPIError, IntegrityError
from datetime import datetime

from backend_edutrack.views.comment import (
    add_comment,
    get_comments_by_post
)
from backend_edutrack.models.comment import Comment
from backend_edutrack.models.post import Post
from backend_edutrack.models.user import User

from .conftest import dummy_request, mock_dbsession


#  FIXTURES KHUSUS UNTUK KOMENTAR 
@pytest.fixture
def mock_user_commenter():
    user = MagicMock(spec=User)
    user.id = 1
    user.name = "Commenter User"
    user.email = "commenter@student.itera.ac.id"
    user._sa_instance_state = MagicMock()
    return user

@pytest.fixture
def mock_post_with_comments():
    post = MagicMock(spec=Post)
    post.id = 201
    post.title = "Post with Comments"
    post.content = "Content of the post."
    post._sa_instance_state = MagicMock()
    return post

@pytest.fixture
def mock_comment(mock_user_commenter, mock_post_with_comments):
    comment = MagicMock(spec=Comment)
    comment.id = 1001
    comment.post_id = mock_post_with_comments.id
    comment.user_id = mock_user_commenter.id
    comment.content = "This is a test comment."
    comment.created_at = datetime(2025, 5, 28, 10, 0, 0)
    comment.user = mock_user_commenter # Penting untuk joinedload
    comment._sa_instance_state = MagicMock()
    return comment

@pytest.fixture
def mock_comments_list(mock_user_commenter, mock_post_with_comments):
    comments = []
    for i in range(1, 15): # 14 comments
        comment = MagicMock(spec=Comment)
        comment.id = 1000 + i
        comment.post_id = mock_post_with_comments.id
        comment.user_id = mock_user_commenter.id
        comment.content = f"Comment {i} for post {mock_post_with_comments.id}"
        comment.created_at = datetime(2025, 5, 28, 9, 0, i)
        comment.user = mock_user_commenter
        comment._sa_instance_state = MagicMock()
        comments.append(comment)
    return comments


#  HELPER UNTUK TEST RESPONSE JSON 
def assert_json_response(response, status_code, key_value_pairs=None):
    assert isinstance(response, Response)
    assert response.status_code == status_code
    assert response.content_type == 'application/json'
    if key_value_pairs:
        for key, value in key_value_pairs.items():
            assert response.json_body.get(key) == value


### Test untuk `add_comment` View


class TestAddCommentView:

    def test_add_comment_success(self, dummy_request, mock_dbsession, mock_user_commenter, mock_post_with_comments):
        dummy_request.user = {"id": mock_user_commenter.id}
        dummy_request.json_body = {
            "post_id": mock_post_with_comments.id,
            "content": "This is a new comment."
        }

        mock_dbsession.get.side_effect = lambda model, obj_id: {
            Post: mock_post_with_comments,
            User: mock_user_commenter
        }.get(model)
        
        with patch('backend_edutrack.models.comment.Comment') as MockComment:
            new_comment_mock = MagicMock(spec=Comment)
            new_comment_mock.id = 1002
            new_comment_mock.content = dummy_request.json_body["content"]
            new_comment_mock.created_at = datetime.utcnow() # Ini akan diset di constructor
            new_comment_mock.post_id = dummy_request.json_body["post_id"]
            new_comment_mock.user_id = mock_user_commenter.id
            new_comment_mock._sa_instance_state = MagicMock()
            MockComment.return_value = new_comment_mock

            response = add_comment(dummy_request)

            assert isinstance(response, dict) # Karena renderer='json'
            assert response["message"] == "Komentar berhasil ditambahkan"
            assert response["comment"]["content"] == dummy_request.json_body["content"]
            assert response["comment"]["post_id"] == mock_post_with_comments.id
            assert response["comment"]["user_id"] == mock_user_commenter.id
            assert response["comment"]["username"] == mock_user_commenter.name
            
            mock_dbsession.add.assert_called_once_with(new_comment_mock)
            mock_dbsession.flush.assert_called_once()


    def test_add_comment_unauthenticated(self, dummy_request):
        dummy_request.user = {}
        dummy_request.json_body = {"post_id": 1, "content": "test"}
        response = add_comment(dummy_request)
        assert_json_response(response, 401, {"error": "Autentikasi diperlukan untuk menambah komentar."})

    def test_add_comment_missing_fields(self, dummy_request, mock_user_commenter):
        dummy_request.user = {"id": mock_user_commenter.id}
        dummy_request.json_body = {"content": "some content"} # Missing post_id
        response = add_comment(dummy_request)
        assert_json_response(response, 400, {"error": "Post ID dan konten komentar wajib diisi."})

    def test_add_comment_invalid_post_id(self, dummy_request, mock_user_commenter):
        dummy_request.user = {"id": mock_user_commenter.id}
        dummy_request.json_body = {"post_id": "abc", "content": "test"}
        response = add_comment(dummy_request)
        assert_json_response(response, 400, {"error": "Post ID tidak valid."})

    def test_add_comment_post_not_found(self, dummy_request, mock_dbsession, mock_user_commenter):
        dummy_request.user = {"id": mock_user_commenter.id}
        dummy_request.json_body = {"post_id": 999, "content": "test"}
        
        mock_dbsession.get.side_effect = lambda model, obj_id: {
            Post: None, # Post not found
            User: mock_user_commenter
        }.get(model)

        response = add_comment(dummy_request)
        assert_json_response(response, 404, {"error": "Post tidak ditemukan."})

    def test_add_comment_user_not_found_in_db(self, dummy_request, mock_dbsession, mock_post_with_comments):
        dummy_request.user = {"id": 999} # Token user_id
        dummy_request.json_body = {"post_id": mock_post_with_comments.id, "content": "test"}
        
        mock_dbsession.get.side_effect = lambda model, obj_id: {
            Post: mock_post_with_comments,
            User: None # User not found in DB
        }.get(model)

        response = add_comment(dummy_request)
        assert_json_response(response, 401, {"error": "Pengguna tidak valid atau tidak ditemukan."})

    def test_add_comment_db_api_error(self, dummy_request, mock_dbsession, mock_user_commenter, mock_post_with_comments):
        dummy_request.user = {"id": mock_user_commenter.id}
        dummy_request.json_body = {"post_id": mock_post_with_comments.id, "content": "test"}

        mock_dbsession.get.side_effect = lambda model, obj_id: {
            Post: mock_post_with_comments,
            User: mock_user_commenter
        }.get(model)
        mock_dbsession.add.side_effect = DBAPIError("Simulated DB error", {}, MagicMock())
        dummy_request.log = MagicMock()

        response = add_comment(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan database saat menambah komentar."})
        dummy_request.log.exception.assert_called_once_with("Database error in add_comment:")

    def test_add_comment_integrity_error(self, dummy_request, mock_dbsession, mock_user_commenter, mock_post_with_comments):
        dummy_request.user = {"id": mock_user_commenter.id}
        dummy_request.json_body = {"post_id": mock_post_with_comments.id, "content": "test"}

        mock_dbsession.get.side_effect = lambda model, obj_id: {
            Post: mock_post_with_comments,
            User: mock_user_commenter
        }.get(model)
        mock_dbsession.flush.side_effect = IntegrityError("Simulated Integrity error", {}, MagicMock())
        dummy_request.log = MagicMock()

        response = add_comment(dummy_request)
        assert_json_response(response, 409, {"error": "Terjadi konflik data saat menambah komentar."})
        dummy_request.log.exception.assert_called_once_with("Database integrity error in add_comment:")

    def test_add_comment_unexpected_error(self, dummy_request, mock_user_commenter):
        dummy_request.user = {"id": mock_user_commenter.id}
        dummy_request.json_body = MagicMock(side_effect=Exception("Unexpected test error"))
        dummy_request.log = MagicMock()

        response = add_comment(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server tidak terduga."})
        dummy_request.log.exception.assert_called_once_with("Unexpected error in add_comment:")


### Test untuk `get_comments_by_post` View


class TestGetCommentsByPostView:

    @patch('sqlalchemy.orm.joinedload')
    def test_get_comments_by_post_success(self, mock_joinedload_func, dummy_request, mock_dbsession, mock_post_with_comments, mock_comments_list, mock_user_commenter):
        dummy_request.matchdict = {"post_id": mock_post_with_comments.id}
        dummy_request.params = {"page": "1", "per_page": "10"}

        # Configure mock_dbsession.get for Post
        mock_dbsession.get.return_value = mock_post_with_comments

        # Configure mock_dbsession.query for Comment
        query_mock = MagicMock()
        query_mock.filter_by.return_value = query_mock
        query_mock.count.return_value = len(mock_comments_list) # Total comments
        query_mock.options.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value.all.return_value = mock_comments_list[:10] # First 10 comments
        mock_dbsession.query.return_value = query_mock

        response = get_comments_by_post(dummy_request)

        assert isinstance(response, dict) # Karena renderer='json'
        assert "comments" in response
        assert len(response["comments"]) == 10
        assert response["comments"][0]["content"] == mock_comments_list[0].content
        assert response["comments"][0]["username"] == mock_user_commenter.name
        
        assert response["pagination"]["total_comments"] == len(mock_comments_list)
        assert response["pagination"]["per_page"] == 10
        assert response["pagination"]["current_page"] == 1
        assert response["pagination"]["total_pages"] == 2 # 14 comments / 10 per page = 2 pages
        assert mock_joinedload_func.called_once_with(Comment.user) # Check that joinedload was called for Comment.user
        assert mock_joinedload_func.call_count == 1 # Only one joinedload call in this view

    def test_get_comments_by_post_no_post_id_in_url(self, dummy_request):
        dummy_request.matchdict = {} # Missing post_id
        response = get_comments_by_post(dummy_request)
        assert_json_response(response, 400, {"error": "Post ID diperlukan sebagai bagian dari URL."})

    def test_get_comments_by_post_invalid_post_id(self, dummy_request):
        dummy_request.matchdict = {"post_id": "abc"}
        response = get_comments_by_post(dummy_request)
        assert_json_response(response, 400, {"error": "Post ID tidak valid."})

    def test_get_comments_by_post_post_not_found(self, dummy_request, mock_dbsession):
        dummy_request.matchdict = {"post_id": 999}
        mock_dbsession.get.return_value = None # Post not found
        response = get_comments_by_post(dummy_request)
        assert_json_response(response, 404, {"error": "Post tidak ditemukan."})

    def test_get_comments_by_post_invalid_pagination_params(self, dummy_request, mock_dbsession, mock_post_with_comments):
        dummy_request.matchdict = {"post_id": mock_post_with_comments.id}
        mock_dbsession.get.return_value = mock_post_with_comments # Post exists

        dummy_request.params = {"page": "invalid", "per_page": "string"}
        response = get_comments_by_post(dummy_request)
        assert_json_response(response, 400, {"error": "Parameter 'page' atau 'per_page' tidak valid."})

        # Test case for page <= 0 and per_page > 100 (should default)
        dummy_request.params = {"page": "0", "per_page": "150"}
        
        # Configure mock_dbsession.query for Comment to allow successful execution
        query_mock = MagicMock()
        query_mock.filter_by.return_value = query_mock
        query_mock.count.return_value = 5 # Dummy total comments
        query_mock.options.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value.all.return_value = [] # No comments returned for this test
        mock_dbsession.query.return_value = query_mock

        response = get_comments_by_post(dummy_request)
        assert isinstance(response, dict)
        assert response["pagination"]["current_page"] == 1
        assert response["pagination"]["per_page"] == 10 # Should default to 10

    def test_get_comments_by_post_db_api_error(self, dummy_request, mock_dbsession, mock_post_with_comments):
        dummy_request.matchdict = {"post_id": mock_post_with_comments.id}
        mock_dbsession.get.return_value = mock_post_with_comments # Post exists
        
        mock_dbsession.query.side_effect = DBAPIError("Simulated DB error", {}, MagicMock())
        dummy_request.log = MagicMock()

        response = get_comments_by_post(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan database saat mengambil komentar."})
        dummy_request.log.exception.assert_called_once_with("Database error in get_comments_by_post:")

    def test_get_comments_by_post_unexpected_error(self, dummy_request, mock_dbsession, mock_post_with_comments):
        dummy_request.matchdict = {"post_id": mock_post_with_comments.id}
        mock_dbsession.get.side_effect = Exception("Unexpected test error") # Simulate error during get()
        dummy_request.log = MagicMock()

        response = get_comments_by_post(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server tidak terduga."})
        dummy_request.log.exception.assert_called_once_with("Unexpected error in get_comments_by_post:")