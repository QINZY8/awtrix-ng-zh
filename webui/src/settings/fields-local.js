// Local fork: fields this branch adds to the upstream screens.
//
// Upstream has no equivalent, so instead of editing settings/fields.js and
// system/fields.js (which upstream changes often) the fork merges its own
// entries into the shared tables right after they are defined. Everything here
// has to be declared before the first render, so this file sits at the end of
// the settings group in manifest.json.

// Scheduled and light-based power control, written by main.cpp.
Object.assign(SYSF, {
  powerOffHour:F('autooff','number','Off at','Scheduled matrix off, hour 0-23. -1 = disabled.',{min:-1,max:23}),
  powerOffMinute:F('autooff','number','Off minute','Minute of the scheduled power off.',{min:0,max:59}),
  powerOnHour:F('autooff','number','On at','Scheduled matrix on, hour 0-23. -1 = disabled.',{min:-1,max:23}),
  powerOnMinute:F('autooff','number','On minute','Minute of the scheduled power on.',{min:0,max:59}),
  lightOnThreshold:F('autooff','number','Light on above','Light level percent above which the matrix turns on. -1 = disabled.',{min:-1,max:100,unit:'%'}),
  lightOffThreshold:F('autooff','number','Light off below','Light level percent below which the matrix turns off. -1 = disabled.',{min:-1,max:100,unit:'%'}),
  randomAppOrder:F('appord','toggle','Random app order','Play apps in random order.'),
});
// Keep them next to the other hardware groups rather than after "Misc".
SYS_GROUPS.splice(SYS_GROUPS.length-1,0,['appord','grpApps','grpAppsH'],
  ['autooff','grpAutoOff','grpAutoOffH']);

// Manual brightness goes up to 200 in this branch (BrightnessPolicy.cpp caps it there).
FIELDS.brightness.max=200;
