import type { DeliverableStatus, StageStatus } from "../api/types";
import StatusPill from "./StatusPill";

const LOOK: Record<DeliverableStatus, { status: StageStatus; label: string }> = {
  ok: { status: "ok", label: "OK" },
  broken: { status: "fail", label: "Broken" },
  unchecked: { status: "unknown", label: "Not checked" },
};

const DocStatus = ({ status }: { status: DeliverableStatus }) => <StatusPill {...LOOK[status]} />;

export default DocStatus;
