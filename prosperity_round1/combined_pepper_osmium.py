from __future__ import annotations

import json
from math import ceil, floor
from typing import Any, Dict, List, Optional, Tuple

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
            if product == PEPPER:
                orders, next_state = self._trade_pepper(order_depth, position, state.timestamp, memory.get("pepper"))
                memory["pepper"] = next_state
            elif product == OSMIUM:
                orders, next_state = self._trade_osmium(order_depth, position, memory.get("osmium"))
                memory["osmium"] = next_state
            else:
                orders = []
            result[product] = orders

        return result, 0, json.dumps(memory, separators=(",", ":"))

    def _trade_pepper(
        self,
        order_depth: OrderDepth,
        position: int,
        timestamp: int,
        state_mem: Optional[dict],
    ) -> Tuple[List[Order], dict]:
        best_bid, best_ask = self._best_bid(order_depth), self._best_ask(order_depth)
        if best_bid[0] is None or best_ask[0] is None:
            return [], state_mem or {"anchor_mid": None, "mid_history": []}

        data = dict(state_mem or {"anchor_mid": None, "mid_history": []})
        data.setdefault("anchor_mid", None)
        data.setdefault("mid_history", [])

        carry_fair, short_fair, imbalance, micro_off = self._pepper_signal_features(
            timestamp=timestamp,
            position=position,
            data=data,
            best_bid=best_bid[0],
            best_ask=best_ask[0],
            bid_volume=best_bid[1],
            ask_volume=best_ask[1],
        )

        signal = 15.0 * imbalance + 2.0 * micro_off
        target_position = LIMITS[PEPPER]
        core_position = 72
        manager = OrderManager(PEPPER, LIMITS[PEPPER], position)

        # Reach a full long quickly when the day opens; this matched the best live run.
        if timestamp <= 300 and position + manager.net_quantity < target_position:
            for ask_price, ask_size in self._sorted_asks(order_depth):
                qty = min(ask_size, target_position - (position + manager.net_quantity), 40)
                manager.buy(ask_price, qty)
                if position + manager.net_quantity >= target_position:
                    break

        # Top up any offers that are still clearly cheap versus the carry fair value.
        for ask_price, ask_size in self._sorted_asks(order_depth):
            if position + manager.net_quantity >= target_position:
                break
            if ask_price > carry_fair - 1:
                break
            manager.buy(ask_price, min(ask_size, target_position - (position + manager.net_quantity), 20))

        # Keep a passive bid working until we are full.
        if position + manager.net_quantity < target_position:
            passive_bid = min(best_ask[0] - 1, int(round(carry_fair - 6)))
            if passive_bid > best_bid[0]:
                manager.buy(passive_bid, min(20, target_position - (position + manager.net_quantity)))

        # Only trim if we are very long and the market looks extended.
        sell_trigger = max(short_fair + 10, carry_fair + 14)
        if position + manager.net_quantity > core_position and signal < -6:
            for bid_price, bid_size in self._sorted_bids(order_depth):
                if bid_price < sell_trigger:
                    break
                qty = min(bid_size, position + manager.net_quantity - core_position, 8)
                manager.sell(bid_price, qty)
                if position + manager.net_quantity <= core_position:
                    break

        if position + manager.net_quantity > core_position and signal < -6:
            passive_ask = max(best_bid[0] + 1, int(round(sell_trigger)))
            if passive_ask < best_ask[0]:
                passive_ask = best_ask[0] - 1
            if passive_ask > best_bid[0]:
                manager.sell(passive_ask, min(6, position + manager.net_quantity - core_position))

        return manager.compact(), data

    def _pepper_signal_features(
        self,
        timestamp: int,
        position: int,
        data: Dict[str, Any],
        best_bid: int,
        best_ask: int,
        bid_volume: int,
        ask_volume: int,
    ) -> Tuple[float, float, float, float]:
        mid_price = (best_bid + best_ask) / 2.0
        history = list(data.get("mid_history", []))
        history.append(mid_price)
        if len(history) > 60:
            history = history[-60:]
        data["mid_history"] = history

        if data["anchor_mid"] is None or timestamp == 0:
            data["anchor_mid"] = mid_price

        total = bid_volume + ask_volume
        imbalance = 0.0 if total <= 0 else (bid_volume - ask_volume) / total
        micro_off = ((best_ask * bid_volume + best_bid * ask_volume) / total - mid_price) if total > 0 else 0.0

        if len(history) >= 6:
            slope = (history[-1] - history[0]) / max(1, len(history) - 1)
        else:
            slope = 0.10
        slope = self._clamp(slope, 0.06, 0.16)

        remaining_steps = max(0.0, 999.0 - timestamp / 100.0)
        projected_terminal = max(data["anchor_mid"] + 100.0, mid_price + remaining_steps * slope)
        carry_fair = projected_terminal + 1.5 * imbalance - 0.02 * (position - LIMITS[PEPPER])
        short_move = 1.30 + 13.4 * imbalance + 1.8 * micro_off
        short_fair = mid_price + short_move
        return carry_fair, short_fair, imbalance, micro_off

    def _trade_osmium(
        self,
        order_depth: OrderDepth,
        position: int,
        state_mem: Optional[dict],
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

        return manager.compact(), {"ema": round(ema, 4)}

    @staticmethod
    def _best_bid(order_depth: OrderDepth) -> Tuple[Optional[int], int]:
        if not order_depth.buy_orders:
            return None, 0
        price = max(order_depth.buy_orders)
        return int(price), int(order_depth.buy_orders[price])

    @staticmethod
    def _best_ask(order_depth: OrderDepth) -> Tuple[Optional[int], int]:
        if not order_depth.sell_orders:
            return None, 0
        price = min(order_depth.sell_orders)
        return int(price), -int(order_depth.sell_orders[price])

    @staticmethod
    def _sorted_asks(order_depth: OrderDepth) -> List[Tuple[int, int]]:
        return [(int(price), -int(volume)) for price, volume in sorted(order_depth.sell_orders.items())]

    @staticmethod
    def _sorted_bids(order_depth: OrderDepth) -> List[Tuple[int, int]]:
        return [(int(price), int(volume)) for price, volume in sorted(order_depth.buy_orders.items(), reverse=True)]

    @staticmethod
    def _top_of_book(order_depth: OrderDepth) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
        if best_bid is not None and best_ask is not None:
            return best_bid, best_ask, (best_bid + best_ask) / 2.0
        if best_bid is not None:
            return best_bid, None, float(best_bid)
        if best_ask is not None:
            return None, best_ask, float(best_ask)
        return None, None, None

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    @staticmethod
    def _load_memory(trader_data: str) -> dict:
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

    def compact(self) -> List[Order]:
        aggregated: Dict[int, int] = {}
        for order in self.orders:
            aggregated[order.price] = aggregated.get(order.price, 0) + order.quantity
        return [Order(self.product, price, qty) for price, qty in sorted(aggregated.items()) if qty != 0]
