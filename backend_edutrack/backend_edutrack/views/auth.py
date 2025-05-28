from passlib.hash import bcrypt
from pyramid.view import view_config
from pyramid.response import Response
from sqlalchemy.exc import DBAPIError, IntegrityError
from ..models import User
from ..security import create_token

def get_role_from_email(email):
    if email.endswith("@student.itera.ac.id"):
        return "Mahasiswa"
    elif email.endswith("@itera.ac.id"):
        return "Dosen"
    else:
        return "Tamu"

@view_config(route_name='change_password', request_method='POST', renderer='json')
def change_password(request):
    try:
        user_data = request.user
        user_id = user_data.get("id")

        if not user_id:
            return Response(json_body={"error": "Autentikasi diperlukan untuk mengubah password."}, status=401)

        user = request.dbsession.get(User, user_id)
        if not user:
            return Response(json_body={"error": "Pengguna tidak ditemukan."}, status=404)

        data = request.json_body
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not old_password or not new_password:
            return Response(json_body={"error": "Password lama dan password baru wajib diisi."}, status=400)

        try:
            if not bcrypt.verify(old_password, user.password):
                return Response(json_body={"error": "Password lama salah."}, status=401)
        except Exception:
            return Response(json_body={"error": "Password lama salah."}, status=401)

        if len(new_password) < 6:
            return Response(json_body={"error": "Password baru minimal 6 karakter."}, status=400)

        user.password = bcrypt.hash(new_password)
        request.dbsession.flush()

        return Response(json_body={"message": "Password berhasil diubah."}, status=200)

    except Exception as e:
        request.log.exception("Change password error:")
        return Response(json_body={"error": "Terjadi kesalahan server."}, status=500)

@view_config(route_name='me', request_method='PATCH', renderer='json')
def update_my_identity(request):
    try:
        user_data = request.user
        user_id = user_data.get("id")
        user_role = user_data.get("role")

        if not user_id:
            return Response(json_body={"error": "Autentikasi diperlukan untuk memperbarui profil."}, status=401)

        user = request.dbsession.get(User, user_id)
        if not user:
            return Response(json_body={"error": "Pengguna tidak ditemukan."}, status=404)

        data = request.json_body
        updated_fields = {}

        if 'name' in data:
            new_name = data['name']
            if not isinstance(new_name, str) or not new_name.strip():
                return Response(json_body={"error": "Nama tidak boleh kosong."}, status=400)
            user.name = new_name.strip()
            updated_fields['name'] = user.name

        if user_role == "Mahasiswa":
            if 'prodi' in data:
                new_prodi = data['prodi']
                user.prodi = new_prodi.strip() if isinstance(new_prodi, str) and new_prodi.strip() else None
                updated_fields['prodi'] = user.prodi

            if 'nim' in data: # Tambahkan penanganan NIM
                new_nim = data['nim']
                if new_nim:
                    if not isinstance(new_nim, str) or not new_nim.strip():
                        return Response(json_body={"error": "NIM tidak valid."}, status=400)
                    # Cek duplikasi NIM
                    existing_nim_user = request.dbsession.query(User).filter(User.nim == new_nim.strip(), User.id != user.id).first()
                    if existing_nim_user:
                        return Response(json_body={"error": "NIM sudah terdaftar."}, status=400)
                    user.nim = new_nim.strip()
                    updated_fields['nim'] = user.nim
                else: # Membolehkan NIM dikosongkan
                    user.nim = None
                    updated_fields['nim'] = None
        else:
            if 'prodi' in data or 'nim' in data:
                return Response(json_body={"error": "Hanya mahasiswa yang dapat mengubah informasi prodi atau NIM."}, status=403)


        if any(k in data for k in ['email', 'password']):
            return Response(json_body={"error": "Perubahan email/password tidak diizinkan melalui endpoint ini."}, status=400)
        if 'role' in data:
            return Response(json_body={"error": "Perubahan role tidak diizinkan."}, status=403)

        if not updated_fields:
            return Response(json_body={"error": "Tidak ada field yang valid untuk diperbarui."}, status=400)

        request.dbsession.flush()

        return Response(json_body={
            "message": "Profil berhasil diperbarui.",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "prodi": user.prodi,
                "nim": user.nim # Tambahkan NIM di respons
            }
        }, status=200)

    except IntegrityError: # Tangkap IntegrityError untuk duplikasi NIM
        request.log.exception("Update profile IntegrityError (NIM duplication):")
        return Response(json_body={"error": "NIM sudah terdaftar."}, status=400)
    except Exception as e:
        request.log.exception("Update profile error:")
        return Response(json_body={"error": "Terjadi kesalahan server saat memperbarui profil."}, status=500)

@view_config(route_name='me', request_method='GET', renderer='json')
def get_my_profile(request):
    try:
        user_data = request.user
        user_id = user_data.get("id")

        if not user_id:
            return Response(json_body={"error": "Autentikasi diperlukan untuk melihat profil."}, status=401)

        user = request.dbsession.get(User, user_id)
        if not user:
            return Response(json_body={"error": "Profil pengguna tidak ditemukan."}, status=404)

        return Response(json_body={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "prodi": user.prodi,
            "nim": user.nim, # Tambahkan NIM di respons
            "message": "Profil berhasil diambil."
        }, status=200)

    except Exception as e:
        request.log.exception("Get profile error:")
        return Response(json_body={"error": "Terjadi kesalahan server saat mengambil profil."}, status=500)

@view_config(route_name="register", renderer="json", request_method="POST")
def register(request):
    try:
        data = request.json_body
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        prodi = data.get("prodi")
        nim = data.get("nim") # Ambil NIM dari request

        if not all([name, email, password]):
            return Response(json_body={"error": "Field tidak lengkap."}, status=400)

        existing_user = request.dbsession.query(User).filter_by(email=email).first()
        if existing_user:
            return Response(json_body={"error": "Email sudah terdaftar."}, status=400)

        hashed_pw = bcrypt.hash(password)
        role = get_role_from_email(email)

        if role == "Tamu":
            return Response(json_body={"error": "Domain email tidak diizinkan."}, status=400)

        user_nim = None
        user_prodi = None

        if role == "Mahasiswa":
            user_prodi = prodi if isinstance(prodi, str) and prodi.strip() else None
            if nim: # Jika ada NIM, validasi dan cek duplikasi
                if not isinstance(nim, str) or not nim.strip():
                    return Response(json_body={"error": "NIM tidak valid."}, status=400)
                existing_nim_user = request.dbsession.query(User).filter_by(nim=nim.strip()).first()
                if existing_nim_user:
                    return Response(json_body={"error": "NIM sudah terdaftar."}, status=400)
                user_nim = nim.strip()
            # NIM tidak wajib saat registrasi, bisa diisi nanti

        new_user = User(
            name=name,
            email=email,
            password=hashed_pw,
            role=role,
            prodi=user_prodi,
            nim=user_nim # Assign NIM ke user baru
        )

        request.dbsession.add(new_user)
        request.dbsession.flush()

        return Response(json_body={"message": "Registrasi berhasil", "role": role}, status=201)

    except IntegrityError:
        request.log.exception("Register IntegrityError (email or NIM duplication):")
        return Response(json_body={"error": "Email atau NIM sudah terdaftar."}, status=409)
    except Exception as e:
        request.log.exception("Register error:")
        return Response(json_body={"error": "Terjadi kesalahan server saat registrasi."}, status=500)


@view_config(route_name="login", renderer="json", request_method="POST")
def login(request):
    try:
        data = request.json_body

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return Response(
                json_body={"error": "Email dan password wajib diisi."},
                status=400,
                content_type="application/json"
            )

        user = request.dbsession.query(User).filter_by(email=email).first()

        if not user:
            return Response(
                json_body={"error": "Email atau password salah."},
                status=401,
                content_type="application/json"
            )

        try:
            if not bcrypt.verify(password, user.password):
                return Response(
                    json_body={"error": "Email atau password salah."},
                    status=401,
                    content_type="application/json"
                )
        except Exception as e:
            request.log.exception("bcrypt error:")
            return Response(
                json_body={"error": "Email atau password salah."},
                status=401,
                content_type="application/json"
            )

        token = create_token({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        })

        return Response(
            json_body={
                "message": "Login berhasil",
                "token": token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "prodi": user.prodi,
                    "nim": user.nim, # Tambahkan NIM di respons
                }
            },
            status=200,
            content_type="application/json"
        )

    except Exception as e:
        request.log.exception("Error during login:")
        return Response(
            json_body={"error": "Terjadi kesalahan server tidak terduga."},
            status=500,
            content_type="application/json"
        )