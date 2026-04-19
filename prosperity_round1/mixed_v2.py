import json
from math import ceil, floor
from typing import Dict, List, Optional, Tuple

from datamodel import Order, OrderDepth, TradingState


OSMIUM = "ASH_COATED_OSMIUM"
PEPPER = "INTARIAN_PEPPER_ROOT"

LIMITS = {
    OSMIUM: 80,
    PEPPER: 80,
}


class Trader:
    def bid(self):
        return 15

    def run(self, state: TradingState):
        memory = self._load_memory(state.traderData)
        result: Dict[str, List[Order]] = {}

        for product, order_depth in state.order_depths.items():
            position = state.position.get(product, 0)
            if product == OSMIUM:
                orders, next_state = self._trade_osmium(order_depth, position, memory.get("osmium"))
                memory["osmium"] = next_state
            elif product == PEPPER:
                orders, next_state = self._trade_pepper(
                    order_depth, position, state.timestamp, memory.get("pepper")
                )
                memory["pepper"] = next_state
            else:
                orders = []
            result[product] = orders

        return result, 0, json.dumps(memory, separators=(",", ":"))

    def _trade_osmium(
        self, order_depth: OrderDepth, position: int, state_mem: Optional[dict]
    ) -> Tuple[List[Order], dict]:
        best_bid, best_ask, mid = self._top_of_book(order_depth)
        if mid is None:
            return [], state_mem or {}

        prev_ema = None if state_mem is None else state_mem.get("ema")
        ema = mid if prev_ema is None else 0.22 * mid + 0.78 * prev_ema

        manager = OrderManager(OSMIUM, LIMITS[OSMIUM], position)
        reservation = ema - 0.15 * position

        for ask_price, ask_volume in sorted(order_depth.sell_orders.items()):
            if ask_price <= floor(reservation - 1):
                manager.buy(ask_price, -ask_volume)

        for bid_price, bid_volume in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid_price >= ceil(reservation + 1):
                manager.sell(bid_price, bid_volume)

        best_bid = best_bid if best_bid is not None else floor(mid - 4)
        best_ask = best_ask if best_ask is not None else ceil(mid + 4)

        passive_bid = min(best_bid + 1, floor(reservation - 3))
        passive_ask = max(best_ask - 1, ceil(reservation + 3))
        if passive_bid >= passive_ask:
            passive_bid = min(passive_bid, passive_ask - 1)
            passive_ask = max(passive_ask, passive_bid + 1)

        if manager.remaining_buy() > 0 and passive_bid < best_ask:
            manager.buy(passive_bid, min(12, manager.remaining_buy()))
        if manager.remaining_sell() > 0 and passive_ask > best_bid:
            manager.sell(passive_ask, min(12, manager.remaining_sell()))

        return manager.orders, {"ema": round(ema, 4)}

    def _trade_pepper(
        self,
        order_depth: OrderDepth,
        position: int,
        timestamp: int,
        state_mem: Optional[dict],
    ) -> Tuple[List[Order], dict]:
        best_bid, best_ask, mid = self._top_of_book(order_depth)
        if mid is None:
            return [], state_mem or {}

        drift = 0.001
        detrended_mid = mid - drift * timestamp
        prev_anchor = None if state_mem is None else state_mem.get("anchor")
        anchor = detrended_mid if prev_anchor is None else 0.10 * detrended_mid + 0.90 * prev_anchor
        fair_value = anchor + drift * timestamp

        manager = OrderManager(PEPPER, LIMITS[PEPPER], position)

        # Pepper trended upward in the sample run. Keep a structural long and
        # only sell above fair when already carrying inventory.
        target_long = 20
        reservation = fair_value - 0.12 * (position - target_long)

        for ask_price, ask_volume in sorted(order_depth.sell_orders.items()):
            if ask_price <= floor(reservation - 1):
                manager.buy(ask_price, min(-ask_volume, 12))

        if position > 0:
            for bid_price, bid_volume in sorted(order_depth.buy_orders.items(), reverse=True):
                if bid_price >= ceil(reservation + 2):
                    manager.sell(bid_price, min(bid_volume, min(10, position + manager.net_quantity)))

        best_bid = best_bid if best_bid is not None else floor(mid - 3)
        best_ask = best_ask if best_ask is not None else ceil(mid + 3)

        passive_bid = min(best_bid + 1, floor(reservation - 2))
        passive_ask = max(best_ask - 1, ceil(reservation + 4))
        if passive_bid >= passive_ask:
            passive_bid = min(passive_bid, passive_ask - 1)
            passive_ask = max(passive_ask, passive_bid + 1)

        if manager.remaining_buy() > 0 and position + manager.net_quantity < target_long + 20 and passive_bid < best_ask:
            size = 16 if position < target_long else 8
            manager.buy(passive_bid, min(size, manager.remaining_buy()))

        if position + manager.net_quantity > target_long and manager.remaining_sell() > 0 and passive_ask > best_bid:
            manager.sell(passive_ask, min(8, manager.remaining_sell(), position + manager.net_quantity - target_long))

        return manager.orders, {"anchor": round(anchor, 4)}

    def _top_of_book(self, order_depth: OrderDepth) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
        if best_bid is not None and best_ask is not None:
            return best_bid, best_ask, (best_bid + best_ask) / 2.0
        if best_bid is not None:
            return best_bid, None, float(best_bid)
        if best_ask is not None:
            return None, best_ask, float(best_ask)
        return None, None, None

    def _load_memory(self, trader_data: str) -> dict:
        if not trader_data:
            return {}
        try:
            out = json.loads(trader_data)
            return out if isinstance(out, dict) else {}
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
