from pyramid.view import view_config
from pyramid.response import Response
# Hapus HTTPNotFound, HTTPBadRequest, HTTPUnauthorized karena kita akan mengembalikan Response objek
# from pyramid.httpexceptions import HTTPNotFound, HTTPBadRequest, HTTPUnauthorized
from sqlalchemy.exc import DBAPIError, IntegrityError # Tambahkan IntegrityError
from sqlalchemy.orm import joinedload
from ..models.comment import Comment
from ..models.post import Post
from ..models.user import User

# Tidak perlu import json jika renderer='json' sudah digunakan di view_config
# import json


@view_config(route_name='comment_add', renderer='json', request_method='POST')
def add_comment(request):
    try:
        user_id = request.user.get("id")

        if not user_id:
            # Mengembalikan Response objek dengan status 401
            return Response(json_body={"error": "Autentikasi diperlukan untuk menambah komentar."}, status=401)

        data = request.json_body
        post_id = data.get("post_id")
        content = data.get("content")

        if not all([post_id, content]):
            # Mengembalikan Response objek dengan status 400
            return Response(json_body={"error": "Post ID dan konten komentar wajib diisi."}, status=400)

        try:
            post_id = int(post_id)
        except ValueError:
            # Mengembalikan Response objek dengan status 400
            return Response(json_body={"error": "Post ID tidak valid."}, status=400)

        post = request.dbsession.get(Post, post_id)
        user = request.dbsession.get(User, user_id)

        if not post:
            # Mengembalikan Response objek dengan status 404
            return Response(json_body={"error": "Post tidak ditemukan."}, status=404)
        
        if not user:
            # Mengembalikan Response objek dengan status 401
            return Response(json_body={"error": "Pengguna tidak valid atau tidak ditemukan."}, status=401)

        comment = Comment(post_id=post_id, user_id=user_id, content=content)
        request.dbsession.add(comment)
        request.dbsession.flush() # Agar comment.id tersedia

        # Respons yang lebih informatif
        return {
            "message": "Komentar berhasil ditambahkan",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "post_id": comment.post_id,
                "user_id": comment.user_id,
                "username": user.name
            }
        }

    except IntegrityError: # Tambahkan penanganan IntegrityError
        request.log.exception("Database integrity error in add_comment:")
        return Response(json_body={"error": "Terjadi konflik data saat menambah komentar."}, status=409)
    except DBAPIError as e:
        request.log.exception("Database error in add_comment:") # Gunakan logging Pyramid
        return Response(json_body={"error": "Terjadi kesalahan database saat menambah komentar."}, status=500)
    except Exception as e:
        request.log.exception("Unexpected error in add_comment:") # Gunakan logging Pyramid
        return Response(json_body={"error": "Terjadi kesalahan server tidak terduga."}, status=500)

@view_config(route_name='comment_by_post', renderer='json', request_method='GET')
def get_comments_by_post(request):
    try:
        post_id = request.matchdict.get("post_id")
        
        if not post_id:
            # Mengembalikan Response objek dengan status 400
            return Response(json_body={"error": "Post ID diperlukan sebagai bagian dari URL."}, status=400)

        try:
            post_id = int(post_id)
        except ValueError:
            # Mengembalikan Response objek dengan status 400
            return Response(json_body={"error": "Post ID tidak valid."}, status=400)

        post = request.dbsession.get(Post, post_id)
        if not post:
            # Mengembalikan Response objek dengan status 404
            return Response(json_body={"error": "Post tidak ditemukan."}, status=404)

        page = request.params.get('page', 1)
        per_page = request.params.get('per_page', 5)

        try:
            page = int(page)
            per_page = int(per_page)
            if page <= 0:
                page = 1
            if per_page <= 0 or per_page > 100:
                per_page = 10
        except ValueError:
            # Mengembalikan Response objek dengan status 400
            return Response(json_body={"error": "Parameter 'page' atau 'per_page' tidak valid."}, status=400)

        offset = (page - 1) * per_page

        total_comments = request.dbsession.query(Comment).filter_by(post_id=post_id).count()

        comments_query = request.dbsession.query(Comment) \
            .filter_by(post_id=post_id) \
            .options(joinedload(Comment.user))

        comments = comments_query.offset(offset).limit(per_page).all()

        result = []
        for c in comments:
            result.append({
                "id": c.id,
                "content": c.content,
                "created_at": c.created_at.isoformat(),
                "user_id": c.user_id,
                "username": c.user.name if c.user else None
            })
        
        total_pages = (total_comments + per_page - 1) // per_page

        return {
            "comments": result,
            "pagination": {
                "total_comments": total_comments,
                "per_page": per_page,
                "current_page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    except DBAPIError as e:
        request.log.exception("Database error in get_comments_by_post:")
        return Response(json_body={"error": "Terjadi kesalahan database saat mengambil komentar."}, status=500)
    except Exception as e:
        request.log.exception("Unexpected error in get_comments_by_post:")
        return Response(json_body={"error": "Terjadi kesalahan server tidak terduga."}, status=500)