from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _flatten_error_messages(errors):
    if isinstance(errors, dict):
        flattened = []
        for field, value in errors.items():
            nested = _flatten_error_messages(value)
            if field == "detail":
                flattened.extend(nested)
            else:
                flattened.extend([f"{field}: {message}" for message in nested])
        return flattened

    if isinstance(errors, list):
        flattened = []
        for item in errors:
            flattened.extend(_flatten_error_messages(item))
        return flattened

    return [str(errors)]


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {"message": "An unexpected error occurred.", "errors": []},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(response.data, dict):
        errors = response.data
    else:
        errors = {"detail": response.data}

    detail_messages = _flatten_error_messages(errors)
    detail = detail_messages[0] if detail_messages else "Request could not be processed."
    return Response({"message": detail, "errors": errors}, status=response.status_code)
