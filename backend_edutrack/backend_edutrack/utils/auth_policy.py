from pyramid.response import Response
from .jwt_helper import decode_token

def get_role_from_email(email):
    if email.endswith('@student.itera.ac.id'):
        return 'Mahasiswa'
    elif email.endswith('@itera.ac.id'):
        return 'Dosen'
    else:
        return 'Tamu'

def auth_tween_factory(handler, registry):
    def auth_tween(request):
        PUBLIC_PATH_PREFIXES = [
            "/api/login",
            "/api/register",
            "/favicon.ico",
            "/_debug_toolbar",
        ]

        if any(request.path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
            return handler(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                json_body={"error": "Unauthorized. Token missing or malformed."},
                status=401,
                content_type="application/json"
            )

        token = auth_header.replace("Bearer ", "")
        try:
            payload = decode_token(token)
            request.user = payload
        except jwt.ExpiredSignatureError:
            return Response(
                json_body={"error": "Token expired"},
                status=401,
                content_type="application/json"
            )
        except jwt.InvalidTokenError:
            return Response(
                json_body={"error": "Invalid token"},
                status=401,
                content_type="application/json"
            )
        except Exception as e:
            print("JWT decode error:", e)
            return Response(
                json_body={"error": "Token tidak valid atau terjadi kesalahan."},
                status=401,
                content_type="application/json"
            )

        return handler(request)

    return auth_tween
