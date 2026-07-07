import "i18next";

import type { defaultNS, resources } from "./index";

// Give `t()` typed keys from the English resources (the source of truth).
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: typeof defaultNS;
    resources: (typeof resources)["en"];
  }
}
