import json
from math import ceil, floor
from typing import Dict, List, Optional, Tuple

from datamodel import Order, OrderDepth, TradingState


LIMITS = {
    "ASH_COATED_OSMIUM": 80,
    "INTARIAN_PEPPER_ROOT": 80,
}

OSMIUM = "ASH_COATED_OSMIUM"
PEPPER = "INTARIAN_PEPPER_ROOT"


class Trader:
    def bid(self):
        return 15

    def run(self, state: TradingState):
        memory = self._load_memory(state.traderData)
        result: Dict[str, List[Order]] = {}

        for product, order_depth in state.order_depths.items():
            position = state.position.get(product, 0)
            if product == PEPPER:
                orders, next_state = self._trade_pepper(order_depth, position, state.timestamp, memory.get("pepper"))
                memory["pepper"] = next_state
            else:
                orders = []
            result[product] = orders

        trader_data = json.dumps(memory, separators=(",", ":"))
        return result, 0, trader_data

    def _trade_pepper(
        self,
        order_depth: OrderDepth,
        position: int,
        timestamp: int,
        product_state: Optional[dict],
    ) -> Tuple[List[Order], dict]:
        best_bid, best_ask, mid, bid_volume, ask_volume = self._top_of_book(order_depth)
        if mid is None:
            return [], product_state or {}

        imbalance, microprice = self._microprice_signal(best_bid, best_ask, bid_volume, ask_volume, mid)
        drift_per_timestamp = 0.001
        detrended_mid = mid - drift_per_timestamp * timestamp

        prev_anchor = None if product_state is None else product_state.get("anchor")
        anchor = detrended_mid if prev_anchor is None else 0.96 * prev_anchor + 0.04 * detrended_mid

        fair_value = anchor + drift_per_timestamp * timestamp + 0.12 * (microprice - mid)
        reservation = fair_value - 0.22 * position

        manager = OrderManager(PEPPER, LIMITS[PEPPER], position)
        take_edge = 2
        quote_edge = 3 if abs(imbalance) < 0.35 else 2

        for ask_price, ask_book_volume in sorted(order_depth.sell_orders.items()):
            if ask_price <= floor(reservation - take_edge):
                manager.buy(ask_price, min(-ask_book_volume, 10))

        for bid_price, bid_book_volume in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid_price >= ceil(reservation + take_edge):
                manager.sell(bid_price, min(bid_book_volume, 10))

        if best_bid is None:
            best_bid = floor(mid - 3)
        if best_ask is None:
            best_ask = ceil(mid + 3)

        bias = imbalance
        passive_bid = min(best_bid + 1, floor(reservation - quote_edge + bias))
        passive_ask = max(best_ask - 1, ceil(reservation + quote_edge + bias))

        if passive_bid >= passive_ask:
            passive_bid = min(passive_bid, passive_ask - 1)
            passive_ask = max(passive_ask, passive_bid + 1)

        if manager.remaining_buy() > 0 and passive_bid < best_ask:
            manager.buy(passive_bid, min(10, manager.remaining_buy()))
        if manager.remaining_sell() > 0 and passive_ask > best_bid:
            manager.sell(passive_ask, min(10, manager.remaining_sell()))

        return manager.orders, {"anchor": round(anchor, 4)}

    def _top_of_book(
        self, order_depth: OrderDepth
    ) -> Tuple[Optional[int], Optional[int], Optional[float], int, int]:
        best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
        bid_volume = order_depth.buy_orders.get(best_bid, 0) if best_bid is not None else 0
        ask_volume = -order_depth.sell_orders.get(best_ask, 0) if best_ask is not None else 0

        if best_bid is not None and best_ask is not None:
            return best_bid, best_ask, (best_bid + best_ask) / 2.0, bid_volume, ask_volume
        if best_bid is not None:
            return best_bid, None, float(best_bid), bid_volume, 0
        if best_ask is not None:
            return None, best_ask, float(best_ask), 0, ask_volume
        return None, None, None, 0, 0

    def _microprice_signal(
        self,
        best_bid: Optional[int],
        best_ask: Optional[int],
        bid_volume: int,
        ask_volume: int,
        mid: float,
    ) -> Tuple[float, float]:
        total_volume = bid_volume + ask_volume
        if best_bid is None or best_ask is None or total_volume <= 0:
            return 0.0, mid
        imbalance = (bid_volume - ask_volume) / total_volume
        microprice = (best_bid * ask_volume + best_ask * bid_volume) / total_volume
        return imbalance, microprice

    def _load_memory(self, trader_data: str) -> dict:
        if not trader_data:
            return {}
        try:
            loaded = json.loads(trader_data)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}


class OrderManager:
    def __init__(self, product: str, limit: int, position: int):
        self.product = product
        self.limit = limit
        self.position = position
        self.net_quantity = 0
        self.orders: List[Order] = []

    def remaining_buy(self) -> int:
        return self.limit - (self.position + self.net_quantity)

    def remaining_sell(self) -> int:
        return self.limit + (self.position + self.net_quantity)

    def buy(self, price: int, quantity: int) -> None:
        quantity = int(min(quantity, self.remaining_buy()))
        if quantity <= 0:
            return
        self.orders.append(Order(self.product, int(price), quantity))
        self.net_quantity += quantity

    def sell(self, price: int, quantity: int) -> None:
        quantity = int(min(quantity, self.remaining_sell()))
        if quantity <= 0:
            return
        self.orders.append(Order(self.product, int(price), -quantity))
        self.net_quantity -= quantity
