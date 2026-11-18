from django.utils.cache import patch_cache_control


class PrivateResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(("/accounts/", "/maintenance/", "/vault/")):
            patch_cache_control(response, private=True, no_store=True)
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
