import jwt
import datetime
from jwt import ExpiredSignatureError, InvalidTokenError

SECRET_KEY = "rahasia-super-aman"  # Boleh nanti pakai dari os.environ

def create_token(data: dict, expires_in_hours: int = 6) -> str:
    payload = data.copy()
    payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=expires_in_hours)
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    # Pastikan token string di Python 3.13+
    return token.decode("utf-8") if isinstance(token, bytes) else token

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

def try_decode_token(token: str):
    """
    Dekode token, tapi kembalikan None jika token invalid atau expired.
    """
    try:
        return decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        return None