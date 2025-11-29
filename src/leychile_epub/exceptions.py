"""
Excepciones personalizadas para LeyChile ePub Generator.

Este módulo define la jerarquía de excepciones del paquete,
permitiendo un manejo de errores granular y específico.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""


class LeyChileError(Exception):
    """Excepción base para todos los errores del paquete LeyChile.

    Attributes:
        message: Mensaje descriptivo del error.
        details: Información adicional sobre el error.
    """

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Detalles: {self.details}"
        return self.message


class ScraperError(LeyChileError):
    """Error durante el proceso de scraping.

    Se lanza cuando hay problemas al obtener o parsear datos de la BCN.
    """

    pass


class NetworkError(ScraperError):
    """Error de conexión de red.

    Se lanza cuando no se puede conectar a la API de la BCN.

    Attributes:
        url: URL que falló.
        status_code: Código de estado HTTP (si aplica).
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        details = details or {}
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details)


class ValidationError(LeyChileError):
    """Error de validación de datos.

    Se lanza cuando los datos de entrada no cumplen con el formato esperado.

    Attributes:
        field: Campo que falló la validación.
        value: Valor inválido.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.field = field
        self.value = value
        details = details or {}
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        super().__init__(message, details)


class GeneratorError(LeyChileError):
    """Error durante la generación del ePub.

    Se lanza cuando hay problemas al crear el archivo ePub.
    """

    pass


class ParsingError(ScraperError):
    """Error al parsear el XML de la BCN.

    Se lanza cuando el XML recibido no tiene el formato esperado.
    """

    pass


class RateLimitError(NetworkError):
    """Error por exceso de solicitudes.

    Se lanza cuando la API de la BCN rechaza solicitudes por rate limiting.

    Attributes:
        retry_after: Segundos a esperar antes de reintentar.
    """

    def __init__(
        self,
        message: str = "Rate limit excedido",
        retry_after: int | None = None,
        details: dict | None = None,
    ) -> None:
        self.retry_after = retry_after
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, details=details)
