/* SPDX-License-Identifier: GPL-3.0-only */
#pragma once

#include <cstdint>
#include <vector>

namespace p1 {

class Engine;

/* Milestone 2 placeholder: linear interpolation from the 44.1 kHz core to the
 * host rate. The 32-tap polyphase bridge replaces this in Milestone 5. The
 * processor bypasses it at 44.1 kHz, so the core stays bit-exact there. */
class RateBridge {
public:
    void prepare(double hostRate, int maxBlock);
    void reset();
    void process(Engine& engine, float* left, float* right, int frames);

private:
    void renderChunk(Engine& engine, int frames);

    double ratio_ = 1.0;
    double phase_ = 0.0;
    std::vector<int32_t> fifo_;
    int capacity_ = 0;
    int head_ = 0;
    int count_ = 0;
};

} // namespace p1
