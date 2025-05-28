def includeme(config):
                """Add routes to the config."""
                config.add_static_view('static', 'static', cache_max_age=3600)
                
                # Default route
                config.add_route('home', '/')
                
                 # Post routes
                config.add_route('create_post', '/api/posts')
                config.add_route('list_posts', '/api/posts/all')
                config.add_route('get_post', '/api/posts/{id}')
                
                # Recommend Posts                
                config.add_route('recommend_post', '/api/posts/{id}/recommend')
                config.add_route('unrecommend_post', '/api/posts/{id}/unrecommend')
                
                # Comment routes
                config.add_route('comment_add', '/api/comments')
                config.add_route('comment_by_post', '/api/comments/post/{post_id}')
                
                # Like/dislike
                config.add_route('like_post', '/api/posts/{id}/like')
                config.add_route('dislike_post', '/api/posts/{id}/dislike')
                
                # Auth
                config.add_route("register", "/api/register")
                config.add_route("login", "/api/login")
                config.add_route("me", "/api/me")
                config.add_route("change_password", "/api/change-password") 
