/* SPDX-License-Identifier: GPL-3.0-only */
#include "Engine.hpp"

namespace p1 {

Engine::Engine() : state_(std::make_unique<type_p_fm1_state>())
{
    type_p_fm1_dsp_state_init(state_.get());
}

Engine::~Engine() = default;

void Engine::reset()
{
    type_p_fm1_dsp_reset_s(state_.get());
}

int Engine::setParam(uint32_t id, int32_t value)
{
    return type_p_fm1_dsp_set_param_s(state_.get(), id, value);
}

int32_t Engine::getParam(uint32_t id)
{
    return type_p_fm1_dsp_get_param_s(state_.get(), id);
}

void Engine::noteOn(uint32_t note, uint32_t velocity, uint32_t channel)
{
    type_p_fm1_dsp_note_on_ch_s(state_.get(), note, velocity, channel);
}

void Engine::noteOff(uint32_t note)
{
    type_p_fm1_dsp_note_off_s(state_.get(), note);
}

void Engine::allNotesOff()
{
    type_p_fm1_dsp_all_notes_off_s(state_.get());
}

void Engine::setBend(uint32_t q16)
{
    type_p_fm1_dsp_set_bend_q16_s(state_.get(), q16);
}

void Engine::render(int32_t* out, uint32_t frames)
{
    type_p_fm1_dsp_render_s(state_.get(), out, frames);
}

uint32_t Engine::lit(uint32_t base)
{
    return type_p_fm1_dsp_lit_s(state_.get(), base);
}

bool Engine::quiet()
{
    return type_p_fm1_dsp_quiet_s(state_.get()) != 0;
}

const int32_t* Engine::tap(uint32_t channel)
{
    return type_p_fm1_dsp_tap_s(state_.get(), channel);
}

type_p_fm1_state* Engine::state()
{
    return state_.get();
}

} // namespace p1
