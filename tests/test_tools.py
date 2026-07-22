from src.core.tools import RetailTools


def test_calculate_basic_expression():
    assert RetailTools.calculate("2 + 3 * 4") == "14"


def test_calculate_rejects_unsafe_expression():
    assert RetailTools.calculate("__import__('os').system('echo x')") == "Error"
