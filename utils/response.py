def success_response(message: str, data=None):
    return {
        "success": True,
        "message": message,
        "data": data
    }

def error_response(message: str, status_code: int = 400):
    return {
        "success": False,
        "message": message,
        "status_code": status_code
    }
