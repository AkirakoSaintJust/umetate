/* SPDX-License-Identifier: GPL-3.0-only */
/* Milestone 3: render the designed editor to PNG for visual review. */
#include <cmath>
#include <cstdio>
#include <memory>

#include <juce_gui_basics/juce_gui_basics.h>

#include "PluginEditor.h"
#include "PluginProcessor.h"

namespace {

bool saveSnapshot(juce::AudioProcessorEditor& editor, const juce::File& file)
{
    const auto image =
        editor.createComponentSnapshot(editor.getLocalBounds(), true, 1.0f);
    if (!image.isValid())
        return false;
    file.deleteFile();
    juce::FileOutputStream output(file);
    if (!output.openedOk())
        return false;
    juce::PNGImageFormat png;
    return png.writeImageToStream(image, output);
}

} // namespace

int main(int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    const juce::File directory =
        argc > 1 ? juce::File(juce::String(argv[1]))
                 : juce::File::getCurrentWorkingDirectory().getChildFile("snapshots");
    directory.createDirectory();

    TypePFm1AudioProcessor processor;
    processor.setRateAndBufferSizeDetails(44100.0, 256);
    processor.prepareToPlay(44100.0, 256);
    std::unique_ptr<juce::AudioProcessorEditor> editor(processor.createEditor());
    if (editor == nullptr) {
        std::printf("editor snapshot: createEditor failed\n");
        return 1;
    }
    auto* p1editor = dynamic_cast<PluginEditor*>(editor.get());
    if (p1editor == nullptr) {
        std::printf("editor snapshot: wrong editor type\n");
        return 1;
    }
    editor->setSize(1240, 985);
    editor->setVisible(true);

    juce::AudioBuffer<float> buffer(2, 256);
    juce::MidiBuffer midi;
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, static_cast<juce::uint8>(100)), 0);
    auto fill = [&] {
        for (int i = 0; i < 8; ++i) {
            buffer.clear();
            processor.processBlock(buffer, midi);
        }
        p1editor->updateVisualizers();
    };

    fill();
    bool ok = saveSnapshot(*editor, directory.getChildFile("editor-patch.png"));
    p1editor->showTab(1);
    fill();
    ok = saveSnapshot(*editor, directory.getChildFile("editor-operators.png")) && ok;
    p1editor->showTab(2);
    fill();
    ok = saveSnapshot(*editor, directory.getChildFile("editor-fxmod.png")) && ok;
    p1editor->showTab(0);
    fill();
    p1editor->showAlgorithmPicker();
    ok = saveSnapshot(*editor, directory.getChildFile("editor-algorithm.png")) && ok;
    p1editor->closeDialog();
    p1editor->showRenameDialog(false, 0);
    ok = saveSnapshot(*editor, directory.getChildFile("editor-rename.png")) && ok;
    p1editor->closeDialog();

    p1editor->applyAlgorithm(7);
    const auto* algorithm0 = processor.parameters().getRawParameterValue("algorithm.p0");
    if (algorithm0 == nullptr || std::lround(algorithm0->load()) != 7) {
        std::printf("editor snapshot: part 0 algorithm was not applied\n");
        ok = false;
    }
    p1editor->setActivePart(1);
    p1editor->applyAlgorithm(6);
    const auto* algorithm1 = processor.parameters().getRawParameterValue("algorithm.p1");
    if (algorithm1 == nullptr || std::lround(algorithm1->load()) != 6) {
        std::printf("editor snapshot: part 1 algorithm was not applied\n");
        ok = false;
    }
    fill();
    ok = saveSnapshot(*editor, directory.getChildFile("editor-part2.png")) && ok;

    p1editor->togglePartMute(0, true);
    const auto* level0 = processor.parameters().getRawParameterValue("level.p0");
    if (level0 == nullptr || level0->load() > 0.5f) {
        std::printf("editor snapshot: part mute did not set level 0\n");
        ok = false;
    }
    p1editor->togglePartMute(0, false);
    if (level0 == nullptr || level0->load() < 98.5f) {
        std::printf("editor snapshot: part unmute did not restore level\n");
        ok = false;
    }

    editor->setSize(620, 493);
    fill();
    ok = saveSnapshot(*editor, directory.getChildFile("editor-half.png")) && ok;

    std::printf("editor snapshot: %s -> %s\n", ok ? "ok" : "FAIL",
                directory.getFullPathName().toRawUTF8());
    return ok ? 0 : 1;
}
