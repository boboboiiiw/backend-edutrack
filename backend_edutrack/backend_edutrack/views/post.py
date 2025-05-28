from pyramid.view import view_config
from pyramid.response import Response
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import joinedload
from datetime import datetime

from ..models.post import Post, PostInteraction
from ..models.user import User
from ..models.url import URL

# --- Helper Function untuk Konversi Model ke Dictionary ---
def post_to_dict(post_obj):
    """
    Mengkonversi objek Post SQLAlchemy menjadi dictionary untuk respons JSON.
    Menyertakan info likes, dislikes, references, recommendedBy, dan author.
    """
    if not isinstance(post_obj, Post):
        return None

    # Ambil semua URL referensi jika ada
    references_data = []
    if post_obj.references:
        references_data = [url_obj.url for url_obj in post_obj.references]

    # Nama penulis jika tersedia
    author_name = post_obj.author.name if hasattr(post_obj, 'author') and post_obj.author else "Unknown Author"

    # Ambil daftar nama pemberi rekomendasi
    recommended_by_data = []
    if hasattr(post_obj, "recommended_by") and post_obj.recommended_by:
        recommended_by_data = [user.name for user in post_obj.recommended_by]  # GANTI username -> name

    return {
        "id": post_obj.id,
        "title": post_obj.title,
        "content": post_obj.content,
        "createdAt": post_obj.created_at.isoformat() if post_obj.created_at else None,
        "author_id": post_obj.author_id,
        "author": author_name,
        "likes": post_obj.likes,
        "dislikes": post_obj.dislikes,
        "references": references_data,
        "recommendedBy": recommended_by_data,
    }


# --- Helper Function untuk Response Error Konsisten ---
def error_response(request, message, status_code):
    """
    Membuat objek Response JSON untuk error dengan format konsisten.
    """
    return Response(
        json={"error": message},
        status=status_code,
        content_type='application/json'
    )

@view_config(route_name='create_post', request_method='POST', renderer='json')
def create_post(request):
    try:
        user_data = request.user
        user_id = user_data.get("id")
        user_role = user_data.get("role")

        if not user_id:
            return error_response(request, "Autentikasi diperlukan untuk membuat post.", 401)
        
        if user_role != "Mahasiswa":
            return error_response(request, "Hanya mahasiswa yang diizinkan membuat post.", 403)

        data = request.json_body
        title = data.get("title")
        content = data.get("content")
        references_data = data.get("references", [])

        if not title or not content:
            return error_response(request, "Judul dan konten harus diisi.", 400)

        new_post = Post(
            title=title,
            content=content,
            author_id=user_id,
        )
        request.dbsession.add(new_post)
        # Flush diperlukan agar new_post memiliki ID dan relasi yang valid sebelum commit
        request.dbsession.flush() 

        for ref_url_str in references_data:
            if not isinstance(ref_url_str, str) or not ref_url_str.strip():
                continue

            url_obj = request.dbsession.query(URL).filter_by(url=ref_url_str).first()
            if not url_obj:
                url_obj = URL(url=ref_url_str)
                request.dbsession.add(url_obj)
            new_post.references.append(url_obj)

        # Hapus request.dbsession.commit()
        # Biarkan transaction manager Pyramid yang mengelola commit secara otomatis

        author_obj = request.dbsession.query(User).get(user_id)
        if author_obj:
            new_post.author = author_obj

        return {"message": "Post berhasil dibuat", "post": post_to_dict(new_post)}

    except IntegrityError:
        # Hapus request.dbsession.rollback()
        # Biarkan transaction manager Pyramid yang mengelola rollback
        return error_response(request, "Terjadi konflik data. Mungkin ada duplikat.", 409)
    except DBAPIError as e:
        print(f"Database error: {e}")
        # Hapus request.dbsession.rollback()
        # Biarkan transaction manager Pyramid yang mengelola rollback
        return error_response(request, "Terjadi kesalahan database.", 500)
    except KeyError as e:
        print(f"KeyError in create_post (user_data): {e}")
        return error_response(request, "Data pengguna tidak lengkap atau tidak valid.", 401)
    except Exception as e:
        print(f"Unexpected error creating post: {e}")
        # Hapus request.dbsession.rollback()
        # Biarkan transaction manager Pyramid yang mengelola rollback
        return error_response(request, "Terjadi kesalahan server tidak terduga.", 500)

@view_config(route_name='list_posts', request_method='GET', renderer='json')
def list_posts(request):
    try:
        page = request.params.get('page', 1)
        per_page = request.params.get('per_page', 10)
        filter_self = request.params.get('author') == 'self'

        try:
            page = int(page)
            per_page = int(per_page)
            if page <= 0:
                page = 1
            if per_page <= 0 or per_page > 100:
                per_page = 10
        except ValueError:
            return error_response(request, "Parameter 'page' atau 'per_page' tidak valid.", 400)

        offset = (page - 1) * per_page

        posts_query = request.dbsession.query(Post)

        if filter_self:
            user_id = request.user.get("id")
            if not user_id:
                return error_response(request, "Autentikasi diperlukan untuk melihat postingan Anda.", 401)
            posts_query = posts_query.filter(Post.author_id == user_id)

        total_posts = posts_query.count()

        posts_query = posts_query \
            .options(joinedload(Post.author)) \
            .options(joinedload(Post.references)) \
            .order_by(Post.created_at.desc())

        posts = posts_query.offset(offset).limit(per_page).all()
        
        posts_data = [post_to_dict(p) for p in posts]
        
        total_pages = (total_posts + per_page - 1) // per_page

        return {
            "posts": posts_data,
            "pagination": {
                "total_posts": total_posts,
                "per_page": per_page,
                "current_page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    except DBAPIError as e:
        print(f"Database error: {e}")
        return error_response(request, "Terjadi kesalahan database.", 500)
    except Exception as e:
        print(f"Unexpected error listing posts: {e}")
        return error_response(request, "Terjadi kesalahan server tidak terduga.", 500)


@view_config(route_name='get_post', request_method='GET', renderer='json')
def get_post(request):
    try:
        post_id = request.matchdict.get("id")
        try:
            post_id = int(post_id)
        except (ValueError, TypeError):
            return error_response(request, "ID Post tidak valid.", 400)

        post = request.dbsession.query(Post) \
            .options(joinedload(Post.author)) \
            .options(joinedload(Post.references)) \
            .options(joinedload(Post.recommended_by)) \
            .filter_by(id=post_id).first()

        if not post:
            return error_response(request, "Post tidak ditemukan.", 404)

        post_data = post_to_dict(post)

        # Ambil user saat ini
        current_user = request.user
        is_recommended = False
        if current_user and hasattr(post, "recommended_by"):
            is_recommended = current_user in post.recommended_by

        post_data["is_recommended_by_current_user"] = is_recommended
        return post_data

    except DBAPIError as e:
        print(f"Database error: {e}")
        return error_response(request, "Terjadi kesalahan database.", 500)
    except Exception as e:
        print(f"Unexpected error getting post: {e}")
        return error_response(request, "Terjadi kesalahan server tidak terduga.", 500)

@view_config(route_name='like_post', request_method='POST', renderer='json')
def like_post(request):
    try:
        user_id = request.user.get("id")
        if not user_id:
            return error_response(request, "Autentikasi diperlukan untuk menyukai post.", 401)

        post_id = request.matchdict.get("id")
        try:
            post_id = int(post_id)
        except (ValueError, TypeError):
            return error_response(request, "ID Post tidak valid.", 400)

        post = request.dbsession.get(Post, post_id)
        if not post:
            return error_response(request, "Post tidak ditemukan.", 404)

        interaction = request.dbsession.query(PostInteraction).filter_by(
            user_id=user_id,
            post_id=post_id
        ).first()

        if interaction:
            if interaction.interaction_type == 'like':
                # Toggle off like
                request.dbsession.delete(interaction)
                post.likes -= 1
                message = "Like dibatalkan."
            else:
                # Ganti dislike ke like
                interaction.interaction_type = 'like'
                post.likes += 1
                post.dislikes -= 1
                message = "Dislike diubah menjadi like."
        else:
            new_interaction = PostInteraction(
                user_id=user_id,
                post_id=post_id,
                interaction_type='like',
                created_at=datetime.utcnow()
            )
            request.dbsession.add(new_interaction)
            post.likes += 1
            message = "Post berhasil disukai."

        request.dbsession.flush()
        return {"message": message, "likes": post.likes, "dislikes": post.dislikes}

    except IntegrityError:
        return error_response(request, "Terjadi konflik interaksi.", 409)
    except DBAPIError as e:
        print(f"Database error in like_post: {e}")
        return error_response(request, "Terjadi kesalahan database saat menyukai post.", 500)
    except Exception as e:
        print(f"Unexpected error in like_post: {e}")
        return error_response(request, "Terjadi kesalahan server tidak terduga.", 500)



@view_config(route_name='dislike_post', request_method='POST', renderer='json')
def dislike_post(request):
    try:
        user_id = request.user.get("id")
        if not user_id:
            return error_response(request, "Autentikasi diperlukan untuk tidak menyukai post.", 401)

        post_id = request.matchdict.get("id")
        try:
            post_id = int(post_id)
        except (ValueError, TypeError):
            return error_response(request, "ID Post tidak valid.", 400)

        post = request.dbsession.get(Post, post_id)
        if not post:
            return error_response(request, "Post tidak ditemukan.", 404)

        interaction = request.dbsession.query(PostInteraction).filter_by(
            user_id=user_id,
            post_id=post_id
        ).first()

        if interaction:
            if interaction.interaction_type == 'dislike':
                # Toggle off dislike
                request.dbsession.delete(interaction)
                post.dislikes -= 1
                message = "Dislike dibatalkan."
            else:
                # Ganti like ke dislike
                interaction.interaction_type = 'dislike'
                post.likes -= 1
                post.dislikes += 1
                message = "Like diubah menjadi dislike."
        else:
            new_interaction = PostInteraction(
                user_id=user_id,
                post_id=post_id,
                interaction_type='dislike',
                created_at=datetime.utcnow()
            )
            request.dbsession.add(new_interaction)
            post.dislikes += 1
            message = "Post berhasil tidak disukai."

        request.dbsession.flush()
        return {"message": message, "likes": post.likes, "dislikes": post.dislikes}

    except IntegrityError:
        return error_response(request, "Terjadi konflik interaksi.", 409)
    except DBAPIError as e:
        print(f"Database error in dislike_post: {e}")
        return error_response(request, "Terjadi kesalahan database saat tidak menyukai post.", 500)
    except Exception as e:
        print(f"Unexpected error in dislike_post: {e}")
        return error_response(request, "Terjadi kesalahan server tidak terduga.", 500)

@view_config(route_name='recommend_post', request_method='POST', renderer='json')
def recommend_post(request):
    try:
        user_id = request.user.get("id")
        user_role = request.user.get("role")

        if not user_id or user_role != "Dosen":
            return Response(json_body={"error": "Hanya dosen yang dapat merekomendasikan."}, status=403)

        post_id = request.matchdict.get("id")
        post = request.dbsession.get(Post, int(post_id))

        if not post:
            return Response(json_body={"error": "Post tidak ditemukan."}, status=404)

        user = request.dbsession.get(User, user_id)

        if user in post.recommended_by:
            return Response(json_body={"message": "Anda sudah merekomendasikan post ini."}, status=200)

        post.recommended_by.append(user)
        request.dbsession.flush()

        return {
            "message": "Post berhasil direkomendasikan.",
            "recommended_by": [u.id for u in post.recommended_by]
        }

    except DBAPIError as e:
        request.log.exception("Database error in recommend_post:")
        return Response(json_body={"error": "Terjadi kesalahan database."}, status=500)
    except Exception as e:
        request.log.exception("Unexpected error in recommend_post:")
        return Response(json_body={"error": "Terjadi kesalahan tidak terduga."}, status=500)

@view_config(route_name='unrecommend_post', request_method='POST', renderer='json')
def unrecommend_post(request):
    try:
        user_id = request.user.get("id")
        user_role = request.user.get("role")

        if not user_id or user_role != "Dosen":
            return Response(json_body={"error": "Hanya dosen yang dapat membatalkan rekomendasi."}, status=403)

        post_id = request.matchdict.get("id")
        post = request.dbsession.get(Post, int(post_id))

        if not post:
            return Response(json_body={"error": "Post tidak ditemukan."}, status=404)

        user = request.dbsession.get(User, user_id)

        if user not in post.recommended_by:
            return Response(json_body={"message": "Anda belum merekomendasikan post ini."}, status=200)

        post.recommended_by.remove(user)
        request.dbsession.flush()

        return {
            "message": "Rekomendasi berhasil dibatalkan.",
            "recommended_by": [u.id for u in post.recommended_by]
        }

    except DBAPIError as e:
        request.log.exception("Database error in unrecommend_post:")
        return Response(json_body={"error": "Terjadi kesalahan database."}, status=500)
    except Exception as e:
        request.log.exception("Unexpected error in unrecommend_post:")
        return Response(json_body={"error": "Terjadi kesalahan tidak terduga."}, status=500)