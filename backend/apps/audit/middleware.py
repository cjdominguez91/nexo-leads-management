import threading

_local = threading.local()


class CurrentRequestMiddleware:
    """Guarda el request actual en thread-local para que las señales de
    modelos (que no reciben `request`) puedan leer usuario/IP al escribir
    en AuditLog. Patrón estándar de Django para este problema; se limpia
    siempre al final del request, incluso si la vista lanza una excepción."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None


def get_current_request():
    return getattr(_local, "request", None)


def get_current_user():
    request = get_current_request()
    if request and request.user and request.user.is_authenticated:
        return request.user
    return None


def get_client_ip():
    request = get_current_request()
    if not request:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
