from .utils.jwt_helper import create_token as _create_token, decode_token as _decode_token, SECRET_KEY

def create_token(data):
    """
    Wrapper ke jwt_helper.create_token, default 6 jam
    """
    return _create_token(data, expires_in_hours=6)

def decode_token(token):
    """
    Wrapper jika ingin extend nanti
    """
    return _decode_token(token)

def get_role_from_email(email: str) -> str:
    """
    Tentukan role berdasarkan domain email
    """
    if email.endswith("@student.itera.ac.id"):
        return "Mahasiswa"
    elif email.endswith("@itera.ac.id"):
        return "Dosen"
    return "Tamu"

def get_current_user(request):
    """
    Ambil payload dari token JWT di header Authorization.
    Tidak mengubah request.user (biarkan ditangani tween).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")
    try:
        return decode_token(token)
    except Exception:
        return None