"""Các loại exception tầng service để ủy quyền từ route sang service."""


class ServiceValidationError(Exception):
    """Được raise khi dữ liệu đầu vào của miền không vượt qua kiểm tra hợp lệ."""


class ServiceAuthorizationError(Exception):
    """Được raise khi người gọi không có quyền thực hiện thao tác."""


class ServiceInvariantError(Exception):
    """Được raise khi các ràng buộc nghiệp vụ bị vi phạm trong quá trình xử lý."""
