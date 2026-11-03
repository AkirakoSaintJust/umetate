/* SPDX-License-Identifier: GPL-3.0-only */
#include "PluginProcessor.h"

#include <algorithm>
#include <cmath>
#include <limits>

#include <juce_audio_utils/juce_audio_utils.h>

namespace {

constexpr double kCoreRate = 44100.0;
constexpr int kControlBlock = 32;
constexpr int kStateVersion = 1;
constexpr float kIntToFloat = 1.0f / 32768.0f;

bool isEngineMessage(const juce::MidiMessage& message)
{
    if (message.getRawDataSize() < 3)
        return false;
    return message.isNoteOnOrOff() || message.isController() ||
           message.isPitchWheel();
}

} // namespace

extern "C" int midi_get(uint8_t*, uint8_t*, uint8_t*)
{
    return 0; /* the plugin feeds MidiBridge directly */
}

TypePFm1AudioProcessor::TypePFm1AudioProcessor()
    : AudioProcessor(BusesProperties().withOutput(
          "Output", juce::AudioChannelSet::stereo(), true)),
      midi_(engine_),
      apvts_(*this, nullptr, "type_p_fm1", createLayout())
{
    lastParams_.fill(std::numeric_limits<int32_t>::min());
    for (int i = 0; i < kP1ParamCount; ++i)
        paramValues_[static_cast<std::size_t>(i)] =
            apvts_.getRawParameterValue(kP1ParamSpecs[static_cast<std::size_t>(i)].id);
}

juce::AudioProcessorValueTreeState::ParameterLayout
TypePFm1AudioProcessor::createLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;
    for (const auto& spec : kP1ParamSpecs) {
        layout.add(std::make_unique<juce::AudioParameterInt>(
            juce::ParameterID{spec.id, 1}, spec.name, spec.min, spec.max, spec.def));
    }
    return layout;
}

void TypePFm1AudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    hostRate_ = sampleRate;
    engine_.reset();
    midi_.reset();
    rateBridge_.reset();
    directBuffer_.assign(static_cast<std::size_t>(kControlBlock) * 2u, 0);
    if (std::abs(sampleRate - kCoreRate) > 0.5)
        rateBridge_.prepare(sampleRate, samplesPerBlock);
    lastParams_.fill(std::numeric_limits<int32_t>::min());
    paramsDirty_.store(false, std::memory_order_relaxed);
    syncParams();
}

void TypePFm1AudioProcessor::releaseResources()
{
    engine_.allNotesOff();
}

bool TypePFm1AudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    if (layouts.getMainInputChannelSet() != juce::AudioChannelSet::disabled())
        return false;
    const auto out = layouts.getMainOutputChannelSet();
    return out == juce::AudioChannelSet::stereo() ||
           out == juce::AudioChannelSet::mono();
}

void TypePFm1AudioProcessor::syncParams()
{
    for (int i = 0; i < kP1ParamCount; ++i) {
        const auto* value = paramValues_[static_cast<std::size_t>(i)];
        if (value == nullptr)
            continue;
        const auto next = static_cast<int32_t>(std::lround(value->load()));
        if (next != lastParams_[static_cast<std::size_t>(i)]) {
            engine_.setParam(
                static_cast<uint32_t>(
                    kP1ParamSpecs[static_cast<std::size_t>(i)].engineId),
                next);
            lastParams_[static_cast<std::size_t>(i)] = next;
        }
    }
}

void TypePFm1AudioProcessor::feedMessage(p1::MidiBridge& midi,
                                         const juce::MidiMessage& message)
{
    const auto* data = message.getRawData();
    midi.feed(data[0], data[1], data[2]);
}

void TypePFm1AudioProcessor::renderCore(int32_t* out, int frames)
{
    engine_.render(out, static_cast<uint32_t>(frames));
}

void TypePFm1AudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                          juce::MidiBuffer& midi)
{
    juce::ScopedNoDenormals noDenormals;
    buffer.clear();

    const int frames = buffer.getNumSamples();
    if (frames == 0)
        return;

    if (paramsDirty_.exchange(false, std::memory_order_relaxed))
        lastParams_.fill(std::numeric_limits<int32_t>::min());

    const int channels = buffer.getNumChannels();
    if (channels == 0) {
        midi.clear();
        return;
    }
    if (std::abs(hostRate_ - kCoreRate) < 0.5) {
        float* left = buffer.getWritePointer(0);
        float* right = channels > 1 ? buffer.getWritePointer(1) : nullptr;
        auto event = midi.begin();
        int pos = 0;
        while (pos < frames) {
            const int length = std::min(kControlBlock, frames - pos);
            const int end = pos + length;

            while (event != midi.end() && (*event).samplePosition < end) {
                const auto message = (*event).getMessage();
                if (isEngineMessage(message))
                    feedMessage(midi_, message);
                ++event;
            }

            syncParams();
            renderCore(directBuffer_.data(), length);
            for (int i = 0; i < length; ++i) {
                const auto index = static_cast<std::size_t>(i) * 2u;
                left[pos + i] = static_cast<float>(directBuffer_[index]) * kIntToFloat;
                if (right != nullptr)
                    right[pos + i] =
                        static_cast<float>(directBuffer_[index + 1u]) * kIntToFloat;
            }
            pos = end;
        }

        while (event != midi.end()) {
            const auto message = (*event).getMessage();
            if (isEngineMessage(message))
                feedMessage(midi_, message);
            ++event;
        }
    } else {
        for (const auto metadata : midi) {
            const auto message = metadata.getMessage();
            if (isEngineMessage(message))
                feedMessage(midi_, message);
        }
        syncParams();
        float* left = buffer.getWritePointer(0);
        float* right = channels > 1 ? buffer.getWritePointer(1) : left;
        rateBridge_.process(engine_, left, right, frames);
    }

    midi.clear();
}

juce::AudioProcessorEditor* TypePFm1AudioProcessor::createEditor()
{
    return new juce::GenericAudioProcessorEditor(*this);
}

void TypePFm1AudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto state = apvts_.copyState();
    state.setProperty("stateVersion", kStateVersion, nullptr);
    if (auto xml = state.createXml())
        copyXmlToBinary(*xml, destData);
}

void TypePFm1AudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xml(getXmlFromBinary(data, sizeInBytes));
    if (xml == nullptr)
        return;
    auto state = juce::ValueTree::fromXml(*xml);
    if (!state.isValid() || !state.hasType(apvts_.state.getType()))
        return;
    apvts_.replaceState(state);
    paramsDirty_.store(true, std::memory_order_relaxed);
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new TypePFm1AudioProcessor();
}
