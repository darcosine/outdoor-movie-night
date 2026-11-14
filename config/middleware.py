class ContentSecurityPolicyMiddleware:
    """Apply a restrictive policy to the site's scripts, forms, and embeds."""

    POLICY = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' https: data:; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        policy = self.POLICY
        if request.path_info.startswith("/admin/"):
            # Django's built-in admin uses inline scripts and styles.
            policy = policy.replace("script-src 'self';", "script-src 'self' 'unsafe-inline';")
            policy = policy.replace(
                "style-src 'self' https://fonts.googleapis.com;",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;",
            )
        response.setdefault("Content-Security-Policy", policy)
        return response
