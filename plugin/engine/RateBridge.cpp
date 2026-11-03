/* SPDX-License-Identifier: GPL-3.0-only */
#include "RateBridge.hpp"

#include <algorithm>
#include <cmath>

#include "Engine.hpp"

namespace p1 {

void RateBridge::prepare(double hostRate, int maxBlock)
{
    ratio_ = 44100.0 / hostRate;
    capacity_ = static_cast<int>(std::ceil(maxBlock * ratio_)) + 128;
    fifo_.assign(static_cast<std::size_t>(capacity_) * 2, 0);
    reset();
}

void RateBridge::reset()
{
    phase_ = 0.0;
    head_ = 0;
    count_ = 0;
}

void RateBridge::renderChunk(Engine& engine, int frames)
{
    int32_t chunk[2 * 64];
    engine.render(chunk, static_cast<uint32_t>(frames));
    for (int i = 0; i < frames; ++i) {
        int index = (head_ + count_) % capacity_;
        fifo_[static_cast<std::size_t>(index) * 2] = chunk[i * 2];
        fifo_[static_cast<std::size_t>(index) * 2 + 1] = chunk[i * 2 + 1];
        ++count_;
    }
}

void RateBridge::process(Engine& engine, float* left, float* right, int frames)
{
    for (int i = 0; i < frames; ++i) {
        while (count_ < 2)
            renderChunk(engine, 32);

        const std::size_t a = static_cast<std::size_t>(head_) * 2;
        const std::size_t b = static_cast<std::size_t>((head_ + 1) % capacity_) * 2;
        const float al = static_cast<float>(fifo_[a]) / 32768.0f;
        const float ar = static_cast<float>(fifo_[a + 1]) / 32768.0f;
        const float bl = static_cast<float>(fifo_[b]) / 32768.0f;
        const float br = static_cast<float>(fifo_[b + 1]) / 32768.0f;
        left[i] = al + (bl - al) * static_cast<float>(phase_);
        right[i] = ar + (br - ar) * static_cast<float>(phase_);

        phase_ += ratio_;
        while (phase_ >= 1.0) {
            phase_ -= 1.0;
            head_ = (head_ + 1) % capacity_;
            --count_;
        }
    }
}

} // namespace p1
