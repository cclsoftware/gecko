/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import {
  ActionsProvider,
  ActionsResult,
} from "resource:///modules/ActionsProvider.sys.mjs";

const lazy = {};
ChromeUtils.defineESModuleGetters(lazy, {
  BrowserWindowTracker: "resource:///modules/BrowserWindowTracker.sys.mjs",
  NimbusFeatures: "resource://nimbus/ExperimentAPI.sys.mjs",
  UrlbarPrefs: "resource:///modules/UrlbarPrefs.sys.mjs",
});

const MIN_SEARCH_PREF = "tabGroups.minSearchLength";

/**
 * A provider that matches the urlbar input to built in actions.
 */
class ProviderTabGroups extends ActionsProvider {
  get name() {
    return "ActionsProviderTabGroups";
  }

  isActive(queryContext) {
    return (
      lazy.NimbusFeatures.tabGroups.getVariable("enabled") &&
      !queryContext.searchMode &&
      queryContext.trimmedSearchString.length < 50 &&
      queryContext.trimmedSearchString.length >=
        lazy.UrlbarPrefs.get(MIN_SEARCH_PREF)
    );
  }

  async queryActions(queryContext) {
    let gBrowser = lazy.BrowserWindowTracker.getTopWindow().gBrowser;
    let input = queryContext.trimmedLowerCaseSearchString;
    let results = [];

    for (let group of gBrowser.getAllTabGroups()) {
      let label = group.attributes.label.value.toLowerCase();
      if (label.startsWith(input)) {
        results.push(
          new ActionsResult({
            key: label,
            icon: "chrome://browser/skin/tabbrowser/tab-groups.svg",
            l10nId: "urlbar-result-action-search-tabgroups",
            l10nArgs: { group: label },
            onPick: (_queryContext, _controller) => {
              this.openGroup(group);
            },
            dataset: { color: group.color },
          })
        );
      }
    }

    return results;
  }

  openGroup(group) {
    group.ownerGlobal.gBrowser.selectedTab = group.tabs[0];
    group.ownerGlobal.focus();
  }
}

export var ActionsProviderTabGroups = new ProviderTabGroups();
