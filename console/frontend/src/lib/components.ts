// Display names for pipeline components, as the cost logs name them.
const COMPONENT_LABELS: Record<string, string> = {
  "bulletin-scan": "Bulletin scan",
  "perimeter-scan": "Perimeter scan",
  "documentation-sync": "Documentation sync",
  reporting: "Reporting",
  "program-console": "Program console",
};

export const componentLabel = (component: string): string =>
  COMPONENT_LABELS[component] ?? component;
