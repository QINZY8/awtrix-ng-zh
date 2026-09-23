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
    // A fresh device has no saved order, and the Battery app is meaningless on a
    // board with no battery wired, so it starts the rotation switched off.
    engine.setAppOrder("{\"disabled\":[\"Battery\"]}");
    return;
  }
  const String content = f.readString();
  f.close();
  engine.setAppOrder(std::string(content.c_str()));
}

}
}
