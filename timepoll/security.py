WIKIMEDIA_CDN_ORIGIN = "https://tools-static.wmflabs.org"
WIKIMEDIA_VUE_CDN_URL = (
    f"{WIKIMEDIA_CDN_ORIGIN}/cdnjs/ajax/libs/vue/3.4.31/vue.global.prod.min.js"
)
WIKIMEDIA_VUE_CDN_INTEGRITY = (
    "sha384-WCkmst01ECz4FO/1B+yi3G9lGcB50Mxb34qU2Gxv8raRtfey/Tjo2Iej7aH7OLvl"
)

CONTENT_SECURITY_POLICY_DIRECTIVES = {
    "default-src": ["'none'"],
    "base-uri": ["'none'"],
    "child-src": ["'none'"],
    "connect-src": ["'self'"],
    "font-src": ["'none'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
    "frame-src": ["'none'"],
    "img-src": ["'self'", "data:", "blob:"],
    "manifest-src": ["'self'"],
    "media-src": ["'none'"],
    "object-src": ["'none'"],
    # The current Vue setup compiles DOM templates at runtime, which requires unsafe-eval.
    "script-src": ["'self'", "'unsafe-eval'", WIKIMEDIA_CDN_ORIGIN],
    "script-src-attr": ["'none'"],
    "style-src": ["'self'"],
    "worker-src": ["'none'"],
}

CONTENT_SECURITY_POLICY = "; ".join(
    f"{directive} {' '.join(sources)}"
    for directive, sources in CONTENT_SECURITY_POLICY_DIRECTIVES.items()
)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        return response
