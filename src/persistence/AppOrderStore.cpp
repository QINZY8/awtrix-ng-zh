#include "persistence/AppOrderStore.h"

#include <LittleFS.h>

#include "core/CoreEngine.h"

namespace awtrix {
namespace apporder {

void save(const std::string& json) {
  File f = LittleFS.open("/apploop.json", "w");
  if (!f) return;
  f.print(json.c_str());
  f.close();
}

void load(CoreEngine& engine) {
  File f = LittleFS.open("/apploop.json", "r");
  if (!f) {
    // First boot: no saved arrangement yet. Hide the apps this build does not want in the
    // rotation by default, so a fresh device starts quiet instead of showing everything.
    engine.setAppOrder("{\"disabled\":[\"Battery\"]}");
    return;
  }
  const String content = f.readString();
  f.close();
  engine.setAppOrder(std::string(content.c_str()));
}

}
}
