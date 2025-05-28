import pytest
from unittest.mock import MagicMock, patch
from pyramid.response import Response
from sqlalchemy.exc import DBAPIError, IntegrityError
from passlib.hash import bcrypt
from backend_edutrack.security import create_token
from backend_edutrack.models import User # Asumsi User model ada di .models

# Import fungsi-fungsi view yang akan diuji
from backend_edutrack.views.auth import (
    register,
    login,
    change_password,
    update_my_identity,
    get_my_profile,
    get_role_from_email # Perlu diuji secara terpisah atau secara implisit
)

# Import fixture dari conftest
from .conftest import dummy_request, mock_dbsession


# --- FIXTURES KHUSUS UNTUK AUTH ---
@pytest.fixture
def mock_user_mahasiswa_auth():
    user = MagicMock(spec=User)
    user.id = 1
    user.name = "Mahasiswa Test"
    user.email = "mahasiswa@student.itera.ac.id"
    user.role = "Mahasiswa"
    user.prodi = "Teknik Informatika"
    user.password = bcrypt.hash("password123") # Hashed password
    user._sa_instance_state = MagicMock() # Penting untuk SQLAlchemy
    return user

@pytest.fixture
def mock_user_dosen_auth():
    user = MagicMock(spec=User)
    user.id = 2
    user.name = "Dosen Test"
    user.email = "dosen@itera.ac.id"
    user.role = "Dosen"
    user.prodi = None
    user.password = bcrypt.hash("dosenpass")
    user._sa_instance_state = MagicMock()
    return user

@pytest.fixture
def mock_user_tamu_email():
    # Ini tidak akan menjadi objek User sebenarnya karena role Tamu tidak diizinkan
    return "tamu@example.com"

# --- HELPER UNTUK TEST RESPONSE JSON ---
# Ini membantu membuat test lebih ringkas
def assert_json_response(response, status_code, key_value_pairs=None):
    assert isinstance(response, Response)
    assert response.status_code == status_code
    assert response.content_type == 'application/json'
    if key_value_pairs:
        for key, value in key_value_pairs.items():
            assert response.json_body.get(key) == value

class TestRegisterView:

    def test_register_success_mahasiswa(self, dummy_request, mock_dbsession):
        dummy_request.json_body = {
            "name": "Mahasiswa Baru",
            "email": "mhs_baru@student.itera.ac.id",
            "password": "newpassword",
            "prodi": "Teknik Fisika"
        }
        
        # Mocking for dbsession.query(User).filter_by(email=email).first()
        # Harus mengembalikan None karena user belum terdaftar
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = None
        mock_dbsession.query.return_value = query_mock

        # Patch the User model constructor
        with patch('backend_edutrack.models.User') as MockUser:
            new_user_mock = MagicMock(spec=User)
            new_user_mock.id = 3
            new_user_mock.name = "Mahasiswa Baru"
            new_user_mock.email = "mhs_baru@student.itera.ac.id"
            new_user_mock.role = "Mahasiswa"
            new_user_mock.prodi = "Teknik Fisika"
            new_user_mock._sa_instance_state = MagicMock() # Penting
            MockUser.return_value = new_user_mock

            # Patch bcrypt for hashing
            with patch('backend_edutrack.views.auth.bcrypt.hash') as mock_bcrypt_hash:
                mock_bcrypt_hash.return_value = "hashed_newpassword"

                response = register(dummy_request)

                assert_json_response(response, 201, {"message": "Registrasi berhasil", "role": "Mahasiswa"})
                mock_dbsession.add.assert_called_once_with(new_user_mock)
                mock_dbsession.flush.assert_called_once()
                # commit tidak di-assert karena ditangani TM

    def test_register_success_dosen(self, dummy_request, mock_dbsession):
        dummy_request.json_body = {
            "name": "Dosen Baru",
            "email": "dsn_baru@itera.ac.id",
            "password": "dosenpass",
            "prodi": None # Prodi harus None untuk dosen
        }
        
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = None
        mock_dbsession.query.return_value = query_mock

        with patch('backend_edutrack.models.User') as MockUser:
            new_user_mock = MagicMock(spec=User)
            new_user_mock.id = 4
            new_user_mock.name = "Dosen Baru"
            new_user_mock.email = "dsn_baru@itera.ac.id"
            new_user_mock.role = "Dosen"
            new_user_mock.prodi = None
            new_user_mock._sa_instance_state = MagicMock()
            MockUser.return_value = new_user_mock

            with patch('backend_edutrack.views.auth.bcrypt.hash'): # Tidak perlu mock return value
                response = register(dummy_request)
                assert_json_response(response, 201, {"message": "Registrasi berhasil", "role": "Dosen"})
                mock_dbsession.add.assert_called_once_with(new_user_mock)
                mock_dbsession.flush.assert_called_once()

    def test_register_missing_fields(self, dummy_request):
        dummy_request.json_body = {"name": "Test", "email": "test@example.com"} # Missing password
        response = register(dummy_request)
        assert_json_response(response, 400, {"error": "Field tidak lengkap."})

    def test_register_email_already_registered(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.json_body = {
            "name": "Existing User",
            "email": mock_user_mahasiswa_auth.email,
            "password": "somepass"
        }
        
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = mock_user_mahasiswa_auth # User already exists
        mock_dbsession.query.return_value = query_mock

        response = register(dummy_request)
        assert_json_response(response, 400, {"error": "Email sudah terdaftar."})
        mock_dbsession.add.assert_not_called() # Tidak ada penambahan user baru

    def test_register_invalid_email_domain(self, dummy_request):
        dummy_request.json_body = {
            "name": "Tamu User",
            "email": "tamu@gmail.com",
            "password": "guestpass"
        }
        response = register(dummy_request)
        assert_json_response(response, 400, {"error": "Domain email tidak diizinkan."})

    def test_register_db_error(self, dummy_request, mock_dbsession):
        dummy_request.json_body = {
            "name": "DB Error User",
            "email": "db_error@student.itera.ac.id",
            "password": "dbpass"
        }
        
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = None
        mock_dbsession.query.return_value = query_mock
        
        # Simulate DBAPIError on add
        mock_dbsession.add.side_effect = DBAPIError("Simulated DB error", {}, MagicMock())

        response = register(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server saat registrasi."})
        # rollback tidak di-assert karena ditangani TM
        
    def test_register_integrity_error(self, dummy_request, mock_dbsession):
        dummy_request.json_body = {
            "name": "Integrity User",
            "email": "integrity@student.itera.ac.id",
            "password": "integritypass"
        }
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = None
        mock_dbsession.query.return_value = query_mock
        
        # Simulate IntegrityError on flush (misalnya karena constraint lain)
        mock_dbsession.flush.side_effect = IntegrityError("Simulated Integrity error", {}, MagicMock())

        response = register(dummy_request)
        assert_json_response(response, 409, {"error": "Terjadi masalah saat registrasi (mis. duplikasi data)."})


    def test_register_unexpected_error(self, dummy_request):
        # Simulate a generic exception before dbsession is even touched
        dummy_request.json_body = MagicMock(side_effect=Exception("Unexpected test error"))
        # Mock logging to prevent actual print
        dummy_request.log = MagicMock()

        response = register(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server saat registrasi."})
        dummy_request.log.exception.assert_called_once()


class TestLoginView:

    def test_login_success(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.json_body = {
            "email": mock_user_mahasiswa_auth.email,
            "password": "password123"
        }
        
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = mock_user_mahasiswa_auth
        mock_dbsession.query.return_value = query_mock

        # Patch bcrypt.verify
        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify:
            mock_bcrypt_verify.return_value = True # Password match

            # Patch create_token
            with patch('backend_edutrack.views.auth.create_token') as mock_create_token:
                mock_create_token.return_value = "mock_jwt_token"

                response = login(dummy_request)

                assert_json_response(response, 200)
                assert response.json_body["message"] == "Login berhasil"
                assert response.json_body["token"] == "mock_jwt_token"
                assert response.json_body["user"]["id"] == mock_user_mahasiswa_auth.id
                assert response.json_body["user"]["email"] == mock_user_mahasiswa_auth.email
                assert response.json_body["user"]["role"] == mock_user_mahasiswa_auth.role
                mock_bcrypt_verify.assert_called_once_with("password123", mock_user_mahasiswa_auth.password)
                mock_create_token.assert_called_once()

    def test_login_missing_fields(self, dummy_request):
        dummy_request.json_body = {"email": "test@example.com"} # Missing password
        response = login(dummy_request)
        assert_json_response(response, 400, {"error": "Email dan password wajib diisi."})

    def test_login_user_not_found(self, dummy_request, mock_dbsession):
        dummy_request.json_body = {"email": "nonexistent@example.com", "password": "anypass"}
        
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = None # User not found
        mock_dbsession.query.return_value = query_mock

        response = login(dummy_request)
        assert_json_response(response, 401, {"error": "Email atau password salah."})

    def test_login_incorrect_password(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.json_body = {"email": mock_user_mahasiswa_auth.email, "password": "wrongpassword"}
        
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = mock_user_mahasiswa_auth
        mock_dbsession.query.return_value = query_mock

        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify:
            mock_bcrypt_verify.return_value = False # Password mismatch
            response = login(dummy_request)
            assert_json_response(response, 401, {"error": "Email atau password salah."})
            mock_bcrypt_verify.assert_called_once_with("wrongpassword", mock_user_mahasiswa_auth.password)

    def test_login_bcrypt_error(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.json_body = {"email": mock_user_mahasiswa_auth.email, "password": "anypass"}
        
        query_mock = MagicMock()
        query_mock.filter_by.return_value.first.return_value = mock_user_mahasiswa_auth
        mock_dbsession.query.return_value = query_mock

        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify:
            mock_bcrypt_verify.side_effect = Exception("Bcrypt internal error") # Simulate bcrypt error
            dummy_request.log = MagicMock() # Mock logging
            response = login(dummy_request)
            assert_json_response(response, 401, {"error": "Email atau password salah."})
            dummy_request.log.exception.assert_called_once_with("bcrypt error:")


    def test_login_unexpected_error(self, dummy_request):
        # Simulate a generic exception before any DB interaction
        dummy_request.json_body = MagicMock(side_effect=Exception("Unexpected login error"))
        dummy_request.log = MagicMock() # Mock logging

        response = login(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server tidak terduga."})
        dummy_request.log.exception.assert_called_once_with("Error during login:")


class TestChangePasswordView:

    def test_change_password_success(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id} # Authenticated user
        dummy_request.json_body = {
            "old_password": "password123",
            "new_password": "newstrongpassword"
        }
        
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth

        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify, \
             patch('backend_edutrack.views.auth.bcrypt.hash') as mock_bcrypt_hash:
            mock_bcrypt_verify.return_value = True
            mock_bcrypt_hash.return_value = "hashed_newstrongpassword"

            response = change_password(dummy_request)

            assert_json_response(response, 200, {"message": "Password berhasil diubah."})
            mock_bcrypt_verify.assert_called_once_with("password123", mock_user_mahasiswa_auth.password)
            mock_bcrypt_hash.assert_called_once_with("newstrongpassword")
            assert mock_user_mahasiswa_auth.password == "hashed_newstrongpassword"
            mock_dbsession.flush.assert_called_once()
            # commit tidak di-assert

    def test_change_password_unauthenticated(self, dummy_request):
        dummy_request.user = {} # No authenticated user
        dummy_request.json_body = {"old_password": "old", "new_password": "new"}
        response = change_password(dummy_request)
        assert_json_response(response, 401, {"error": "Autentikasi diperlukan untuk mengubah password."})

    def test_change_password_user_not_found(self, dummy_request, mock_dbsession):
        dummy_request.user = {"id": 999} # User ID that doesn't exist
        dummy_request.json_body = {"old_password": "old", "new_password": "new"}
        mock_dbsession.get.return_value = None # User not found
        response = change_password(dummy_request)
        assert_json_response(response, 404, {"error": "Pengguna tidak ditemukan."})

    def test_change_password_missing_fields(self, dummy_request, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        dummy_request.json_body = {"old_password": "old"} # Missing new_password
        response = change_password(dummy_request)
        assert_json_response(response, 400, {"error": "Password lama dan password baru wajib diisi."})

    def test_change_password_incorrect_old_password(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        dummy_request.json_body = {"old_password": "wrongoldpassword", "new_password": "newpass"}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth

        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify:
            mock_bcrypt_verify.return_value = False # Password mismatch
            response = change_password(dummy_request)
            assert_json_response(response, 401, {"error": "Password lama salah."})
            mock_bcrypt_verify.assert_called_once_with("wrongoldpassword", mock_user_mahasiswa_auth.password)

    def test_change_password_bcrypt_verify_exception(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        dummy_request.json_body = {"old_password": "old", "new_password": "new"}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        
        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify:
            mock_bcrypt_verify.side_effect = Exception("Corrupt hash") # Simulate bcrypt error
            response = change_password(dummy_request)
            assert_json_response(response, 401, {"error": "Password lama salah."})

    def test_change_password_new_password_too_short(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        dummy_request.json_body = {"old_password": "password123", "new_password": "short"} # < 6 chars
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth

        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify:
            mock_bcrypt_verify.return_value = True
            response = change_password(dummy_request)
            assert_json_response(response, 400, {"error": "Password baru minimal 6 karakter."})

    def test_change_password_db_error(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        dummy_request.json_body = {"old_password": "password123", "new_password": "newpass"}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth

        with patch('backend_edutrack.views.auth.bcrypt.verify') as mock_bcrypt_verify, \
             patch('backend_edutrack.views.auth.bcrypt.hash') as mock_bcrypt_hash:
            mock_bcrypt_verify.return_value = True
            mock_bcrypt_hash.return_value = "hashed_newpass"
            mock_dbsession.flush.side_effect = DBAPIError("Simulated DB error", {}, MagicMock())
            dummy_request.log = MagicMock()

            response = change_password(dummy_request)
            assert_json_response(response, 500, {"error": "Terjadi kesalahan server."})
            dummy_request.log.exception.assert_called_once_with("Change password error:")


    def test_change_password_unexpected_error(self, dummy_request, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        # Simulate error during json_body access
        dummy_request.json_body = MagicMock(side_effect=Exception("Unexpected test error"))
        dummy_request.log = MagicMock()

        response = change_password(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server."})
        dummy_request.log.exception.assert_called_once_with("Change password error:")



class TestUpdateMyIdentityView:

    def test_update_my_identity_success_name(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"name": "Nama Baru Mahasiswa"}
        
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        old_name = mock_user_mahasiswa_auth.name

        response = update_my_identity(dummy_request)

        assert_json_response(response, 200)
        assert response.json_body["message"] == "Profil berhasil diperbarui."
        assert response.json_body["user"]["name"] == "Nama Baru Mahasiswa"
        assert mock_user_mahasiswa_auth.name == "Nama Baru Mahasiswa" # Ensure user object is updated
        mock_dbsession.flush.assert_called_once()

    def test_update_my_identity_success_prodi(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"prodi": "Teknik Lingkungan"}
        
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth

        response = update_my_identity(dummy_request)

        assert_json_response(response, 200)
        assert response.json_body["message"] == "Profil berhasil diperbarui."
        assert response.json_body["user"]["prodi"] == "Teknik Lingkungan"
        assert mock_user_mahasiswa_auth.prodi == "Teknik Lingkungan"
        mock_dbsession.flush.assert_called_once()

    def test_update_my_identity_success_prodi_to_none(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"prodi": ""} # Empty string should become None
        
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        mock_user_mahasiswa_auth.prodi = "Teknik Informatika" # Set initial prodi

        response = update_my_identity(dummy_request)

        assert_json_response(response, 200)
        assert response.json_body["message"] == "Profil berhasil diperbarui."
        assert response.json_body["user"]["prodi"] is None
        assert mock_user_mahasiswa_auth.prodi is None
        mock_dbsession.flush.assert_called_once()

    def test_update_my_identity_unauthenticated(self, dummy_request):
        dummy_request.user = {}
        dummy_request.json_body = {"name": "Test"}
        response = update_my_identity(dummy_request)
        assert_json_response(response, 401, {"error": "Autentikasi diperlukan untuk memperbarui profil."})

    def test_update_my_identity_user_not_found(self, dummy_request, mock_dbsession):
        dummy_request.user = {"id": 999, "role": "Mahasiswa"}
        dummy_request.json_body = {"name": "Test"}
        mock_dbsession.get.return_value = None
        response = update_my_identity(dummy_request)
        assert_json_response(response, 404, {"error": "Pengguna tidak ditemukan."})

    def test_update_my_identity_invalid_name(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"name": ""} # Empty name
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        response = update_my_identity(dummy_request)
        assert_json_response(response, 400, {"error": "Nama tidak boleh kosong."})

    def test_update_my_identity_dosen_change_prodi(self, dummy_request, mock_dbsession, mock_user_dosen_auth):
        dummy_request.user = {"id": mock_user_dosen_auth.id, "role": mock_user_dosen_auth.role}
        dummy_request.json_body = {"prodi": "Teknik Sipil"}
        mock_dbsession.get.return_value = mock_user_dosen_auth
        response = update_my_identity(dummy_request)
        assert_json_response(response, 403, {"error": "Hanya mahasiswa yang dapat mengubah informasi prodi."})

    def test_update_my_identity_change_email(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"email": "new@example.com"}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        response = update_my_identity(dummy_request)
        assert_json_response(response, 400, {"error": "Perubahan email/password tidak diizinkan melalui endpoint ini."})

    def test_update_my_identity_change_password(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"password": "newpass"}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        response = update_my_identity(dummy_request)
        assert_json_response(response, 400, {"error": "Perubahan email/password tidak diizinkan melalui endpoint ini."})

    def test_update_my_identity_change_role(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"role": "Admin"}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        response = update_my_identity(dummy_request)
        assert_json_response(response, 403, {"error": "Perubahan role tidak diizinkan."})

    def test_update_my_identity_no_valid_fields(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"unknown_field": "value"} # Invalid field
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        response = update_my_identity(dummy_request)
        assert_json_response(response, 400, {"error": "Tidak ada field yang valid untuk diperbarui."})

    def test_update_my_identity_db_error(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = {"name": "Test Name"}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth
        mock_dbsession.flush.side_effect = DBAPIError("Simulated DB error", {}, MagicMock())
        dummy_request.log = MagicMock()

        response = update_my_identity(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server saat memperbarui profil."})
        dummy_request.log.exception.assert_called_once_with("Update profile error:")

    def test_update_my_identity_unexpected_error(self, dummy_request, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id, "role": mock_user_mahasiswa_auth.role}
        dummy_request.json_body = MagicMock(side_effect=Exception("Unexpected test error"))
        dummy_request.log = MagicMock()

        response = update_my_identity(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server saat memperbarui profil."})
        dummy_request.log.exception.assert_called_once_with("Update profile error:")


class TestGetMyProfileView:

    def test_get_my_profile_success(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        mock_dbsession.get.return_value = mock_user_mahasiswa_auth

        response = get_my_profile(dummy_request)

        assert_json_response(response, 200)
        assert response.json_body["id"] == mock_user_mahasiswa_auth.id
        assert response.json_body["name"] == mock_user_mahasiswa_auth.name
        assert response.json_body["email"] == mock_user_mahasiswa_auth.email
        assert response.json_body["role"] == mock_user_mahasiswa_auth.role
        assert response.json_body["prodi"] == mock_user_mahasiswa_auth.prodi
        assert response.json_body["message"] == "Profil berhasil diambil."

    def test_get_my_profile_unauthenticated(self, dummy_request):
        dummy_request.user = {}
        response = get_my_profile(dummy_request)
        assert_json_response(response, 401, {"error": "Autentikasi diperlukan untuk melihat profil."})

    def test_get_my_profile_user_not_found(self, dummy_request, mock_dbsession):
        dummy_request.user = {"id": 999}
        mock_dbsession.get.return_value = None
        response = get_my_profile(dummy_request)
        assert_json_response(response, 404, {"error": "Profil pengguna tidak ditemukan."})

    def test_get_my_profile_db_error(self, dummy_request, mock_dbsession, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        mock_dbsession.get.side_effect = DBAPIError("Simulated DB error", {}, MagicMock())
        dummy_request.log = MagicMock()

        response = get_my_profile(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server saat mengambil profil."})
        dummy_request.log.exception.assert_called_once_with("Get profile error:")

    def test_get_my_profile_unexpected_error(self, dummy_request, mock_user_mahasiswa_auth):
        dummy_request.user = {"id": mock_user_mahasiswa_auth.id}
        dummy_request.dbsession = MagicMock() # Ensure dbsession exists to attach side_effect
        dummy_request.dbsession.get.side_effect = Exception("Unexpected test error")
        dummy_request.log = MagicMock()

        response = get_my_profile(dummy_request)
        assert_json_response(response, 500, {"error": "Terjadi kesalahan server saat mengambil profil."})
        dummy_request.log.exception.assert_called_once_with("Get profile error:")