import pytest
from unittest.mock import MagicMock, patch
from pyramid.testing import DummyRequest # Untuk membuat dummy request

# Import fungsi-fungsi dari security.py
from backend_edutrack.security import (
    create_token,
    decode_token,
    get_role_from_email,
    get_current_user
)

# Import helper JWT dari utils, karena security.py memanggilnya
from backend_edutrack.utils.jwt_helper import (
    create_token as _create_token_helper,
    decode_token as _decode_token_helper,
    SECRET_KEY # Mungkin tidak perlu di mock, tapi penting untuk diketahui
)

# --- Test untuk get_role_from_email ---
class TestGetRoleFromEmail:
    def test_mahasiswa_role(self):
        email = "nama.mahasiswa@student.itera.ac.id"
        assert get_role_from_email(email) == "Mahasiswa"

    def test_dosen_role(self):
        email = "nama.dosen@itera.ac.id"
        assert get_role_from_email(email) == "Dosen"

    def test_tamu_role(self):
        # Ini akan mencakup baris `return "Tamu"`
        email = "user@gmail.com"
        assert get_role_from_email(email) == "Tamu"
        email_other = "admin@example.org"
        assert get_role_from_email(email_other) == "Tamu"

# --- Test untuk get_current_user ---
class TestGetCurrentUser:

    @patch('backend_edutrack.security.decode_token')
    def test_get_current_user_success(self, mock_decode_token):
        # Skenario sukses: header ada dan token valid
        mock_decode_token.return_value = {"id": 1, "role": "Mahasiswa"}
        
        request = DummyRequest()
        request.headers["Authorization"] = "Bearer valid_jwt_token"
        
        user_payload = get_current_user(request)
        
        assert user_payload == {"id": 1, "role": "Mahasiswa"}
        mock_decode_token.assert_called_once_with("valid_jwt_token")

    def test_get_current_user_no_authorization_header(self):
        # Ini akan mencakup `if not auth_header`
        request = DummyRequest()
        # Tidak ada header Authorization
        
        user_payload = get_current_user(request)
        
        assert user_payload is None

    def test_get_current_user_malformed_authorization_header(self):
        # Ini akan mencakup `or not auth_header.startswith("Bearer ")`
        request = DummyRequest()
        request.headers["Authorization"] = "Basic some_credentials" # Bukan "Bearer "
        
        user_payload = get_current_user(request)
        
        assert user_payload is None

    @patch('backend_edutrack.security.decode_token')
    def test_get_current_user_decode_token_exception(self, mock_decode_token):
        # Ini akan mencakup `except Exception`
        mock_decode_token.side_effect = Exception("Invalid token signature") # Simulasikan token tidak valid
        
        request = DummyRequest()
        request.headers["Authorization"] = "Bearer invalid_jwt_token"
        
        user_payload = get_current_user(request)
        
        assert user_payload is None
        mock_decode_token.assert_called_once_with("invalid_jwt_token")

# --- Test untuk wrapper create_token dan decode_token ---
# Ini penting untuk memastikan baris `return _create_token(...)` dan `return _decode_token(...)` dieksekusi.
# Jika sudah tercakup oleh test view login/autentikasi, bagian ini bisa diabaikan.
# Namun, untuk jaminan 100% coverage di file security.py, sebaiknya ada.

class TestTokenWrappers:
    @patch('backend_edutrack.security._create_token')
    def test_create_token_wrapper(self, mock_jwt_helper_create_token):
        data = {"user_id": 1}
        create_token(data)
        mock_jwt_helper_create_token.assert_called_once_with(data, expires_in_hours=6)

    @patch('backend_edutrack.security._decode_token')
    def test_decode_token_wrapper(self, mock_jwt_helper_decode_token):
        token = "some_token"
        decode_token(token)
        mock_jwt_helper_decode_token.assert_called_once_with(token)