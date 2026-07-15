#!/usr/bin/env sed
# Convert `pkg>=X.Y` into `pkg==X.Y` so pip-audit can pin exact versions
# without invoking pip's resolver.
s/^\([A-Za-z0-9_.-]\+\)>=\([0-9][^ ]*\)\(\s*$\)/\1==\2\3/
