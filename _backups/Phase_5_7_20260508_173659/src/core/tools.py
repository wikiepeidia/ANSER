import ast
import operator

from src.core.external_data import ExternalIntelligence


class RetailTools:
    def __init__(self):
        self.external = ExternalIntelligence()

    def get_strategic_forecast(self, memory, store_id):
        """
        Combines Internal Data + GPS Weather + Market Trends.
        """
        # 1. Get Store Location
        store = memory.get_store_details(store_id)
        if not store:
            return "Store not found."

        # 2. Get Weather (Real-time)
        weather = self.external.get_weather_forecast(store['lat'], store['lon'])

        # 3. Get Market Trend (Mock/Search)
        # For demo speed, we check a key product
        market = self.external.check_market_prices("Bỉm Bobby")

        # 4. Synthesize Context
        report = f'''
        [STRATEGIC FORECAST REPORT]
        📍 Location: {store['location']} (Lat: {store['lat']}, Lon: {store['lon']})
        🌤️ Weather Forecast: {weather['summary']}
        🛒 Market Intel: Found {len(market['competitor_snippets'])} competitor listings.

        [IMPACT ANALYSIS]
        - If Rain > 50%: Foot traffic will drop. Suggest Delivery Promo.
        - If Competitor Price < Your Price: Suggest Bundle.
        '''
        return report

    @staticmethod
    def calculate(expression: str):
        allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](_eval(node.operand))
            raise ValueError("Unsupported expression")

        try:
            parsed = ast.parse(expression, mode="eval")
            return str(_eval(parsed))
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
            return "Error"

    @staticmethod
    def health_check(saas, store_id):
        return [] # Simplified for now
