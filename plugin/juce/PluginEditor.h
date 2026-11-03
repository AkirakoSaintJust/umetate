/* SPDX-License-Identifier: GPL-3.0-only */
#pragma once

#include <array>
#include <functional>
#include <map>
#include <memory>

#include <juce_audio_processors/juce_audio_processors.h>

#include "PluginProcessor.h"
#include "Widgets.h"

class Header;
class Toolbar;

namespace p1::ui {

class P1Canvas : public juce::Component {
public:
    void paint(juce::Graphics& g) override;
};

class PageBase : public juce::Component {
public:
    ~PageBase() override = default;
    virtual void tick() = 0;
};

} // namespace p1::ui

class PluginEditor : public juce::AudioProcessorEditor, private juce::Timer {
public:
    explicit PluginEditor(TypePFm1AudioProcessor& processor);
    ~PluginEditor() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;

    TypePFm1AudioProcessor& processor() { return processor_; }
    juce::AudioProcessorValueTreeState& state() { return processor_.parameters(); }
    int activePart() const { return activePart_; }
    int activeTab() const { return activeTab_; }

    void setActivePart(int part);
    void showTab(int tab);
    void refreshNames();
    void showAlgorithmPicker();
    void applyAlgorithm(int algorithm);
    void showRenameDialog(bool part, int index);
    void showPartMenu();
    void copyPart(int part);
    void pastePart(int part);
    void initPart(int part);
    void togglePartMute(int part, bool muted);
    void closeDialog();
    void updateVisualizers();

private:
    void buildUi();
    void buildHeader();
    void buildToolbar();
    void buildPage();
    void setSpectroMode(bool spectro);
    void setStatusMessage(const juce::String& message);

    TypePFm1AudioProcessor& processor_;
    p1::ui::P1LookAndFeel lookAndFeel_;
    p1::ui::P1Canvas canvas_;
    std::unique_ptr<Header> header_;
    std::unique_ptr<Toolbar> toolbar_;
    p1::ui::P1TabBar tabs_;
    std::unique_ptr<p1::ui::PageBase> page_;
    std::unique_ptr<p1::ui::P1Dialog> dialog_;
    int activePart_ = 0;
    int activeTab_ = 0;
    bool spectroMode_ = false;
    bool switchingTab_ = false;
    juce::String statusMessage_;
    std::array<int, 2> mutedLevel_{99, 99};
    std::map<juce::String, double> partClipboard_;
};
