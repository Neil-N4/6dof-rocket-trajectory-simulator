#pragma once

#include <array>
#include <atomic>
#include <cstddef>

namespace rocketsim {

// Single-producer/single-consumer lock-free ring buffer.
template <typename T, std::size_t Capacity>
class SpscRing {
 public:
  bool push(const T& item) {
    const std::size_t head = head_.load(std::memory_order_relaxed);
    const std::size_t next = increment(head);
    if (next == tail_.load(std::memory_order_acquire)) {
      return false;
    }
    data_[head] = item;
    head_.store(next, std::memory_order_release);
    return true;
  }

  bool pop(T& out) {
    const std::size_t tail = tail_.load(std::memory_order_relaxed);
    if (tail == head_.load(std::memory_order_acquire)) {
      return false;
    }
    out = data_[tail];
    tail_.store(increment(tail), std::memory_order_release);
    return true;
  }

 private:
  static constexpr std::size_t increment(std::size_t i) { return (i + 1) % Capacity; }

  std::array<T, Capacity> data_{};
  std::atomic<std::size_t> head_{0};
  std::atomic<std::size_t> tail_{0};
};

}  // namespace rocketsim

