/* SPDX-License-Identifier: GPL-3.0-only */
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <limits>
#include <vector>

#include <juce_audio_processors/juce_audio_processors.h>

#include "Engine.hpp"
#include "MidiBridge.hpp"
#include "Params.h"
#include "RateBridge.hpp"

class TypePFm1AudioProcessor : public juce::AudioProcessor {
public:
    TypePFm1AudioProcessor();
    ~TypePFm1AudioProcessor() override = default;

    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    bool isBusesLayoutSupported(const BusesLayout& layouts) const override;
    using juce::AudioProcessor::processBlock;
    void processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return "Type P.fm1"; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 8.0; }

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}

    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    juce::AudioProcessorValueTreeState& parameters() { return apvts_; }

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();
    static void feedMessage(p1::MidiBridge& midi, const juce::MidiMessage& message);
    void syncParams();
    void renderCore(int32_t* out, int frames);

    p1::Engine engine_;
    p1::MidiBridge midi_;
    p1::RateBridge rateBridge_;
    juce::AudioProcessorValueTreeState apvts_;
    std::array<int32_t, kP1ParamCount> lastParams_{};
    std::array<std::atomic<float>*, kP1ParamCount> paramValues_{};
    std::vector<int32_t> directBuffer_;
    std::atomic<bool> paramsDirty_{false};
    double hostRate_ = 44100.0;
};
